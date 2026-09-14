import { expect, test as base, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { RestartRuntime } from './restartRuntime'
import { importAssessmentPackage, originalAssessmentPackage, type AssessmentPackage } from './assessmentTestData'
import type { AssessmentGradingResult, AttemptSnapshot, AttemptResponses } from '../../packages/contracts/generated/api-types'
const test = base.extend<{ runtime: RestartRuntime }>({
  runtime: async ({}, use) => { const runtime = await RestartRuntime.start(); try { await use(runtime) } finally { await runtime.close() } },
  page: async ({ runtime, playwright }, use) => { const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; await runtime.authenticateOnly(page); await use(page) },
})
async function preview(page: Page, prefix: string, profile: AssessmentPackage['profile'] = 'author') {
  const fixture = originalAssessmentPackage(prefix, profile)
  const imported = await importAssessmentPackage(page, fixture)
  await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  await page.goto(`${new URL(page.url()).origin}/?reader=${encodeURIComponent(JSON.stringify({ course: fixture.course, lesson: fixture.lesson }))}`)
  await expect(page.locator('.real-reader > h1')).toBeVisible()
  await page.getByRole('navigation', { name: '学习主导航', exact: true }).getByRole('button', { name: '测试题', exact: true }).click()
  const entry = page.locator('.assessment-directory details').first()
  await entry.locator('summary').click()
  await entry.getByRole('button', { name: /^查看测试范围：/ }).click()
  await expect(page.getByRole('heading', { name: '范围与内容状态', exact: true })).toBeVisible()
  return fixture
}
async function start(page: Page, prefix: string, mode: 'independent' | 'open_book' | 'assisted' = 'independent') {
  const fixture = await preview(page, prefix)
  return begin(page, fixture, mode)
}
async function begin(page: Page, fixture: AssessmentPackage, mode: 'independent' | 'open_book' | 'assisted' = 'independent') {
  await page.getByRole('radio', { name: { independent: '独立测试', open_book: '开卷测试', assisted: '辅助测试' }[mode], exact: true }).check()
  await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
  const creating = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith(`/assessments/${fixture.assessment.id}/attempts`))
  await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
  const response = await creating; expect(response.status()).toBe(201)
  const attempt: AttemptSnapshot = await response.json()
  await saved(page)
  return { fixture, attempt }
}
async function saved(page: Page) { await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible(); await expect(page.getByText('本机草稿存储可用', { exact: true })).toBeVisible() }
async function question(page: Page, index: number) { await page.getByRole('navigation', { name: '本次测试题目', exact: true }).getByRole('button', { name: new RegExp(`^第 ${index} 题`) }).click() }
async function snapshot(page: Page, id: string): Promise<AttemptSnapshot> { const response = await page.request.get(`/api/v1/attempts/${id}`); expect(response.status()).toBe(200); return response.json() }
async function responses(page: Page, id: string): Promise<AttemptResponses> { const response = await page.request.get(`/api/v1/attempts/${id}/responses`); expect(response.status()).toBe(200); return response.json() }

