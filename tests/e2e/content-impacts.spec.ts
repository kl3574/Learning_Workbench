import { writeFileSync } from 'node:fs'
import { expect, test, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { ContentImpactPage as ImpactPage, ContentImpactView as View, ImpactObjectDecisionWrite as Write, ImpactObjectDecisionReceipt as Receipt } from '../../packages/contracts/generated/api-types'
import { RestartRuntime } from './restartRuntime'
import { publishEditedBlock, publishExtra } from './contentImpactsData'
import { importAssessmentPackage, originalAssessmentPackage } from './assessmentTestData'
const panel = (page: Page) => page.getByRole('region', { name: '内容变更影响复核', exact: true })
async function open(page: Page) { await page.getByRole('button', { name: '创作', exact: true }).click(); await page.getByRole('button', { name: '打开内容变更影响复核', exact: true }).click(); await expect(panel(page).getByRole('button', { name: '从第一页读取内容变更', exact: true })).toBeVisible() }
async function list(page: Page, filter = '', limit = '20'): Promise<ImpactPage> {
  await panel(page).getByLabel('按原变更对象标识筛选（留空查看全部）', { exact: true }).fill(filter); await panel(page).getByLabel('每页事件数', { exact: true }).fill(limit)
  const response = page.waitForResponse(r => r.request().method() === 'GET' && new URL(r.url()).pathname === '/api/v1/content/impacts')
  await panel(page).getByRole('button', { name: '从第一页读取内容变更', exact: true }).click(); const r = await response; expect(r.status()).toBe(200); return r.json()
}
async function freeze(page: Page, event: string, target: string) {
  await panel(page).getByRole('button', { name: `读取对象当前依据 ${target}`, exact: true }).click()
  await panel(page).getByRole('button', { name: '采用本次对象依据准备决定', exact: true }).click()
  await expect(panel(page).getByRole('group', { name: '本次人工内容决定', exact: true })).toContainText(event)
}
async function form(page: Page, decision: Write['decision'], reason: string) {
  await panel(page).getByLabel('本次人工决定', { exact: true }).selectOption(decision); await panel(page).getByRole('textbox', { name: '决定理由', exact: true }).fill(reason)
  await panel(page).getByLabel('我已比对原变更、当前对象和冻结依据，明确追加这次人工判断。', { exact: true }).check()
}
async function submit(page: Page) { await panel(page).getByRole('button', { name: '明确保存内容决定', exact: true }).click() }
async function view(page: Page, event: string, target: string): Promise<View> { const r = await page.request.get(`/api/v1/content/impacts/${event}?target_id=${target}`); expect(r.status()).toBe(200); return r.json() }
async function journal(page: Page) {
  return page.evaluate(async () => { const db = await new Promise<IDBDatabase>((yes, no) => { const r = indexedDB.open('learning-workbench.content-impact-commands.v1', 1); r.onsuccess = () => yes(r.result); r.onerror = () => no(r.error) }); try { return await new Promise<string[]>((yes, no) => { const t = db.transaction('drafts', 'readonly'), r = t.objectStore('drafts').getAll(); r.onsuccess = () => yes(r.result.map((x: { text: string }) => x.text)); r.onerror = () => no(r.error) }) } finally { db.close() } })
}
test('native edit publication discovers actual impacts and preserves human decisions through CAS, lost reply, IDB failure, access changes, stable pages and restart', async ({ playwright }, info) => {
  test.setTimeout(210_000)
  const runtime = await RestartRuntime.start(), errors: string[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; page.on('pageerror', e => errors.push(e.message)); await runtime.authenticateOnly(page)
    const publication = await publishEditedBlock(page, runtime), target = publication.fixture.lessons[0].id, block = publication.fixture.blocks[0].id
    const session = await page.request.get('/api/v1/session').then(r => r.json())
    const parentRead = await page.request.get(`/api/v1/lessons/${target}?revision=1`); expect(parentRead.status()).toBe(200); const parentBefore = await parentRead.json(); expect(parentBefore.block_refs).toEqual([publication.fixture.blocks[0]])
    await open(page)
    const discovered = await list(page, block); expect(discovered.items).toHaveLength(1)
    const event = discovered.items[0].event_id // Obtained solely from actual UI request, never SQL/outbox injection.
    await panel(page).getByRole('button', { name: `查看影响详情 ${event}`, exact: true }).click(); await freeze(page, event, target); await form(page, 'no_revision_needed', 'Explicit synthetic first Content judgment; no other owner completion.')
    const competing = await context.browser()!.newContext({ storageState: await context.storageState() }), other = await competing.newPage(); await other.goto(runtime.origin); await open(other); expect((await list(other, block)).items[0].event_id).toBe(event)
    await panel(other).getByRole('button', { name: `查看影响详情 ${event}`, exact: true }).click(); await freeze(other, event, target); await form(other, 'new_revision_required', 'Synthetic competing old-head judgment')
    const commands: { key: string; body: Write }[] = []; let original!: Receipt, accepted!: () => void; const acceptance = new Promise<void>(r => { accepted = r }), endpoint = `**/api/v1/content/impacts/${event}/decisions`
    await page.route(endpoint, async route => { commands.push({ key: route.request().headers()['idempotency-key'], body: route.request().postDataJSON() }); if (commands.length === 1) { const r = await route.fetch(); expect(r.status()).toBe(200); original = await r.json(); accepted(); await route.abort('failed') } else await route.continue() })
    await other.route(endpoint, async route => { await acceptance; await route.continue() })
    await Promise.all([submit(page), submit(other)])
    await expect(panel(page).getByText(/决定结果未知，原提交内容已保留/)).toBeVisible(); await expect(panel(other).getByText(/对象修订或决定版本已变化（412）/)).toBeVisible()
    expect(original.classification).toBe('exact_ref'); expect((await view(page, event, target)).target_decision_head).toBe(1)
    await page.evaluate(() => { const original = IDBDatabase.prototype.transaction; Object.assign(window, { restoreImpactIdb: () => { IDBDatabase.prototype.transaction = original } }); IDBDatabase.prototype.transaction = function (...args: Parameters<IDBDatabase['transaction']>) { const tx = original.apply(this, args); if (this.name === 'learning-workbench.content-impact-commands.v1' && args[1] === 'readwrite') queueMicrotask(() => tx.abort()); return tx } })
    await panel(page).getByText(/决定结果未知，原提交内容已保留/).click()
    const replay = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/content/impacts/${event}/decisions`))
    await panel(page).getByRole('button', { name: `按原提交内容重试 ${commands[0].key}`, exact: true }).click(); expect((await replay).status()).toBe(200)
    await expect(panel(page).getByText(/原决定或已收到的回执尚未安全保存到本机/)).toBeVisible(); expect(commands[1]).toEqual(commands[0]); expect(JSON.parse((await journal(page))[0]).ack).toBeNull()
    await page.getByRole('button', { name: '关闭创作', exact: true }).click(); const guard = page.getByRole('dialog', { name: '保留创作原命令', exact: true })
    await expect(guard.getByRole('button', { name: '保留原命令，明确丢弃临时表单并关闭', exact: true })).toBeDisabled()
    await guard.getByRole('button', { name: '保留内容决定隔离内存，丢弃临时表单并前往角色控制', exact: true }).click()
    await page.getByRole('button', { name: '切换为学习者角色', exact: true }).click(); await page.getByRole('button', { name: '关闭导入', exact: true }).click()
    await page.getByRole('button', { name: '创作', exact: true }).click(); await page.getByRole('button', { name: '打开内容变更影响复核', exact: true }).click()
    await expect(panel(page).getByText(/原决定或已收到的回执尚未安全保存到本机/)).toBeVisible(); await expect(panel(page).getByRole('region', { name: '本机保留的内容决定', exact: true })).toHaveCount(0)
    await expect(panel(page).getByRole('button', { name: '只保存原会话的内容决定内存', exact: true })).toBeDisabled()
    await page.evaluate(() => (window as unknown as { restoreImpactIdb(): void }).restoreImpactIdb())
    await page.getByRole('button', { name: '关闭创作', exact: true }).click(); await guard.getByRole('button', { name: '保留内容决定隔离内存，丢弃临时表单并前往角色控制', exact: true }).click()
    await page.getByRole('button', { name: '切换为作者角色', exact: true }).click(); await page.getByRole('button', { name: '关闭导入', exact: true }).click(); await open(page)
    await panel(page).getByRole('button', { name: '只保存原会话的内容决定内存', exact: true }).click(); await expect(panel(page).getByText(new RegExp(`原决定回执已保存.*${commands[0].key}`))).toBeVisible(); expect(commands).toHaveLength(2)
    expect(JSON.parse((await journal(page))[0]).ack).toEqual(original); await panel(page).getByText(new RegExp(`原决定回执已保存.*${commands[0].key}`)).click()
    await expect(panel(page).getByRole('button', { name: `按原提交内容重试 ${commands[0].key}`, exact: true })).toBeDisabled(); await competing.close()
    const extra = [publishExtra(runtime, session.workspace_id, publication.fixture.lessons[0], [2])]
    await panel(page).getByRole('button', { name: `另行读取原决定对象 ${commands[0].key}`, exact: true }).click(); await panel(page).getByRole('button', { name: '采用本次对象依据准备决定', exact: true }).click()
    await form(page, 'new_revision_required', 'Explicit new-head correction after target revision changed; ID-only remains conservative.'); await submit(page)
    await expect.poll(async () => (await view(page, event, target)).target_decision_head).toBe(2)
    const corrected = await view(page, event, target); expect(corrected.decisions[1].classification).toBe('id_only_candidate'); expect(corrected.action_required_target_ids).toContain(target)
    expect(corrected.decisions[0]).toEqual(original)
    extra.push(publishExtra(runtime, session.workspace_id, publication.published, [3, 4]))
    const firstPage = await list(page, block, '1'), ids = [firstPage.items[0].event_id]; expect(firstPage.next_cursor).not.toBeNull()
    extra.push(publishExtra(runtime, session.workspace_id, publication.published, [5]))
    for (let n = 0; n < 2; n++) { const next = page.waitForResponse(r => r.request().method() === 'GET' && new URL(r.url()).pathname === '/api/v1/content/impacts'); await panel(page).getByRole('button', { name: '沿原筛选读取下一页事件', exact: true }).click(); const response = await next; expect(response.status()).toBe(200); const value: ImpactPage = await response.json(); ids.push(value.items[0].event_id); if (n === 1) expect(value.next_cursor).toBeNull() }
    expect(new Set(ids).size).toBe(3); expect((await list(page, block)).items).toHaveLength(4); expect((await list(page, target)).items).toHaveLength(1)
    const all = await list(page); expect(all.items).toHaveLength(5)
    await panel(page).getByRole('button', { name: `查看影响详情 ${event}`, exact: true }).click()
    for (const width of [1440, 390]) { await page.setViewportSize({ width, height: 900 }); await panel(page).scrollIntoViewIfNeeded(); expect(await panel(page).evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true); await page.screenshot({ path: info.outputPath(`content-impacts-${width}.png`) }) }
    const durable = await journal(page), database = runtime.databaseIdentity(); await runtime.closeBrowser(); await runtime.restartApiAfterBrowserClosed()
    const next = await runtime.openBrowser(playwright.chromium), restored = next.pages()[0]; await restored.goto(runtime.origin); await open(restored)
    expect((await list(restored, block)).items.map(x => x.event_id)).toContain(event); expect(await journal(restored)).toEqual(durable); expect(runtime.databaseIdentity()).toEqual(database)
    await panel(restored).getByText(new RegExp(`原决定回执已保存.*${commands[0].key}`)).click(); await expect(panel(restored).getByRole('button', { name: `按原提交内容重试 ${commands[0].key}`, exact: true })).toBeDisabled()
    expect(await restored.request.get(`/api/v1/lessons/${target}?revision=1`).then(r => r.json())).toEqual(parentBefore)
    await panel(restored).getByRole('button', { name: `查看影响详情 ${event}`, exact: true }).click(); await expect(panel(restored).getByRole('region', { name: '本次读取的内容影响详情', exact: true })).toBeVisible()
    const policyPage = await next.newPage(); await policyPage.goto(runtime.origin); const assessment = originalAssessmentPackage('impactpolicy'); const imported = await importAssessmentPackage(policyPage, assessment); await imported.dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click(); await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    await panel(restored).getByRole('button', { name: '重新核验内容复核权限', exact: true }).click(); await list(restored, block); await panel(restored).getByRole('button', { name: `查看影响详情 ${event}`, exact: true }).click(); await expect(panel(restored).getByRole('region', { name: '本次读取的内容影响详情', exact: true })).toBeVisible()
    expect((await restored.request.get('/api/v1/session').then(r => r.json())).role).toBe('author')
    const href = `${runtime.origin}/?assessment=${encodeURIComponent(JSON.stringify({ assessment_ref: assessment.assessment, course_ref: assessment.course }))}`; await policyPage.goto(href)
    await policyPage.getByRole('checkbox', { name: '我已核对内容状态与模式，确认开始未评分测试', exact: true }).check(); await policyPage.getByRole('button', { name: '明确开始本次测试', exact: true }).click()
    await expect(policyPage.getByText('独立测试进行中', { exact: true }).first()).toBeVisible(); await expect(panel(restored).getByRole('region', { name: '本次读取的内容影响详情', exact: true })).toHaveCount(0); await expect(panel(restored).getByRole('region', { name: '本机保留的内容决定', exact: true })).toHaveCount(0)
    expect((await restored.request.get('/api/v1/content/impacts')).status()).toBe(409)
    writeFileSync(info.outputPath('actual-content-impacts.json'), JSON.stringify({ scope: 'Actual native UI Edit/Review/manual publication then public impact discovery, decisions, lost response, real IDB abort and actor isolation. Extra owner publications only test pagination; event IDs always from HTTP. Synthetic intent; no academic/numeric approval.', publication, discovered, original, corrected, commands, page_membership: ids, all, extra, durable, parentBefore, page_errors: errors }, null, 2))
    expect(errors).toEqual([])
  } finally { await runtime.close() }
})

test('native unsubmitted Content judgment survives role cycles with original basis and explicit close discard', async ({ playwright }, info) => {
  test.setTimeout(150_000)
  const runtime = await RestartRuntime.start(), decisionWrites: string[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; page.on('request', request => { const path = new URL(request.url()).pathname; if (request.method() === 'POST' && /^\/api\/v1\/content\/impacts\/[^/]+\/decisions$/.test(path)) decisionWrites.push(path) }); await runtime.authenticateOnly(page)
    const publication = await publishEditedBlock(page, runtime), target = publication.fixture.lessons[0].id
    const currentSession = await page.request.get('/api/v1/session').then(r => r.json())
    await open(page); const event = (await list(page, publication.published.id)).items[0].event_id
    await panel(page).getByRole('button', { name: `查看影响详情 ${event}`, exact: true }).click(); await freeze(page, event, target)
    const reason = '尚未提交的原始人工理由 α\n保留换行、Unicode 与旧依据。'
    await form(page, 'new_revision_required', reason)
    const controls = await context.newPage(); await controls.goto(runtime.origin); await expect(controls.getByText('✓ UI 会话已保存')).toBeVisible(); await controls.keyboard.press('Control+Shift+P'); await controls.getByRole('dialog', { name: '命令面板', exact: true }).getByRole('button', { name: /^导入/ }).click()
    for (let i = 0; i < 2; i++) {
      await controls.getByRole('button', { name: '切换为学习者角色', exact: true }).click()
      await expect(panel(page).getByRole('textbox', { name: '决定理由', exact: true })).toHaveCount(0)
      await expect(panel(page).getByText(/本页仍保留未提交的内容决定表单与原依据/)).toBeVisible()
      await expect(panel(page).getByRole('button', { name: '重新核验权限与当前依据，恢复原会话表单', exact: true })).toBeDisabled()
      if (i === 1) publishExtra(runtime, currentSession.workspace_id, publication.fixture.lessons[0], [2])
      await controls.getByRole('button', { name: '切换为作者角色', exact: true }).click()
      const restoring = panel(page).getByRole('button', { name: '重新核验权限与当前依据，恢复原会话表单', exact: true }); await expect(restoring).toBeEnabled(); await restoring.click()
      await expect(panel(page).getByRole('textbox', { name: '决定理由', exact: true })).toHaveValue(reason)
      await expect(panel(page).getByLabel('我已比对原变更、当前对象和冻结依据，明确追加这次人工判断。', { exact: true })).not.toBeChecked()
      expect(await journal(page)).toEqual([])
    }
    await expect(panel(page).getByText(/新读取与已采用依据不同/)).toBeVisible()
    await panel(page).getByLabel('我已比对原变更、当前对象和冻结依据，明确追加这次人工判断。', { exact: true }).check()
    await expect(panel(page).getByRole('button', { name: '明确保存内容决定', exact: true })).toBeDisabled()
    await panel(page).getByRole('button', { name: '丢弃未提交表单与冻结依据', exact: true }).click()
    await panel(page).getByRole('button', { name: '采用本次对象依据准备决定', exact: true }).click(); await form(page, 'no_revision_needed', reason)
    await page.getByRole('button', { name: '关闭创作', exact: true }).click()
    const guard = page.getByRole('dialog', { name: '保留创作原命令', exact: true }); await guard.getByRole('button', { name: '返回创作', exact: true }).click(); await expect(panel(page).getByRole('textbox', { name: '决定理由', exact: true })).toHaveValue(reason)
    await page.getByRole('button', { name: '关闭创作', exact: true }).click(); await guard.getByRole('button', { name: '保留原命令，明确丢弃临时表单并关闭', exact: true }).click()
    await open(page); await expect(panel(page).getByText(/本页仍保留未提交的内容决定表单与原依据/)).toHaveCount(0)
    expect(await journal(page)).toEqual([]); expect((await view(page, event, target)).decisions).toEqual([]); expect(decisionWrites).toEqual([])
    writeFileSync(info.outputPath('unsubmitted-form-readback.json'), JSON.stringify({ scope: 'Synthetic unsubmitted judgment; two real role cycles, fresh same-session restore, changed target keeps original basis, confirmed explicit close discard. No Content decision HTTP write.', reason, event, decisionWrites, original_target: publication.fixture.lessons[0], durable_commands: await journal(page), decisions: (await view(page, event, target)).decisions }, null, 2))
  } finally { await runtime.close() }
})
