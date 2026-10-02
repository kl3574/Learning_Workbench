# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: review-form-memory.spec.ts >> real Policy and role cycles retain unsent Review note and reason with fresh reads, explicit discard and zero automatic decisions
- Location: ../../tests/e2e/review-form-memory.spec.ts:7:1

# Error details

```
Error: expect(locator).toHaveValue(expected) failed

Locator:  getByRole('dialog', { name: '导入', exact: true }).getByRole('region', { name: '候选审核与原命令恢复', exact: true }).getByRole('region', { name: '恢复的临时审核表单 1', exact: true }).getByLabel('本次审核备注', { exact: true })
Expected: "尚未提交的原创备注 🧠"
Received: ""
Timeout:  5000ms

Call log:
  - Expect "toHaveValue" getByRole('dialog', { name: '导入', exact: true }).getByRole('region', { name: '候选审核与原命令恢复', exact: true }).getByRole('region', { name: '恢复的临时审核表单 1', exact: true }).getByLabel('本次审核备注', { exact: true }) with timeout 5000ms
  - waiting for getByRole('dialog', { name: '导入', exact: true }).getByRole('region', { name: '候选审核与原命令恢复', exact: true }).getByRole('region', { name: '恢复的临时审核表单 1', exact: true }).getByLabel('本次审核备注', { exact: true })
    11 × locator resolved to <textarea aria-label="本次审核备注"></textarea>
       - unexpected value ""

```

```yaml
- textbox "本次审核备注"
```

# Test source

```ts
  1  | import { writeFileSync } from 'node:fs'
  2  | import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
  3  | import type { AttemptSnapshot, ImportDraftSnapshot, StoredReviewReceipt } from '../../packages/contracts/generated/api-types'
  4  | import { RestartRuntime } from './restartRuntime'
  5  | import { importAssessmentPackage, originalAssessmentPackage } from './assessmentTestData'
  6  | 
  7  | test('real Policy and role cycles retain unsent Review note and reason with fresh reads, explicit discard and zero automatic decisions', async ({ playwright }, info) => {
  8  |   test.setTimeout(120_000)
  9  |   const runtime = await RestartRuntime.start(), errors: string[] = [], trace: { method: string; path: string; status: number }[] = []
  10 |   try {
  11 |     const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
  12 |     page.on('pageerror', error => errors.push(error.message)); page.on('response', r => { trace.push({ method: r.request().method(), path: new URL(r.url()).pathname, status: r.status() }) }); await runtime.authenticateOnly(page)
  13 |     const fixture = originalAssessmentPackage('reviewformpolicy')
  14 |     const imported = await importAssessmentPackage(page, fixture)
  15 |     await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  16 |     await page.getByRole('button', { name: '导入', exact: true }).click()
  17 |     const dialog = page.getByRole('dialog', { name: '导入', exact: true })
  18 |     await dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
  19 |     await expect(dialog.getByText('操作角色：作者', { exact: true })).toBeVisible()
  20 |     await dialog.getByLabel('解析格式').selectOption('markdown')
  21 |     await dialog.getByLabel('选择导入文件', { exact: true }).setInputFiles({ name: 'original-review-form.md', mimeType: 'text/markdown', buffer: Buffer.from('# 原创审核表单恢复材料\n\n只验证软件数据保留，不作学术验收。\n') })
  22 |     await dialog.getByRole('button', { name: '上传并生成预览', exact: true }).click()
  23 |     await expect(dialog.getByText('预览已就绪，等待确认', { exact: true })).toBeVisible()
  24 |     await expect(dialog.getByLabel('当前候选正文', { exact: true })).toBeVisible()
  25 |     const id = await dialog.getByLabel('选择预览候选').inputValue()
  26 |     const draft: ImportDraftSnapshot = await page.request.get(`/api/v1/drafts/${id}`).then(r => r.json())
  27 |     await dialog.getByRole('button', { name: '打开候选审核与恢复', exact: true }).click()
  28 |     const panel = dialog.getByRole('region', { name: '候选审核与原命令恢复', exact: true })
  29 |     await panel.getByLabel('我已核对候选 ID、修订、哈希与本次检查范围，明确创建审核任务。', { exact: true }).check()
  30 |     const creating = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/drafts/${id}/review`))
  31 |     await panel.getByRole('button', { name: '明确创建本次审核任务', exact: true }).click()
  32 |     const created = await creating; expect(created.status()).toBe(202); const ack = await created.json()
  33 |     await expect(panel.getByRole('button', { name: '另行读取当前审核回执', exact: true })).toBeEnabled()
  34 |     await panel.getByRole('button', { name: '另行读取当前审核回执', exact: true }).click()
  35 |     const original: StoredReviewReceipt = await page.request.get(`/api/v1/reviews/${ack.id}`).then(r => r.json())
  36 |     const note = '尚未提交的原创备注 🧠', reason = '尚未提交的原创人工理由：未进行真实学术验收。'
  37 |     await panel.getByLabel('本次审核备注', { exact: true }).fill(note)
  38 |     await panel.getByLabel('审核理由', { exact: true }).fill(reason)
  39 |     await panel.getByLabel('数学审核决定').selectOption('REJECTED')
  40 |     const writes: string[] = [], reads: string[] = []
  41 |     page.on('request', r => { if (/\/(?:review|decision)$/.test(r.url()) && r.method() === 'POST') writes.push(r.url()); if (r.method() === 'GET' && (r.url().endsWith(`/drafts/${id}`) || r.url().endsWith(`/reviews/${ack.id}`))) reads.push(r.url()) })
  42 |     const session = await page.request.get('/api/v1/session').then(r => r.json())
  43 |     const headers = { Origin: runtime.origin, 'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': crypto.randomUUID() }
  44 |     const started = await page.request.post(`/api/v1/assessments/${fixture.assessment.id}/attempts`, { headers, data: { assessment_ref: fixture.assessment, mode: 'independent' } })
  45 |     expect(started.status()).toBe(201); const attempt: AttemptSnapshot = await started.json()
  46 |     await expect(panel.getByText('当前只开放安全审核任务控制。候选、备注、审核回执与报告已收起；权限恢复后请明确重新读取。', { exact: true })).toBeVisible()
  47 |     await expect(panel.getByLabel('本次审核备注', { exact: true })).toHaveCount(0)
  48 |     await expect(panel.getByLabel('审核理由', { exact: true })).toHaveCount(0)
  49 |     const abandoned = await page.request.post(`/api/v1/attempts/${attempt.id}/abandon`, { headers: { ...headers, 'Idempotency-Key': crypto.randomUUID() }, data: { expected_revision: attempt.revision } })
  50 |     expect(abandoned.status()).toBe(200)
  51 |     const recover = panel.getByRole('button', { name: '核验原会话与准确基准，恢复临时审核表单', exact: true })
  52 |     await expect(recover).toBeEnabled(); expect(writes).toEqual([])
  53 |     await recover.click()
  54 |     const recoveredNote = panel.getByRole('region', { name: '恢复的临时审核表单 1', exact: true })
  55 |     const recoveredReason = panel.getByRole('region', { name: '恢复的临时审核表单 2', exact: true })
