# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: assessment-restart.spec.ts >> same assessment instance rejects forged course and assessment hashes while its independent policy remains active
- Location: ../../tests/e2e/assessment-restart.spec.ts:43:1

# Error details

```
TimeoutError: locator.click: Timeout 10000ms exceeded.
Call log:
  - waiting for getByText('原始 Markdown 与精确选文', { exact: true })

```

# Test source

```ts
  1   | import { expect, test, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  2   | import { writeFileSync } from 'node:fs'
  3   | import type { WorkbenchSession } from '../../packages/contracts/generated/types'
  4   | import type { AttemptSnapshot, AttemptResponses, PracticeSessionCreated } from '../../packages/contracts/generated/api-types'
  5   | import { RestartRuntime } from './restartRuntime'
  6   | import { originalAssessmentPackage, importAssessmentPackage, type AssessmentPackage } from './assessmentTestData'
  7   | 
  8   | async function workbench(page: Page): Promise<WorkbenchSession> {
  9   |   const response = await page.request.get('/api/v1/workbench/session')
  10  |   expect(response.status()).toBe(200)
  11  |   return response.json()
  12  | }
  13  | async function attempt(page: Page, id: string): Promise<AttemptSnapshot> {
  14  |   const response = await page.request.get(`/api/v1/attempts/${id}`)
  15  |   expect(response.status()).toBe(200)
  16  |   return response.json()
  17  | }
  18  | async function responses(page: Page, id: string): Promise<AttemptResponses> {
  19  |   const response = await page.request.get(`/api/v1/attempts/${id}/responses`)
  20  |   expect(response.status()).toBe(200)
  21  |   return response.json()
  22  | }
  23  | async function csrf(page: Page) {
  24  |   const response = await page.request.get('/api/v1/session')
  25  |   expect(response.status()).toBe(200)
  26  |   return (await response.json()).csrf_token as string
  27  | }
  28  | async function start(page: Page, runtime: RestartRuntime, fixture: AssessmentPackage) {
  29  |   const target = { assessment_ref: fixture.assessment, course_ref: fixture.course }
  30  |   await page.goto(`${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify(target))}`)
  31  |   await page.getByRole('radio', { name: '独立测试', exact: true }).check()
  32  |   await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
  33  |   const creating = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/api/v1/assessments/${fixture.assessment.id}/attempts`))
  34  |   await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
  35  |   const created = await creating
  36  |   expect(created.status()).toBe(201)
  37  |   const value: AttemptSnapshot = await created.json()
  38  |   await expect(page.getByRole('heading', { name: '本次测试作答', exact: true })).toBeVisible()
  39  |   await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
  40  |   return value
  41  | }
  42  | 
  43  | test('same assessment instance rejects forged course and assessment hashes while its independent policy remains active', async ({ playwright }, info) => {
  44  |   test.setTimeout(90_000)
  45  |   const runtime = await RestartRuntime.start(), fixture = originalAssessmentPackage('assessmentidentity')
  46  |   try {
  47  |     const browser = await runtime.openBrowser(playwright.chromium), page = browser.pages()[0]
  48  |     await runtime.authenticateOnly(page)
  49  |     const imported = await importAssessmentPackage(page, fixture)
  50  |     await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  51  |     await page.goto(`${runtime.origin}/?reader=${encodeURIComponent(JSON.stringify({ course: fixture.course, lesson: fixture.lesson }))}`)
> 52  |     await page.getByText('原始 Markdown 与精确选文', { exact: true }).click()
      |                                                                ^ TimeoutError: locator.click: Timeout 10000ms exceeded.
  53  |     const original = page.getByLabel('原始 Markdown：数量、步骤与单位', { exact: true })
  54  |     const originalBody = await original.inputValue()
  55  |     await original.focus()
  56  |     await expect(original).toBeFocused()
  57  |     await page.keyboard.press('Control+A')
  58  |     await expect(page.getByRole('button', { name: '为当前选文记笔记', exact: true })).toBeEnabled()
  59  |     await expect.poll(async () => {
  60  |       const current = await workbench(page)
  61  |       return current.tabs.find(tab => tab.id === current.active_tab_id)?.context.selection?.exact_quote
  62  |     }).toBe(originalBody)
  63  |     const reading = await workbench(page), readingTab = reading.tabs.find(tab => tab.id === reading.active_tab_id)!
  64  |     const created = await start(page, runtime, fixture)
  65  |     await expect.poll(async () => {
  66  |       const current = await workbench(page)
  67  |       return current.tabs.find(tab => tab.id === current.active_tab_id)?.context.attempt_id
  68  |     }).toBe(created.id)
  69  |     const before = await workbench(page), active = before.tabs.find(tab => tab.id === before.active_tab_id)!
  70  |     expect(before.tabs.every(tab => tab.context.selection === null)).toBe(true)
  71  |     const frozen = await attempt(page, created.id)
  72  |     const target = { assessment_ref: fixture.assessment, course_ref: fixture.course, attempt_id: created.id }
  73  |     for (const forged of [
  74  |       { ...target, course_ref: { ...fixture.course, sha256: '0'.repeat(64) } },
  75  |       { ...target, assessment_ref: { ...fixture.assessment, sha256: '0'.repeat(64) } },
  76  |     ]) {
  77  |       await page.goto(`${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify(forged))}`)
  78  |       await expect(page.getByRole('heading', { name: '无法打开此精确链接', exact: true })).toBeVisible()
  79  |       const retained = await workbench(page)
  80  |       expect(retained.course_ref).toEqual(before.course_ref)
  81  |       expect(retained.active_tab_id).toBe(active.id)
  82  |       expect(retained.tabs.find(tab => tab.id === active.id)?.context).toEqual(active.context)
  83  |       expect(await attempt(page, created.id)).toEqual(frozen)
  84  |       await page.getByRole('button', { name: '返回原标签', exact: true }).click()
  85  |       await expect(page.getByRole('heading', { name: '本次测试作答', exact: true })).toBeVisible()
  86  |     }
  87  |     expect((await page.request.get(`/api/v1/lessons/${fixture.lesson.id}?revision=1`)).status()).toBe(409)
  88  |     const redactedResponse = await page.request.get('/api/v1/workbench/session')
  89  |     const redacted: WorkbenchSession = await redactedResponse.json(), etag = redactedResponse.headers()['etag']
  90  |     expect(etag).toBeTruthy()
  91  |     const abandoning = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/api/v1/attempts/${created.id}/abandon`))
  92  |     await page.getByRole('button', { name: '放弃本次测试', exact: true }).click()
  93  |     await page.getByRole('dialog', { name: '确认放弃测试', exact: true }).getByRole('button', { name: '确认放弃并保留本机候选', exact: true }).click()
  94  |     expect((await abandoning).status()).toBe(200)
  95  |     // A delayed save based on a real redacted HTTP response cannot clear the
  96  |     // earlier source selection after the active policy ends.
  97  |     const late = await page.request.put('/api/v1/workbench/session', { headers: { Origin: runtime.origin, 'X-CSRF-Token': await csrf(page), 'If-Match': etag }, data: { expected_revision: redacted.revision, session: redacted } })
  98  |     expect(late.status()).toBe(412)
  99  |     const after = await workbench(page)
  100 |     expect(after.tabs.find(tab => tab.id === readingTab.id)?.context.selection).toEqual(readingTab.context.selection)
  101 |     writeFileSync(info.outputPath('assessment-frozen-navigation.json'), JSON.stringify({
  102 |       scope: 'Actual imported original fixture and UI-created independent attempt; invalid links never replace its frozen context.',
  103 |       attempt_id: created.id, same_tab_identity: active.id, context: active.context,
  104 |       forged_course_hash_rejected: true, forged_assessment_hash_rejected: true,
  105 |       own_active_attempt_readable: true, material_direct_request_blocked: true,
  106 |       prior_source_selection_hidden_while_active: true, late_redacted_save_rejected: true,
  107 |       original_source_selection_retained_after_abandon: true,
  108 |     }, null, 2))
  109 |   } finally { await runtime.close() }
  110 | })
  111 | 
  112 | test('actual browser and API restarts retain independent drafts and keep old solution receipts protected after submission', async ({ playwright }, info) => {
  113 |   test.setTimeout(150_000)
  114 |   const runtime = await RestartRuntime.start(), fixture = originalAssessmentPackage('assessmentrestart')
  115 |   const errors: string[] = [], automaticSolutions: string[] = []
  116 |   const observe = (page: Page) => {
  117 |     page.on('pageerror', error => errors.push(error.message))
  118 |     page.on('request', request => { if (/\/practice\/sessions\/[^/]+\/solutions$/.test(request.url())) automaticSolutions.push(request.method()) })
  119 |   }
  120 |   try {
  121 |     const firstBrowser = await runtime.openBrowser(playwright.chromium), page = firstBrowser.pages()[0]
  122 |     observe(page)
  123 |     await runtime.authenticateOnly(page)
  124 |     const imported = await importAssessmentPackage(page, fixture)
  125 |     await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  126 |     // Explicit adversarial setup through the actual API: obtain a prior practice
  127 |     // solution receipt, then prove that its idempotency key never bypasses a test.
  128 |     const token = await csrf(page)
  129 |     const practiceResponse = await page.request.post('/api/v1/practice/sessions', { headers: { Origin: runtime.origin, 'X-CSRF-Token': token, 'Idempotency-Key': 'prior-practice' }, data: { practice_ref: fixture.practice } })
  130 |     expect(practiceResponse.status()).toBe(201)
  131 |     const practice: PracticeSessionCreated = await practiceResponse.json()
  132 |     const solutionPath = `/api/v1/practice/sessions/${practice.id}/solutions`
  133 |     const solutionBody = { question_id: fixture.questions[0].id, expected_revision: practice.revision }
  134 |     const reveal = (current: Page, auth: string) => current.request.post(solutionPath, { headers: { Origin: runtime.origin, 'X-CSRF-Token': auth, 'Idempotency-Key': 'prior-solution' }, data: solutionBody })
  135 |     expect((await reveal(page, token)).status()).toBe(200)
  136 |     const created = await start(page, runtime, fixture)
  137 |     expect(created.preflight.grading.status).toBe('unreviewed')
  138 |     expect(created.preflight.prior_seen.questions.every(item => item.state === 'seen')).toBe(true)
  139 |     expect(created.policy).toMatchObject({ mode: 'independent', allow_web: false, allow_materials: false, tutor_scope: 'operation_help_only' })
  140 |     expect((await reveal(page, token)).status()).toBe(409)
  141 |     await page.getByRole('navigation', { name: '本次测试题目', exact: true }).getByRole('button', { name: /^第 2 题/ }).click()
  142 |     await page.getByLabel('第 2 题答案', { exact: true }).fill('加法交换律')
  143 |     await page.getByLabel('第 2 题推导步骤', { exact: true }).fill('先核对运算和交换前后的各项。')
  144 |     await expect.poll(async () => (await responses(page, created.id)).responses.find(item => item.question_id === fixture.questions[1].id)?.answer).toBe('加法交换律')
  145 |     await expect(page.getByText('服务端作答已保存', { exact: true })).toBeVisible()
  146 |     const before = await attempt(page, created.id), beforeResponses = await responses(page, created.id)
  147 |     const responseRoute = `**/api/v1/attempts/${created.id}/responses`
  148 |     await page.route(responseRoute, route => route.request().method() === 'PUT' ? route.abort('internetdisconnected') : route.continue())
  149 |     const localAnswer = '独立作答的本机候选 🧠：还需区分结合律。'
  150 |     await page.getByLabel('第 2 题答案', { exact: true }).fill(localAnswer)
  151 |     await expect(page.getByText('作答尚未确认同步', { exact: true })).toBeVisible()
  152 |     await expect(page.getByText('本机草稿存储可用', { exact: true })).toBeVisible()
```