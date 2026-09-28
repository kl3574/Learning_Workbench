# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: assessments.spec.ts >> two pages preserve independent local CAS candidates; a later submitted snapshot never accepts restored edits
- Location: ../../tests/e2e/assessments.spec.ts:145:1

# Error details

```
Error: expect(locator).toContainText(expected) failed

Locator: locator('.practice-comparison')
Expected substring: "本机测试共同基准"
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toContainText" locator('.practice-comparison') with timeout 5000ms
  - waiting for locator('.practice-comparison')

```

# Test source

```ts
  64  |   await expect(page.locator('.practice-stem svg').first()).toBeVisible()
  65  |   await page.screenshot({ path: info.outputPath('assessment-independent-active-1440.png') })
  66  |   expect(resultReads).toEqual([])
  67  |   await page.getByRole('button', { name: '提交本次测试', exact: true }).click()
  68  |   const sending = page.waitForResponse(value => value.url().endsWith(`/attempts/${attempt.id}/submit`))
  69  |   await page.getByRole('dialog', { name: '确认提交测试', exact: true }).getByRole('button', { name: '确认提交已保存作答', exact: true }).click()
  70  |   expect((await sending).status()).toBe(202)
  71  |   await expect(page.getByRole('heading', { name: '测试结束状态', exact: true })).toBeVisible()
  72  |   await expect.poll(async () => (await snapshot(page, attempt.id)).status).toBe('needs_review')
  73  |   const ended = await snapshot(page, attempt.id)
  74  |   expect(ended.grading_status).toBe('needs_review'); expect(ended.submitted_at).not.toBeNull()
  75  |   const resultResponse = await page.request.get(`/api/v1/attempts/${attempt.id}/result`); expect(resultResponse.status()).toBe(200)
  76  |   const result: AssessmentGradingResult = await resultResponse.json()
  77  |   expect(result.status).toBe('needs_review'); expect(result.items).toHaveLength(5); expect(result.items.every(item => item.score === null && item.solution_markdown == null)).toBe(true)
  78  |   expect((await responses(page, attempt.id)).responses).toEqual(before.responses)
  79  |   await expect(page.getByRole('radio', { name: '5', exact: true })).toBeDisabled()
  80  |   expect(answers).toEqual([])
  81  |   await page.setViewportSize({ width: 390, height: 844 })
  82  |   await page.locator('.practice-submit').scrollIntoViewIfNeeded()
  83  |   await expect(page.locator('.practice-submit > p')).toBeInViewport()
  84  |   expect(await page.locator('.assessment-scroll').evaluate(node => node.scrollWidth - node.clientWidth)).toBeLessThanOrEqual(1)
  85  |   expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390)
  86  |   await page.screenshot({ path: info.outputPath('assessment-submitted-390.png') })
  87  |   expect(errors).toEqual([])
  88  | })
  89  | 
  90  | test('open-book and assisted freeze actual policies; explicit abandon retains saved answers and yields no score', async ({ page }) => {
  91  |   const { attempt } = await start(page, 'nativeassessmentopen', 'open_book')
  92  |   expect(attempt.policy).toMatchObject({ mode: 'open_book', allow_materials: true, allow_web: false, tutor_scope: 'operation_help_only' })
  93  |   await expect(page.getByRole('heading', { name: 'Agent · 固定操作帮助', exact: true })).toBeVisible()
  94  |   await question(page, 2); await page.getByLabel('第 2 题答案', { exact: true }).fill('放弃前已保存的原创答案'); await saved(page)
  95  |   const before = await responses(page, attempt.id)
  96  |   await page.getByRole('button', { name: '放弃本次测试', exact: true }).click()
  97  |   const abandoning = page.waitForResponse(value => value.url().endsWith(`/attempts/${attempt.id}/abandon`))
  98  |   await page.getByRole('button', { name: '确认放弃并保留本机候选', exact: true }).click()
  99  |   expect((await abandoning).status()).toBe(200)
  100 |   expect((await snapshot(page, attempt.id)).status).toBe('abandoned')
  101 |   expect((await responses(page, attempt.id)).responses).toEqual(before.responses)
  102 |   await expect(page.locator('.assessment-content')).toContainText('不计为独立测试零分')
  103 |   const { attempt: assisted } = await start(page, 'nativeassessmentassist', 'assisted')
  104 |   expect(assisted.policy).toMatchObject({ mode: 'assisted', allow_materials: true, allow_web: false, tutor_scope: 'academic' })
  105 |   await expect(page.getByText('本地任务 · 明确授权', { exact: true })).toBeVisible()
  106 |   await expect(page.getByRole('button', { name: '创建本次问答任务 ↑', exact: true })).toBeDisabled()
  107 | })
  108 | 
  109 | test('two profiles retain a real server CAS conflict with three-way comparison and reject forged same-identity parent', async ({ page, browser }) => {
  110 |   const { attempt, fixture } = await start(page, 'nativeassessmentcas', 'assisted')
  111 |   await question(page, 2); await page.getByLabel('第 2 题答案', { exact: true }).fill('测试共同基准'); await saved(page)
  112 |   await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  113 |   const other = await browser.newContext({ baseURL: new URL(page.url()).origin, storageState: await page.context().storageState() })
  114 |   let release!: () => void
  115 |   try {
  116 |     const second = await other.newPage(); await second.goto(page.url()); await saved(second); await question(second, 2)
  117 |     let entered!: () => void
  118 |     const held = new Promise<void>(resolve => { release = resolve }), started = new Promise<void>(resolve => { entered = resolve })
  119 |     await page.route(`**/api/v1/attempts/${attempt.id}/responses`, async route => { if (route.request().method() !== 'PUT') { await route.continue(); return }; entered(); await held; await route.continue() })
  120 |     await page.getByLabel('第 2 题答案', { exact: true }).fill('A测试候选'); await started
  121 |     await second.getByLabel('第 2 题答案', { exact: true }).fill('B测试候选'); await saved(second)
  122 |     const rejected = page.waitForResponse(value => value.request().method() === 'PUT' && value.url().endsWith(`/attempts/${attempt.id}/responses`))
  123 |     release(); expect((await rejected).status()).toBe(412)
  124 |     const comparison = page.locator('.practice-comparison'); await expect(comparison).toContainText('测试共同基准'); await expect(comparison).toContainText('A测试候选'); await expect(comparison).toContainText('B测试候选')
  125 |     await page.unroute(`**/api/v1/attempts/${attempt.id}/responses`)
  126 |     await page.getByRole('button', { name: '保留本页作答并采用新基准', exact: true }).click(); await saved(page)
  127 |     expect((await responses(page, attempt.id)).responses[0].answer).toBe('A测试候选')
  128 |     const baseline = await page.request.get('/api/v1/workbench/session').then(value => value.json())
  129 |     const target = { assessment_ref: fixture.assessment, course_ref: { ...fixture.course, sha256: '0'.repeat(64) }, attempt_id: attempt.id }
  130 |     await page.evaluate(href => { history.pushState(null, '', href); dispatchEvent(new PopStateEvent('popstate')) }, `/?assessment=${encodeURIComponent(JSON.stringify(target))}`)
  131 |     await expect(page.getByRole('heading', { name: '无法打开此精确链接', exact: true })).toBeVisible()
  132 |     await expect(page.locator('.assessment-content')).toHaveCount(0)
  133 |     const after = await page.request.get('/api/v1/workbench/session').then(value => value.json())
  134 |     expect(after.tabs).toEqual(baseline.tabs); expect(after.course_ref).toEqual(baseline.course_ref)
  135 |   } finally { release?.(); await other.close() }
  136 | })
  137 | 
  138 | test('missing private binding visibly blocks start instead of fabricating a usable test', async ({ page }) => {
  139 |   await preview(page, 'nativeassessmentmissing', 'learner')
  140 |   await expect(page.locator('.assessment-facts')).toContainText('缺失 5')
  141 |   await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
  142 |   await expect(page.getByRole('button', { name: '明确开始本次测试', exact: true })).toBeDisabled()
  143 | })
  144 | 
  145 | test('two pages preserve independent local CAS candidates; a later submitted snapshot never accepts restored edits', async ({ page }, info) => {
  146 |   let releaseResult = () => {}, releaseRefresh = () => {}
  147 |   const { attempt } = await start(page, 'nativeassessmentlocal', 'assisted')
  148 |   await question(page, 2); await page.getByLabel('第 2 题答案', { exact: true }).fill('本机测试共同基准'); await saved(page)
  149 |   const before = await responses(page, attempt.id), pattern = `**/api/v1/attempts/${attempt.id}/responses`
  150 |   const denyWrites = async (route: import('../../apps/web/node_modules/@playwright/test/index.mjs').Route) => { if (route.request().method() === 'PUT') await route.abort('internetdisconnected'); else await route.continue() }
  151 |   await page.route(pattern, denyWrites)
  152 |   await page.getByLabel('第 2 题答案', { exact: true }).fill('A测试本机候选 🧠')
  153 |   await expect(page.getByText('作答尚未确认同步', { exact: true })).toBeVisible()
  154 |   await expect(page.getByText('本机草稿存储可用', { exact: true })).toBeVisible()
  155 |   const second = await page.context().newPage()
  156 |   await second.route(pattern, denyWrites)
  157 |   try {
  158 |     await second.goto(page.url())
  159 |     await second.getByRole('button', { name: '恢复这份本机测试作答', exact: true }).click()
  160 |     await expect(second.getByLabel('第 2 题答案', { exact: true })).toHaveValue('A测试本机候选 🧠')
  161 |     await expect(second.getByText('作答尚未确认同步', { exact: true })).toBeVisible()
  162 |     await second.getByLabel('第 2 题答案', { exact: true }).fill('B测试本机候选 é')
  163 |     const comparison = page.locator('.practice-comparison')
> 164 |     await expect(comparison).toContainText('本机测试共同基准'); await expect(comparison).toContainText('A测试本机候选 🧠'); await expect(comparison).toContainText('B测试本机候选 é')
      |                              ^ Error: expect(locator).toContainText(expected) failed
  165 |     // The still-open peer owns its unsynced branch and is allowed to retain it
  166 |     // again after another page resolves a conflict. Explicitly close that safe
  167 |     // branch before selecting under one remaining writer; never discard it.
  168 |     await expect(second.getByText('本机草稿存储可用', { exact: true })).toBeVisible()
  169 |     await second.locator('.object-tab.active .tab-close').click()
  170 |     await second.getByRole('dialog', { name: '保留未同步测试作答', exact: true }).getByRole('button', { name: '保留本机测试作答并关闭', exact: true }).click()
  171 |     await expect(second.getByRole('heading', { name: '本次测试作答', exact: true })).toHaveCount(0)
  172 |     await second.close()
  173 |     const choice = page.locator('.practice-recovery details').filter({ hasText: 'A测试本机候选 🧠' }).first()
  174 |     await choice.getByRole('button', { name: /采用本机候选/ }).click()
  175 |     await expect(page.getByRole('heading', { name: '本机测试作答冲突', exact: true })).toHaveCount(0)
  176 |     await expect(page.getByText('本机草稿存储可用', { exact: true })).toBeVisible()
  177 |     const href = page.url()
  178 |     await page.locator('.object-tab.active .tab-close').click()
  179 |     const closing = page.getByRole('dialog', { name: '保留未同步测试作答', exact: true })
  180 |     await expect(closing.getByRole('button', { name: '保留本机测试作答并关闭', exact: true })).toBeEnabled()
  181 |     await closing.getByRole('button', { name: '返回测试作答', exact: true }).click()
  182 |     await expect(page.getByLabel('第 2 题答案', { exact: true })).toHaveValue('A测试本机候选 🧠')
  183 |     await page.locator('.object-tab.active .tab-close').click()
  184 |     await page.getByRole('button', { name: '保留本机测试作答并关闭', exact: true }).click()
  185 |     await second.close()
  186 |     await expect.poll(async () => await page.getByText('✓ UI 会话已保存').count() > 0 || await page.getByRole('button', { name: '采用本地会话并重新保存', exact: true }).count() > 0).toBe(true)
  187 |     if (await page.getByRole('button', { name: '采用本地会话并重新保存', exact: true }).count()) await page.getByRole('button', { name: '采用本地会话并重新保存', exact: true }).click()
  188 |     await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  189 |     const token: { csrf_token: string } = await page.request.get('/api/v1/session').then(value => value.json())
  190 |     const current = await snapshot(page, attempt.id)
  191 |     const receipt = await page.request.post(`/api/v1/attempts/${attempt.id}/submit`, { headers: { Origin: new URL(page.url()).origin, 'X-CSRF-Token': token.csrf_token, 'Idempotency-Key': crypto.randomUUID() }, data: { expected_revision: current.revision } })
  192 |     expect(receipt.status()).toBe(202)
  193 |     expect((await receipt.json() as AttemptSnapshot).status).toBe('submitted')
  194 |     // Grading legitimately advances Attempt.revision after submit. Pin the real
  195 |     // completed worker state before checking that restoring drafts cannot edit it.
  196 |     await expect.poll(async () => (await snapshot(page, attempt.id)).status).toBe('needs_review')
  197 |     const ended = await snapshot(page, attempt.id)
  198 |     let resultCaptured = () => {}, refreshStarted = () => {}, resultReleased = false
  199 |     const resultReady = new Promise<void>(resolve => { resultCaptured = resolve })
  200 |     const resultRelease = new Promise<void>(resolve => { releaseResult = resolve })
  201 |     const refreshReady = new Promise<void>(resolve => { refreshStarted = resolve })
  202 |     const refreshRelease = new Promise<void>(resolve => { releaseRefresh = resolve })
  203 |     await page.route(`**/api/v1/attempts/${attempt.id}/result`, async route => {
  204 |       const actual = await route.fetch(); expect(actual.status()).toBe(200)
  205 |       if (!resultReleased) { resultCaptured(); await resultRelease }
  206 |       await route.fulfill({ response: actual })
  207 |     })
  208 |     await page.route(`**/api/v1/attempts/${attempt.id}`, async route => {
  209 |       const actual = await route.fetch()
  210 |       if (resultReleased) { refreshStarted(); await refreshRelease }
  211 |       await route.fulfill({ response: actual })
  212 |     })
  213 |     await page.exposeFunction('releaseAssessmentResult', () => { resultReleased = true; releaseResult() })
  214 |     await page.goto(href); await resultReady
  215 |     const restoring = page.getByRole('button', { name: '恢复这份本机测试作答', exact: true })
  216 |     await expect(restoring).toBeEnabled()
  217 |     await restoring.scrollIntoViewIfNeeded()
  218 |     await restoring.evaluate(button => {
  219 |       const probe = { pointerdown: false, pointerup: false, clicks: 0 }
  220 |       Object.assign(window, { assessmentPointerProbe: probe })
  221 |       button.addEventListener('pointerdown', () => { probe.pointerdown = true; void (window as unknown as { releaseAssessmentResult: () => Promise<void> }).releaseAssessmentResult() }, { once: true })
  222 |       document.addEventListener('pointerup', () => { probe.pointerup = true }, { once: true, capture: true })
  223 |       button.addEventListener('click', () => { probe.clicks++ })
  224 |     })
  225 |     // Release a genuine result during an ordinary pointer gesture, and hold its
  226 |     // passive refresh until pointerup. No response body or parsed grade is mocked.
  227 |     const bounds = (await restoring.boundingBox())!
  228 |     expect(await restoring.evaluate(button => { const box = button.getBoundingClientRect(); return button.contains(document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2)) })).toBe(true)
  229 |     await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2)
  230 |     await page.mouse.down(); await refreshReady
  231 |     await page.evaluate(() => new Promise<void>(resolve => requestAnimationFrame(() => resolve())))
  232 |     const disabledBeforePointerUp = await restoring.evaluate(button => (button as HTMLButtonElement).disabled)
  233 |     await page.mouse.up()
  234 |     const pointer = await page.evaluate(() => (window as unknown as { assessmentPointerProbe: { pointerdown: boolean; pointerup: boolean; clicks: number } }).assessmentPointerProbe)
  235 |     releaseRefresh()
  236 |     await info.attach('grading-refresh-pointer', { body: JSON.stringify({ ...pointer, disabledBeforePointerUp }), contentType: 'application/json' })
  237 |     await expect(page.getByRole('heading', { name: '服务端测试作答冲突 · 三方比较', exact: true })).toBeVisible()
  238 |     expect({ ...pointer, disabledBeforePointerUp }).toEqual({ pointerdown: true, pointerup: true, clicks: 1, disabledBeforePointerUp: false })
  239 |     await page.getByRole('button', { name: '保留本页作答并采用新基准', exact: true }).click()
  240 |     await expect(page.getByLabel('第 2 题答案', { exact: true })).toHaveValue('A测试本机候选 🧠')
  241 |     await expect(page.getByLabel('第 2 题答案', { exact: true })).toBeDisabled()
  242 |     await page.unroute(pattern)
  243 |     await page.getByRole('button', { name: '重新读取测试状态', exact: true }).click()
  244 |     expect((await responses(page, attempt.id)).responses).toEqual(before.responses)
  245 |     expect((await snapshot(page, attempt.id)).revision).toBe(ended.revision)
  246 |     await page.getByRole('heading', { name: '服务端测试作答冲突 · 三方比较', exact: true }).scrollIntoViewIfNeeded()
  247 |     await page.screenshot({ path: info.outputPath('assessment-terminal-local-candidate-1440.png') })
  248 |   } finally { releaseResult(); releaseRefresh(); await second.close() }
  249 | })
  250 | 
  251 | test('late redacted Workbench save uses its original ETag and retains hidden selection after explicit three-way choice', async ({ page }) => {
  252 |   const fixture = await preview(page, 'nativeassessmentprojection')
  253 |   const origin = new URL(page.url()).origin
  254 |   await page.goto(`${origin}/?reader=${encodeURIComponent(JSON.stringify({ course: fixture.course, lesson: fixture.lesson }))}`)
  255 |   await expect(page.locator('.real-reader > h1')).toBeVisible()
  256 |   await page.getByText('原始 Markdown 与精确选文', { exact: true }).click()
  257 |   const source = page.getByRole('textbox', { name: /^原始 Markdown：/ })
  258 |   await source.focus(); await page.keyboard.press('Control+A')
  259 |   await expect(page.getByText('已从原始 Markdown 建立准确选文。', { exact: true })).toBeVisible()
  260 |   await expect(page.getByText('✓ UI 会话已保存')).toBeVisible()
  261 |   const before: import('../../packages/contracts/generated/types').WorkbenchSession = await page.request.get('/api/v1/workbench/session').then(value => value.json())
  262 |   const readerTab = before.tabs.find(tab => tab.id === before.active_tab_id)!
  263 |   expect(readerTab.context.selection?.exact_quote).toBeTruthy()
  264 |   await page.goto(`${origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`)
```