test('real unreviewed independent assessment saves five types and submits without fabricated grades or answer calls', async ({ page }, info) => {
  const errors: string[] = [], answers: string[] = [], resultReads: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  page.on('request', request => { if (/\/(solutions|grades)(?:\?|$)/.test(request.url())) answers.push(request.url()); if (/\/result(?:\?|$)/.test(request.url())) resultReads.push(request.url()) })
  const { attempt, fixture } = await start(page, 'nativeassessmentall')
  expect(attempt.preflight.grading.needs_review_count).toBe(5); expect(attempt.grading_status).toBe('not_graded'); expect(attempt.deadline_at).toBeNull()
  expect(attempt.policy).toMatchObject({ mode: 'independent', tutor_scope: 'operation_help_only', allow_web: false, allow_materials: false })
  await expect(page.getByRole('heading', { name: 'Agent · 固定操作帮助', exact: true })).toBeVisible()
  await expect(page.getByLabel('问题草稿', { exact: true })).toHaveCount(0)
  await page.getByRole('radio', { name: '4', exact: true }).focus()
  await page.keyboard.press('ArrowDown')
  await expect(page.getByRole('radio', { name: '5', exact: true })).toBeChecked()
  for (const [index, answer] of [[2, '测试加法'], [3, '0.5 m'], [4, '2+3=5'], [5, 'x+x']] as const) {
    await question(page, index); await page.getByLabel(`第 ${index} 题答案`, { exact: true }).fill(answer)
    await page.getByLabel(`第 ${index} 题推导步骤`, { exact: true }).fill(`测试合成步骤 ${index} 🧠 é`)
  }
  await saved(page)
  const before = await responses(page, attempt.id)
  expect(before.responses.map(item => item.question_id).sort()).toEqual(fixture.questions.map(ref => ref.id).sort())
  await page.reload(); await saved(page)
  await expect(page.getByLabel('第 5 题答案', { exact: true })).toHaveValue('x+x')
  await expect(page.getByLabel('第 5 题推导步骤', { exact: true })).toBeFocused()
  await question(page, 1)
  await expect(page.locator('.practice-stem svg').first()).toBeVisible()
  await page.screenshot({ path: info.outputPath('assessment-independent-active-1440.png') })
  expect(resultReads).toEqual([])
  await page.getByRole('button', { name: '提交本次测试', exact: true }).click()
  const sending = page.waitForResponse(value => value.url().endsWith(`/attempts/${attempt.id}/submit`))
  await page.getByRole('dialog', { name: '确认提交测试', exact: true }).getByRole('button', { name: '确认提交已保存作答', exact: true }).click()
  expect((await sending).status()).toBe(202)
  await expect(page.getByRole('heading', { name: '测试结束状态', exact: true })).toBeVisible()
  await expect.poll(async () => (await snapshot(page, attempt.id)).status).toBe('needs_review')
  const ended = await snapshot(page, attempt.id)
  expect(ended.grading_status).toBe('needs_review'); expect(ended.submitted_at).not.toBeNull()
  const resultResponse = await page.request.get(`/api/v1/attempts/${attempt.id}/result`); expect(resultResponse.status()).toBe(200)
  const result: AssessmentGradingResult = await resultResponse.json()
  expect(result.status).toBe('needs_review'); expect(result.items).toHaveLength(5); expect(result.items.every(item => item.score === null && item.solution_markdown == null)).toBe(true)
  expect((await responses(page, attempt.id)).responses).toEqual(before.responses)
  await expect(page.getByRole('radio', { name: '5', exact: true })).toBeDisabled()
  expect(answers).toEqual([])
  await page.setViewportSize({ width: 390, height: 844 })
  await page.locator('.practice-submit').scrollIntoViewIfNeeded()
  await expect(page.locator('.practice-submit > p')).toBeInViewport()
  expect(await page.locator('.assessment-scroll').evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  await page.screenshot({ path: info.outputPath('assessment-submitted-390.png') })
  expect(errors).toEqual([])
})

test('open-book and assisted freeze actual policies; explicit abandon retains saved answers and yields no score', async ({ page }) => {
  const { attempt } = await start(page, 'nativeassessmentopen', 'open_book')
  expect(attempt.policy).toMatchObject({ mode: 'open_book', allow_materials: true, allow_web: false, tutor_scope: 'operation_help_only' })
  await expect(page.getByRole('heading', { name: 'Agent · 固定操作帮助', exact: true })).toBeVisible()
  await question(page, 2); await page.getByLabel('第 2 题答案', { exact: true }).fill('放弃前已保存的原创答案'); await saved(page)
  const before = await responses(page, attempt.id)
  await page.getByRole('button', { name: '放弃本次测试', exact: true }).click()
  const abandoning = page.waitForResponse(value => value.url().endsWith(`/attempts/${attempt.id}/abandon`))
  await page.getByRole('button', { name: '确认放弃并保留本机候选', exact: true }).click()
  expect((await abandoning).status()).toBe(200)
  expect((await snapshot(page, attempt.id)).status).toBe('abandoned')
  expect((await responses(page, attempt.id)).responses).toEqual(before.responses)
  await expect(page.locator('.assessment-content')).toContainText('不计为独立测试零分')
  const { attempt: assisted } = await start(page, 'nativeassessmentassist', 'assisted')
  expect(assisted.policy).toMatchObject({ mode: 'assisted', allow_materials: true, allow_web: false, tutor_scope: 'academic' })
  await expect(page.getByText('未配置模型', { exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '发送 ↑', exact: true })).toBeDisabled()
})

test('two profiles retain a real server CAS conflict with three-way comparison and reject forged same-identity parent', async ({ page, browser }) => {
  const { attempt, fixture } = await start(page, 'nativeassessmentcas', 'assisted')
  await question(page, 2); await page.getByLabel('第 2 题答案', { exact: true }).fill('测试共同基准'); await saved(page)
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  const other = await browser.newContext({ baseURL: new URL(page.url()).origin, storageState: await page.context().storageState() })
  let release!: () => void
  try {
    const second = await other.newPage(); await second.goto(page.url()); await saved(second); await question(second, 2)
    let entered!: () => void
    const held = new Promise<void>(resolve => { release = resolve }), started = new Promise<void>(resolve => { entered = resolve })
    await page.route(`**/api/v1/attempts/${attempt.id}/responses`, async route => { if (route.request().method() !== 'PUT') { await route.continue(); return }; entered(); await held; await route.continue() })
    await page.getByLabel('第 2 题答案', { exact: true }).fill('A测试候选'); await started
    await second.getByLabel('第 2 题答案', { exact: true }).fill('B测试候选'); await saved(second)
    const rejected = page.waitForResponse(value => value.request().method() === 'PUT' && value.url().endsWith(`/attempts/${attempt.id}/responses`))
    release(); expect((await rejected).status()).toBe(412)
    const comparison = page.locator('.practice-comparison'); await expect(comparison).toContainText('测试共同基准'); await expect(comparison).toContainText('A测试候选'); await expect(comparison).toContainText('B测试候选')
    await page.unroute(`**/api/v1/attempts/${attempt.id}/responses`)
    await page.getByRole('button', { name: '保留本页作答并采用新基准', exact: true }).click(); await saved(page)
    expect((await responses(page, attempt.id)).responses[0].answer).toBe('A测试候选')
    const baseline = await page.request.get('/api/v1/workbench/session').then(value => value.json())
    const target = { assessment_ref: fixture.assessment, course_ref: { ...fixture.course, sha256: '0'.repeat(64) }, attempt_id: attempt.id }
    await page.evaluate(href => { history.pushState(null, '', href); dispatchEvent(new PopStateEvent('popstate')) }, `/?assessment=${encodeURIComponent(JSON.stringify(target))}`)
    await expect(page.getByRole('heading', { name: '无法打开此精确链接', exact: true })).toBeVisible()
    await expect(page.locator('.assessment-content')).toHaveCount(0)
    const after = await page.request.get('/api/v1/workbench/session').then(value => value.json())
    expect(after.tabs).toEqual(baseline.tabs); expect(after.course_ref).toEqual(baseline.course_ref)
  } finally { release?.(); await other.close() }
})

test('missing private binding visibly blocks start instead of fabricating a usable test', async ({ page }) => {
  await preview(page, 'nativeassessmentmissing', 'learner')
  await expect(page.locator('.assessment-facts')).toContainText('缺失 5')
  await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
  await expect(page.getByRole('button', { name: '明确开始本次测试', exact: true })).toBeDisabled()
})

test('two pages preserve independent local CAS candidates; a later submitted snapshot never accepts restored edits', async ({ page }, info) => {
  let releaseResult = () => {}, releaseRefresh = () => {}
  const { attempt } = await start(page, 'nativeassessmentlocal', 'assisted')
  await question(page, 2); await page.getByLabel('第 2 题答案', { exact: true }).fill('本机测试共同基准'); await saved(page)
  const before = await responses(page, attempt.id), pattern = `**/api/v1/attempts/${attempt.id}/responses`
  const denyWrites = async (route: import('../../apps/web/node_modules/@playwright/test/index.mjs').Route) => { if (route.request().method() === 'PUT') await route.abort('internetdisconnected'); else await route.continue() }
  await page.route(pattern, denyWrites)
  await page.getByLabel('第 2 题答案', { exact: true }).fill('A测试本机候选 🧠')
  await expect(page.getByText('作答尚未确认同步', { exact: true })).toBeVisible()
  await expect(page.getByText('本机草稿存储可用', { exact: true })).toBeVisible()
  const second = await page.context().newPage()
  await second.route(pattern, denyWrites)
  try {
    await second.goto(page.url())
    await second.getByRole('button', { name: '恢复这份本机测试作答', exact: true }).click()
    await expect(second.getByLabel('第 2 题答案', { exact: true })).toHaveValue('A测试本机候选 🧠')
    await expect(second.getByText('作答尚未确认同步', { exact: true })).toBeVisible()
    await second.getByLabel('第 2 题答案', { exact: true }).fill('B测试本机候选 é')
    const comparison = page.locator('.practice-comparison')
    await expect(comparison).toContainText('本机测试共同基准'); await expect(comparison).toContainText('A测试本机候选 🧠'); await expect(comparison).toContainText('B测试本机候选 é')
    // The still-open peer owns its unsynced branch and is allowed to retain it
    // again after another page resolves a conflict. Explicitly close that safe
    // branch before selecting under one remaining writer; never discard it.
    await expect(second.getByText('本机草稿存储可用', { exact: true })).toBeVisible()
    await second.locator('.object-tab.active .tab-close').click()
    await second.getByRole('dialog', { name: '保留未同步测试作答', exact: true }).getByRole('button', { name: '保留本机测试作答并关闭', exact: true }).click()
    await expect(second.getByRole('heading', { name: '本次测试作答', exact: true })).toHaveCount(0)
    await second.close()
    const choice = page.locator('.practice-recovery details').filter({ hasText: 'A测试本机候选 🧠' }).first()
    await choice.getByRole('button', { name: /采用本机候选/ }).click()
    await expect(page.getByRole('heading', { name: '本机测试作答冲突', exact: true })).toHaveCount(0)
    await expect(page.getByText('本机草稿存储可用', { exact: true })).toBeVisible()
    const href = page.url()
    await page.locator('.object-tab.active .tab-close').click()
    const closing = page.getByRole('dialog', { name: '保留未同步测试作答', exact: true })
    await expect(closing.getByRole('button', { name: '保留本机测试作答并关闭', exact: true })).toBeEnabled()
    await closing.getByRole('button', { name: '返回测试作答', exact: true }).click()
    await expect(page.getByLabel('第 2 题答案', { exact: true })).toHaveValue('A测试本机候选 🧠')
    await page.locator('.object-tab.active .tab-close').click()
    await page.getByRole('button', { name: '保留本机测试作答并关闭', exact: true }).click()
    await second.close()
    await expect.poll(async () => await page.getByText('✓ UI 会话已保存').count() > 0 || await page.getByRole('button', { name: '采用本地会话并重新保存', exact: true }).count() > 0).toBe(true)
    if (await page.getByRole('button', { name: '采用本地会话并重新保存', exact: true }).count()) await page.getByRole('button', { name: '采用本地会话并重新保存', exact: true }).click()
    await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
    const token: { csrf_token: string } = await page.request.get('/api/v1/session').then(value => value.json())
    const current = await snapshot(page, attempt.id)
    const receipt = await page.request.post(`/api/v1/attempts/${attempt.id}/submit`, { headers: { Origin: new URL(page.url()).origin, 'X-CSRF-Token': token.csrf_token, 'Idempotency-Key': crypto.randomUUID() }, data: { expected_revision: current.revision } })
    expect(receipt.status()).toBe(202)
    expect((await receipt.json() as AttemptSnapshot).status).toBe('submitted')
    // Grading legitimately advances Attempt.revision after submit. Pin the real
    // completed worker state before checking that restoring drafts cannot edit it.
    await expect.poll(async () => (await snapshot(page, attempt.id)).status).toBe('needs_review')
    const ended = await snapshot(page, attempt.id)
    let resultCaptured = () => {}, refreshStarted = () => {}, resultReleased = false
    const resultReady = new Promise<void>(resolve => { resultCaptured = resolve })
    const resultRelease = new Promise<void>(resolve => { releaseResult = resolve })
    const refreshReady = new Promise<void>(resolve => { refreshStarted = resolve })
    const refreshRelease = new Promise<void>(resolve => { releaseRefresh = resolve })
    await page.route(`**/api/v1/attempts/${attempt.id}/result`, async route => {
      const actual = await route.fetch(); expect(actual.status()).toBe(200)
      if (!resultReleased) { resultCaptured(); await resultRelease }
      await route.fulfill({ response: actual })
    })
    await page.route(`**/api/v1/attempts/${attempt.id}`, async route => {
      const actual = await route.fetch()
      if (resultReleased) { refreshStarted(); await refreshRelease }
      await route.fulfill({ response: actual })
    })
    await page.exposeFunction('releaseAssessmentResult', () => { resultReleased = true; releaseResult() })
    await page.goto(href); await resultReady
    const restoring = page.getByRole('button', { name: '恢复这份本机测试作答', exact: true })
    await expect(restoring).toBeEnabled()
    await restoring.scrollIntoViewIfNeeded()
    await restoring.evaluate(button => {
      const probe = { pointerdown: false, pointerup: false, clicks: 0 }
      Object.assign(window, { assessmentPointerProbe: probe })
      button.addEventListener('pointerdown', () => { probe.pointerdown = true; void (window as unknown as { releaseAssessmentResult: () => Promise<void> }).releaseAssessmentResult() }, { once: true })
      document.addEventListener('pointerup', () => { probe.pointerup = true }, { once: true, capture: true })
      button.addEventListener('click', () => { probe.clicks++ })
    })
    // Release a genuine result during an ordinary pointer gesture, and hold its
    // passive refresh until pointerup. No response body or parsed grade is mocked.
    const bounds = (await restoring.boundingBox())!
    expect(await restoring.evaluate(button => { const box = button.getBoundingClientRect(); return button.contains(document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2)) })).toBe(true)
    await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2)
    await page.mouse.down(); await refreshReady
    await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => resolve())))
    const disabledBeforePointerUp = await restoring.evaluate(button => (button as HTMLButtonElement).disabled)
    await page.mouse.up()
    const pointer = await page.evaluate(() => (window as unknown as { assessmentPointerProbe: { pointerdown: boolean; pointerup: boolean; clicks: number } }).assessmentPointerProbe)
    releaseRefresh()
    await info.attach('grading-refresh-pointer', { body: JSON.stringify({ ...pointer, disabledBeforePointerUp }), contentType: 'application/json' })
    await expect(page.getByRole('heading', { name: '服务端测试作答冲突 · 三方比较', exact: true })).toBeVisible()
    expect({ ...pointer, disabledBeforePointerUp }).toEqual({ pointerdown: true, pointerup: true, clicks: 1, disabledBeforePointerUp: false })
    await page.getByRole('button', { name: '保留本页作答并采用新基准', exact: true }).click()
    await expect(page.getByLabel('第 2 题答案', { exact: true })).toHaveValue('A测试本机候选 🧠')
    await expect(page.getByLabel('第 2 题答案', { exact: true })).toBeDisabled()
    await page.unroute(pattern)
    await page.getByRole('button', { name: '重新读取测试状态', exact: true }).click()
    expect((await responses(page, attempt.id)).responses).toEqual(before.responses)
    expect((await snapshot(page, attempt.id)).revision).toBe(ended.revision)
    await page.getByRole('heading', { name: '服务端测试作答冲突 · 三方比较', exact: true }).scrollIntoViewIfNeeded()
    await page.screenshot({ path: info.outputPath('assessment-terminal-local-candidate-1440.png') })
  } finally { releaseResult(); releaseRefresh(); await second.close() }
})

