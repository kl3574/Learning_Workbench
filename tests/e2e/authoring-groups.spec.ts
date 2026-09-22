import { writeFileSync } from 'node:fs'
import { expect, test, type Locator, type Page, type TestInfo } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { AuthoringGroupDraftView, AuthoringGroupJobView, AuthoringGroupNumericCheckView, AuthoringPrivateSolutionView, ConsentProposalView, JobRef, NumericCheckDecisionAck, SessionResponse } from '../../packages/contracts/generated/api-types'
import { AuthoringRuntime } from './authoringRuntime'

const providerId = 'provider_authoring_group_native'
const topic = '原创合成组合创作'
const objective = '区分草稿结构、数值复算与教学审核。'
async function configure(page: Page, runtime: AuthoringRuntime) {
  const auth: SessionResponse = await page.request.get('/api/v1/session').then(value => value.json())
  const headers = { Origin: runtime.origin, 'X-CSRF-Token': auth.csrf_token }
  expect((await page.request.post('/api/v1/session/role', { data: { role: 'author' }, headers: { ...headers, 'Idempotency-Key': 'native-group-author' } })).status()).toBe(200)
  const config = runtime.control()
  expect(config.test_only).toBe(true); expect(config.proof_registered).toBe(true)
  expect((await page.request.put(`/api/v1/providers/${providerId}/config`, { data: { expected_revision: 0, adapter: config.adapter, base_url: config.base_url, model: config.model, embedding_model: null, endpoint_policy: 'explicit_loopback', pricing: null }, headers: { ...headers, 'Idempotency-Key': 'native-group-config' } })).status()).toBe(200)
  expect((await page.request.post(`/api/v1/providers/${providerId}/secret`, { data: { expected_revision: 1, secret: 'synthetic-group-native-constant-only' }, headers: { ...headers, 'Idempotency-Key': 'native-group-secret' } })).status()).toBe(200)
  await page.reload()
  await expect(page.getByText('✓ UI 会话已保存', { exact: true })).toBeVisible()
}
async function form(page: Page, kind: 'lesson' | 'practice_set') {
  await page.getByRole('button', { name: '创作', exact: true }).click()
  const dialog = page.getByRole('dialog', { name: '创作', exact: true })
  await expect(dialog.getByRole('combobox', { name: '创作类型', exact: true })).toBeEnabled()
  await dialog.getByRole('combobox', { name: '创作类型', exact: true }).selectOption(kind)
  await dialog.getByLabel('创作主题', { exact: true }).fill(topic)
  await dialog.getByLabel('学习目标（每行一条，至少一条）', { exact: true }).fill(objective)
  await dialog.getByLabel('已配置的提供商 ID', { exact: true }).fill(providerId)
  if (kind === 'practice_set') {
    const target = dialog.getByRole('region', { name: '明确选择已有目标', exact: true })
    await target.getByRole('button', { name: '读取课程目录以选择目标', exact: true }).click()
    await target.getByRole('button', { name: '原创合成组目标课程 · r1 · 选择目标', exact: true }).click()
    await target.getByRole('button', { name: '加入概念：concept_group_native · r1', exact: true }).click()
    await target.getByRole('button', { name: '选择所属小节：原创合成已有小节 · r1', exact: true }).click()
    await expect(target.getByText('已选概念 1 / 32', { exact: true })).toBeVisible()
  }
  return dialog
}
async function readPrepared(page: Page, dialog: Locator, ack: JobRef) {
  expect(ack.status).toBe('awaiting_approval')
  await dialog.getByRole('button', { name: `读取创作详情 ${ack.id}`, exact: true }).click()
  await expect(dialog.getByRole('region', { name: '受保护创作详情', exact: true })).toBeVisible()
  const result: AuthoringGroupJobView = await page.request.get(`/api/v1/authoring/jobs/${ack.id}`).then(value => value.json())
  expect(result.variant).toBe('group'); expect(result.request.source_refs).toEqual([])
  expect(result.raw_answer).toBeNull(); expect(result.consent_id).toBeNull(); expect(result.content_plan).toBeNull()
  return result
}
async function grant(page: Page, dialog: Locator, ack: JobRef) {
  const preview = dialog.getByRole('region', { name: '准备授权预览', exact: true })
  await expect(preview.getByLabel('最大输入 token', { exact: true })).toBeEnabled()
  await preview.getByLabel('最大输入 token', { exact: true }).fill('20000')
  await preview.getByLabel('最大输出 token', { exact: true }).fill('10000')
  await preview.getByLabel('总超时秒数', { exact: true }).fill('10')
  await preview.getByLabel('到期时间 UTC', { exact: true }).fill(new Date(Date.now() + 300_000).toISOString())
  await preview.getByRole('button', { name: '准备服务端预览命令', exact: true }).click()
  const preparing = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/consents/preview'))
  await dialog.getByRole('button', { name: '确认发送授权预览', exact: true }).click()
  const response = await preparing; expect(response.status()).toBe(201)
  const proposal: ConsentProposalView = await response.json()
  expect(proposal.summary.job_id).toBe(ack.id)
  await dialog.getByLabel('我已核对本次组合草稿的冻结范围、提供商、预算与到期时间', { exact: true }).check()
  await dialog.getByRole('button', { name: '准备批准组合草稿模型调用', exact: true }).click()
  const granting = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/consents'))
  await dialog.getByRole('button', { name: '确认发送批准授权', exact: true }).click()
  expect((await granting).status()).toBe(201)
  let completed!: AuthoringGroupJobView
  // Preserve Playwright's actual default 5 s assertion; failure is diagnosed,
  // never converted into a longer hidden acceptance window.
  await expect.poll(async () => { completed = await page.request.get(`/api/v1/authoring/jobs/${ack.id}`).then(value => value.json()); return completed.summary.status }).toBe('completed')
  await dialog.getByRole('button', { name: '重新读取本次创作任务', exact: true }).click()
  await dialog.getByRole('button', { name: '读取这份准确组合候选', exact: true }).click()
  const group = dialog.getByRole('region', { name: '组合草稿候选', exact: true })
  await expect(group).toBeVisible()
  const draft: AuthoringGroupDraftView = await page.request.get(`/api/v1/authoring/draft-groups/${completed.summary.candidate!.draft_id}`).then(value => value.json())
  expect(draft.candidate).toEqual(completed.summary.candidate)
  expect(draft.content_plan).toEqual(completed.content_plan); expect(draft.plan_ref).toEqual(completed.plan_ref)
  expect(draft.state).toBe('draft'); expect(draft.base_ref).toBeNull()
  expect(draft.validation.mathematical).toBe('NOT_RUN'); expect(draft.validation.independent_pedagogy).toBe('NOT_RUN')
  await expect(group.getByRole('region', { name: '冻结的内容计划', exact: true })).toContainText(objective)
  return { completed, draft, group, proposal }
}
async function numericPreview(page: Page, dialog: Locator, group: Locator, draft: AuthoringGroupDraftView) {
  const receiving = page.waitForResponse(value => value.request().method() === 'POST' && value.url().includes(`/api/v1/authoring/draft-groups/${draft.candidate.draft_id}/members/`) && value.url().endsWith('/numeric-checks'))
  await group.getByRole('button', { name: '为例题 原创合成双倍例题 准备独立数值预览', exact: true }).click()
  const response = await receiving; expect(response.status()).toBe(201)
  const check: AuthoringGroupNumericCheckView = await response.json()
  expect(check.target.member_key).toBe('example'); expect(check.candidate).toEqual(draft.candidate)
  expect(check.decision).toBe('pending'); expect(check.revision).toBe(1)
  expect(check.job).toBeNull(); expect(check.result).toBeNull()
  await group.getByRole('button', { name: '刷新组合候选的检查记录', exact: true }).click()
  await group.getByRole('button', { name: `读取组数值检查 ${check.id}`, exact: true }).click()
  await expect(dialog.getByRole('region', { name: '独立数值执行批准', exact: true })).toBeVisible()
  return check
}
async function picture(page: Page, dialog: Locator, target: Locator, width: number, name: string, info: TestInfo) {
  await page.setViewportSize({ width, height: 900 })
  await target.scrollIntoViewIfNeeded(); await expect(target).toBeVisible()
  const bounds = await dialog.evaluate(element => {
    const inner = element.querySelector('.dialog-inner')!
    return { client: element.clientWidth, scroll: element.scrollWidth, inner_client: inner.clientWidth, inner_scroll: inner.scrollWidth, left: element.getBoundingClientRect().left, right: element.getBoundingClientRect().right, viewport: innerWidth, document: document.documentElement.scrollWidth }
  })
  writeFileSync(info.outputPath(`${name}-geometry.json`), JSON.stringify(bounds, null, 2))
  await page.screenshot({ path: info.outputPath(`${name}.png`) })
  expect(bounds.inner_scroll).toBeLessThanOrEqual(bounds.inner_client + 1)
  expect(bounds.scroll).toBeLessThanOrEqual(bounds.client + 1)
  expect(bounds.left).toBeGreaterThanOrEqual(0); expect(bounds.right).toBeLessThanOrEqual(bounds.viewport)
  expect(bounds.document).toBeLessThanOrEqual(bounds.viewport)
  return bounds
}

