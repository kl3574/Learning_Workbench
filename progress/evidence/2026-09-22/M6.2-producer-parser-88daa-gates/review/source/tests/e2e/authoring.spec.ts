import { writeFileSync } from 'node:fs'
import { expect, test, type Locator, type Page, type TestInfo } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { AuthoringDraftView, AuthoringJobPage, AuthoringJobView, ConsentProposalView, JobRef, NumericCheckView, ProviderConfigWrite, SessionResponse } from '../../packages/contracts/generated/api-types'
import { AuthoringRuntime } from './authoringRuntime'

const providerId = 'provider_authoring_native'
async function role(page: Page, origin: string, value: 'author' | 'learner') {
  const session: SessionResponse = await page.request.get('/api/v1/session').then(v => v.json())
  const response = await page.request.post('/api/v1/session/role', { data: { role: value }, headers: { Origin: origin, 'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': `synthetic-authoring-role-${value}` } })
  expect(response.status()).toBe(200)
  // Only the real role endpoint changes permissions; reloading observes it.
  await page.reload()
  await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible()
}
async function configure(page: Page, runtime: AuthoringRuntime) {
  const session: SessionResponse = await page.request.get('/api/v1/session').then(v => v.json())
  const headers = { Origin: runtime.origin, 'X-CSRF-Token': session.csrf_token }
  const control = runtime.control()
  const config: ProviderConfigWrite = { expected_revision: 0, adapter: control.adapter, base_url: control.base_url, model: control.model, embedding_model: null, endpoint_policy: 'explicit_loopback', pricing: null }
  expect((await page.request.put(`/api/v1/providers/${providerId}/config`, { data: config, headers: { ...headers, 'Idempotency-Key': 'synthetic-authoring-native-config' } })).status()).toBe(200)
  expect((await page.request.post(`/api/v1/providers/${providerId}/secret`, { data: { expected_revision: 1, secret: 'synthetic-authoring-native-constant-only' }, headers: { ...headers, 'Idempotency-Key': 'synthetic-authoring-native-secret' } })).status()).toBe(200)
}
async function prepare(page: Page) {
  await page.getByRole('button', { name: '创作', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: '创作', exact: true })
  await expect(dialog.getByLabel('例题主题', { exact: true })).toBeEnabled()
  await dialog.getByLabel('例题主题', { exact: true }).fill('原创合成双倍例题')
  await dialog.getByLabel('学习目标（每行一条，至少一条）', { exact: true }).fill('明确区分模型草稿、数值复算与数学审核。')
  await dialog.getByLabel('已配置的提供商 ID', { exact: true }).fill(providerId)
  const response = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith('/api/v1/authoring/jobs'))
  await dialog.getByRole('button', { name: '明确准备本次例题任务', exact: true }).click()
  const accepted = await response; expect(accepted.status()).toBe(202)
  const ack: JobRef = await accepted.json()
  expect(ack.status).toBe('awaiting_approval')
  await dialog.getByRole('button', { name: `读取创作详情 ${ack.id}`, exact: true }).click()
  await expect(dialog.getByRole('region', { name: '受保护创作详情', exact: true })).toBeVisible()
  const original: AuthoringJobView = await page.request.get(`/api/v1/authoring/jobs/${ack.id}`).then(v => v.json())
  expect(original.request.source_refs).toEqual([]); expect(original.preparation.materials).toEqual([])
  expect(original.consent_id).toBeNull(); expect(original.proposal_id).toBeNull(); expect(original.raw_answer).toBeNull()
  return { dialog, ack, original }
}
async function preview(page: Page, dialog: Locator) {
  const panel = dialog.getByRole('region', { name: '准备授权预览', exact: true })
  await expect(panel.getByLabel('最大输入 token', { exact: true })).toBeEnabled()
  await panel.getByLabel('最大输入 token', { exact: true }).fill('20000')
  await panel.getByLabel('最大输出 token', { exact: true }).fill('5000')
  await panel.getByLabel('总超时秒数', { exact: true }).fill('10')
  await panel.getByLabel('到期时间 UTC', { exact: true }).fill(new Date(Date.now() + 300_000).toISOString())
  await panel.getByRole('button', { name: '准备服务端预览命令', exact: true }).click()
  const response = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith('/api/v1/consents/preview'))
  await dialog.getByRole('button', { name: '确认发送授权预览', exact: true }).click()
  return response
}
async function numericPreview(page: Page, dialog: Locator, draftId: string) {
  const response = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith(`/api/v1/authoring/drafts/${draftId}/numeric-checks`))
  await dialog.getByRole('button', { name: '明确准备独立数值检查预览', exact: true }).click()
  const accepted = await response; expect(accepted.status()).toBe(201)
  const value: NumericCheckView = await accepted.json()
  expect(value.decision).toBe('pending'); expect(value.job).toBeNull(); expect(value.result).toBeNull()
  await dialog.getByRole('button', { name: '刷新候选的检查记录', exact: true }).click()
  await dialog.getByRole('button', { name: `读取数值检查 ${value.id}`, exact: true }).click()
  await expect(dialog.getByRole('region', { name: '独立数值执行批准', exact: true })).toBeVisible()
  return value
}
async function screenshot(page: Page, dialog: Locator, width: number, target: Locator, name: string, info: TestInfo) {
  await page.setViewportSize({ width, height: 900 })
  await target.scrollIntoViewIfNeeded()
  await expect(target).toBeVisible()
  const bounds = await dialog.evaluate(element => { const inner = element.querySelector('.dialog-inner')!; return { client: element.clientWidth, scroll: element.scrollWidth, inner_client: inner.clientWidth, inner_scroll: inner.scrollWidth, left: element.getBoundingClientRect().left, right: element.getBoundingClientRect().right, viewport: innerWidth, document: document.documentElement.scrollWidth } })
  writeFileSync(info.outputPath(name.replace('.png', '-geometry.json')), JSON.stringify(bounds, null, 2))
  await page.screenshot({ path: info.outputPath(name) })
  expect(bounds.inner_scroll).toBeLessThanOrEqual(bounds.inner_client + 1)
  expect(bounds.scroll).toBeLessThanOrEqual(bounds.client + 1)
  expect(bounds.left).toBeGreaterThanOrEqual(0); expect(bounds.right).toBeLessThanOrEqual(bounds.viewport)
  expect(bounds.document).toBeLessThanOrEqual(bounds.viewport)
  await page.screenshot({ path: info.outputPath(name) })
  return bounds
}