> 56 |     try { await expect(recoveredNote.getByLabel('本次审核备注', { exact: true })).toHaveValue(note) } catch (error) { writeFileSync(info.outputPath('panel.html'), await panel.innerHTML()); throw error }
     |                                                                             ^ Error: expect(locator).toHaveValue(expected) failed
  57 |     await expect(recoveredReason.getByLabel('审核理由', { exact: true })).toHaveValue(reason)
  58 |     await expect(recoveredReason.getByLabel('数学审核决定')).toHaveValue('REJECTED')
  59 |     await expect(recoveredReason.getByLabel('我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。', { exact: true })).not.toBeChecked()
  60 |     expect(reads.filter(url => url.endsWith(`/drafts/${id}`)).length).toBeGreaterThanOrEqual(2)
  61 |     expect(reads.some(url => url.endsWith(`/reviews/${ack.id}`))).toBe(true)
  62 |     await dialog.getByRole('button', { name: '切换为学习者角色', exact: true }).click()
  63 |     await expect(dialog.getByText('操作角色：学习者', { exact: true })).toBeVisible()
  64 |     await expect(panel.getByLabel('审核理由', { exact: true })).toHaveCount(0)
  65 |     await dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
  66 |     await expect(recover).toBeEnabled(); await expect(recoveredReason).toHaveCount(0)
  67 |     await recover.click(); await expect(recoveredReason.getByLabel('审核理由', { exact: true })).toHaveValue(reason)
  68 |     expect(writes).toEqual([])
  69 |     expect(await page.request.get(`/api/v1/reviews/${ack.id}`).then(r => r.json())).toEqual(original)
  70 |     expect(await page.request.get(`/api/v1/drafts/${id}`).then(r => r.json())).toEqual(draft)
  71 |     await dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  72 |     await page.getByRole('button', { name: '返回导入与审核', exact: true }).click()
  73 |     await expect(recoveredReason.getByLabel('审核理由', { exact: true })).toHaveValue(reason)
  74 |     await dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  75 |     await page.getByRole('button', { name: '保留审核原命令，明确丢弃临时表单并关闭', exact: true }).click()
  76 |     await page.getByRole('button', { name: '导入', exact: true }).click()
  77 |     await dialog.getByRole('button', { name: '打开候选审核与恢复', exact: true }).click()
  78 |     await expect(panel.getByRole('button', { name: `读取审核任务 ${ack.id}`, exact: true })).toBeVisible()
  79 |     await expect(recover).toHaveCount(0)
  80 |     expect(writes).toEqual([]); expect(errors).toEqual([])
  81 |     writeFileSync(info.outputPath('review-form-memory.json'), JSON.stringify({ scope: 'Synthetic UI, real SQLite/HTTP/worker/Policy; no academic approval', candidate: { id, revision: draft.revision, sha256: draft.candidate_sha256 }, original_review: original, attempt_id: attempt.id, protected_reads: reads, automatic_writes: writes, errors }, null, 2))
  82 |   } finally { writeFileSync(info.outputPath('http-trace.json'), JSON.stringify(trace, null, 2)); await runtime.close() }
  83 | })
  84 | 
```