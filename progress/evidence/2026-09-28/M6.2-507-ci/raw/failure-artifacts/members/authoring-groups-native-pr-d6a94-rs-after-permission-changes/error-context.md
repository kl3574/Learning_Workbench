# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: authoring-groups.spec.ts >> native practice group replays its lost prepare ACK with one key and clears explicitly read private answers after permission changes
- Location: ../../tests/e2e/authoring-groups.spec.ts:294:1

# Error details

```
TimeoutError: locator.click: Timeout 10000ms exceeded.
Call log:
  - waiting for getByRole('dialog', { name: '创作', exact: true }).getByRole('button', { name: '读取创作详情 authoring_b50fbd4b80424e36a296c2deb3fbcc9b', exact: true })

```

# Test source

```ts
  1   | import { writeFileSync } from 'node:fs'
  2   | import { expect, test, type BrowserType, type Locator, type Page, type TestInfo } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  3   | import type { AuthoringGroupDraftView, AuthoringGroupJobView, AuthoringGroupNumericCheckView, AuthoringPrivateSolutionView, ConsentProposalView, JobRef, JobSnapshot, NumericCheckDecisionAck, SessionResponse } from '../../packages/contracts/generated/api-types'
  4   | import { AuthoringRuntime } from './authoringRuntime'
  5   | 
  6   | const providerId = 'provider_authoring_group_native'
  7   | const topic = '原创合成组合创作'
  8   | const objective = '区分草稿结构、数值复算与教学审核。'
  9   | async function configure(page: Page, runtime: AuthoringRuntime) {
  10  |   const auth: SessionResponse = await page.request.get('/api/v1/session').then(value => value.json())
  11  |   const headers = { Origin: runtime.origin, 'X-CSRF-Token': auth.csrf_token }
  12  |   expect((await page.request.post('/api/v1/session/role', { data: { role: 'author' }, headers: { ...headers, 'Idempotency-Key': 'native-group-author' } })).status()).toBe(200)
  13  |   const config = runtime.control()
  14  |   expect(config.test_only).toBe(true); expect(config.proof_registered).toBe(true)
  15  |   expect((await page.request.put(`/api/v1/providers/${providerId}/config`, { data: { expected_revision: 0, adapter: config.adapter, base_url: config.base_url, model: config.model, embedding_model: null, endpoint_policy: 'explicit_loopback', pricing: null }, headers: { ...headers, 'Idempotency-Key': 'native-group-config' } })).status()).toBe(200)
  16  |   expect((await page.request.post(`/api/v1/providers/${providerId}/secret`, { data: { expected_revision: 1, secret: 'synthetic-group-native-constant-only' }, headers: { ...headers, 'Idempotency-Key': 'native-group-secret' } })).status()).toBe(200)
  17  |   await page.reload()
  18  |   await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible()
  19  | }
  20  | async function form(page: Page, kind: 'lesson' | 'practice_set' | 'assessment') {
  21  |   await page.getByRole('button', { name: '创作', exact: true }).click()
  22  |   const dialog = page.getByRole('dialog', { name: '创作', exact: true })
  23  |   await expect(dialog.getByRole('combobox', { name: '创作类型', exact: true })).toBeEnabled()
  24  |   await dialog.getByRole('combobox', { name: '创作类型', exact: true }).selectOption(kind)
  25  |   await dialog.getByLabel('创作主题', { exact: true }).fill(topic)
  26  |   await dialog.getByLabel('学习目标（每行一条，至少一条）', { exact: true }).fill(objective)
  27  |   await dialog.getByLabel('已配置的提供商 ID', { exact: true }).fill(providerId)
  28  |   if (kind !== 'lesson') {
  29  |     const target = dialog.getByRole('region', { name: '明确选择已有目标', exact: true })
  30  |     await target.getByRole('button', { name: '读取课程目录以选择目标', exact: true }).click()
  31  |     await target.getByRole('button', { name: '原创合成组目标课程 · r1 · 选择目标', exact: true }).click()
  32  |     await target.getByRole('button', { name: '加入概念：concept_group_native · r1', exact: true }).click()
  33  |     if (kind === 'practice_set') await target.getByRole('button', { name: '选择所属小节：原创合成已有小节 · r1', exact: true }).click()
  34  |     await expect(target.getByText('已选概念 1 / 32', { exact: true })).toBeVisible()
  35  |   }
  36  |   if (kind === 'assessment') {
  37  |     const requirements = dialog.getByRole('region', { name: '本次测试要求', exact: true })
  38  |     await requirements.getByLabel('独立测试', { exact: true }).check()
  39  |     await requirements.getByLabel('开卷测试', { exact: true }).check()
  40  |     await requirements.getByLabel('测试时限（秒）', { exact: true }).fill('600')
  41  |     await expect(requirements.getByLabel('辅助测试', { exact: true })).not.toBeChecked()
  42  |     await expect(requirements.getByLabel('明确不限时', { exact: true })).not.toBeChecked()
  43  |   }
  44  |   return dialog
  45  | }
  46  | async function readPrepared(page: Page, dialog: Locator, ack: JobRef) {
  47  |   expect(ack.status).toBe('awaiting_approval')
> 48  |   await dialog.getByRole('button', { name: `读取创作详情 ${ack.id}`, exact: true }).click()
      |                                                                               ^ TimeoutError: locator.click: Timeout 10000ms exceeded.
  49  |   await expect(dialog.getByRole('region', { name: '受保护创作详情', exact: true })).toBeVisible()
  50  |   const result: AuthoringGroupJobView = await page.request.get(`/api/v1/authoring/jobs/${ack.id}`).then(value => value.json())
  51  |   expect(result.variant).toBe('group'); expect(result.request.source_refs).toEqual([])
  52  |   expect(result.raw_answer).toBeNull(); expect(result.consent_id).toBeNull(); expect(result.content_plan).toBeNull()
  53  |   return result
  54  | }
  55  | async function grant(page: Page, dialog: Locator, ack: JobRef) {
  56  |   const preview = dialog.getByRole('region', { name: '准备授权预览', exact: true })
  57  |   await expect(preview.getByLabel('最大输入 token', { exact: true })).toBeEnabled()
  58  |   await preview.getByLabel('最大输入 token', { exact: true }).fill('20000')
  59  |   await preview.getByLabel('最大输出 token', { exact: true }).fill('10000')
  60  |   await preview.getByLabel('总超时秒数', { exact: true }).fill('10')
  61  |   await preview.getByLabel('到期时间 UTC', { exact: true }).fill(new Date(Date.now() + 300_000).toISOString())
  62  |   await preview.getByRole('button', { name: '准备服务端预览命令', exact: true }).click()
  63  |   const preparing = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/consents/preview'))
  64  |   await dialog.getByRole('button', { name: '确认发送授权预览', exact: true }).click()
  65  |   const response = await preparing; expect(response.status()).toBe(201)
  66  |   const proposal: ConsentProposalView = await response.json()
  67  |   expect(proposal.summary.job_id).toBe(ack.id)
  68  |   await dialog.getByLabel('我已核对本次组合草稿的冻结范围、提供商、预算与到期时间', { exact: true }).check()
  69  |   await dialog.getByRole('button', { name: '准备批准组合草稿模型调用', exact: true }).click()
  70  |   const granting = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/consents'))
  71  |   await dialog.getByRole('button', { name: '确认发送批准授权', exact: true }).click()
  72  |   expect((await granting).status()).toBe(201)
  73  |   let completed!: AuthoringGroupJobView
  74  |   // Preserve Playwright's actual default 5 s assertion; failure is diagnosed,
  75  |   // never converted into a longer hidden acceptance window.
  76  |   await expect.poll(async () => { completed = await page.request.get(`/api/v1/authoring/jobs/${ack.id}`).then(value => value.json()); return completed.summary.status }).toBe('completed')
  77  |   await dialog.getByRole('button', { name: '重新读取本次创作任务', exact: true }).click()
  78  |   await dialog.getByRole('button', { name: '读取这份准确组合候选', exact: true }).click()
  79  |   const group = dialog.getByRole('region', { name: '组合草稿候选', exact: true })
  80  |   await expect(group).toBeVisible()
  81  |   const draft: AuthoringGroupDraftView = await page.request.get(`/api/v1/authoring/draft-groups/${completed.summary.candidate!.draft_id}`).then(value => value.json())
  82  |   expect(draft.candidate).toEqual(completed.summary.candidate)
  83  |   expect(draft.content_plan).toEqual(completed.content_plan); expect(draft.plan_ref).toEqual(completed.plan_ref)
  84  |   expect(draft.state).toBe('draft'); expect(draft.base_ref).toBeNull()
  85  |   expect(draft.validation.mathematical).toBe('NOT_RUN'); expect(draft.validation.independent_pedagogy).toBe('NOT_RUN')
  86  |   await expect(group.getByRole('region', { name: '冻结的内容计划', exact: true })).toContainText(objective)
  87  |   return { completed, draft, group, proposal }
  88  | }
  89  | async function numericPreview(page: Page, dialog: Locator, group: Locator, draft: AuthoringGroupDraftView, solution?: AuthoringPrivateSolutionView) {
  90  |   if (solution) {
  91  |     // Refreshing the candidate intentionally clears private reads. Explicitly
  92  |     // request the exact solution again for each new question preview.
  93  |     const reading = page.waitForResponse(value => value.request().method() === 'GET' && value.url().endsWith(`/api/v1/authoring/draft-groups/${draft.candidate.draft_id}/solutions/question_double`))
  94  |     await group.getByRole('button', { name: '明确读取第 1 题的私有解答草稿', exact: true }).click()
  95  |     const response = await reading; expect(response.status()).toBe(200); expect(await response.json()).toEqual(solution)
  96  |   }
  97  |   const receiving = page.waitForResponse(value => value.request().method() === 'POST' && value.url().includes(`/api/v1/authoring/draft-groups/${draft.candidate.draft_id}/members/`) && value.url().endsWith('/numeric-checks'))
  98  |   await group.getByRole('button', { name: solution ? '为这份准确题目解答准备独立数值预览' : '为例题 原创合成双倍例题 准备独立数值预览', exact: true }).click()
  99  |   const response = await receiving; expect(response.status()).toBe(201)
  100 |   const check: AuthoringGroupNumericCheckView = await response.json()
  101 |   expect(check.target.member_key).toBe(solution ? 'question_double' : 'example'); expect(check.candidate).toEqual(draft.candidate)
  102 |   if (solution) { expect(check.target).toEqual(solution.payload.question); expect(check.plan).toEqual(solution.payload.answer.numeric_plan) }
  103 |   expect(check.decision).toBe('pending'); expect(check.revision).toBe(1)
  104 |   expect(check.job).toBeNull(); expect(check.result).toBeNull()
  105 |   await group.getByRole('button', { name: '刷新组合候选的检查记录', exact: true }).click()
  106 |   await group.getByRole('button', { name: `读取组数值检查 ${check.id}`, exact: true }).click()
  107 |   await expect(dialog.getByRole('region', { name: '独立数值执行批准', exact: true })).toBeVisible()
  108 |   return check
  109 | }
  110 | async function picture(page: Page, dialog: Locator, target: Locator, width: number, name: string, info: TestInfo) {
  111 |   await page.setViewportSize({ width, height: 900 })
  112 |   await target.scrollIntoViewIfNeeded(); await expect(target).toBeVisible()
  113 |   const bounds = await dialog.evaluate(element => {
  114 |     const inner = element.querySelector('.dialog-inner')!
  115 |     return { client: element.clientWidth, scroll: element.scrollWidth, inner_client: inner.clientWidth, inner_scroll: inner.scrollWidth, left: element.getBoundingClientRect().left, right: element.getBoundingClientRect().right, viewport: innerWidth, document: document.documentElement.scrollWidth }
  116 |   })
  117 |   writeFileSync(info.outputPath(`${name}-geometry.json`), JSON.stringify(bounds, null, 2))
  118 |   await page.screenshot({ path: info.outputPath(`${name}.png`) })
  119 |   expect(bounds.inner_scroll).toBeLessThanOrEqual(bounds.inner_client + 1)
  120 |   expect(bounds.scroll).toBeLessThanOrEqual(bounds.client + 1)
  121 |   expect(bounds.left).toBeGreaterThanOrEqual(0); expect(bounds.right).toBeLessThanOrEqual(bounds.viewport)
  122 |   expect(bounds.document).toBeLessThanOrEqual(bounds.viewport)
  123 |   return bounds
  124 | }
  125 | 
  126 | async function cancelSecondWithoutConsent(page: Page, dialog: Locator, runtime: AuthoringRuntime, first: JobRef, draft: AuthoringGroupDraftView) {
  127 |   const originalGroup = dialog.getByRole('region', { name: '组合草稿候选', exact: true })
  128 |   await expect(originalGroup).toBeVisible()
  129 |   let privateBeforeLock: AuthoringPrivateSolutionView | null = null
  130 |   if (draft.root.entity !== 'lesson') {
  131 |     const reading = page.waitForResponse(value => value.request().method() === 'GET' && value.url().endsWith(`/api/v1/authoring/draft-groups/${draft.candidate.draft_id}/solutions/question_double`))
  132 |     await originalGroup.getByRole('button', { name: '明确读取第 1 题的私有解答草稿', exact: true }).click()
  133 |     const response = await reading; expect(response.status()).toBe(200); privateBeforeLock = await response.json()
  134 |     expect(privateBeforeLock!.candidate).toEqual(draft.candidate); expect(privateBeforeLock!.ref).toEqual(draft.private_solution_refs[0])
  135 |   }
  136 |   // A second explicitly prepared Job has never received consent. The completed
  137 |   // first Job and its already consumed Provider request are not being cancelled.
  138 |   const preparing = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/authoring/group-jobs'))
  139 |   await dialog.getByRole('button', { name: '明确准备本次组合创作任务', exact: true }).click()
  140 |   const accepted = await preparing; expect(accepted.status()).toBe(202)
  141 |   const ack: JobRef = await accepted.json()
  142 |   expect(ack.id).not.toBe(first.id); expect(ack.status).toBe('awaiting_approval')
  143 |   const second: AuthoringGroupJobView = await page.request.get(`/api/v1/authoring/jobs/${ack.id}`).then(value => value.json())
  144 |   expect(second.request.output_kind).toBe(draft.root.entity)
  145 |   expect(second.consent_id).toBeNull(); expect(second.proposal_id).toBeNull(); expect(second.raw_answer).toBeNull(); expect(second.summary.candidate).toBeNull()
  146 |   const before: JobSnapshot = await page.request.get(`/api/v1/jobs/${ack.id}`).then(value => value.json())
  147 |   expect(before.status).toBe('awaiting_approval'); expect(runtime.control().received_request_count).toBe(1)
  148 |   await expect(originalGroup.getByRole('heading', { name: draft.root.title, exact: true })).toBeVisible()
```