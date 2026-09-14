import { expect, test, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { writeFileSync } from 'node:fs'
import type { WorkbenchSession } from '../../packages/contracts/generated/types'
import type { AttemptSnapshot, AttemptResponses, PracticeSessionCreated } from '../../packages/contracts/generated/api-types'
import { RestartRuntime } from './restartRuntime'
import { originalAssessmentPackage, importAssessmentPackage, type AssessmentPackage } from './assessmentTestData'

async function workbench(page: Page): Promise<WorkbenchSession> {
  const response = await page.request.get('/api/v1/workbench/session')
  expect(response.status()).toBe(200)
  return response.json()
}
async function attempt(page: Page, id: string): Promise<AttemptSnapshot> {
  const response = await page.request.get(`/api/v1/attempts/${id}`)
  expect(response.status()).toBe(200)
  return response.json()
}
async function responses(page: Page, id: string): Promise<AttemptResponses> {
  const response = await page.request.get(`/api/v1/attempts/${id}/responses`)
  expect(response.status()).toBe(200)
  return response.json()
}
async function csrf(page: Page) {
  const response = await page.request.get('/api/v1/session')
  expect(response.status()).toBe(200)
  return (await response.json()).csrf_token as string
}
async function start(page: Page, runtime: RestartRuntime, fixture: AssessmentPackage) {
  const target = { assessment_ref: fixture.assessment, course_ref: fixture.course }
  await page.goto(`${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify(target))}`)
  await page.getByRole('radio', { name: '独立测试', exact: true }).check()
  await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
  const creating = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/api/v1/assessments/${fixture.assessment.id}/attempts`))
  await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
  const created = await creating
  expect(created.status()).toBe(201)
  const value: AttemptSnapshot = await created.json()
  await expect(page.getByRole('heading', { name: '本次测试作答', exact: true })).toBeVisible()
  await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
  return value
}

test('same assessment instance rejects forged course and assessment hashes while its independent policy remains active', async ({ playwright }, info) => {
  test.setTimeout(90_000)
  const runtime = await RestartRuntime.start(), fixture = originalAssessmentPackage('assessmentidentity')
  try {
    const browser = await runtime.openBrowser(playwright.chromium), page = browser.pages()[0]
    await runtime.authenticateOnly(page)
    const imported = await importAssessmentPackage(page, fixture)
    await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    await page.goto(`${runtime.origin}/?reader=${encodeURIComponent(JSON.stringify({ course: fixture.course, lesson: fixture.lesson }))}`)
    await page.getByText('原始 Markdown 与精确选文', { exact: true }).click()
    const original = page.getByLabel('原始 Markdown：数量、步骤与单位', { exact: true })
    const originalBody = await original.inputValue()
    await original.focus()
    await expect(original).toBeFocused()
    await page.keyboard.press('Control+A')
    await expect(page.getByRole('button', { name: '为当前选文记笔记', exact: true })).toBeEnabled()
    await expect.poll(async () => {
      const current = await workbench(page)
      return current.tabs.find(tab => tab.id === current.active_tab_id)?.context.selection?.exact_quote
    }).toBe(originalBody)
    const reading = await workbench(page), readingTab = reading.tabs.find(tab => tab.id === reading.active_tab_id)!
    const created = await start(page, runtime, fixture)
    await expect.poll(async () => {
      const current = await workbench(page)
      return current.tabs.find(tab => tab.id === current.active_tab_id)?.context.attempt_id
    }).toBe(created.id)
    const before = await workbench(page), active = before.tabs.find(tab => tab.id === before.active_tab_id)!
    expect(before.tabs.every(tab => tab.context.selection === null)).toBe(true)
    const frozen = await attempt(page, created.id)
    const target = { assessment_ref: fixture.assessment, course_ref: fixture.course, attempt_id: created.id }
    for (const forged of [
      { ...target, course_ref: { ...fixture.course, sha256: '0'.repeat(64) } },
      { ...target, assessment_ref: { ...fixture.assessment, sha256: '0'.repeat(64) } },
    ]) {
      await page.goto(`${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify(forged))}`)
      await expect(page.getByRole('heading', { name: '无法打开此精确链接', exact: true })).toBeVisible()
      const retained = await workbench(page)
      expect(retained.course_ref).toEqual(before.course_ref)
      expect(retained.active_tab_id).toBe(active.id)
      expect(retained.tabs.find(tab => tab.id === active.id)?.context).toEqual(active.context)
      expect(await attempt(page, created.id)).toEqual(frozen)
      await page.getByRole('button', { name: '返回原标签', exact: true }).click()
      await expect(page.getByRole('heading', { name: '本次测试作答', exact: true })).toBeVisible()
    }
    expect((await page.request.get(`/api/v1/lessons/${fixture.lesson.id}?revision=1`)).status()).toBe(409)
    const redactedResponse = await page.request.get('/api/v1/workbench/session')
    const redacted: WorkbenchSession = await redactedResponse.json(), etag = redactedResponse.headers()['etag']
    expect(etag).toBeTruthy()
    const abandoning = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/api/v1/attempts/${created.id}/abandon`))
    await page.getByRole('button', { name: '放弃本次测试', exact: true }).click()
    await page.getByRole('dialog', { name: '确认放弃测试', exact: true }).getByRole('button', { name: '确认放弃并保留本机候选', exact: true }).click()
    expect((await abandoning).status()).toBe(200)
    // A delayed save based on a real redacted HTTP response cannot clear the
    // earlier source selection after the active policy ends.
    const late = await page.request.put('/api/v1/workbench/session', { headers: { Origin: runtime.origin, 'X-CSRF-Token': await csrf(page), 'If-Match': etag }, data: { expected_revision: redacted.revision, session: redacted } })
    expect(late.status()).toBe(412)
    const after = await workbench(page)
    expect(after.tabs.find(tab => tab.id === readingTab.id)?.context.selection).toEqual(readingTab.context.selection)
    writeFileSync(info.outputPath('assessment-frozen-navigation.json'), JSON.stringify({
      scope: 'Actual imported original fixture and UI-created independent attempt; invalid links never replace its frozen context.',
      attempt_id: created.id, same_tab_identity: active.id, context: active.context,
      forged_course_hash_rejected: true, forged_assessment_hash_rejected: true,
      own_active_attempt_readable: true, material_direct_request_blocked: true,
      prior_source_selection_hidden_while_active: true, late_redacted_save_rejected: true,
      original_source_selection_retained_after_abandon: true,
    }, null, 2))
  } finally { await runtime.close() }
})