test('native lesson group preserves its plan and formulas, then separately declines and executes one exact numeric member', async ({ playwright }, info) => {
  test.setTimeout(120_000)
  const runtime = await AuthoringRuntime.start('lesson', 'groups'), errors: string[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    page.on('pageerror', error => errors.push(error.message))
    await runtime.authenticateOnly(page); await configure(page, runtime)
    const dialog = await form(page, 'lesson')
    const preparing = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/authoring/group-jobs'))
    await dialog.getByRole('button', { name: '明确准备本次组合创作任务', exact: true }).click()
    const accepted = await preparing; expect(accepted.status()).toBe(202)
    const ack: JobRef = await accepted.json(), prepared = await readPrepared(page, dialog, ack)
    expect(runtime.control().received_request_count).toBe(0)
    const { completed, draft, group, proposal } = await grant(page, dialog, ack)
    expect(completed.raw_answer).toBe(runtime.control().answer_markdown)
    await expect(group.locator('.formula svg').first()).toBeVisible()
    const wide = await picture(page, dialog, group.getByRole('heading', { name: '原创合成倍数定义', exact: true }), 1440, 'group-lesson-1440', info)
    const narrow = await picture(page, dialog, group.getByRole('heading', { name: '原创合成倍数定义', exact: true }), 390, 'group-lesson-390', info)
    const first = await numericPreview(page, dialog, group, draft)
    const declining = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith(`/api/v1/authoring/group-numeric-checks/${first.id}/decision`))
    await dialog.getByRole('button', { name: '明确拒绝本次数值执行', exact: true }).click()
    const declined = await declining; expect(declined.status()).toBe(200)
    const declineAck: NumericCheckDecisionAck = await declined.json()
    expect(declineAck).toEqual({ id: first.id, revision: 2, operation_sha256: first.operation_sha256, decision: 'decline', applied: true, job: null })
    const declineReading = await page.request.get(`/api/v1/authoring/group-numeric-checks/${first.id}`)
    expect(declineReading.status()).toBe(200)
    const declineReadback: AuthoringGroupNumericCheckView = await declineReading.json()
    expect(declineReadback).toEqual({ ...first, revision: 2, decision: 'decline', job: null, job_revision: null, result: null })
    const second = await numericPreview(page, dialog, group, draft)
    expect(second.id).not.toBe(first.id); expect(second.operation_sha256).not.toBe(first.operation_sha256)
    await dialog.getByLabel('我已核对全部变量、表达式、容差、候选与本机隔离范围，单独批准这一次执行', { exact: true }).check()
    const approving = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith(`/api/v1/authoring/group-numeric-checks/${second.id}/decision`))
    await dialog.getByRole('button', { name: '明确批准本次数值执行', exact: true }).click()
    const approved = await approving; expect(approved.status()).toBe(202)
    const approveAck: NumericCheckDecisionAck = await approved.json()
    expect(approveAck).toEqual({ id: second.id, revision: 2, operation_sha256: second.operation_sha256, decision: 'approve_once', applied: true, job: { id: expect.any(String), status: 'queued' } })
    expect(approveAck.job!.id).not.toBe(ack.id)
    let numeric!: AuthoringGroupNumericCheckView
    await expect.poll(async () => { numeric = await page.request.get(`/api/v1/authoring/group-numeric-checks/${second.id}`).then(value => value.json()); return numeric.result !== null }).toBe(true)
    expect(numeric.id).toBe(second.id); expect(numeric.revision).toBe(2); expect(numeric.decision).toBe('approve_once')
    expect(numeric.operation_sha256).toBe(second.operation_sha256); expect(numeric.candidate).toEqual(second.candidate); expect(numeric.target).toEqual(second.target)
    expect(numeric.job!.id).toBe(approveAck.job!.id); expect(numeric.result!.job_id).toBe(approveAck.job!.id)
    expect(['passed', 'environment_unavailable']).toContain(numeric.result!.outcome)
    expect(numeric.result!.verdict).toBe(numeric.result!.outcome === 'passed' ? 'PASS' : 'BLOCKED')
    await dialog.getByRole('button', { name: '另行读取数值检查当前状态', exact: true }).click()
    await expect(dialog.getByRole('heading', { name: `实际数值结果：${numeric.result!.verdict}`, exact: true })).toBeVisible()
    await picture(page, dialog, dialog.getByRole('region', { name: '实际数值结果', exact: true }), 390, 'group-numeric-390', info)
    const finalDraft: AuthoringGroupDraftView = await page.request.get(`/api/v1/authoring/draft-groups/${draft.candidate.draft_id}`).then(value => value.json())
    expect(finalDraft.candidate).toEqual(draft.candidate); expect(finalDraft.content_plan).toEqual(draft.content_plan)
    expect(finalDraft.state).toBe('draft'); expect(finalDraft.numeric_check_ids).toEqual([first.id, second.id])
    await expect.poll(() => runtime.control().validated_request_count).toBe(1)
    expect(runtime.control().received_request_count).toBe(1); expect(runtime.control().invalid_request_count).toBe(0)
    expect(errors).toEqual([])
    writeFileSync(info.outputPath('group-lesson-actual.json'), JSON.stringify({ scope: 'Real browser, SQLite and test-only loopback single consent. Original pending preview ACKs, actual decision ACKs and declined GET readback are distinct. Numeric actual environment verdict is preserved; BLOCKED is not successful arithmetic. Candidate and quality remain unreviewed draft.', prepared, completed, proposal_id: proposal.id, draft: finalDraft, first_preview_ack: first, second_preview_ack: second, decline_ack: declineAck, decline_readback: declineReadback, approve_ack: approveAck, numeric, runtime: runtime.control(), bounds: { wide, narrow }, page_errors: errors }, null, 2))
  } finally { await runtime.close() }
})