test('late redacted Workbench save uses its original ETag and retains hidden selection after explicit three-way choice', async ({ page }) => {
  const fixture = await preview(page, 'nativeassessmentprojection')
  const origin = new URL(page.url()).origin
  await page.goto(`${origin}/?reader=${encodeURIComponent(JSON.stringify({ course: fixture.course, lesson: fixture.lesson }))}`)
  await expect(page.locator('.real-reader > h1')).toBeVisible()
  await page.getByText('原始 Markdown 与精确选文', { exact: true }).click()
  const source = page.getByRole('textbox', { name: /^原始 Markdown：/ })
  await source.focus(); await page.keyboard.press('Control+A')
  await expect(page.getByText('已从原始 Markdown 建立准确选文。', { exact: true })).toBeVisible()
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  const before: import('../../packages/contracts/generated/types').WorkbenchSession = await page.request.get('/api/v1/workbench/session').then(value => value.json())
  const readerTab = before.tabs.find(tab => tab.id === before.active_tab_id)!
  expect(readerTab.context.selection?.exact_quote).toBeTruthy()
  await page.goto(`${origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
  const { attempt } = await begin(page, fixture)
  await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  const projected: import('../../packages/contracts/generated/types').WorkbenchSession = await page.request.get('/api/v1/workbench/session').then(value => value.json())
  expect(projected.tabs.every(tab => !tab.context.selection)).toBe(true)
  let release!: () => void, entered!: () => void, capturedEtag: string | undefined
  const held = new Promise<void>(resolve => { release = resolve }), started = new Promise<void>(resolve => { entered = resolve })
  await page.route('**/api/v1/workbench/session', async route => { if (route.request().method() !== 'PUT') { await route.continue(); return }; capturedEtag = route.request().headers()['if-match']; entered(); await held; await route.continue() })
  try {
    await page.getByRole('button', { name: '切换导航栏', exact: true }).click(); await started
    expect(capturedEtag).toBeTruthy()
    const auth: { csrf_token: string } = await page.request.get('/api/v1/session').then(value => value.json())
    const receipt = await page.request.post(`/api/v1/attempts/${attempt.id}/submit`, { headers: { Origin: origin, 'X-CSRF-Token': auth.csrf_token, 'Idempotency-Key': crypto.randomUUID() }, data: { expected_revision: attempt.revision } })
    expect(receipt.status()).toBe(202)
    const fullRead = await page.request.get('/api/v1/workbench/session')
    expect(fullRead.headers().etag).not.toBe(capturedEtag)
    const full: import('../../packages/contracts/generated/types').WorkbenchSession = await fullRead.json()
    expect(full.tabs.find(tab => tab.id === readerTab.id)?.context.selection).toEqual(readerTab.context.selection)
    const rejected = page.waitForResponse(value => value.request().method() === 'PUT' && value.url().endsWith('/workbench/session'))
    release(); expect((await rejected).status()).toBe(412)
    await expect(page.getByRole('region', { name: '会话三方比较', exact: true })).toBeVisible()
    await page.unroute('**/api/v1/workbench/session')
    await page.getByRole('button', { name: '采用本地会话并重新保存', exact: true }).click()
    await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
    const retained: import('../../packages/contracts/generated/types').WorkbenchSession = await page.request.get('/api/v1/workbench/session').then(value => value.json())
    expect(retained.nav_collapsed).toBe(true)
    expect(retained.tabs.find(tab => tab.id === readerTab.id)?.context.selection).toEqual(readerTab.context.selection)
    expect(['submitted', 'grading', 'needs_review']).toContain((await snapshot(page, attempt.id)).status)
  } finally { release?.() }
})

test('a genuine solution response held in flight cannot appear after another page starts an open-book assessment', async ({ page }) => {
  const fixture = await preview(page, 'nativeassessmentlatehelp')
  const origin = new URL(page.url()).origin
  await page.goto(`${origin}/?practice=${encodeURIComponent(JSON.stringify({ practice_ref: fixture.practice, course_ref: fixture.course, lesson_ref: fixture.lesson }))}`)
  const creating = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/practice/sessions'))
  await page.getByRole('button', { name: '开始此练习', exact: true }).click()
  expect((await creating).status()).toBe(201)
  const practice: import('../../packages/contracts/generated/api-types').PracticeSession = await (await creating).json()
  await saved(page)
  let release!: () => void, accepted!: () => void
  const held = new Promise<void>(resolve => { release = resolve }), received = new Promise<void>(resolve => { accepted = resolve })
  let status = 0
  await page.route(`**/api/v1/practice/sessions/${practice.id}/solutions`, async route => { const response = await route.fetch(); status = response.status(); accepted(); await held; await route.fulfill({ response }) })
  const second = await page.context().newPage()
  try {
    await page.getByRole('button', { name: '明确展开参考解答并记录暴露', exact: true }).click()
    await received; expect(status).toBe(200)
    await expect(page.locator('.practice-solution')).toHaveCount(0)
    await second.goto(`${origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
    const { attempt } = await begin(second, fixture, 'open_book')
    expect(attempt.preflight.prior_seen.questions[0].state).toBe('seen')
    const returned = page.waitForResponse(value => value.url().endsWith(`/practice/sessions/${practice.id}/solutions`))
    release(); expect((await returned).status()).toBe(200)
    await page.unroute(`**/api/v1/practice/sessions/${practice.id}/solutions`)
    await expect(page.locator('.practice-solution')).toHaveCount(0)
    await expect(page.getByRole('button', { name: '重新获取已释放的参考解答', exact: true })).toBeVisible()
    const blocked = page.waitForResponse(value => value.url().endsWith(`/practice/sessions/${practice.id}/solutions`))
    await page.getByRole('button', { name: '重新获取已释放的参考解答', exact: true }).click()
    expect((await blocked).status()).toBe(409)
    await expect(page.locator('.practice-solution')).toHaveCount(0)
    const auth: { csrf_token: string } = await second.request.get('/api/v1/session').then(value => value.json())
    expect((await second.request.post(`/api/v1/attempts/${attempt.id}/abandon`, { headers: { Origin: origin, 'X-CSRF-Token': auth.csrf_token, 'Idempotency-Key': crypto.randomUUID() }, data: { expected_revision: attempt.revision } })).status()).toBe(200)
  } finally { release?.(); await second.close() }
})