test('actual Authoring preparation diagnoses missing proof without dispatch and learner can recover safe cancellation', async ({ playwright }, info) => {
  test.setTimeout(90_000)
  const runtime = await AuthoringRuntime.start('no_proof')
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    await runtime.authenticateOnly(page); await role(page, runtime.origin, 'author'); await configure(page, runtime)
    expect(runtime.control().proof_registered).toBe(false)
    const { dialog, ack, original } = await prepare(page)
    expect(runtime.control().received_request_count).toBe(0)
    const rejected = await preview(page, dialog)
    expect(rejected.status()).toBe(409); expect((await rejected.json()).error.code).toBe('CAPABILITY_UNSUPPORTED')
    const unchanged: AuthoringJobView = await page.request.get(`/api/v1/authoring/jobs/${ack.id}`).then(v => v.json())
    expect(unchanged.consent_id).toBeNull(); expect(unchanged.proposal_id).toBeNull(); expect(unchanged.raw_answer).toBeNull()
    await role(page, runtime.origin, 'learner')
    await page.getByRole('button', { name: '创作', exact: true }).click()
    await expect(dialog.getByLabel('例题主题', { exact: true })).toHaveCount(0)
    await expect(dialog.getByRole('region', { name: '受保护创作详情', exact: true })).toHaveCount(0)
    const cancelling = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith(`/api/v1/jobs/${ack.id}/cancel`))
    await dialog.getByRole('button', { name: `明确取消任务 ${ack.id}`, exact: true }).click()
    expect((await cancelling).status()).toBe(200)
    await expect(dialog.getByText(new RegExp(`^${ack.id} · cancelled · r`))).toBeVisible()
    const final: AuthoringJobPage = await page.request.get('/api/v1/authoring/jobs').then(v => v.json())
    expect(final.items).toHaveLength(1); expect(final.items[0].status).toBe('cancelled')
    expect(final.items[0].result_refs).toEqual([]); expect(final.items[0].warnings).toEqual([])
    expect(JSON.stringify(final)).not.toContain(original.request.topic)
    expect(runtime.control().received_request_count).toBe(0)
    writeFileSync(info.outputPath('actual-authoring-no-proof.json'), JSON.stringify({ scope: 'Real local HTTP/SQLite/worker/browser. Production-style empty proof registry; original synthetic provider configuration only. Preview rejected, zero dispatch, learner safe cancellation. No model or numeric result.', prepared: original, no_proposal: unchanged, safe_final: final, runtime: runtime.control() }, null, 2))
  } finally { await runtime.close() }
})

