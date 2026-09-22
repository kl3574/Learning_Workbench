# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: authoring.spec.ts >> explicit same-Job loopback grant creates a draft and numeric preview needs its own decision
- Location: tests/e2e/authoring.spec.ts:110:1

# Error details

```
Error: expect(received).toBeLessThanOrEqual(expected)

Expected: <= 361
Received:    504
```

# Test source

```ts
  1   | import { writeFileSync } from 'node:fs'
  2   | import { expect, test, type Locator, type Page, type TestInfo } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  3   | import type { AuthoringDraftView, AuthoringJobPage, AuthoringJobView, ConsentProposalView, JobRef, NumericCheckView, ProviderConfigWrite, SessionResponse } from '../../packages/contracts/generated/api-types'
  4   | import { AuthoringRuntime } from './authoringRuntime'
  5   | 
  6   | const providerId = 'provider_authoring_native'
  7   | async function role(page: Page, origin: string, value: 'author' | 'learner') {
  8   |   const session: SessionResponse = await page.request.get('/api/v1/session').then(v => v.json())
  9   |   const response = await page.request.post('/api/v1/session/role', { data: { role: value }, headers: { Origin: origin, 'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': `synthetic-authoring-role-${value}` } })
  10  |   expect(response.status()).toBe(200)
  11  |   // Only the real role endpoint changes permissions; reloading observes it.
  12  |   await page.reload()
  13  |   await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible()
  14  | }
  15  | async function configure(page: Page, runtime: AuthoringRuntime) {
  16  |   const session: SessionResponse = await page.request.get('/api/v1/session').then(v => v.json())
  17  |   const headers = { Origin: runtime.origin, 'X-CSRF-Token': session.csrf_token }
  18  |   const control = runtime.control()
  19  |   const config: ProviderConfigWrite = { expected_revision: 0, adapter: control.adapter, base_url: control.base_url, model: control.model, embedding_model: null, endpoint_policy: 'explicit_loopback', pricing: null }
  20  |   expect((await page.request.put(`/api/v1/providers/${providerId}/config`, { data: config, headers: { ...headers, 'Idempotency-Key': 'synthetic-authoring-native-config' } })).status()).toBe(200)
  21  |   expect((await page.request.post(`/api/v1/providers/${providerId}/secret`, { data: { expected_revision: 1, secret: 'synthetic-authoring-native-constant-only' }, headers: { ...headers, 'Idempotency-Key': 'synthetic-authoring-native-secret' } })).status()).toBe(200)
  22  | }
  23  | async function prepare(page: Page) {
  24  |   await page.getByRole('button', { name: '创作', exact: true }).click()
  25  |   const dialog = page.getByRole('dialog', { name: '创作', exact: true })
  26  |   await expect(dialog.getByLabel('例题主题', { exact: true })).toBeEnabled()
  27  |   await dialog.getByLabel('例题主题', { exact: true }).fill('原创合成双倍例题')
  28  |   await dialog.getByLabel('学习目标（每行一条，至少一条）', { exact: true }).fill('明确区分模型草稿、数值复算与数学审核。')
  29  |   await dialog.getByLabel('已配置的提供商 ID', { exact: true }).fill(providerId)
  30  |   const response = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith('/api/v1/authoring/jobs'))
  31  |   await dialog.getByRole('button', { name: '明确准备本次例题任务', exact: true }).click()
  32  |   const accepted = await response; expect(accepted.status()).toBe(202)
  33  |   const ack: JobRef = await accepted.json()
  34  |   expect(ack.status).toBe('awaiting_approval')
  35  |   await dialog.getByRole('button', { name: `读取创作详情 ${ack.id}`, exact: true }).click()
  36  |   await expect(dialog.getByRole('region', { name: '受保护创作详情', exact: true })).toBeVisible()
  37  |   const original: AuthoringJobView = await page.request.get(`/api/v1/authoring/jobs/${ack.id}`).then(v => v.json())
  38  |   expect(original.request.source_refs).toEqual([]); expect(original.preparation.materials).toEqual([])
  39  |   expect(original.consent_id).toBeNull(); expect(original.proposal_id).toBeNull(); expect(original.raw_answer).toBeNull()
  40  |   return { dialog, ack, original }
  41  | }
  42  | async function preview(page: Page, dialog: Locator) {
  43  |   const panel = dialog.getByRole('region', { name: '准备授权预览', exact: true })
  44  |   await expect(panel.getByLabel('最大输入 token', { exact: true })).toBeEnabled()
  45  |   await panel.getByLabel('最大输入 token', { exact: true }).fill('20000')
  46  |   await panel.getByLabel('最大输出 token', { exact: true }).fill('5000')
  47  |   await panel.getByLabel('总超时秒数', { exact: true }).fill('10')
  48  |   await panel.getByLabel('到期时间 UTC', { exact: true }).fill(new Date(Date.now() + 300_000).toISOString())
  49  |   await panel.getByRole('button', { name: '准备服务端预览命令', exact: true }).click()
  50  |   const response = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith('/api/v1/consents/preview'))
  51  |   await dialog.getByRole('button', { name: '确认发送授权预览', exact: true }).click()
  52  |   return response
  53  | }
  54  | async function numericPreview(page: Page, dialog: Locator, draftId: string) {
  55  |   const response = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith(`/api/v1/authoring/drafts/${draftId}/numeric-checks`))
  56  |   await dialog.getByRole('button', { name: '明确准备独立数值检查预览', exact: true }).click()
  57  |   const accepted = await response; expect(accepted.status()).toBe(201)
  58  |   const value: NumericCheckView = await accepted.json()
  59  |   expect(value.decision).toBe('pending'); expect(value.job).toBeNull(); expect(value.result).toBeNull()
  60  |   await dialog.getByRole('button', { name: '刷新候选的检查记录', exact: true }).click()
  61  |   await dialog.getByRole('button', { name: `读取数值检查 ${value.id}`, exact: true }).click()
  62  |   await expect(dialog.getByRole('region', { name: '独立数值执行批准', exact: true })).toBeVisible()
  63  |   return value
  64  | }
  65  | async function screenshot(page: Page, dialog: Locator, width: number, target: Locator, name: string, info: TestInfo) {
  66  |   await page.setViewportSize({ width, height: 900 })
  67  |   await target.scrollIntoViewIfNeeded()
  68  |   await expect(target).toBeVisible()
  69  |   const bounds = await dialog.evaluate(element => { const inner = element.querySelector('.dialog-inner')!; return { client: element.clientWidth, scroll: element.scrollWidth, inner_client: inner.clientWidth, inner_scroll: inner.scrollWidth, left: element.getBoundingClientRect().left, right: element.getBoundingClientRect().right, viewport: innerWidth, document: document.documentElement.scrollWidth } })
  70  |   writeFileSync(info.outputPath(name.replace('.png', '-geometry.json')), JSON.stringify(bounds, null, 2))
  71  |   await page.screenshot({ path: info.outputPath(name) })
> 72  |   expect(bounds.inner_scroll).toBeLessThanOrEqual(bounds.inner_client + 1)
      |                               ^ Error: expect(received).toBeLessThanOrEqual(expected)
  73  |   expect(bounds.scroll).toBeLessThanOrEqual(bounds.client + 1)
  74  |   expect(bounds.left).toBeGreaterThanOrEqual(0); expect(bounds.right).toBeLessThanOrEqual(bounds.viewport)
  75  |   expect(bounds.document).toBeLessThanOrEqual(bounds.viewport)
  76  |   await page.screenshot({ path: info.outputPath(name) })
  77  |   return bounds
  78  | }
  79  | 
  80  | test('actual Authoring preparation diagnoses missing proof without dispatch and learner can recover safe cancellation', async ({ playwright }, info) => {
  81  |   test.setTimeout(90_000)
  82  |   const runtime = await AuthoringRuntime.start('no_proof')
  83  |   try {
  84  |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
  85  |     await runtime.authenticateOnly(page); await role(page, runtime.origin, 'author'); await configure(page, runtime)
  86  |     expect(runtime.control().proof_registered).toBe(false)
  87  |     const { dialog, ack, original } = await prepare(page)
  88  |     expect(runtime.control().received_request_count).toBe(0)
  89  |     const rejected = await preview(page, dialog)
  90  |     expect(rejected.status()).toBe(409); expect((await rejected.json()).error.code).toBe('CAPABILITY_UNSUPPORTED')
  91  |     const unchanged: AuthoringJobView = await page.request.get(`/api/v1/authoring/jobs/${ack.id}`).then(v => v.json())
  92  |     expect(unchanged.consent_id).toBeNull(); expect(unchanged.proposal_id).toBeNull(); expect(unchanged.raw_answer).toBeNull()
  93  |     await role(page, runtime.origin, 'learner')
  94  |     await page.getByRole('button', { name: '创作', exact: true }).click()
  95  |     await expect(dialog.getByLabel('例题主题', { exact: true })).toHaveCount(0)
  96  |     await expect(dialog.getByRole('region', { name: '受保护创作详情', exact: true })).toHaveCount(0)
  97  |     const cancelling = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith(`/api/v1/jobs/${ack.id}/cancel`))
  98  |     await dialog.getByRole('button', { name: `明确取消任务 ${ack.id}`, exact: true }).click()
  99  |     expect((await cancelling).status()).toBe(200)
  100 |     await expect(dialog.getByText(new RegExp(`^${ack.id} · cancelled · r`))).toBeVisible()
  101 |     const final: AuthoringJobPage = await page.request.get('/api/v1/authoring/jobs').then(v => v.json())
  102 |     expect(final.items).toHaveLength(1); expect(final.items[0].status).toBe('cancelled')
  103 |     expect(final.items[0].result_refs).toEqual([]); expect(final.items[0].warnings).toEqual([])
  104 |     expect(JSON.stringify(final)).not.toContain(original.request.topic)
  105 |     expect(runtime.control().received_request_count).toBe(0)
  106 |     writeFileSync(info.outputPath('actual-authoring-no-proof.json'), JSON.stringify({ scope: 'Real local HTTP/SQLite/worker/browser. Production-style empty proof registry; original synthetic provider configuration only. Preview rejected, zero dispatch, learner safe cancellation. No model or numeric result.', prepared: original, no_proposal: unchanged, safe_final: final, runtime: runtime.control() }, null, 2))
  107 |   } finally { await runtime.close() }
  108 | })
  109 | 
  110 | test('explicit same-Job loopback grant creates a draft and numeric preview needs its own decision', async ({ playwright }, info) => {
  111 |   test.setTimeout(120_000)
  112 |   const runtime = await AuthoringRuntime.start('complete'), errors: string[] = []
  113 |   try {
  114 |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
  115 |     page.on('pageerror', error => errors.push(error.message))
  116 |     await runtime.authenticateOnly(page); await role(page, runtime.origin, 'author'); await configure(page, runtime)
  117 |     let prepares = 0
  118 |     page.on('request', value => { if (value.method() === 'POST' && value.url().endsWith('/api/v1/authoring/jobs')) prepares++ })
  119 |     const { dialog, ack } = await prepare(page)
  120 |     expect(runtime.control().proof_registered).toBe(true); expect(runtime.control().received_request_count).toBe(0)
  121 |     const previewResponse = await preview(page, dialog); expect(previewResponse.status()).toBe(201)
  122 |     const proposal: ConsentProposalView = await previewResponse.json()
  123 |     expect(proposal.summary.job_id).toBe(ack.id); expect(proposal.summary.purpose).toBe('authoring')
  124 |     expect(runtime.control().received_request_count).toBe(0)
  125 |     await dialog.getByLabel('我已核对本次例题的冻结范围、提供商、预算与到期时间', { exact: true }).check()
  126 |     await dialog.getByRole('button', { name: '准备批准例题模型调用', exact: true }).click()
  127 |     const granting = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith('/api/v1/consents'))
  128 |     await dialog.getByRole('button', { name: '确认发送批准授权', exact: true }).click()
  129 |     expect((await granting).status()).toBe(201)
  130 |     let current!: AuthoringJobView
  131 |     await expect.poll(async () => { current = await page.request.get(`/api/v1/authoring/jobs/${ack.id}`).then(v => v.json()); return current.summary.status }, { timeout: 10_000 }).toBe('completed')
  132 |     await dialog.getByRole('button', { name: '重新读取本次创作任务', exact: true }).click()
  133 |     await dialog.getByRole('button', { name: '读取这份准确例题候选', exact: true }).click()
  134 |     const candidate = current.summary.candidate; expect(candidate).not.toBeNull()
  135 |     const draft: AuthoringDraftView = await page.request.get(`/api/v1/authoring/drafts/${candidate!.draft_id}`).then(v => v.json())
  136 |     expect(draft.state).toBe('draft'); expect(draft.base_ref).toBeNull(); expect(draft.numeric_check_ids).toEqual([])
  137 |     expect(current.raw_answer).toBe(runtime.control().answer_markdown)
  138 |     await expect(dialog.getByLabel('完整候选正文', { exact: true })).toHaveText(draft.payload.body_markdown)
  139 |     expect(draft.validation.mathematical).toBe('NOT_RUN'); expect(draft.validation.independent_pedagogy).toBe('NOT_RUN')
  140 |     const rejectedPreview = await numericPreview(page, dialog, candidate!.draft_id)
  141 |     expect((await page.request.get('/api/v1/authoring/jobs').then(v => v.json()) as AuthoringJobPage).items).toHaveLength(1)
  142 |     const declining = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith(`/api/v1/authoring/numeric-checks/${rejectedPreview.id}/decision`))
  143 |     await dialog.getByRole('button', { name: '明确拒绝本次数值执行', exact: true }).click()
  144 |     const declinedAck = await declining; expect(declinedAck.status()).toBe(200); expect((await declinedAck.json()).job).toBeNull()
  145 |     await dialog.getByRole('button', { name: '另行读取数值检查当前状态', exact: true }).click()
  146 |     await expect(dialog.getByText('当前决定：decline · r2', { exact: true })).toBeVisible()
  147 |     const approvedPreview = await numericPreview(page, dialog, candidate!.draft_id)
  148 |     await dialog.getByLabel('我已核对全部变量、表达式、容差、候选与本机隔离范围，单独批准这一次执行', { exact: true }).check()
  149 |     const approving = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith(`/api/v1/authoring/numeric-checks/${approvedPreview.id}/decision`))
  150 |     await dialog.getByRole('button', { name: '明确批准本次数值执行', exact: true }).click()
  151 |     const approvedAck = await approving; expect(approvedAck.status()).toBe(202)
  152 |     const numericAck = await approvedAck.json(); expect(numericAck.job).not.toBeNull()
  153 |     let numeric!: NumericCheckView
  154 |     await expect.poll(async () => { numeric = await page.request.get(`/api/v1/authoring/numeric-checks/${approvedPreview.id}`).then(v => v.json()); return numeric.result !== null }, { timeout: 15_000 }).toBe(true)
  155 |     expect(['passed', 'environment_unavailable']).toContain(numeric.result!.outcome)
  156 |     expect(numeric.result!.verdict).toBe(numeric.result!.outcome === 'passed' ? 'PASS' : 'BLOCKED')
  157 |     await dialog.getByRole('button', { name: '另行读取数值检查当前状态', exact: true }).click()
  158 |     await expect(dialog.getByRole('heading', { name: `实际数值结果：${numeric.result!.verdict}`, exact: true })).toBeVisible()
  159 |     const finalDraft: AuthoringDraftView = await page.request.get(`/api/v1/authoring/drafts/${candidate!.draft_id}`).then(v => v.json())
  160 |     expect(finalDraft.candidate).toEqual(draft.candidate); expect(finalDraft.state).toBe('draft')
  161 |     expect(finalDraft.payload).toEqual(draft.payload); expect(finalDraft.numeric_check_ids).toEqual([rejectedPreview.id, approvedPreview.id])
  162 |     writeFileSync(info.outputPath('actual-authoring-execution-before-layout.json'), JSON.stringify({ scope: 'Actual authoring and numeric HTTP/worker results before viewport and role checks; subsequent test outcome is separate.', completed: current, draft: finalDraft, declined_preview: rejectedPreview, approved_preview: approvedPreview, actual_numeric: numeric, runtime: runtime.control() }, null, 2))
  163 |     const wide = await screenshot(page, dialog, 1440, dialog.getByLabel('完整候选正文', { exact: true }), 'authoring-candidate-1440.png', info)
  164 |     const narrow = await screenshot(page, dialog, 390, dialog.getByLabel('完整候选正文', { exact: true }), 'authoring-candidate-390.png', info)
  165 |     await screenshot(page, dialog, 390, dialog.getByRole('region', { name: '实际数值结果', exact: true }), 'authoring-actual-numeric-390.png', info)
  166 |     await expect.poll(() => runtime.control().validated_request_count).toBe(1)
  167 |     expect(runtime.control().received_request_count).toBe(1); expect(runtime.control().invalid_request_count).toBe(0); expect(prepares).toBe(1)
  168 |     await role(page, runtime.origin, 'learner')
  169 |     await page.locator('.command-trigger').click()
  170 |     await page.getByRole('dialog', { name: '命令面板', exact: true }).getByRole('button', { name: /^创作/ }).click()
  171 |     const control = dialog.getByRole('region', { name: '创作任务安全控制', exact: true })
  172 |     await expect(control.getByText('例题候选生成任务', { exact: true })).toBeVisible()
```