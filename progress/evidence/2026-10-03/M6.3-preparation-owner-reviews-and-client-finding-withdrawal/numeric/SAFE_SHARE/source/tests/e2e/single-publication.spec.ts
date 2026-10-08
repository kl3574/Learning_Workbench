import { writeFileSync } from 'node:fs'
import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { AuthoringDraftView, AuthoringJobView, ContentRef, NumericCheckView, SessionResponse, StoredReviewReceipt } from '../../packages/contracts/generated/api-types'
import { AuthoringRuntime } from './authoringRuntime'
import { role, configure, prepare, preview, numericPreview, screenshot } from './authoringTestData'

test('single generated example uses actual sealed numeric facts and fresh human Review before independent publication readback', async ({ playwright }, info) => {
  test.setTimeout(120_000)
  const runtime = await AuthoringRuntime.start('complete'), errors: string[] = []
  const writes: { key: string | null; body: unknown }[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    page.on('pageerror', error => errors.push(error.message))
    await runtime.authenticateOnly(page); await role(page, runtime.origin, 'author'); await configure(page, runtime)
    const { dialog, ack } = await prepare(page)
    expect((await preview(page, dialog)).status()).toBe(201)
    await dialog.getByLabel('我已核对本次例题的冻结范围、提供商、预算与到期时间', { exact: true }).check()
    await dialog.getByRole('button', { name: '准备批准例题模型调用', exact: true }).click()
    const granting = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/api/v1/consents'))
    await dialog.getByRole('button', { name: '确认发送批准授权', exact: true }).click(); expect((await granting).status()).toBe(201)
    let generated!: AuthoringJobView
    await expect.poll(async () => { generated = await page.request.get(`/api/v1/authoring/jobs/${ack.id}`).then(r => r.json()); return generated.summary.status }, { timeout: 10_000 }).toBe('completed')
    await dialog.getByRole('button', { name: '重新读取本次创作任务', exact: true }).click()
    await dialog.getByRole('button', { name: '读取这份准确例题候选', exact: true }).click()
    const candidate = generated.summary.candidate!; expect(candidate).not.toBeNull()
    const original: AuthoringDraftView = await page.request.get(`/api/v1/authoring/drafts/${candidate.draft_id}`).then(r => r.json())
    expect(original.state).toBe('draft'); expect(original.published_ref).toBeNull()
    const numeric = await numericPreview(page, dialog, candidate.draft_id)
    await dialog.getByLabel('我已核对全部变量、表达式、容差、候选与本机隔离范围，单独批准这一次执行', { exact: true }).check()
    const approving = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/numeric-checks/${numeric.id}/decision`))
    await dialog.getByRole('button', { name: '明确批准本次数值执行', exact: true }).click()
    const approval = await approving; expect(approval.status()).toBe(202); const numericAck = await approval.json()
    let actual!: NumericCheckView
    await expect.poll(async () => { actual = await page.request.get(`/api/v1/authoring/numeric-checks/${numeric.id}`).then(r => r.json()); return actual.result !== null }, { timeout: 30_000 }).toBe(true)
    expect(['passed', 'environment_unavailable']).toContain(actual.result!.outcome)
    expect(actual.result!.verdict).toBe(actual.result!.outcome === 'passed' ? 'PASS' : 'BLOCKED')
    expect(actual.job!.id).toBe(numericAck.job.id)
    writeFileSync(info.outputPath('single-publication-actual.json'), JSON.stringify({
      stage: 'numeric_observed_before_review', scope: 'Actual sealed numeric result from the original controlled loopback fixture. Later Review, publication and browser assertions have not completed. No external provider or academic approval.',
      candidate, numericPreview: numeric, numericAck, actual, externalModelCalls: 0, physicalNumeric: actual.result!.verdict,
    }, null, 2))
    await dialog.getByRole('button', { name: '另行读取数值检查当前状态', exact: true }).click()
    await expect(dialog.getByRole('heading', { name: `实际数值结果：${actual.result!.verdict}`, exact: true })).toBeVisible()
    await dialog.getByRole('button', { name: '刷新候选的检查记录', exact: true }).click()
    await dialog.getByRole('button', { name: '打开候选审核与恢复', exact: true }).click()
    const review = dialog.getByRole('region', { name: '候选审核与原命令恢复', exact: true })
    await review.getByLabel('本次审核备注', { exact: true }).fill('实际数值终态之后的新审核；软件合成验收，不作学术或来源正确性批准。')
    await review.getByLabel('我已核对候选 ID、修订、哈希与本次检查范围，明确创建审核任务。', { exact: true }).check()
    const reviewing = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/drafts/${candidate.draft_id}/review`))
    await review.getByRole('button', { name: '明确创建本次审核任务', exact: true }).click()
    const reviewResponse = await reviewing; expect(reviewResponse.status()).toBe(202); const reviewJob = await reviewResponse.json()
    const readReview = review.getByRole('button', { name: '另行读取当前审核回执', exact: true })
    await expect(readReview).toBeEnabled(); await readReview.click()
    const human = review.getByRole('region', { name: '明确人工审核决定', exact: true })
    await human.getByLabel('数学审核决定').selectOption('APPROVED'); await human.getByLabel('来源审核决定').selectOption('APPROVED')
    await human.getByLabel('审核理由').fill('仅原创合成协议验收：新人工决定不能覆盖数值失败，不声称数学、来源或教学已验收。')
    await human.getByLabel('我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。', { exact: true }).check()
    const deciding = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/reviews/${reviewJob.id}/decision`))
    await human.getByRole('button', { name: '明确保存这次人工审核决定', exact: true }).click(); expect((await deciding).status()).toBe(200)
    await expect(readReview).toBeEnabled(); await readReview.click()
    const receipt: StoredReviewReceipt = await page.request.get(`/api/v1/reviews/${reviewJob.id}`).then(r => r.json())
    const publication = review.getByRole('region', { name: '生成例题发布与恢复', exact: true })
    const selecting = publication.getByRole('button', { name: '选择此审核并重新读取生成发布基准', exact: true })
    await expect(selecting).toBeEnabled(); await selecting.click()
    const basis = publication.getByRole('region', { name: '本次生成发布基准', exact: true })
    let outcome: { status: number; body: unknown }, published: ContentRef | null = null
    if (actual.result!.verdict === 'BLOCKED') {
      expect(actual.result!.exit_code).not.toBe(0)
      await expect(publication.getByRole('status')).toBeVisible(); await expect(selecting).toBeEnabled()
      await expect(basis).toHaveCount(0); await expect(publication.getByRole('button', { name: '明确发布这一生成例题', exact: true })).toHaveCount(0)
      // The UI refused to form a publish command. Independently exercise the
      // actual server's numeric refusal, with explicit synthetic human intent.
      const session: SessionResponse = await page.request.get('/api/v1/session').then(r => r.json())
      const body = { expected_revision: candidate.draft_revision, expected_content_sha256: candidate.candidate_sha256,
        review_receipt_id: receipt.id, acknowledged_warning_codes: [...new Set([...generated.preparation.warnings, ...actual.warnings].filter(w => w.severity === 'warning').map(w => w.code))] }
      const response = await page.request.post(`/api/v1/drafts/${candidate.draft_id}/publish`, { data: body,
        headers: { Origin: runtime.origin, 'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': 'single-physical-blocked-refusal' } })
      outcome = { status: response.status(), body: await response.json() }
      expect(outcome.status).toBe(409); expect(outcome.body).toMatchObject({ error: { code: 'PUBLISH_NUMERIC_REQUIRED' } })
      await screenshot(page, dialog, 1440, publication, 'single-numeric-blocked-1440.png', info)
      await screenshot(page, dialog, 390, publication, 'single-numeric-blocked-390.png', info)
    } else {
      expect(actual.result!.exit_code).toBe(0); expect(actual.result!.started_at).not.toBeNull()
      expect(actual.result!.assertions.every(value => value.passed)).toBe(true)
      await expect(basis).toContainText(candidate.candidate_sha256)
      for (const checkbox of await basis.getByRole('group', { name: '逐条确认真实来源与数值警告', exact: true }).getByRole('checkbox').all()) await checkbox.check()
      await basis.getByLabel('我已核对原候选、来源、数值记录和所选人工审核，明确新建这一个公开例题块。', { exact: true }).check()
      let dropped = false
      await page.route(`**/api/v1/drafts/${candidate.draft_id}/publish`, async route => {
        writes.push({ key: await route.request().headerValue('Idempotency-Key'), body: route.request().postDataJSON() })
        if (!dropped) { const response = await route.fetch(); expect(response.status()).toBe(201); dropped = true; await route.abort('failed') } else await route.continue()
      })
      await basis.getByRole('button', { name: '明确发布这一生成例题', exact: true }).click()
      await expect(publication.getByText('发布结果未知，原 key 与完整命令保留', { exact: true })).toBeVisible()
      expect(writes).toHaveLength(1)
      const replaying = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/drafts/${candidate.draft_id}/publish`))
      await publication.getByRole('button', { name: `显式回放原生成发布命令 ${writes[0].key}`, exact: true }).click()
      const response = await replaying; outcome = { status: response.status(), body: await response.json() }
      expect(outcome.status).toBe(201); published = outcome.body as ContentRef
      expect(writes).toHaveLength(2); expect(writes[1]).toEqual(writes[0]); expect(published.revision).toBe(1)
      expect(published.sha256).not.toBe(candidate.candidate_sha256)
      await expect(publication.getByText('原生成发布 ACK 已保存', { exact: true })).toBeVisible()
      await publication.getByRole('button', { name: `另行读取该候选发布状态 ${candidate.draft_id}`, exact: true }).click()
      await expect(dialog.getByRole('region', { name: '例题草稿候选', exact: true })).toContainText('状态 published')
      await expect(dialog.getByRole('button', { name: '明确准备独立数值检查预览', exact: true })).toBeDisabled()
      await publication.getByRole('button', { name: `另行读取当前引用 ${published.id}`, exact: true }).click()
      await expect(publication).toContainText(`本次 GET current：${published.id} · r1`)
      expect(await page.request.get(`/api/v1/blocks/${published.id}/body?revision=1`).then(r => r.text())).toBe(original.payload.body_markdown)
      const block = await page.request.get(`/api/v1/blocks/${published.id}?revision=1`).then(r => r.json())
      expect(block.title).toBe(original.payload.title); expect(block.depends_on).toEqual(original.payload.declared_source_refs)
      expect(block.concepts).toEqual([]); expect(block.citations).toEqual([])
      await screenshot(page, dialog, 1440, publication, 'single-published-1440.png', info)
      await screenshot(page, dialog, 390, publication, 'single-published-390.png', info)
    }
    const finalDraft: AuthoringDraftView = await page.request.get(`/api/v1/authoring/drafts/${candidate.draft_id}`).then(r => r.json())
    expect(finalDraft.candidate).toEqual(original.candidate); expect(finalDraft.payload).toEqual(original.payload)
    expect(finalDraft.state).toBe(published ? 'published' : 'draft'); expect(finalDraft.published_ref).toEqual(published)
    expect(await page.request.get(`/api/v1/authoring/jobs/${ack.id}`).then(r => r.json())).toEqual(generated)
    expect(runtime.control().received_request_count).toBe(1); expect(runtime.control().validated_request_count).toBe(1)
    expect(runtime.control().invalid_request_count).toBe(0); expect(errors).toEqual([])
    writeFileSync(info.outputPath('single-publication-actual.json'), JSON.stringify({
      stage: 'closed_chain',
      scope: 'Real SQLite/HTTP/browser and actual sealed numeric runtime. The provider is a complete-byte controlled loopback fixture, never DeepSeek. Human decisions are synthetic software intent, not academic/source/teaching acceptance. Physical BLOCKED denies UI preparation and independently rejects HTTP publish; only actual physical PASS exercises lost-ACK publication and independent current/ref reads.',
      candidate, numericPreview: numeric, numericAck, actual, receipt, outcome, published, finalDraft, writes, errors,
      externalModelCalls: 0, loopbackCalls: 1, physicalNumeric: actual.result!.verdict,
    }, null, 2))
  } finally { await runtime.close() }
})
