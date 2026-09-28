import { createHash } from 'node:crypto'
import { readFileSync, writeFileSync } from 'node:fs'
import { expect, test, type Locator, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { DraftCandidate, ImportDraftSnapshot, ReviewJobAck, StoredReviewReceipt } from '../../packages/contracts/generated/api-types'
import { RestartRuntime } from './restartRuntime'

async function currentReceipt(page: Page, panel: Locator, id: string) {
  await panel.getByRole('button', { name: `读取审核任务 ${id}`, exact: true }).click()
  const read = panel.getByRole('button', { name: '另行读取当前审核回执', exact: true })
  await expect(read).toBeEnabled(); await read.click()
  await expect(panel.getByRole('region', { name: '当前审核回执', exact: true })).toBeVisible()
  const response = await page.request.get(`/api/v1/reviews/${id}`)
  expect(response.status()).toBe(200)
  return response.json() as Promise<StoredReviewReceipt>
}

test('real imported candidate review keeps original ACK, authenticated report bytes and explicit rejected decision across reload', async ({ playwright }, info) => {
  test.setTimeout(120_000)
  const runtime = await RestartRuntime.start(), errors: string[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    page.on('pageerror', error => errors.push(error.message))
    await runtime.authenticateOnly(page)
    await page.getByRole('button', { name: '导入', exact: true }).click()
    let dialog = page.getByRole('dialog', { name: '导入', exact: true })
    await dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
    await expect(dialog.getByText('操作角色：作者', { exact: true })).toBeVisible()
    await dialog.getByLabel('解析格式').selectOption('markdown')
    await dialog.getByLabel('选择导入文件', { exact: true }).setInputFiles({ name: 'synthetic-review.md', mimeType: 'text/markdown', buffer: Buffer.from('# 原创合成审核材料\n\n未经过真实人工审核的纯文本。\n') })
    const uploading = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/imports'))
    await dialog.getByRole('button', { name: '上传并生成预览', exact: true }).click()
    const imported = await uploading; expect(imported.status()).toBe(202)
    const importAck = await imported.json()
    await expect(dialog.getByText('预览已就绪，等待确认', { exact: true })).toBeVisible()
    await expect(dialog.getByLabel('当前候选正文', { exact: true })).toBeVisible()
    const selected = await dialog.getByLabel('选择预览候选').inputValue()
    const draft: ImportDraftSnapshot = await page.request.get(`/api/v1/drafts/${selected}`).then(value => value.json())
    const candidate: DraftCandidate = { draft_id: draft.id, draft_revision: draft.revision, entity: draft.kind, candidate_sha256: draft.candidate_sha256 }
    expect(draft.state).toBe('draft')
    await dialog.getByRole('button', { name: '打开候选审核与恢复', exact: true }).click()
    let panel = dialog.getByRole('region', { name: '候选审核与原命令恢复', exact: true })
    await expect(panel.getByRole('region', { name: '准备准确候选审核', exact: true })).toContainText(candidate.candidate_sha256)
    await expect(panel.getByRole('button', { name: '明确创建本次审核任务', exact: true })).toBeDisabled()
    const creates: { key: string; body: unknown }[] = []
    let created!: ReviewJobAck, droppedCreate = false
    const createPattern = `**/api/v1/drafts/${candidate.draft_id}/review`
    await page.route(createPattern, async route => {
      const request = route.request(); creates.push({ key: request.headers()['idempotency-key'], body: request.postDataJSON() })
      if (creates.length === 1) {
        const actual = await route.fetch(); expect(actual.status()).toBe(202); created = await actual.json()
        await route.abort('failed'); droppedCreate = true
      } else await route.continue()
    })
    await panel.getByLabel('本次审核备注', { exact: true }).fill('合成浏览器验证；不代表真实数学、来源或教学审校。')
    await panel.getByLabel('我已核对候选 ID、修订、哈希与本次检查范围，明确创建审核任务。', { exact: true }).check()
    await panel.getByRole('button', { name: '明确创建本次审核任务', exact: true }).click()
    await expect.poll(() => droppedCreate).toBe(true)
    await expect(panel.getByText('创建审核 · 结果未知，原 key 与完整命令保留', { exact: true })).toBeVisible()
    expect(creates).toHaveLength(1); expect(created.status).toBe('queued')
    const replaying = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith(`/api/v1/drafts/${candidate.draft_id}/review`))
    await panel.getByRole('button', { name: `显式回放原审核命令 ${creates[0].key}`, exact: true }).click()
    const replay = await replaying; expect(replay.status()).toBe(202); expect(await replay.json()).toEqual(created)
    expect(creates).toHaveLength(2); expect(creates[1]).toEqual(creates[0])
    await page.unroute(createPattern)
    const machine = await currentReceipt(page, panel, created.id)
    expect(machine.candidate).toEqual(candidate); expect(machine.revision).toBe(1)
    expect(machine.mathematical).toBe('NOT_RUN'); expect(machine.sources).toBe('NOT_RUN'); expect(machine.independent_pedagogy).toBe('NOT_RUN')
    await panel.getByRole('button', { name: '读取受控审核报告', exact: true }).click()
    await expect(panel.getByText('已取得的原报告文本', { exact: true })).toBeVisible()
    await panel.getByText('已取得的原报告文本', { exact: true }).scrollIntoViewIfNeeded()
    await page.screenshot({ path: info.outputPath('review-report-1440.png') })
    const actualReport = await page.request.get(machine.evidence_paths[0]); expect(actualReport.status()).toBe(200)
    const originalBytes = await actualReport.body(), digest = createHash('sha256').update(originalBytes).digest('hex')
    expect(actualReport.headers()['etag']).toBe(`"${digest}"`)
    await expect(panel.getByText('本次字节 SHA256：', { exact: false })).toContainText(digest)
    const downloading = page.waitForEvent('download')
    await panel.getByRole('button', { name: '下载审核附件 1', exact: true }).click()
    const download = await downloading, downloaded = info.outputPath('actual-report.json')
    await download.saveAs(downloaded); expect(readFileSync(downloaded)).toEqual(originalBytes)
    const decision = panel.getByRole('region', { name: '明确人工审核决定', exact: true })
    await expect(decision.getByLabel('数学审核决定')).toHaveValue('')
    await expect(decision.getByLabel('来源审核决定')).toHaveValue('')
    await decision.getByLabel('数学审核决定').selectOption('REJECTED')
    await decision.getByLabel('来源审核决定').selectOption('REJECTED')
    const reason = '原创合成拒绝：尚未进行真实数学、来源或独立教学验收。'
    await decision.getByLabel('审核理由').fill(reason)
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 }); await decision.scrollIntoViewIfNeeded()
      await page.screenshot({ path: info.outputPath(`review-decision-${width}.png`) })
      const geometry = await dialog.evaluate(element => ({ width: element.clientWidth, scroll: element.scrollWidth, document: document.documentElement.scrollWidth, viewport: innerWidth }))
      expect(geometry.scroll).toBeLessThanOrEqual(geometry.width + 1); expect(geometry.document).toBeLessThanOrEqual(geometry.viewport)
    }
    await page.setViewportSize({ width: 1440, height: 900 })
    await dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    await page.getByRole('dialog', { name: '保留审核原命令', exact: true }).getByRole('button', { name: '返回导入与审核', exact: true }).click()
    await expect(decision.getByLabel('审核理由')).toHaveValue(reason)
    await expect(decision.getByRole('button', { name: '明确保存这次人工审核决定', exact: true })).toBeDisabled()
    const decisions: { key: string; body: unknown }[] = []
    let decided!: StoredReviewReceipt, droppedDecision = false
    const decisionPattern = `**/api/v1/reviews/${created.id}/decision`
    await page.route(decisionPattern, async route => {
      const request = route.request(); decisions.push({ key: request.headers()['idempotency-key'], body: request.postDataJSON() })
      const actual = await route.fetch(); expect(actual.status()).toBe(200); decided = await actual.json()
      await route.abort('failed'); droppedDecision = true
    })
    await decision.getByLabel('我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。', { exact: true }).check()
    await decision.getByRole('button', { name: '明确保存这次人工审核决定', exact: true }).click()
    await expect.poll(() => droppedDecision).toBe(true)
    await expect(panel.getByText('人工决定 · 结果未知，原 key 与完整命令保留', { exact: true })).toBeVisible()
    expect(decisions).toHaveLength(1); expect(decided.revision).toBe(2)
    expect(decided.mathematical).toBe('REJECTED'); expect(decided.sources).toBe('REJECTED'); expect(decided.independent_pedagogy).toBe('NOT_RUN')
    expect(decided.decision_reason).toBe(reason); expect(decided.candidate).toEqual(candidate)
    expect(decisions[0].body).toEqual({ expected_revision: 1, candidate_sha256: candidate.candidate_sha256, mathematical: 'REJECTED', sources: 'REJECTED', reason, evidence_artifact_ids: [] })
    await expect(dialog.getByLabel('我已核对本次候选、警告和原件 SHA-256，确认按当前 ID 映射入库。导入不代表内容已经审校。', { exact: true })).not.toBeChecked()
    page.once('dialog', async dialog => { expect(dialog.type()).toBe('beforeunload'); await dialog.accept() })
    await page.reload(); await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible()
    await page.getByRole('button', { name: '导入', exact: true }).click()
    dialog = page.getByRole('dialog', { name: '导入', exact: true })
    await dialog.getByRole('button', { name: '打开候选审核与恢复', exact: true }).click()
    panel = dialog.getByRole('region', { name: '候选审核与原命令恢复', exact: true })
    await expect(panel.getByRole('button', { name: `显式回放原审核命令 ${decisions[0].key}`, exact: true })).toBeDisabled()
    await expect(panel.getByText('无法核对原操作者；刷新或访问代次变化后的原命令仅保留只读，不用新会话同 key 冒充原回放。', { exact: true })).toBeVisible()
    const recovered = await currentReceipt(page, panel, created.id)
    expect(recovered).toEqual(decided); expect(decisions).toHaveLength(1)
    expect((await page.request.get(`/api/v1/drafts/${candidate.draft_id}`).then(value => value.json())).state).toBe('draft')
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 }); await panel.scrollIntoViewIfNeeded()
      await page.screenshot({ path: info.outputPath(`review-recovery-${width}.png`) })
      const geometry = await dialog.evaluate(element => ({ width: element.clientWidth, scroll: element.scrollWidth, document: document.documentElement.scrollWidth, viewport: innerWidth }))
      expect(geometry.scroll).toBeLessThanOrEqual(geometry.width + 1); expect(geometry.document).toBeLessThanOrEqual(geometry.viewport)
    }
    expect(errors).toEqual([])
    writeFileSync(info.outputPath('review-flow.json'), JSON.stringify({ scope: 'Actual synthetic import/Jobs/worker/Artifacts/UI; no real human approval or publication', candidate, importAck, creates, original_create_ack: created, machine_receipt: machine, report_sha256: digest, decisions, actual_decision_receipt: decided, recovered, errors }, null, 2))
  } finally { await runtime.close() }
})
