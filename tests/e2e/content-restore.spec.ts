import { createHash } from 'node:crypto'
import { writeFileSync } from 'node:fs'
import { expect, test, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { ContentRef, ContentRestoreDraftCreateAck, ContentRestoreDraftSnapshot, StoredReviewReceipt } from '../../packages/contracts/generated/api-types'
import { RestartRuntime } from './restartRuntime'
import { importReaderPackage, originalReaderPackage } from './readerTestData'

const id = 'block_nativerestore_proof'
const block = (page: Page) => page.locator(`#block-${id}-r2`)
const restore = (page: Page) => block(page).getByRole('region', { name: '历史内容块恢复与审核', exact: true })
async function journal(page: Page, name: 'create' | 'publication') {
  return page.evaluate(async name => {
    const db = await new Promise<IDBDatabase>((yes, no) => { const request = indexedDB.open(`learning-workbench.restore-${name}-commands.v1`, 1); request.onsuccess = () => yes(request.result); request.onerror = () => no(request.error) })
    try { return await new Promise<string[]>((yes, no) => { const tx = db.transaction('drafts', 'readonly'), request = tx.objectStore('drafts').getAll(); request.onsuccess = () => yes(request.result.map((value: { text: string }) => value.text)); request.onerror = () => no(request.error) }) } finally { db.close() }
  }, name)
}
async function historical(page: Page, runtime: RestartRuntime) {
  const current = originalReaderPackage('nativerestore', 2, true), old = originalReaderPackage('nativerestore', 1)
  const imported = await importReaderPackage(page, current)
  await imported.dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
  await expect(imported.dialog.getByText('操作角色：作者', { exact: true })).toBeVisible()
  await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  const href = `${runtime.origin}/?reader=${encodeURIComponent(JSON.stringify({ course: current.course, lesson: current.lessons[0], block: current.blocks[1], view: 'lesson' }))}`
  await page.goto(href)
  const compare = block(page).getByRole('region', { name: '块修订比较', exact: true })
  await compare.getByRole('button', { name: '比较此块的两个修订', exact: true }).click()
  await compare.getByRole('combobox', { name: '左侧修订', exact: true }).selectOption(old.blocks[1].sha256)
  await compare.getByRole('combobox', { name: '右侧修订', exact: true }).selectOption(current.blocks[1].sha256)
  await compare.getByRole('button', { name: '读取所选两个修订', exact: true }).click()
  expect(await compare.getByLabel('左侧完整原文', { exact: true }).textContent()).toBe(old.bodies[id])
  await compare.getByRole('button', { name: '选择左侧历史版本准备恢复', exact: true }).click()
  await restore(page).getByRole('button', { name: '重新读取当前基准并核验所选历史原件', exact: true }).click()
  expect(await restore(page).getByLabel('历史来源完整正文', { exact: true }).textContent()).toBe(old.bodies[id])
  await restore(page).getByRole('textbox', { name: '本次恢复理由', exact: true }).fill('原创合成历史 proof 恢复，仅作软件协议验收，不作真实数学或教学批准。')
  await restore(page).getByLabel('我已核对历史来源、当前基准与全部字段，明确创建独立待审恢复稿。', { exact: true }).check()
  return { current, old, href }
}
async function createReview(page: Page, lostCreate = false) {
  const creates: { key: string; body: unknown }[] = []; let createAck!: ContentRestoreDraftCreateAck, dropped = false
  await page.route('**/api/v1/content/restore-drafts', async route => {
    creates.push({ key: route.request().headers()['idempotency-key'], body: route.request().postDataJSON() })
    if (lostCreate && creates.length === 1) { const response = await route.fetch(); expect(response.status()).toBe(201); createAck = await response.json(); dropped = true; await route.abort('failed') }
    else await route.continue()
  })
  if (lostCreate) {
    await restore(page).getByRole('button', { name: '明确创建本次历史恢复稿', exact: true }).click()
    await expect.poll(() => dropped).toBe(true)
    await expect(restore(page).getByText('创建结果未知，原 key 与完整命令保留', { exact: false })).toBeVisible()
    const raw = (await journal(page, 'create')).map(value => JSON.parse(value)); expect(raw).toHaveLength(1); expect(raw[0].body).toEqual(creates[0].body); expect(raw[0].ack).toBeNull()
    const replay = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/content/restore-drafts'))
    await restore(page).getByRole('button', { name: `显式回放原恢复创建命令 ${creates[0].key}`, exact: true }).click()
    const response = await replay; expect(response.status()).toBe(201); expect(await response.json()).toEqual(createAck); expect(creates[1]).toEqual(creates[0])
  } else {
    const creating = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith('/content/restore-drafts'))
    await restore(page).getByRole('button', { name: '明确创建本次历史恢复稿', exact: true }).click()
    const response = await creating; expect(response.status()).toBe(201); createAck = await response.json()
  }
  await page.unroute('**/api/v1/content/restore-drafts')
  await restore(page).getByRole('button', { name: `另行读取恢复稿 ${createAck.candidate.draft_id}`, exact: true }).click()
  const draft: ContentRestoreDraftSnapshot = await page.request.get(`/api/v1/content/restore-drafts/${createAck.candidate.draft_id}`).then(response => response.json())
  expect(draft.owner).toBe('authoring_restore'); expect(draft.proposed_block.kind).toBe('proof'); expect(draft.proposed_block.revision).toBe(3)
  expect(await restore(page).getByLabel('恢复候选完整正文', { exact: true }).textContent()).toBe(draft.body_markdown)
  await restore(page).getByRole('button', { name: '打开恢复审核与发布恢复', exact: true }).click()
  const review = restore(page).getByRole('region', { name: '候选审核与原命令恢复', exact: true })
  await review.getByRole('textbox', { name: '本次审核备注', exact: true }).fill('本次新恢复候选的合成人审链，不继承旧批准。')
  await review.getByLabel('我已核对候选 ID、修订、哈希与本次检查范围，明确创建审核任务。', { exact: true }).check()
  const reviewing = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/drafts/${createAck.candidate.draft_id}/review`))
  await review.getByRole('button', { name: '明确创建本次审核任务', exact: true }).click()
  const response = await reviewing; expect(response.status()).toBe(202); const job = await response.json()
  const read = review.getByRole('button', { name: '另行读取当前审核回执', exact: true }); await expect(read).toBeEnabled(); await read.click()
  const decision = review.getByRole('region', { name: '明确人工审核决定', exact: true })
  await decision.getByLabel('数学审核决定').selectOption('APPROVED'); await decision.getByLabel('来源审核决定').selectOption('APPROVED')
  await decision.getByLabel('审核理由').fill('仅原创合成软件验收判断，不声称真实数学、来源或教学批准。')
  await decision.getByLabel('我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。', { exact: true }).check()
  const deciding = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/reviews/${job.id}/decision`))
  await decision.getByRole('button', { name: '明确保存这次人工审核决定', exact: true }).click()
  expect((await deciding).status()).toBe(200); await expect(read).toBeEnabled(); await read.click()
  const publication = review.getByRole('region', { name: '恢复稿发布与恢复', exact: true })
  await publication.getByRole('button', { name: '选择此审核并重新读取恢复发布基准', exact: true }).click()
  const basis = publication.getByRole('region', { name: '本次恢复发布基准', exact: true })
  await expect(basis).toContainText(draft.candidate.candidate_sha256)
  for (const box of await basis.getByRole('group', { name: '逐条确认此块警告' }).getByRole('checkbox').all()) await box.check()
  await basis.getByLabel('我已核对准确恢复稿、历史原块、当前基准与所选人工审核，明确发布为当前基准下一修订。', { exact: true }).check()
  return { createAck, draft, creates, publication, basis }
}
test('native historical proof restores through its own candidate, fresh human Review, lost ACK/IDB/role recovery and restart without changing parent pins', async ({ playwright }, info) => {
  test.setTimeout(150_000)
  const runtime = await RestartRuntime.start(), errors: string[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    page.on('pageerror', error => errors.push(error.message)); await runtime.authenticateOnly(page)
    const fixture = await historical(page, runtime), prepared = await createReview(page, true)
    const { draft, publication, basis } = prepared, draftId = draft.candidate.draft_id
    const parentBefore = await page.request.get(`/api/v1/lessons/${fixture.current.lessons[0].id}?revision=2`).then(response => response.json())
    for (const width of [1440, 390]) { await page.setViewportSize({ width, height: 900 }); await basis.scrollIntoViewIfNeeded(); expect(await restore(page).evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBe(true); await page.screenshot({ path: info.outputPath(`restore-basis-${width}.png`) }) }
    await page.setViewportSize({ width: 1440, height: 900 })
    const commands: { key: string; body: unknown }[] = []; let original!: ContentRef, dropped = false
    await page.route(`**/api/v1/drafts/${draftId}/publish`, async route => {
      commands.push({ key: route.request().headers()['idempotency-key'], body: route.request().postDataJSON() })
      if (commands.length === 1) { const response = await route.fetch(); expect(response.status()).toBe(201); original = await response.json(); dropped = true; await route.abort('failed') } else await route.continue()
    })
    await basis.getByRole('button', { name: '明确发布这一恢复稿', exact: true }).click(); await expect.poll(() => dropped).toBe(true)
    await expect(publication.getByText('发布结果未知，原 key 与完整命令保留', { exact: true })).toBeVisible()
    expect((await journal(page, 'publication')).map(value => JSON.parse(value))[0].ack).toBeNull()
    await page.evaluate(() => {
      const original = IDBDatabase.prototype.transaction
      Object.assign(window, { restoreIdb: () => { IDBDatabase.prototype.transaction = original } })
      IDBDatabase.prototype.transaction = function (...args: Parameters<IDBDatabase['transaction']>) {
        const tx = original.apply(this, args)
        if (this.name === 'learning-workbench.restore-publication-commands.v1' && args[1] === 'readwrite') queueMicrotask(() => tx.abort())
        return tx
      }
    })
    const replay = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/drafts/${draftId}/publish`))
    await publication.getByRole('button', { name: `显式回放原恢复发布命令 ${commands[0].key}`, exact: true }).click()
    const ack = await replay; expect(ack.status()).toBe(201); expect(await ack.json()).toEqual(original); expect(commands[1]).toEqual(commands[0])
    await expect(publication.getByText(/原发布命令或回执尚未安全落盘/)).toBeVisible()
    await page.getByRole('button', { name: '导入', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: '导入', exact: true })
    await dialog.getByRole('button', { name: '切换为学习者角色', exact: true }).click(); await expect(dialog.getByText('操作角色：学习者', { exact: true })).toBeVisible()
    await dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    await block(page).getByRole('button', { name: '打开此块的恢复原记录', exact: true }).click()
    await restore(page).getByRole('button', { name: '打开恢复审核与发布恢复', exact: true }).click()
    expect(await restore(page).getByLabel('恢复候选完整正文', { exact: true }).count()).toBe(0)
    expect(await publication.getByText(draft.candidate.candidate_sha256, { exact: true }).count()).toBe(0)
    expect(await page.evaluate(() => { const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event); return event.defaultPrevented })).toBe(true)
    await page.evaluate(() => { (window as unknown as { restoreIdb(): void }).restoreIdb() })
    await page.getByRole('button', { name: '导入', exact: true }).click(); await dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click(); await expect(dialog.getByText('操作角色：作者', { exact: true })).toBeVisible(); await dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    await block(page).getByRole('button', { name: '打开此块的恢复原记录', exact: true }).click(); await restore(page).getByRole('button', { name: '打开恢复审核与发布恢复', exact: true }).click()
    await publication.getByRole('button', { name: '保存原会话的恢复发布内存记录', exact: true }).click()
    await expect(publication.getByText('原发布 ACK 已保存', { exact: true })).toBeVisible(); expect(commands).toHaveLength(2)
    await expect(publication.getByRole('button', { name: `显式回放原恢复发布命令 ${commands[0].key}`, exact: true })).toBeDisabled()
    expect(original.id).toBe(id); expect(original.revision).toBe(3); expect(original.sha256).not.toBe(draft.candidate.candidate_sha256)
    const body = await page.request.get(`/api/v1/blocks/${id}/body?revision=3`).then(response => response.text())
    expect(body).toBe(fixture.old.bodies[id]); expect(createHash('sha256').update(body).digest('hex')).toBe(draft.proposed_block.body_sha256)
    expect(await page.request.get(`/api/v1/blocks/${id}?revision=3`).then(response => response.json())).toEqual(draft.proposed_block)
    expect(await page.request.get(`/api/v1/lessons/${fixture.current.lessons[0].id}?revision=2`).then(response => response.json())).toEqual(parentBefore)
    const retained = await journal(page, 'publication'), db = runtime.databaseIdentity()
    await runtime.closeBrowser(); await runtime.restartApiAfterBrowserClosed()
    const reopened = await runtime.openBrowser(playwright.chromium), restored = reopened.pages()[0]; await restored.goto(fixture.href)
    await block(restored).getByRole('button', { name: '打开此块的恢复原记录', exact: true }).click()
    await restore(restored).getByRole('button', { name: `另行读取恢复稿 ${draftId}`, exact: true }).click()
    await expect(restore(restored).getByRole('region', { name: '实际读取的恢复候选', exact: true })).toContainText('published')
    expect((await restored.request.get(`/api/v1/content/restore-drafts/${draftId}`).then(response => response.json())).published_ref).toEqual(original)
    expect(await journal(restored, 'publication')).toEqual(retained); expect(runtime.databaseIdentity()).toEqual(db); expect(errors).toEqual([])
    writeFileSync(info.outputPath('restore-flow.json'), JSON.stringify({ scope: 'Synthetic real UI/HTTP/SQLite/IndexedDB proof restoration; explicit synthetic human judgments are not quality approval.', createAck: prepared.createAck, creates: prepared.creates, draft, commands, original, parentBefore, retained, generations: runtime.generations.length, errors }, null, 2))
  } finally { await runtime.close() }
})

async function post(page: Page, path: string, body: unknown, key: string) {
  return page.evaluate(async ({ path, body, key }) => {
    const session = await fetch('/api/v1/session').then(response => response.json())
    const response = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': session.csrf_token, 'Idempotency-Key': key }, body: JSON.stringify(body) })
    return { status: response.status, body: await response.json() }
  }, { path, body, key })
}
test('unsubmitted Restore reason survives a role cycle and explicit fresh read without creating a draft', async ({ playwright }, info) => {
  test.setTimeout(120_000)
  const runtime = await RestartRuntime.start(), commands: string[] = [], errors: string[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    page.on('pageerror', error => errors.push(error.message))
    page.on('request', request => { if (request.method() === 'POST' && request.url().endsWith('/content/restore-drafts')) commands.push(request.postData() ?? '') })
    await runtime.authenticateOnly(page)
    const fixture = await historical(page, runtime)
    const reason = '尚未提交的恢复理由：保留 Unicode 数学文字 α 与原始依据。'
    await restore(page).getByRole('textbox', { name: '本次恢复理由', exact: true }).fill(reason)
    await restore(page).getByLabel('我已核对历史来源、当前基准与全部字段，明确创建独立待审恢复稿。', { exact: true }).check()
    expect(await page.evaluate(() => { const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event); return event.defaultPrevented })).toBe(true)
    await page.getByRole('button', { name: '导入', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: '导入', exact: true })
    await dialog.getByRole('button', { name: '切换为学习者角色', exact: true }).click()
    await expect(dialog.getByText('操作角色：学习者', { exact: true })).toBeVisible()
    await dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    await block(page).getByRole('button', { name: '打开此块的恢复原记录', exact: true }).click()
    await expect(restore(page).getByText('本页保留了未提交的恢复理由和原依据。', { exact: false })).toBeVisible()
    expect(await restore(page).getByRole('textbox', { name: '本次恢复理由', exact: true }).count()).toBe(0)
    expect(await restore(page).getByText(reason, { exact: true }).count()).toBe(0)
    await expect(restore(page).getByRole('button', { name: '重新核验并恢复原会话的恢复表单', exact: true })).toBeDisabled()
    await page.getByRole('button', { name: '导入', exact: true }).click()
    await dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
    await expect(dialog.getByText('操作角色：作者', { exact: true })).toBeVisible()
    await dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    await block(page).getByRole('button', { name: '打开此块的恢复原记录', exact: true }).click()
    const reads: string[] = []
    page.on('request', request => { if (request.method() === 'GET') reads.push(new URL(request.url()).pathname) })
    await restore(page).getByRole('button', { name: '重新核验并恢复原会话的恢复表单', exact: true }).click()
    await expect(restore(page).getByRole('textbox', { name: '本次恢复理由', exact: true })).toHaveValue(reason)
    await expect(restore(page).getByLabel('我已核对历史来源、当前基准与全部字段，明确创建独立待审恢复稿。', { exact: true })).not.toBeChecked()
    expect(reads).toContain('/api/v1/session')
    expect(reads).toContain(`/api/v1/objects/${id}/current`)
    expect(reads.filter(path => path === `/api/v1/blocks/${id}/body`)).toHaveLength(2)
    expect(await restore(page).getByLabel('历史来源完整正文', { exact: true }).textContent()).toBe(fixture.old.bodies[id])
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 })
      await restore(page).getByRole('textbox', { name: '本次恢复理由', exact: true }).scrollIntoViewIfNeeded()
      expect(await restore(page).evaluate(element => element.scrollWidth <= element.clientWidth + 1)).toBe(true)
      await page.screenshot({ path: info.outputPath(`restore-unsent-form-${width}.png`) })
    }
    await restore(page).getByRole('button', { name: '明确清除未提交的恢复表单', exact: true }).click()
    expect(await restore(page).getByRole('textbox', { name: '本次恢复理由', exact: true }).count()).toBe(0)
    expect(await page.evaluate(() => { const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event); return event.defaultPrevented })).toBe(false)
    expect(commands).toEqual([]); expect(errors).toEqual([])
    writeFileSync(info.outputPath('restore-unsent-form.json'), JSON.stringify({ source: fixture.old.blocks[1], base: fixture.current.blocks[1], reason, reads, commands, errors, scope: 'Real UI role cycle and fresh source reads; zero Restore create POST; page-only same-session form.' }, null, 2))
  } finally { await runtime.close() }
})
test('actual current publication race returns 412 without rebasing the already prepared Restore UI candidate', async ({ playwright }, info) => {
  test.setTimeout(120_000)
  const runtime = await RestartRuntime.start()
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; await runtime.authenticateOnly(page)
    const fixture = await historical(page, runtime), prepared = await createReview(page)
    const create = await post(page, '/api/v1/content/restore-drafts', { source_ref: fixture.old.blocks[1], expected_current_ref: fixture.current.blocks[1], reason: '独立竞态恢复稿，仅合成软件验收。' }, 'restore_competitor_create'); expect(create.status).toBe(201)
    const candidate = create.body.candidate
    const reviewing = await post(page, `/api/v1/drafts/${candidate.draft_id}/review`, { expected_revision: 1, checks: ['structure', 'mathematics', 'sources'], reviewer_note: '独立合成审核。' }, 'restore_competitor_review'); expect(reviewing.status).toBe(202)
    let machine!: StoredReviewReceipt
    await expect.poll(async () => { const response = await page.request.get(`/api/v1/reviews/${reviewing.body.id}`); if (response.status() === 200) machine = await response.json(); return response.status() }).toBe(200)
    const decision = await post(page, `/api/v1/reviews/${machine.id}/decision`, { expected_revision: machine.revision, candidate_sha256: candidate.candidate_sha256, mathematical: 'APPROVED', sources: 'APPROVED', reason: '仅竞态协议验证，不作真实质量批准。', evidence_artifact_ids: [] }, 'restore_competitor_human'); expect(decision.status).toBe(200)
    const other: ContentRestoreDraftSnapshot = await page.request.get(`/api/v1/content/restore-drafts/${candidate.draft_id}`).then(response => response.json())
    const winner = await post(page, `/api/v1/drafts/${candidate.draft_id}/publish`, { expected_revision: 1, expected_content_sha256: candidate.candidate_sha256, review_receipt_id: machine.id, acknowledged_warning_codes: [...new Set(other.warnings.filter(value => value.severity === 'warning').map(value => value.code))] }, 'restore_competitor_publish'); expect(winner.status).toBe(201)
    const publishing = page.waitForResponse(response => response.request().method() === 'POST' && response.url().endsWith(`/drafts/${prepared.draft.candidate.draft_id}/publish`))
    await prepared.basis.getByRole('button', { name: '明确发布这一恢复稿', exact: true }).click(); expect((await publishing).status()).toBe(412)
    await expect(prepared.publication.getByText('服务端拒绝，原发布基准保留', { exact: true })).toBeVisible()
    const records = (await journal(page, 'publication')).map(value => JSON.parse(value)); expect(records).toHaveLength(1); expect(records[0].rejection.status).toBe(412); expect(records[0].basis.snapshot.base_ref).toEqual(fixture.current.blocks[1])
    expect((await page.request.get(`/api/v1/content/restore-drafts/${prepared.draft.candidate.draft_id}`).then(response => response.json())).state).toBe('draft')
    expect(await page.request.get(`/api/v1/objects/${id}/current`).then(response => response.json())).toEqual(winner.body)
    writeFileSync(info.outputPath('restore-race.json'), JSON.stringify({ prepared: prepared.draft, winner: winner.body, records, quality: 'Synthetic protocol judgments only.' }, null, 2))
  } finally { await runtime.close() }
})
