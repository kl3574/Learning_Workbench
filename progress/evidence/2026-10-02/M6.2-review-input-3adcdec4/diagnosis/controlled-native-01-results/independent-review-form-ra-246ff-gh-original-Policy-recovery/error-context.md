# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: independent-review-form-race.spec.ts >> independent audit held real Review GET interleaves native fill and preserves exact form memory through original Policy recovery
- Location: ../../tests/e2e/independent-review-form-race.spec.ts:7:1

# Error details

```
Error: expect(received).toEqual(expected) // deep equality

- Expected  - 1
+ Received  + 1

  Array [
-   "尚未提交的原创备注 🧠",
+   "",
  ]
```

# Test source

```ts
  1   | import { writeFileSync } from 'node:fs'
  2   | import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  3   | import type { AttemptSnapshot, ImportDraftSnapshot, StoredReviewReceipt } from '../../packages/contracts/generated/api-types'
  4   | import { RestartRuntime } from './restartRuntime'
  5   | import { importAssessmentPackage, originalAssessmentPackage } from './assessmentTestData'
  6   | 
  7   | test('independent audit held real Review GET interleaves native fill and preserves exact form memory through original Policy recovery', async ({ playwright }, info) => {
  8   |   test.setTimeout(120_000)
  9   |   const runtime = await RestartRuntime.start(), errors: string[] = [], trace: { method: string; path: string; status: number }[] = []
  10  |   try {
  11  |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
  12  |     page.on('pageerror', error => errors.push(error.message)); page.on('response', r => { trace.push({ method: r.request().method(), path: new URL(r.url()).pathname, status: r.status() }) }); await runtime.authenticateOnly(page)
  13  |     const fixture = originalAssessmentPackage('reviewformpolicy')
  14  |     const imported = await importAssessmentPackage(page, fixture)
  15  |     await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  16  |     await page.getByRole('button', { name: '导入', exact: true }).click()
  17  |     const dialog = page.getByRole('dialog', { name: '导入', exact: true })
  18  |     await dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
  19  |     await expect(dialog.getByText('操作角色：作者', { exact: true })).toBeVisible()
  20  |     await dialog.getByLabel('解析格式').selectOption('markdown')
  21  |     await dialog.getByLabel('选择导入文件', { exact: true }).setInputFiles({ name: 'original-review-form.md', mimeType: 'text/markdown', buffer: Buffer.from('# 原创审核表单恢复材料\n\n只验证软件数据保留，不作学术验收。\n') })
  22  |     await dialog.getByRole('button', { name: '上传并生成预览', exact: true }).click()
  23  |     await expect(dialog.getByText('预览已就绪，等待确认', { exact: true })).toBeVisible()
  24  |     await expect(dialog.getByLabel('当前候选正文', { exact: true })).toBeVisible()
  25  |     const id = await dialog.getByLabel('选择预览候选').inputValue()
  26  |     const draft: ImportDraftSnapshot = await page.request.get(`/api/v1/drafts/${id}`).then(r => r.json())
  27  |     await dialog.getByRole('button', { name: '打开候选审核与恢复', exact: true }).click()
  28  |     const panel = dialog.getByRole('region', { name: '候选审核与原命令恢复', exact: true })
  29  |     await panel.getByLabel('我已核对候选 ID、修订、哈希与本次检查范围，明确创建审核任务。', { exact: true }).check()
  30  |     const creating = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/drafts/${id}/review`))
  31  |     await panel.getByRole('button', { name: '明确创建本次审核任务', exact: true }).click()
  32  |     const created = await creating; expect(created.status()).toBe(202); const ack = await created.json()
  33  |     await expect(panel.getByRole('button', { name: '另行读取当前审核回执', exact: true })).toBeEnabled()
  34  |     let releaseRead!: () => void, readHeld!: () => void
  35  |     const release = new Promise<void>(resolve => { releaseRead = resolve })
  36  |     const held = new Promise<void>(resolve => { readHeld = resolve })
  37  |     let intercepted = false
  38  |     await page.route(`**/api/v1/reviews/${ack.id}`, async route => {
  39  |       if (intercepted || route.request().method() !== 'GET') { await route.continue(); return }
  40  |       intercepted = true
  41  |       const response = await route.fetch()
  42  |       readHeld(); await release; await route.fulfill({ response })
  43  |     })
  44  |     await panel.getByRole('button', { name: '另行读取当前审核回执', exact: true }).click()
  45  |     await held
  46  |     await expect(panel.getByLabel('本次审核备注', { exact: true })).toBeDisabled()
  47  |     const original: StoredReviewReceipt = await page.request.get(`/api/v1/reviews/${ack.id}`).then(r => r.json())
  48  |     const note = '尚未提交的原创备注 🧠', reason = '尚未提交的原创人工理由：未进行真实学术验收。'
  49  |     const filling = panel.getByLabel('本次审核备注', { exact: true }).fill(note)
  50  |     releaseRead(); await filling
  51  |     const samples: unknown[] = []
  52  |     const observe = async (stage: string) => {
  53  |       const snapshot = await page.evaluate(async ({ stage, id }) => {
  54  |         const response = await fetch('/api/v1/session', { credentials: 'same-origin' })
  55  |         const session = await response.json()
  56  |         if (session.role !== 'author' || session.active_independent_attempt_id !== null || session.active_open_book_attempt_id !== null) throw new Error('Synthetic probe cannot inspect restricted form')
  57  |         const path = '/src/features/draftReview/reviewFormMemory.ts'
  58  |         const memory = await import(path)
  59  |         const forms = memory.originalReviewForms(session.workspace_id, 'import', session.actor_session_id)
  60  |         return { stage, forms: forms.map((form: {kind: string; candidate: {draft_id: string}; value: object}) => ({ kind: form.kind, matches: form.candidate.draft_id === id, value: form.value })), notes: [...document.querySelectorAll<HTMLTextAreaElement>('textarea[aria-label="本次审核备注"]')].map(el => el.value) }
  61  |       }, { stage, id })
  62  |       samples.push(snapshot)
  63  |       writeFileSync(info.outputPath('independent-form-memory-observations.json'), JSON.stringify(samples, null, 2))
  64  |       return snapshot
  65  |     }
  66  |     const justFilled = await observe('native_fill_completed')