test('actual browser and API restarts retain independent drafts and keep old solution receipts protected after submission', async ({ playwright }, info) => {
  test.setTimeout(150_000)
  const runtime = await RestartRuntime.start(), fixture = originalAssessmentPackage('assessmentrestart')
  const errors: string[] = [], automaticSolutions: string[] = []
  const observe = (page: Page) => {
    page.on('pageerror', error => errors.push(error.message))
    page.on('request', request => { if (/\/practice\/sessions\/[^/]+\/solutions$/.test(request.url())) automaticSolutions.push(request.method()) })
  }
  try {
    const firstBrowser = await runtime.openBrowser(playwright.chromium), page = firstBrowser.pages()[0]
    observe(page)
    await runtime.authenticateOnly(page)
    const imported = await importAssessmentPackage(page, fixture)
    await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    // Explicit adversarial setup through the actual API: obtain a prior practice
    // solution receipt, then prove that its idempotency key never bypasses a test.
    const token = await csrf(page)
    const practiceResponse = await page.request.post('/api/v1/practice/sessions', { headers: { Origin: runtime.origin, 'X-CSRF-Token': token, 'Idempotency-Key': 'prior-practice' }, data: { practice_ref: fixture.practice } })
    expect(practiceResponse.status()).toBe(201)
    const practice: PracticeSessionCreated = await practiceResponse.json()
    const solutionPath = `/api/v1/practice/sessions/${practice.id}/solutions`
    const solutionBody = { question_id: fixture.questions[0].id, expected_revision: practice.revision }
    const reveal = (current: Page, auth: string) => current.request.post(solutionPath, { headers: { Origin: runtime.origin, 'X-CSRF-Token': auth, 'Idempotency-Key': 'prior-solution' }, data: solutionBody })
    expect((await reveal(page, token)).status()).toBe(200)
    const created = await start(page, runtime, fixture)
    expect(created.preflight.grading.status).toBe('unreviewed')
    expect(created.preflight.prior_seen.questions.every(item => item.state === 'seen')).toBe(true)
    expect(created.policy).toMatchObject({ mode: 'independent', allow_web: false, allow_materials: false, tutor_scope: 'operation_help_only' })
    expect((await reveal(page, token)).status()).toBe(409)
    await page.getByRole('navigation', { name: '本次测试题目', exact: true }).getByRole('button', { name: /^第 2 题/ }).click()
    await page.getByLabel('第 2 题答案', { exact: true }).fill('加法交换律')
    await page.getByLabel('第 2 题推导步骤', { exact: true }).fill('先核对运算和交换前后的各项。')
    await expect.poll(async () => (await responses(page, created.id)).responses.find(item => item.question_id === fixture.questions[1].id)?.answer).toBe('加法交换律')
    await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
    const before = await attempt(page, created.id), beforeResponses = await responses(page, created.id)
    const responseRoute = `**/api/v1/attempts/${created.id}/responses`
    await page.route(responseRoute, route => route.request().method() === 'PUT' ? route.abort('internetdisconnected') : route.continue())
    const localAnswer = '独立作答的本机候选 🧠：还需区分结合律。'
    await page.getByLabel('第 2 题答案', { exact: true }).fill(localAnswer)
    await expect(page.getByText('作答尚未确认同步', { exact: true })).toBeVisible()
    await expect(page.getByText('本机草稿存储可用', { exact: true })).toBeVisible()
    await expect.poll(async () => {
      const current = await workbench(page)
      return current.tabs.find(tab => tab.id === current.active_tab_id)?.context.attempt_id
    }).toBe(created.id)
    await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
    const beforeWorkbench = await workbench(page), contextBefore = beforeWorkbench.tabs.find(tab => tab.id === beforeWorkbench.active_tab_id)!.context
    const database = runtime.databaseIdentity(), connection = firstBrowser.browser()
    await runtime.closeBrowser()
    expect(connection?.isConnected()).toBe(false)
    await runtime.restartApiAfterBrowserClosed()
    expect(runtime.databaseIdentity()).toEqual(database)
    const secondBrowser = await runtime.openBrowser(playwright.chromium), restored = secondBrowser.pages()[0]
    observe(restored)
    await restored.route(responseRoute, route => route.request().method() === 'PUT' ? route.abort('internetdisconnected') : route.continue())
    await runtime.authenticateOnly(restored)
    await expect(restored.getByRole('heading', { name: '发现本机未同步测试作答', exact: true })).toBeVisible()
    expect(await attempt(restored, created.id)).toEqual(before)
    expect(await responses(restored, created.id)).toEqual(beforeResponses)
    const restoredWorkbench = await workbench(restored)
    expect(restoredWorkbench.tabs.find(tab => tab.id === restoredWorkbench.active_tab_id)?.context).toEqual(contextBefore)
    await restored.getByRole('button', { name: '恢复这份本机测试作答', exact: true }).click()
    await expect(restored.getByLabel('第 2 题答案', { exact: true })).toHaveValue(localAnswer)
    await expect(restored.getByText('作答尚未确认同步', { exact: true })).toBeVisible()
    expect((await reveal(restored, await csrf(restored))).status()).toBe(409)
    await restored.setViewportSize({ width: 390, height: 844 })
    await restored.getByLabel('第 2 题答案', { exact: true }).scrollIntoViewIfNeeded()
    expect(await restored.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
    expect(await restored.locator('.assessment-scroll').evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1)
    await restored.screenshot({ path: info.outputPath('assessment-restored-independent-390.png') })
    await restored.unroute(responseRoute)
    await restored.getByRole('button', { name: '重新读取测试状态', exact: true }).click()
    await expect.poll(async () => (await responses(restored, created.id)).responses.find(item => item.question_id === fixture.questions[1].id)?.answer).toBe(localAnswer)
    await expect(restored.getByText('服务端作答已保存', { exact: true })).toBeVisible()
    const submitting = restored.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/api/v1/attempts/${created.id}/submit`))
    await restored.getByRole('button', { name: '提交本次测试', exact: true }).click()
    await restored.getByRole('dialog', { name: '确认提交测试', exact: true }).getByRole('button', { name: '确认提交已保存作答', exact: true }).click()
    expect((await submitting).status()).toBe(202)
    const submitted = await attempt(restored, created.id)
    expect(submitted.status).toBe('submitted')
    expect(submitted.grading_status).toBe('not_graded')
    expect((await reveal(restored, await csrf(restored))).status()).toBe(409)
    await runtime.closeBrowser()
    await runtime.restartApiAfterBrowserClosed()
    const thirdBrowser = await runtime.openBrowser(playwright.chromium), finalPage = thirdBrowser.pages()[0]
    observe(finalPage)
    await runtime.authenticateOnly(finalPage)
    expect(await attempt(finalPage, created.id)).toEqual(submitted)
    const finalAuth = await csrf(finalPage)
    const switching = await finalPage.request.post('/api/v1/session/role', { headers: { Origin: runtime.origin, 'X-CSRF-Token': finalAuth, 'Idempotency-Key': 'pending-author-role' }, data: { role: 'author' } })
    expect(switching.status()).toBe(200)
    expect((await reveal(finalPage, await csrf(finalPage))).status()).toBe(409)
    expect((await finalPage.request.get(`/api/v1/lessons/${fixture.lesson.id}?revision=1`)).status()).toBe(200)
    expect(automaticSolutions).toEqual([])
    expect(errors).toEqual([])
    writeFileSync(info.outputPath('actual-assessment-restart.json'), JSON.stringify({
      scope: 'Original author learnpack, explicit prior solution API setup, UI-created independent test, real Chrome closure and two API stop/start cycles without resets.',
      different_api_process_generations: new Set(runtime.generations).size, same_database_inode: runtime.databaseIdentity().inode === database.inode,
      attempt_id: created.id, assessment_ref: fixture.assessment, context: contextBefore,
      original_policy: created.policy, unchanged_active_snapshot_after_restart: true, restored_unsynced_question_index: 2,
      submitted_snapshot_unchanged_after_second_restart: true, grading_status: submitted.grading_status,
      cached_solution_denied_active_and_submitted: true, author_role_does_not_release_pending_answer: true,
      ordinary_material_read_resumes_after_submit: true, automatic_solution_requests: automaticSolutions, runtime_errors: errors,
    }, null, 2))
  } finally { await runtime.close() }
})
