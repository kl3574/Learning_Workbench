# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: authoring.spec.ts >> explicit same-Job loopback grant creates a draft and numeric preview needs its own decision
- Location: tests/e2e/authoring.spec.ts:107:1

# Error details

```
TimeoutError: locator.click: Timeout 10000ms exceeded.
Call log:
  - waiting for getByRole('button', { name: '创作', exact: true })

```

# Test source

```ts
  65  | async function screenshot(page: Page, dialog: Locator, width: number, target: Locator, name: string, info: TestInfo) {
  66  |   await page.setViewportSize({ width, height: 900 })
  67  |   await target.scrollIntoViewIfNeeded()
  68  |   await expect(target).toBeVisible()
  69  |   const bounds = await dialog.evaluate(element => ({ client: element.clientWidth, scroll: element.scrollWidth, left: element.getBoundingClientRect().left, right: element.getBoundingClientRect().right, viewport: innerWidth, document: document.documentElement.scrollWidth }))
  70  |   expect(bounds.scroll).toBeLessThanOrEqual(bounds.client + 1)
  71  |   expect(bounds.left).toBeGreaterThanOrEqual(0); expect(bounds.right).toBeLessThanOrEqual(bounds.viewport)
  72  |   expect(bounds.document).toBeLessThanOrEqual(bounds.viewport)
  73  |   await page.screenshot({ path: info.outputPath(name) })
  74  |   return bounds
  75  | }
  76  | 
  77  | test('actual Authoring preparation diagnoses missing proof without dispatch and learner can recover safe cancellation', async ({ playwright }, info) => {
  78  |   test.setTimeout(90_000)
  79  |   const runtime = await AuthoringRuntime.start('no_proof')
  80  |   try {
  81  |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
  82  |     await runtime.authenticateOnly(page); await role(page, runtime.origin, 'author'); await configure(page, runtime)
  83  |     expect(runtime.control().proof_registered).toBe(false)
  84  |     const { dialog, ack, original } = await prepare(page)
  85  |     expect(runtime.control().received_request_count).toBe(0)
  86  |     const rejected = await preview(page, dialog)
  87  |     expect(rejected.status()).toBe(409); expect((await rejected.json()).error.code).toBe('CAPABILITY_UNSUPPORTED')
  88  |     const unchanged: AuthoringJobView = await page.request.get(`/api/v1/authoring/jobs/${ack.id}`).then(v => v.json())
  89  |     expect(unchanged.consent_id).toBeNull(); expect(unchanged.proposal_id).toBeNull(); expect(unchanged.raw_answer).toBeNull()
  90  |     await role(page, runtime.origin, 'learner')
  91  |     await page.getByRole('button', { name: '创作', exact: true }).click()
  92  |     await expect(dialog.getByLabel('例题主题', { exact: true })).toHaveCount(0)
  93  |     await expect(dialog.getByRole('region', { name: '受保护创作详情', exact: true })).toHaveCount(0)
  94  |     const cancelling = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith(`/api/v1/jobs/${ack.id}/cancel`))
  95  |     await dialog.getByRole('button', { name: `明确取消任务 ${ack.id}`, exact: true }).click()
  96  |     expect((await cancelling).status()).toBe(200)
  97  |     await expect(dialog.getByText(new RegExp(`^${ack.id} · cancelled · r`))).toBeVisible()
  98  |     const final: AuthoringJobPage = await page.request.get('/api/v1/authoring/jobs').then(v => v.json())
  99  |     expect(final.items).toHaveLength(1); expect(final.items[0].status).toBe('cancelled')
  100 |     expect(final.items[0].result_refs).toEqual([]); expect(final.items[0].warnings).toEqual([])
  101 |     expect(JSON.stringify(final)).not.toContain(original.request.topic)
  102 |     expect(runtime.control().received_request_count).toBe(0)
  103 |     writeFileSync(info.outputPath('actual-authoring-no-proof.json'), JSON.stringify({ scope: 'Real local HTTP/SQLite/worker/browser. Production-style empty proof registry; original synthetic provider configuration only. Preview rejected, zero dispatch, learner safe cancellation. No model or numeric result.', prepared: original, no_proposal: unchanged, safe_final: final, runtime: runtime.control() }, null, 2))
  104 |   } finally { await runtime.close() }
  105 | })
  106 | 
  107 | test('explicit same-Job loopback grant creates a draft and numeric preview needs its own decision', async ({ playwright }, info) => {
  108 |   test.setTimeout(120_000)
  109 |   const runtime = await AuthoringRuntime.start('complete'), errors: string[] = []
  110 |   try {
  111 |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
  112 |     page.on('pageerror', error => errors.push(error.message))
  113 |     await runtime.authenticateOnly(page); await role(page, runtime.origin, 'author'); await configure(page, runtime)
  114 |     let prepares = 0
  115 |     page.on('request', value => { if (value.method() === 'POST' && value.url().endsWith('/api/v1/authoring/jobs')) prepares++ })
  116 |     const { dialog, ack } = await prepare(page)
  117 |     expect(runtime.control().proof_registered).toBe(true); expect(runtime.control().received_request_count).toBe(0)
  118 |     const previewResponse = await preview(page, dialog); expect(previewResponse.status()).toBe(201)
  119 |     const proposal: ConsentProposalView = await previewResponse.json()
  120 |     expect(proposal.summary.job_id).toBe(ack.id); expect(proposal.summary.purpose).toBe('authoring')
  121 |     expect(runtime.control().received_request_count).toBe(0)
  122 |     await dialog.getByLabel('我已核对本次例题的冻结范围、提供商、预算与到期时间', { exact: true }).check()
  123 |     await dialog.getByRole('button', { name: '准备批准例题模型调用', exact: true }).click()
  124 |     const granting = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith('/api/v1/consents'))
  125 |     await dialog.getByRole('button', { name: '确认发送批准授权', exact: true }).click()
  126 |     expect((await granting).status()).toBe(201)
  127 |     let current!: AuthoringJobView
  128 |     await expect.poll(async () => { current = await page.request.get(`/api/v1/authoring/jobs/${ack.id}`).then(v => v.json()); return current.summary.status }, { timeout: 10_000 }).toBe('completed')
  129 |     await dialog.getByRole('button', { name: '重新读取本次创作任务', exact: true }).click()
  130 |     await dialog.getByRole('button', { name: '读取这份准确例题候选', exact: true }).click()
  131 |     const candidate = current.summary.candidate; expect(candidate).not.toBeNull()
  132 |     const draft: AuthoringDraftView = await page.request.get(`/api/v1/authoring/drafts/${candidate!.draft_id}`).then(v => v.json())
  133 |     expect(draft.state).toBe('draft'); expect(draft.base_ref).toBeNull(); expect(draft.numeric_check_ids).toEqual([])
  134 |     expect(current.raw_answer).toBe(runtime.control().answer_markdown)
  135 |     await expect(dialog.getByLabel('完整候选正文', { exact: true })).toHaveText(draft.payload.body_markdown)
  136 |     expect(draft.validation.mathematical).toBe('NOT_RUN'); expect(draft.validation.independent_pedagogy).toBe('NOT_RUN')
  137 |     const rejectedPreview = await numericPreview(page, dialog, candidate!.draft_id)
  138 |     expect((await page.request.get('/api/v1/authoring/jobs').then(v => v.json()) as AuthoringJobPage).items).toHaveLength(1)
  139 |     const declining = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith(`/api/v1/authoring/numeric-checks/${rejectedPreview.id}/decision`))
  140 |     await dialog.getByRole('button', { name: '明确拒绝本次数值执行', exact: true }).click()
  141 |     const declinedAck = await declining; expect(declinedAck.status()).toBe(200); expect((await declinedAck.json()).job).toBeNull()
  142 |     await dialog.getByRole('button', { name: '另行读取数值检查当前状态', exact: true }).click()
  143 |     await expect(dialog.getByText('当前决定：decline · r2', { exact: true })).toBeVisible()
  144 |     const approvedPreview = await numericPreview(page, dialog, candidate!.draft_id)
  145 |     await dialog.getByLabel('我已核对全部变量、表达式、容差、候选与本机隔离范围，单独批准这一次执行', { exact: true }).check()
  146 |     const approving = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith(`/api/v1/authoring/numeric-checks/${approvedPreview.id}/decision`))
  147 |     await dialog.getByRole('button', { name: '明确批准本次数值执行', exact: true }).click()
  148 |     const approvedAck = await approving; expect(approvedAck.status()).toBe(202)
  149 |     const numericAck = await approvedAck.json(); expect(numericAck.job).not.toBeNull()
  150 |     let numeric!: NumericCheckView
  151 |     await expect.poll(async () => { numeric = await page.request.get(`/api/v1/authoring/numeric-checks/${approvedPreview.id}`).then(v => v.json()); return numeric.result !== null }, { timeout: 15_000 }).toBe(true)
  152 |     expect(['passed', 'environment_unavailable']).toContain(numeric.result!.outcome)
  153 |     expect(numeric.result!.verdict).toBe(numeric.result!.outcome === 'passed' ? 'PASS' : 'BLOCKED')
  154 |     await dialog.getByRole('button', { name: '另行读取数值检查当前状态', exact: true }).click()
  155 |     await expect(dialog.getByRole('heading', { name: `实际数值结果：${numeric.result!.verdict}`, exact: true })).toBeVisible()
  156 |     const finalDraft: AuthoringDraftView = await page.request.get(`/api/v1/authoring/drafts/${candidate!.draft_id}`).then(v => v.json())
  157 |     expect(finalDraft.candidate).toEqual(draft.candidate); expect(finalDraft.state).toBe('draft')
  158 |     expect(finalDraft.payload).toEqual(draft.payload); expect(finalDraft.numeric_check_ids).toEqual([rejectedPreview.id, approvedPreview.id])
  159 |     const wide = await screenshot(page, dialog, 1440, dialog.getByLabel('完整候选正文', { exact: true }), 'authoring-candidate-1440.png', info)
  160 |     const narrow = await screenshot(page, dialog, 390, dialog.getByLabel('完整候选正文', { exact: true }), 'authoring-candidate-390.png', info)
  161 |     await screenshot(page, dialog, 390, dialog.getByRole('region', { name: '实际数值结果', exact: true }), 'authoring-actual-numeric-390.png', info)
  162 |     await expect.poll(() => runtime.control().validated_request_count).toBe(1)
  163 |     expect(runtime.control().received_request_count).toBe(1); expect(runtime.control().invalid_request_count).toBe(0); expect(prepares).toBe(1)
  164 |     await role(page, runtime.origin, 'learner')
> 165 |     await page.getByRole('button', { name: '创作', exact: true }).click()
      |                                                                 ^ TimeoutError: locator.click: Timeout 10000ms exceeded.
  166 |     const control = dialog.getByRole('region', { name: '创作任务安全控制', exact: true })
  167 |     await expect(control.getByText('例题候选生成任务', { exact: true })).toBeVisible()
  168 |     await expect(control.getByText('独立数值检查任务', { exact: true })).toBeVisible()
  169 |     await expect(control.getByRole('button', { name: `明确取消任务 ${numericAck.job.id}`, exact: true })).toBeDisabled()
  170 |     await expect(dialog.getByLabel('完整候选正文', { exact: true })).toHaveCount(0)
  171 |     await expect(dialog.getByRole('region', { name: '独立数值执行批准', exact: true })).toHaveCount(0)
  172 |     const safe: AuthoringJobPage = await page.request.get('/api/v1/authoring/jobs').then(v => v.json())
  173 |     expect(new Set(safe.items.map(v => v.kind))).toEqual(new Set(['authoring', 'authoring_numeric_check']))
  174 |     expect(JSON.stringify(safe)).not.toContain(candidate!.draft_id); expect(JSON.stringify(safe)).not.toContain(approvedPreview.id)
  175 |     expect(errors).toEqual([])
  176 |     writeFileSync(info.outputPath('actual-authoring-loopback.json'), JSON.stringify({ scope: 'Actual test-only loopback full-byte protocol and native UI. One original authoring Job and one actual provider dispatch. Draft remains unpublished and unreviewed. Numeric decline has no Job; separate approve records actual environment verdict, BLOCKED is not arithmetic PASS. Both safe kinds discoverable after real learner role change.', prepares, proposal_id: proposal.id, completed: current, draft: finalDraft, declined_preview: rejectedPreview, approved_preview: approvedPreview, actual_numeric: numeric, safe_controls: safe, runtime: runtime.control(), viewport_bounds: { wide, narrow }, page_errors: errors }, null, 2))
  177 |   } finally { await runtime.close() }
  178 | })
  179 | 
```