> 67  |     expect(justFilled.notes).toEqual([note])
      |                              ^ Error: expect(received).toEqual(expected) // deep equality
  68  |     expect(justFilled.forms).toContainEqual(expect.objectContaining({ kind: 'create', matches: true, value: expect.objectContaining({ note }) }))
  69  |     await panel.getByLabel('审核理由', { exact: true }).fill(reason)
  70  |     await panel.getByLabel('数学审核决定').selectOption('REJECTED')
  71  |     await observe('after_reason_and_math_inputs')
  72  |     const writes: string[] = [], reads: string[] = []
  73  |     page.on('request', r => { if (/\/(?:review|decision)$/.test(r.url()) && r.method() === 'POST') writes.push(r.url()); if (r.method() === 'GET' && (r.url().endsWith(`/drafts/${id}`) || r.url().endsWith(`/reviews/${ack.id}`))) reads.push(r.url()) })
  74  |     const session = await page.request.get('/api/v1/session').then(r => r.json())
  75  |     const headers = { Origin: runtime.origin, 'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': crypto.randomUUID() }
  76  |     const started = await page.request.post(`/api/v1/assessments/${fixture.assessment.id}/attempts`, { headers, data: { assessment_ref: fixture.assessment, mode: 'independent' } })
  77  |     expect(started.status()).toBe(201); const attempt: AttemptSnapshot = await started.json()
  78  |     await expect(panel.getByText('当前只开放安全审核任务控制。候选、备注、审核回执与报告已收起；权限恢复后请明确重新读取。', { exact: true })).toBeVisible()
  79  |     await expect(panel.getByLabel('本次审核备注', { exact: true })).toHaveCount(0)
  80  |     await expect(panel.getByLabel('审核理由', { exact: true })).toHaveCount(0)
  81  |     const abandoned = await page.request.post(`/api/v1/attempts/${attempt.id}/abandon`, { headers: { ...headers, 'Idempotency-Key': crypto.randomUUID() }, data: { expected_revision: attempt.revision } })
  82  |     expect(abandoned.status()).toBe(200)
  83  |     const recover = panel.getByRole('button', { name: '核验原会话与准确基准，恢复临时审核表单', exact: true })
  84  |     await expect(recover).toBeEnabled(); expect(writes).toEqual([])
  85  |     await recover.click()
  86  |     const recoveredNote = panel.getByRole('region', { name: '恢复的临时审核表单 1', exact: true })
  87  |     const recoveredReason = panel.getByRole('region', { name: '恢复的临时审核表单 2', exact: true })
  88  |     try { await expect(recoveredNote.getByLabel('本次审核备注', { exact: true })).toHaveValue(note) } catch (error) { writeFileSync(info.outputPath('panel.html'), await panel.innerHTML()); throw error }
  89  |     await observe('explicit_recovery_completed')
  90  |     await expect(recoveredReason.getByLabel('审核理由', { exact: true })).toHaveValue(reason)
  91  |     await expect(recoveredReason.getByLabel('数学审核决定')).toHaveValue('REJECTED')
  92  |     await expect(recoveredReason.getByLabel('我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。', { exact: true })).not.toBeChecked()
  93  |     expect(reads.filter(url => url.endsWith(`/drafts/${id}`)).length).toBeGreaterThanOrEqual(2)
  94  |     expect(reads.some(url => url.endsWith(`/reviews/${ack.id}`))).toBe(true)
  95  |     await dialog.getByRole('button', { name: '切换为学习者角色', exact: true }).click()
  96  |     await expect(dialog.getByText('操作角色：学习者', { exact: true })).toBeVisible()
  97  |     await expect(panel.getByLabel('审核理由', { exact: true })).toHaveCount(0)
  98  |     await dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
  99  |     await expect(recover).toBeEnabled(); await expect(recoveredReason).toHaveCount(0)
  100 |     await recover.click(); await expect(recoveredReason.getByLabel('审核理由', { exact: true })).toHaveValue(reason)
  101 |     expect(writes).toEqual([])
  102 |     expect(await page.request.get(`/api/v1/reviews/${ack.id}`).then(r => r.json())).toEqual(original)
  103 |     expect(await page.request.get(`/api/v1/drafts/${id}`).then(r => r.json())).toEqual(draft)
  104 |     await dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  105 |     await page.getByRole('button', { name: '返回导入与审核', exact: true }).click()
  106 |     await expect(recoveredReason.getByLabel('审核理由', { exact: true })).toHaveValue(reason)
  107 |     await dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  108 |     await page.getByRole('button', { name: '保留审核原命令，明确丢弃临时表单并关闭', exact: true }).click()
  109 |     await page.getByRole('button', { name: '导入', exact: true }).click()
  110 |     await dialog.getByRole('button', { name: '打开候选审核与恢复', exact: true }).click()
  111 |     await expect(panel.getByRole('button', { name: `读取审核任务 ${ack.id}`, exact: true })).toBeVisible()
  112 |     await expect(recover).toHaveCount(0)
  113 |     expect(writes).toEqual([]); expect(errors).toEqual([])
  114 |     writeFileSync(info.outputPath('review-form-memory.json'), JSON.stringify({ scope: 'Synthetic UI, real SQLite/HTTP/worker/Policy; no academic approval', candidate: { id, revision: draft.revision, sha256: draft.candidate_sha256 }, original_review: original, attempt_id: attempt.id, protected_reads: reads, automatic_writes: writes, errors }, null, 2))
  115 |   } finally { writeFileSync(info.outputPath('http-trace.json'), JSON.stringify(trace, null, 2)); await runtime.close() }
  116 | })
  117 | 
```