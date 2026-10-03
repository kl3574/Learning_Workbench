# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: review-form-publication-input.spec.ts >> Publication refresh preserves Review input and focus while blocking submission, then original Policy recovery preserves both forms
- Location: ../../tests/e2e/review-form-publication-input.spec.ts:7:1

# Error details

```
Error: expect(locator).toBeEditable() failed

Locator:  getByRole('dialog', { name: '导入', exact: true }).getByRole('region', { name: '候选审核与原命令恢复', exact: true }).getByLabel('本次审核备注', { exact: true })
Expected: editable
Received: disabled
Timeout:  5000ms

Call log:
  - Expect "toBeEditable" getByRole('dialog', { name: '导入', exact: true }).getByRole('region', { name: '候选审核与原命令恢复', exact: true }).getByLabel('本次审核备注', { exact: true }) with timeout 5000ms
  - waiting for getByRole('dialog', { name: '导入', exact: true }).getByRole('region', { name: '候选审核与原命令恢复', exact: true }).getByLabel('本次审核备注', { exact: true })
    14 × locator resolved to <textarea disabled aria-label="本次审核备注"></textarea>
       - unexpected value "disabled"

```

```yaml
- textbox "本次审核备注" [disabled]
```

# Test source

```ts
  1   | import { writeFileSync } from 'node:fs'
  2   | import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  3   | import type { AttemptSnapshot, ImportDraftSnapshot, StoredReviewReceipt } from '../../packages/contracts/generated/api-types'
  4   | import { RestartRuntime } from './restartRuntime'
  5   | import { importAssessmentPackage, originalAssessmentPackage } from './assessmentTestData'
  6   | 
  7   | test('Publication refresh preserves Review input and focus while blocking submission, then original Policy recovery preserves both forms', async ({ playwright }, info) => {
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
  34  |     // Delay only the named Publication read port's actual session response.
  35  |     // No fabricated response, input event, form value or backend mutation.
  36  |     await page.evaluate(async () => {
  37  |       const path = '/src/features/draftPublication/publicationClient.ts'
  38  |       const { publicationClient } = await import(path), original = publicationClient.session
  39  |       let release!: () => void
  40  |       const gate = new Promise<void>(resolve => { release = resolve })
  41  |       let once = false
  42  |       publicationClient.session = async () => {
  43  |         const actual = await original()
  44  |         if (!once) { once = true; Object.assign(window, { reviewPublicationReadHeld: true }); await gate }
  45  |         return actual
  46  |       }
  47  |       Object.assign(window, { releaseReviewPublicationRead: release })
  48  |     })
  49  |     await panel.getByRole('button', { name: '另行读取当前审核回执', exact: true }).click()
  50  |     const original: StoredReviewReceipt = await page.request.get(`/api/v1/reviews/${ack.id}`).then(r => r.json())
  51  |     const note = '尚未提交的原创备注 🧠', reason = '尚未提交的原创人工理由：未进行真实学术验收。'
  52  |     await expect.poll(() => page.evaluate(() => (window as unknown as { reviewPublicationReadHeld?: boolean }).reviewPublicationReadHeld === true)).toBe(true)
  53  |     const publication = panel.getByRole('region', { name: 'Import 文本块发布与恢复', exact: true })
  54  |     await expect(publication.getByRole('button', { name: '重新核验发布权限与本机记录', exact: true })).toBeDisabled()
  55  |     const noteInput = panel.getByLabel('本次审核备注', { exact: true })
> 56  |     await expect(noteInput).toBeEditable()
      |                             ^ Error: expect(locator).toBeEditable() failed
  57  |     await noteInput.focus(); await expect(noteInput).toBeFocused()
  58  |     await noteInput.fill(note); await expect(noteInput).toHaveValue(note)
  59  |     await expect(noteInput).toBeFocused()
  60  |     await expect(panel.getByRole('button', { name: '明确创建本次审核任务', exact: true })).toBeDisabled()
  61  |     await panel.getByLabel('审核理由', { exact: true }).fill(reason)
  62  |     await panel.getByLabel('数学审核决定').selectOption('REJECTED')
  63  |     await panel.getByLabel('来源审核决定').selectOption('REJECTED')
  64  |     await panel.getByLabel('我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。', { exact: true }).check()
  65  |     await expect(panel.getByRole('button', { name: '明确保存这次人工审核决定', exact: true })).toBeDisabled()
  66  |     expect(trace.filter(row => row.method === 'POST' && row.path.endsWith('/decision'))).toEqual([])
  67  |     await page.evaluate(() => (window as unknown as { releaseReviewPublicationRead: () => void }).releaseReviewPublicationRead())
  68  |     await expect(panel.getByRole('button', { name: '明确创建本次审核任务', exact: true })).toBeEnabled()
  69  |     await expect(panel.getByRole('button', { name: '明确保存这次人工审核决定', exact: true })).toBeEnabled()
  70  |     const writes: string[] = [], reads: string[] = []
  71  |     page.on('request', r => { if (/\/(?:review|decision)$/.test(r.url()) && r.method() === 'POST') writes.push(r.url()); if (r.method() === 'GET' && (r.url().endsWith(`/drafts/${id}`) || r.url().endsWith(`/reviews/${ack.id}`))) reads.push(r.url()) })
  72  |     const session = await page.request.get('/api/v1/session').then(r => r.json())
  73  |     const headers = { Origin: runtime.origin, 'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': crypto.randomUUID() }
  74  |     const started = await page.request.post(`/api/v1/assessments/${fixture.assessment.id}/attempts`, { headers, data: { assessment_ref: fixture.assessment, mode: 'independent' } })
  75  |     expect(started.status()).toBe(201); const attempt: AttemptSnapshot = await started.json()
  76  |     await expect(panel.getByText('当前只开放安全审核任务控制。候选、备注、审核回执与报告已收起；权限恢复后请明确重新读取。', { exact: true })).toBeVisible()
  77  |     await expect(panel.getByLabel('本次审核备注', { exact: true })).toHaveCount(0)
  78  |     await expect(panel.getByLabel('审核理由', { exact: true })).toHaveCount(0)
  79  |     const abandoned = await page.request.post(`/api/v1/attempts/${attempt.id}/abandon`, { headers: { ...headers, 'Idempotency-Key': crypto.randomUUID() }, data: { expected_revision: attempt.revision } })
  80  |     expect(abandoned.status()).toBe(200)
  81  |     const recover = panel.getByRole('button', { name: '核验原会话与准确基准，恢复临时审核表单', exact: true })
  82  |     await expect(recover).toBeEnabled(); expect(writes).toEqual([])
  83  |     await recover.click()
  84  |     const recoveredNote = panel.getByRole('region', { name: '恢复的临时审核表单 1', exact: true })
  85  |     const recoveredReason = panel.getByRole('region', { name: '恢复的临时审核表单 2', exact: true })
  86  |     try { await expect(recoveredNote.getByLabel('本次审核备注', { exact: true })).toHaveValue(note) } catch (error) { writeFileSync(info.outputPath('panel.html'), await panel.innerHTML()); throw error }
  87  |     await expect(recoveredReason.getByLabel('审核理由', { exact: true })).toHaveValue(reason)
  88  |     await expect(recoveredReason.getByLabel('数学审核决定')).toHaveValue('REJECTED')
  89  |     await expect(recoveredReason.getByLabel('我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。', { exact: true })).not.toBeChecked()
  90  |     expect(reads.filter(url => url.endsWith(`/drafts/${id}`)).length).toBeGreaterThanOrEqual(2)
  91  |     expect(reads.some(url => url.endsWith(`/reviews/${ack.id}`))).toBe(true)
  92  |     await dialog.getByRole('button', { name: '切换为学习者角色', exact: true }).click()
  93  |     await expect(dialog.getByText('操作角色：学习者', { exact: true })).toBeVisible()
  94  |     await expect(panel.getByLabel('审核理由', { exact: true })).toHaveCount(0)
  95  |     await dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
  96  |     await expect(recover).toBeEnabled(); await expect(recoveredReason).toHaveCount(0)
  97  |     await recover.click(); await expect(recoveredReason.getByLabel('审核理由', { exact: true })).toHaveValue(reason)
  98  |     expect(writes).toEqual([])
  99  |     expect(await page.request.get(`/api/v1/reviews/${ack.id}`).then(r => r.json())).toEqual(original)
  100 |     expect(await page.request.get(`/api/v1/drafts/${id}`).then(r => r.json())).toEqual(draft)
  101 |     await dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  102 |     await page.getByRole('button', { name: '返回导入与审核', exact: true }).click()
  103 |     await expect(recoveredReason.getByLabel('审核理由', { exact: true })).toHaveValue(reason)
  104 |     await dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  105 |     await page.getByRole('button', { name: '保留审核原命令，明确丢弃临时表单并关闭', exact: true }).click()
  106 |     await page.getByRole('button', { name: '导入', exact: true }).click()
  107 |     await dialog.getByRole('button', { name: '打开候选审核与恢复', exact: true }).click()
  108 |     await expect(panel.getByRole('button', { name: `读取审核任务 ${ack.id}`, exact: true })).toBeVisible()
  109 |     await expect(recover).toHaveCount(0)
  110 |     expect(writes).toEqual([]); expect(errors).toEqual([])
  111 |     writeFileSync(info.outputPath('review-form-publication-input.json'), JSON.stringify({ scope: 'Synthetic UI, real SQLite/HTTP/worker/Policy; no academic approval', candidate: { id, revision: draft.revision, sha256: draft.candidate_sha256 }, original_review: original, attempt_id: attempt.id, protected_reads: reads, automatic_writes: writes, errors }, null, 2))
  112 |   } finally { writeFileSync(info.outputPath('http-trace.json'), JSON.stringify(trace, null, 2)); await runtime.close() }
  113 | })
  114 | 
```