test('native practice group replays its lost prepare ACK with one key and clears explicitly read private answers after permission changes', async ({ playwright }, info) => {
  test.setTimeout(120_000)
  const runtime = await AuthoringRuntime.start('practice_set', 'groups'), errors: string[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    page.on('pageerror', error => errors.push(error.message))
    await runtime.authenticateOnly(page); await configure(page, runtime)
    const dialog = await form(page, 'practice_set')
    const attempts: { key: string; body: unknown }[] = []
    let originalAck!: JobRef
    await page.route('**/api/v1/authoring/group-jobs', async route => {
      const request = route.request()
      attempts.push({ key: request.headers()['idempotency-key'], body: request.postDataJSON() })
      if (attempts.length === 1) {
        const actual = await route.fetch(); expect(actual.status()).toBe(202)
        originalAck = await actual.json()
        // Server commits the actual first prepare; only its browser response is lost.
        await route.abort('failed')
      } else await route.continue()
    })
    await dialog.getByRole('button', { name: '明确准备本次组合创作任务', exact: true }).click()
    await expect(dialog.getByText('准备组合草稿 · 结果未知，原 key 与完整命令保留', { exact: true })).toBeVisible()
    expect(attempts).toHaveLength(1); expect(runtime.control().received_request_count).toBe(0)
    const replaying = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/authoring/group-jobs'))
    await dialog.getByRole('button', { name: `回放原命令 ${attempts[0].key}`, exact: true }).click()
    const replay = await replaying; expect(replay.status()).toBe(202); expect(await replay.json()).toEqual(originalAck)
    expect(attempts).toHaveLength(2); expect(attempts[1]).toEqual(attempts[0])
    const prepared = await readPrepared(page, dialog, originalAck)
    expect(prepared.preparation.targets.map(value => value.ref.entity)).toEqual(['lesson', 'concept'])
    const { completed, draft, group, proposal } = await grant(page, dialog, originalAck)
    expect(draft.root.entity).toBe('practice_set')
    expect(JSON.stringify(draft)).not.toContain('accepted_answers'); expect(JSON.stringify(draft)).not.toContain('私有合成解答')
    await expect(group.getByRole('region', { name: '私有解答草稿', exact: true })).toHaveCount(0)
    await expect(group.locator('.formula svg').first()).toBeVisible()
    const wide = await picture(page, dialog, group.getByRole('heading', { name: '第 1 题 · numeric', exact: true }), 1440, 'group-practice-1440', info)
    const narrow = await picture(page, dialog, group.getByRole('heading', { name: '第 1 题 · numeric', exact: true }), 390, 'group-practice-390', info)
    const reading = page.waitForResponse(value => value.request().method() === 'GET' && value.url().endsWith(`/api/v1/authoring/draft-groups/${draft.candidate.draft_id}/solutions/question_double`))
    await group.getByRole('button', { name: '明确读取第 1 题的私有解答草稿', exact: true }).click()
    const response = await reading; expect(response.status()).toBe(200)
    const solution: AuthoringPrivateSolutionView = await response.json()
    expect(solution.payload.answer.accepted_answers).toEqual(['18', '18.0'])
    const privatePanel = group.getByRole('region', { name: '私有解答草稿', exact: true })
    await expect(privatePanel).toContainText('私有合成解答')
    await picture(page, dialog, privatePanel, 390, 'group-private-390', info)
    const auth: SessionResponse = await page.request.get('/api/v1/session').then(value => value.json())
    expect((await page.request.post('/api/v1/session/role', { data: { role: 'learner' }, headers: { Origin: runtime.origin, 'X-CSRF-Token': auth.csrf_token, 'Idempotency-Key': 'native-group-demote' } })).status()).toBe(200)
    await dialog.getByRole('button', { name: '刷新安全任务列表与当前权限', exact: true }).click()
    await expect(privatePanel).toHaveCount(0)
    await expect(dialog.getByRole('region', { name: '组合草稿候选', exact: true })).toHaveCount(0)
    await expect(dialog.getByRole('region', { name: '受保护创作详情', exact: true })).toHaveCount(0)
    await expect(dialog.getByRole('region', { name: '创作任务安全控制', exact: true })).toBeVisible()
    expect((await page.request.get(`/api/v1/authoring/draft-groups/${draft.candidate.draft_id}/solutions/question_double`)).status()).toBe(403)
    await expect.poll(() => runtime.control().validated_request_count).toBe(1)
    expect(runtime.control().received_request_count).toBe(1); expect(runtime.control().invalid_request_count).toBe(0)
    expect(errors).toEqual([])
    writeFileSync(info.outputPath('group-practice-actual.json'), JSON.stringify({ scope: 'Lost browser prepare response after actual server commit, then explicit identical original command replay. One original Job and one actual loopback model dispatch. Exact existing Content targets, public/private separation and real role change clearing without page reload. No review or publication.', prepare_attempts: attempts, original_prepare_ack: originalAck, prepared, completed, proposal_id: proposal.id, draft, solution, runtime: runtime.control(), bounds: { wide, narrow }, page_errors: errors }, null, 2))
  } finally { await runtime.close() }
})
