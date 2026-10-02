import { execFileSync } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { AssessmentGradingResult, ConceptStateResponse, ContentRef, EvidenceApplicabilityDecisionView as View, EvidenceImpactDecisionWrite as Write, EvidenceImpactDecisionReceipt as Receipt } from '../../packages/contracts/generated/api-types'
import { RestartRuntime } from './restartRuntime'
import { importAssessmentPackage, originalAssessmentPackage } from './assessmentTestData'

const panel = (page: Page) => page.getByRole('region', { name: '学习证据适用性决定', exact: true })
const root = resolve(import.meta.dirname, '../..')
async function headers(page: Page, runtime: RestartRuntime, key: string) { const session = await page.request.get('/api/v1/session').then(r => r.json()); return { Origin: runtime.origin, 'X-CSRF-Token': session.csrf_token as string, 'Idempotency-Key': key } }
async function view(page: Page, evidence: string, event?: string): Promise<View> { const response = await page.request.get(`/api/v1/learning/evidence/${evidence}/applicability${event ? `?event_id=${event}` : ''}`); expect(response.status()).toBe(200); return response.json() }
async function open(page: Page) { await page.getByRole('button', { name: '设置', exact: true }).click(); await page.getByRole('dialog', { name: '设置', exact: true }).getByRole('button', { name: '概念与技能证据', exact: true }).click() }
async function select(page: Page, evidence: string) {
  const source = page.locator('.learning-source').filter({ has: page.getByRole('button', { name: `检查此原证据的适用性 ${evidence}`, exact: true, includeHidden: true }) }).first()
  const group = source.locator('..'); if (await group.getAttribute('open') === null) await group.locator(':scope > summary').click()
  if (await source.getAttribute('open') === null) await source.locator(':scope > summary').click()
  await source.getByRole('button', { name: `检查此原证据的适用性 ${evidence}`, exact: true }).click()
  await panel(page).getByRole('button', { name: '读取所选原证据当前适用性', exact: true }).click()
}
async function freeze(page: Page, event: string) {
  await panel(page).getByRole('button', { name: `读取事件决定基准 ${event}`, exact: true }).click()
  await panel(page).getByRole('button', { name: '采用本次已读依据准备决定', exact: true }).click()
}
async function form(page: Page, decision: Write['decision'], reason: string) {
  await panel(page).getByLabel('明确适用性决定', { exact: true }).selectOption(decision)
  await panel(page).getByLabel('适用性理由', { exact: true }).fill(reason)
  await panel(page).getByLabel('我已核对原证据、真实事件、冻结依据及理由，明确追加这一人工决定。', { exact: true }).check()
}
async function submit(page: Page) { await panel(page).getByRole('button', { name: '明确保存适用性决定', exact: true }).click() }
function contentChanges(runtime: RestartRuntime, workspace: string, ref: ContentRef) {
  const program = `import json,sys\nfrom pathlib import Path\nfrom services.api.app.infrastructure.config import Settings\nfrom services.api.app.infrastructure.database import Database\nfrom services.api.app.application.content import ContentService\nfrom services.api.app.infrastructure.content_repository import reference\nfrom packages.contracts.domain_models import ContentRef\nd=Database(Settings(data_dir=Path(sys.argv[1])));s=ContentService(d);ref=ContentRef.model_validate_json(sys.argv[3]);v=s.read(sys.argv[2],'concept',ref.id,ref.revision);assert reference(v)==ref\nfor revision in (2,3): s.publish(sys.argv[2],[v.model_copy(update={'revision':revision,'title':'Original synthetic changed concept '+str(revision)})],{})\nprint(json.dumps({'scope':'Controlled original fixture publishes two real Concept revisions through ContentService; no event/evidence/grade injection; not a production Concept editor'}))`
  return JSON.parse(execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', program, runtime.data, workspace, JSON.stringify(ref)], { cwd: root, encoding: 'utf8' }))
}
function protectedHistory(runtime: RestartRuntime) {
  const program = `import json,sys\nfrom pathlib import Path\nfrom services.api.app.infrastructure.config import Settings\nfrom services.api.app.infrastructure.database import Database\nfrom tests.integration.test_evidence_applicability_decisions import protected_history\nprint(json.dumps(protected_history(Database(Settings(data_dir=Path(sys.argv[1]))))))`
  return JSON.parse(execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', program, runtime.data], { cwd: root, encoding: 'utf8' }))
}
async function journal(page: Page) { return page.evaluate(async () => { const db = await new Promise<IDBDatabase>((yes, no) => { const r = indexedDB.open('learning-workbench.evidence-applicability-commands.v1', 1); r.onsuccess = () => yes(r.result); r.onerror = () => no(r.error) }); try { return await new Promise<string[]>((yes, no) => { const r = db.transaction('drafts', 'readonly').objectStore('drafts').getAll(); r.onsuccess = () => yes(r.result.map((x: { text: string }) => x.text)); r.onerror = () => no(r.error) }) } finally { db.close() } }) }

test('native original evidence: two real events, two-page CAS, lost ACK, actual IDB abort, role isolation, correction and restart preserve grade/private pins', async ({ playwright }, info) => {
  test.setTimeout(180_000)
  const runtime = await RestartRuntime.start(), errors: string[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; page.on('pageerror', e => errors.push(e.message)); await runtime.authenticateOnly(page)
    const fixture = originalAssessmentPackage('evidenceapplicabilitynative'), imported = await importAssessmentPackage(page, fixture)
    await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    const href = `${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: fixture.assessment, course_ref: fixture.course }))}`
    await page.goto(href); await page.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
    const start = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/api/v1/assessments/${fixture.assessment.id}/attempts`)); await page.getByRole('button', { name: '明确开始本次测试', exact: true }).click(); const attempt = await (await start).json()
    await page.getByRole('button', { name: '提交本次测试', exact: true }).click(); await page.getByRole('button', { name: '确认提交已保存作答', exact: true }).click(); await expect(page.getByRole('region', { name: '当前评分结果', exact: true })).toBeVisible()
    await page.getByRole('button', { name: '导入', exact: true }).click(); await page.getByRole('button', { name: '切换为作者角色', exact: true }).click(); await page.getByRole('button', { name: '关闭导入', exact: true }).click()
    const graded: AssessmentGradingResult = await page.request.get(`/api/v1/attempts/${attempt.id}/result`).then(r => r.json())
    const review = await page.request.post(`/api/v1/attempts/${attempt.id}/regrade`, { headers: await headers(page, runtime, 'synthetic-human-regrade'), data: { expected_grading_revision: graded.grading_revision, reason: 'Explicit synthetic software fixture review; not academic or source approval.', item_reviews: graded.items.map(item => ({ question_id: item.question_ref.id, score: item.max_score * 0.5, feedback_markdown: 'Original synthetic partial credit for software acceptance.' })) } }); expect(review.status()).toBe(202)
    await expect.poll(async () => (await page.request.get(`/api/v1/attempts/${attempt.id}/result`).then(r => r.json())).grading_revision).toBe(2)
    const sources: ConceptStateResponse = await page.request.get('/api/v1/learning/concept-states').then(r => r.json()), source = sources.items.flatMap(row => row.sources)[0]; expect(source).toBeTruthy(); expect(source.evidence.eligible).toBe(false)
    const session = await page.request.get('/api/v1/session').then(r => r.json()), changes = contentChanges(runtime, session.workspace_id, source.concept_ref)
    const initial = await view(page, source.evidence.id); expect(initial.relevant_event_ids).toHaveLength(2); const [first, second] = initial.relevant_event_ids
    const before = protectedHistory(runtime)
    await open(page); await select(page, source.evidence.id); await freeze(page, first); await form(page, 'usable', 'Synthetic first event judgment; original score and qualifications unchanged.')
    const competing = await context.browser()!.newContext({ storageState: await context.storageState() }); const other = await competing.newPage(); other.on('pageerror', e => errors.push(e.message)); await other.goto(runtime.origin); await open(other); await select(other, source.evidence.id); await freeze(other, first); await form(other, 'confirmed_stale', 'Synthetic competing old-head decision')
    const commands: { key: string; body: Write }[] = []; let original!: Receipt, accepted!: () => void; const acceptance = new Promise<void>(resolve => { accepted = resolve })
    const endpoint = `**/api/v1/learning/evidence/${source.evidence.id}/applicability-decisions`
    await page.route(endpoint, async route => { commands.push({ key: route.request().headers()['idempotency-key'], body: route.request().postDataJSON() }); if (commands.length === 1) { const response = await route.fetch(); expect(response.status()).toBe(200); original = await response.json(); accepted(); await route.abort('failed') } else await route.continue() })
    await other.route(endpoint, async route => { await acceptance; await route.continue() })
    await Promise.all([submit(page), submit(other)])
    await expect(panel(page).getByText(/决定结果未知，原 key 与完整命令保留/)).toBeVisible(); await expect(panel(other).getByText(/412：原依据/)).toBeVisible()
    expect((await view(page, source.evidence.id)).applicability).toBe('pending_review')
    await page.evaluate(() => { const original = IDBDatabase.prototype.transaction; Object.assign(window, { restoreEvidenceIdb: () => { IDBDatabase.prototype.transaction = original } }); IDBDatabase.prototype.transaction = function (...args: Parameters<IDBDatabase['transaction']>) { const tx = original.apply(this, args); if (this.name === 'learning-workbench.evidence-applicability-commands.v1' && args[1] === 'readwrite') queueMicrotask(() => tx.abort()); return tx } })
    const replayResponse = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/learning/evidence/${source.evidence.id}/applicability-decisions`)); await panel(page).getByText(/决定结果未知，原 key 与完整命令保留/).click(); await panel(page).getByRole('button', { name: `显式回放原适用性命令 ${commands[0].key}`, exact: true }).click()
    expect((await replayResponse).status()).toBe(200); await expect(panel(page).getByText(/原适用性命令或已收到回执尚未安全落盘/)).toBeVisible(); expect(commands[1]).toEqual(commands[0])
    expect((await journal(page)).map(raw => JSON.parse(raw)).find(c => c.command_id === commands[0].key).ack).toBeNull()
    await page.getByRole('button', { name: '关闭知识画像', exact: true }).click(); const guard = page.getByRole('dialog', { name: '保留适用性原命令', exact: true }); await expect(guard.getByRole('button', { name: '保留原命令，丢弃临时表单并关闭', exact: true })).toBeDisabled()
    await guard.getByRole('button', { name: '保留隔离内存，前往角色控制', exact: true }).click(); await page.getByRole('button', { name: '切换为学习者角色', exact: true }).click(); await page.getByRole('button', { name: '关闭导入', exact: true }).click()
    await open(page); await page.getByRole('button', { name: '打开适用性原命令恢复', exact: true }).click(); await expect(panel(page).getByText(/原适用性命令或已收到回执尚未安全落盘/)).toBeVisible(); expect(await panel(page).getByText(initial.current_basis_sha256, { exact: true }).count()).toBe(0)
    await expect(panel(page).getByRole('button', { name: '只保存原会话的适用性内存记录', exact: true })).toBeDisabled()
    await page.evaluate(() => (window as unknown as { restoreEvidenceIdb(): void }).restoreEvidenceIdb())
    await page.getByRole('button', { name: '关闭知识画像', exact: true }).click(); await guard.getByRole('button', { name: '保留隔离内存，前往角色控制', exact: true }).click(); await page.getByRole('button', { name: '切换为作者角色', exact: true }).click(); await page.getByRole('button', { name: '关闭导入', exact: true }).click()
    await open(page); await page.getByRole('button', { name: '打开适用性原命令恢复', exact: true }).click(); await panel(page).getByRole('button', { name: '只保存原会话的适用性内存记录', exact: true }).click(); await expect(panel(page).getByText(new RegExp(`原决定 ACK 已保存.*${commands[0].key}`))).toBeVisible(); expect(commands).toHaveLength(2)
    await panel(page).getByText(new RegExp(`原决定 ACK 已保存.*${commands[0].key}`)).click(); await expect(panel(page).getByRole('button', { name: `显式回放原适用性命令 ${commands[0].key}`, exact: true })).toBeDisabled()
    expect((await journal(page)).map(raw => JSON.parse(raw)).find(c => c.command_id === commands[0].key).ack).toEqual(original)
    await competing.close()
    await panel(page).getByRole('button', { name: `另行读取此原命令的当前基准 ${commands[0].key}`, exact: true }).click(); await panel(page).getByRole('button', { name: '采用本次已读依据准备决定', exact: true }).click(); await form(page, 'confirmed_stale', 'Explicit synthetic correction after current head read'); await submit(page)
    await expect.poll(async () => (await view(page, source.evidence.id, first)).event_decision_head).toBe(2); expect((await view(page, source.evidence.id)).applicability).toBe('confirmed_stale')
    await freeze(page, first); await form(page, 'usable', 'Explicit synthetic second correction'); await submit(page); await expect.poll(async () => (await view(page, source.evidence.id, first)).event_decision_head).toBe(3)
    await freeze(page, second); await form(page, 'usable', 'Explicit second event judgment; no original qualification change'); await submit(page); await expect.poll(async () => (await view(page, source.evidence.id)).applicability).toBe('usable')
    const current = await view(page, source.evidence.id); expect(current.original_evidence).toEqual(initial.original_evidence); expect(current.decisions).toHaveLength(4); expect(protectedHistory(runtime)).toEqual(before)
    await panel(page).getByRole('button', { name: `读取事件决定基准 ${first}`, exact: true }).click()
    for (const width of [1440, 390]) { await page.setViewportSize({ width, height: 900 }); await panel(page).getByRole('heading', { name: '学习证据适用性决定', exact: true }).scrollIntoViewIfNeeded(); expect(await panel(page).evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true); await page.screenshot({ path: info.outputPath(`applicability-${width}.png`) }) }
    const durable = await journal(page), database = runtime.databaseIdentity(); await runtime.closeBrowser(); await runtime.restartApiAfterBrowserClosed(); const next = await runtime.openBrowser(playwright.chromium), restored = next.pages()[0]; await restored.goto(runtime.origin); await open(restored); await restored.getByRole('button', { name: '打开适用性原命令恢复', exact: true }).click(); await expect(panel(restored).getByText(new RegExp(`原决定 ACK 已保存.*${commands[0].key}`))).toBeVisible()
    expect(await journal(restored)).toEqual(durable); expect(runtime.databaseIdentity()).toEqual(database); expect(await view(restored, source.evidence.id)).toEqual(current); expect(protectedHistory(runtime)).toEqual(before)
    await panel(restored).getByText(new RegExp(`原决定 ACK 已保存.*${commands[0].key}`)).click(); await expect(panel(restored).getByRole('button', { name: `显式回放原适用性命令 ${commands[0].key}`, exact: true })).toBeDisabled()
    // Current assessment Policy also invalidates this mounted page, independent
    // of role; it must hide previously read pins and the private journal.
    await panel(restored).getByRole('button', { name: `另行读取此原命令的当前基准 ${commands[0].key}`, exact: true }).click()
    await expect(panel(restored).getByRole('region', { name: '另行读取的当前适用性', exact: true })).toBeVisible()
    const policyPage = await next.newPage(); await policyPage.goto(href)
    await policyPage.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check()
    await policyPage.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
    await expect(policyPage.getByText('独立测试进行中', { exact: true }).first()).toBeVisible()
    await expect(panel(restored).getByRole('region', { name: '另行读取的当前适用性', exact: true })).toHaveCount(0)
    await expect(panel(restored).getByRole('region', { name: '本机适用性原命令', exact: true })).toHaveCount(0)
    expect((await restored.request.get(`/api/v1/learning/evidence/${source.evidence.id}/applicability`)).status()).toBe(409)
    await policyPage.getByRole('button', { name: '放弃本次测试', exact: true }).click()
    await policyPage.getByRole('button', { name: '确认放弃并保留本机候选', exact: true }).click()
    await expect.poll(async () => (await restored.request.get('/api/v1/session').then(r => r.json())).active_independent_attempt_id).toBeNull()
    await policyPage.close(); expect(await view(restored, source.evidence.id)).toEqual(current)
    const afterPolicy = protectedHistory(runtime)
    for (const name of ['solutions', 'revisions', 'grades', 'assessment_grade_audits', 'evidence', 'learning_evidence_refs', 'learning_grade_bindings']) expect(afterPolicy[name]).toEqual(before[name])
    expect(errors).toEqual([])
    writeFileSync(info.outputPath('applicability-flow.json'), JSON.stringify({ scope: 'Original imported questions, real HTTP submit/human regrade, controlled Content owner publication of two real revisions, real decisions/SQLite/IDB; synthetic judgments are software evidence only.', changes, source, initial, original, commands, current, original_protected_table_hashes: before, decision_and_restart_protected_tables_unchanged: true, active_assessment_policy_hidden_and_http409: true, post_policy_protected_table_hashes: afterPolicy, errors, generations: runtime.generations.length }, null, 2))
  } finally { await runtime.close() }
})