test('explicit same-Job loopback grant creates a draft and numeric preview needs its own decision', async ({ playwright }, info) => {
  test.setTimeout(120_000)
  const runtime = await AuthoringRuntime.start('complete'), errors: string[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    page.on('pageerror', error => errors.push(error.message))
    await runtime.authenticateOnly(page); await role(page, runtime.origin, 'author'); await configure(page, runtime)
    let prepares = 0
    page.on('request', value => { if (value.method() === 'POST' && value.url().endsWith('/api/v1/authoring/jobs')) prepares++ })
    const { dialog, ack } = await prepare(page)
    expect(runtime.control().proof_registered).toBe(true); expect(runtime.control().received_request_count).toBe(0)
    const previewResponse = await preview(page, dialog); expect(previewResponse.status()).toBe(201)
    const proposal: ConsentProposalView = await previewResponse.json()
    expect(proposal.summary.job_id).toBe(ack.id); expect(proposal.summary.purpose).toBe('authoring')
    expect(runtime.control().received_request_count).toBe(0)
    await dialog.getByLabel('我已核对本次例题的冻结范围、提供商、预算与到期时间', { exact: true }).check()
    await dialog.getByRole('button', { name: '准备批准例题模型调用', exact: true }).click()
    const granting = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith('/api/v1/consents'))
    await dialog.getByRole('button', { name: '确认发送批准授权', exact: true }).click()
    expect((await granting).status()).toBe(201)
    let current!: AuthoringJobView
    await expect.poll(async () => { current = await page.request.get(`/api/v1/authoring/jobs/${ack.id}`).then(v => v.json()); return current.summary.status }, { timeout: 10_000 }).toBe('completed')
    await dialog.getByRole('button', { name: '重新读取本次创作任务', exact: true }).click()
    await dialog.getByRole('button', { name: '读取这份准确例题候选', exact: true }).click()
    const candidate = current.summary.candidate; expect(candidate).not.toBeNull()
    const draft: AuthoringDraftView = await page.request.get(`/api/v1/authoring/drafts/${candidate!.draft_id}`).then(v => v.json())
    expect(draft.state).toBe('draft'); expect(draft.base_ref).toBeNull(); expect(draft.numeric_check_ids).toEqual([])
    expect(current.raw_answer).toBe(runtime.control().answer_markdown)
    await expect(dialog.getByLabel('完整候选正文', { exact: true })).toHaveText(draft.payload.body_markdown)
    expect(draft.validation.mathematical).toBe('NOT_RUN'); expect(draft.validation.independent_pedagogy).toBe('NOT_RUN')
    const rejectedPreview = await numericPreview(page, dialog, candidate!.draft_id)
    expect((await page.request.get('/api/v1/authoring/jobs').then(v => v.json()) as AuthoringJobPage).items).toHaveLength(1)
    const declining = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith(`/api/v1/authoring/numeric-checks/${rejectedPreview.id}/decision`))
    await dialog.getByRole('button', { name: '明确拒绝本次数值执行', exact: true }).click()
    const declinedAck = await declining; expect(declinedAck.status()).toBe(200); expect((await declinedAck.json()).job).toBeNull()
    await dialog.getByRole('button', { name: '另行读取数值检查当前状态', exact: true }).click()
    await expect(dialog.getByText('当前决定：decline · r2', { exact: true })).toBeVisible()
    const approvedPreview = await numericPreview(page, dialog, candidate!.draft_id)
    await dialog.getByLabel('我已核对全部变量、表达式、容差、候选与本机隔离范围，单独批准这一次执行', { exact: true }).check()
    const approving = page.waitForResponse(v => v.request().method() === 'POST' && v.url().endsWith(`/api/v1/authoring/numeric-checks/${approvedPreview.id}/decision`))
    await dialog.getByRole('button', { name: '明确批准本次数值执行', exact: true }).click()
    const approvedAck = await approving; expect(approvedAck.status()).toBe(202)
    const numericAck = await approvedAck.json(); expect(numericAck.job).not.toBeNull()
    let numeric!: NumericCheckView
    await expect.poll(async () => { numeric = await page.request.get(`/api/v1/authoring/numeric-checks/${approvedPreview.id}`).then(v => v.json()); return numeric.result !== null }, { timeout: 15_000 }).toBe(true)
    expect(['passed', 'environment_unavailable']).toContain(numeric.result!.outcome)
    expect(numeric.result!.verdict).toBe(numeric.result!.outcome === 'passed' ? 'PASS' : 'BLOCKED')
    await dialog.getByRole('button', { name: '另行读取数值检查当前状态', exact: true }).click()
    await expect(dialog.getByRole('heading', { name: `实际数值结果：${numeric.result!.verdict}`, exact: true })).toBeVisible()
    const finalDraft: AuthoringDraftView = await page.request.get(`/api/v1/authoring/drafts/${candidate!.draft_id}`).then(v => v.json())
    expect(finalDraft.candidate).toEqual(draft.candidate); expect(finalDraft.state).toBe('draft')
    expect(finalDraft.payload).toEqual(draft.payload); expect(finalDraft.numeric_check_ids).toEqual([rejectedPreview.id, approvedPreview.id])
    writeFileSync(info.outputPath('actual-authoring-execution-before-layout.json'), JSON.stringify({ scope: 'Actual authoring and numeric HTTP/worker results before viewport and role checks; subsequent test outcome is separate.', completed: current, draft: finalDraft, declined_preview: rejectedPreview, approved_preview: approvedPreview, actual_numeric: numeric, runtime: runtime.control() }, null, 2))
    const wide = await screenshot(page, dialog, 1440, dialog.getByLabel('完整候选正文', { exact: true }), 'authoring-candidate-1440.png', info)
    const narrow = await screenshot(page, dialog, 390, dialog.getByLabel('完整候选正文', { exact: true }), 'authoring-candidate-390.png', info)
    await screenshot(page, dialog, 390, dialog.getByRole('region', { name: '实际数值结果', exact: true }), 'authoring-actual-numeric-390.png', info)
    await expect.poll(() => runtime.control().validated_request_count).toBe(1)
    expect(runtime.control().received_request_count).toBe(1); expect(runtime.control().invalid_request_count).toBe(0); expect(prepares).toBe(1)
    await role(page, runtime.origin, 'learner')
    await page.locator('.command-trigger').click()
    await page.getByRole('dialog', { name: '命令面板', exact: true }).getByRole('button', { name: /^创作/ }).click()
    const control = dialog.getByRole('region', { name: '创作任务安全控制', exact: true })
    await expect(control.getByText('例题候选生成任务', { exact: true })).toBeVisible()
    await expect(control.getByText('独立数值检查任务', { exact: true })).toBeVisible()
    await expect(control.getByRole('button', { name: `明确取消任务 ${numericAck.job.id}`, exact: true })).toBeDisabled()
    await expect(dialog.getByLabel('完整候选正文', { exact: true })).toHaveCount(0)
    await expect(dialog.getByRole('region', { name: '独立数值执行批准', exact: true })).toHaveCount(0)
    const safe: AuthoringJobPage = await page.request.get('/api/v1/authoring/jobs').then(v => v.json())
    expect(new Set(safe.items.map(v => v.kind))).toEqual(new Set(['authoring', 'authoring_numeric_check']))
    expect(JSON.stringify(safe)).not.toContain(candidate!.draft_id); expect(JSON.stringify(safe)).not.toContain(approvedPreview.id)
    expect(errors).toEqual([])
    writeFileSync(info.outputPath('actual-authoring-loopback.json'), JSON.stringify({ scope: 'Actual test-only loopback full-byte protocol and native UI. One original authoring Job and one actual provider dispatch. Draft remains unpublished and unreviewed. Numeric decline has no Job; separate approve records actual environment verdict, BLOCKED is not arithmetic PASS. Both safe kinds discoverable after real learner role change.', prepares, proposal_id: proposal.id, completed: current, draft: finalDraft, declined_preview: rejectedPreview, approved_preview: approvedPreview, actual_numeric: numeric, safe_controls: safe, runtime: runtime.control(), viewport_bounds: { wide, narrow }, page_errors: errors }, null, 2))
  } finally { await runtime.close() }
})
