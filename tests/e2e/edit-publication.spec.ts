import { execFileSync } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { ContentRef, DraftCreated, DraftPublishWrite, EditDraftSnapshot, StoredReviewReceipt } from '../../packages/contracts/generated/api-types'
import { RestartRuntime } from './restartRuntime'
import { importReaderPackage, type ReaderPackage } from './readerTestData'

function originalEditPackage(): ReaderPackage {
  const root = resolve(import.meta.dirname, '../..')
  const script = `import base64,hashlib,json,io,zipfile
from packages.contracts import domain_models as d
from packages.contracts.canonical import canonical_bytes,metadata_sha256
body='原创合成编辑正文。仅验证软件保存、冲突与恢复，不作教学批准。\\n'
b=d.ContentBlock(id='block_native_edit',revision=1,kind='text',title='原创合成编辑标题',body_path='content/native-edit.md',body_sha256=hashlib.sha256(body.encode()).hexdigest())
def ref(x): return d.ContentRef(entity=x.entity,id=x.id,revision=x.revision,sha256=metadata_sha256(x))
l=d.Lesson(id='lesson_native_edit',revision=1,title='原创编辑验收小节',objectives=['保留原文'],block_refs=[ref(b)])
c=d.Course(id='course_native_edit',revision=1,title='原创编辑验收教材',audience='合成验收',lesson_refs=[ref(l)])
p={'course.json':canonical_bytes(c),'concepts.json':b'[]','symbols.json':b'[]','sources/citations.json':b'[]','blocks/native-edit.json':canonical_bytes(b),'lessons/native-edit.json':canonical_bytes(l),b.body_path:body.encode()}
m=d.Manifest(package_id='package_native_edit',profile='learner',created_at='2026-09-28T00:00:00Z',files=[d.FileEntry(path=k,sha256=hashlib.sha256(v).hexdigest(),size=len(v),media_type='text/markdown' if k.endswith('.md') else 'application/json',visibility='learner') for k,v in sorted(p.items())])
p['manifest.json']=canonical_bytes(m)
f=io.BytesIO()
with zipfile.ZipFile(f,'w') as z:
 for k,v in sorted(p.items()): z.writestr(zipfile.ZipInfo(k,date_time=(2026,9,28,0,0,0)),v)
print(json.dumps({'archive':base64.b64encode(f.getvalue()).decode(),'course':ref(c).model_dump(),'lessons':[ref(l).model_dump()],'blocks':[ref(b).model_dump()],'bodies':{b.id:body}}))`
  const value = JSON.parse(execFileSync(`${root}/.venv/bin/python`, ['-B', '-c', script], { cwd: root, encoding: 'utf8' }))
  return { ...value, bytes: Buffer.from(value.archive, 'base64') }
}

const editor = (page: Page) => page.getByRole('region', { name: '文本块编辑与恢复', exact: true })
async function readDraft(page: Page, id: string) {
  await editor(page).getByLabel('读取已有编辑稿 ID', { exact: true }).fill(id)
  await editor(page).getByRole('button', { name: '另行读取服务端草稿头', exact: true }).click()
  await expect(editor(page).getByLabel('本机正文', { exact: true })).toBeVisible()
}
async function journal(page: Page) {
  return page.evaluate(async () => {
    const db = await new Promise<IDBDatabase>((yes, no) => { const r = indexedDB.open('learning-workbench.edit-publication-commands.v1', 1); r.onsuccess = () => yes(r.result); r.onerror = () => no(r.error) })
    try { return await new Promise<string[]>((yes, no) => { const t = db.transaction('drafts', 'readonly'), r = t.objectStore('drafts').getAll(); r.onsuccess = () => yes(r.result.map((x: { text: string }) => x.text)); r.onerror = () => no(r.error) }) } finally { db.close() }
  })
}
test('native saved edit enters Review, explicit synthetic decisions publish base+1, preserve parent pins, original ACK and restart recovery', async ({ playwright }, info) => {
  test.setTimeout(150_000)
  const runtime = await RestartRuntime.start(), errors: string[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]
    page.on('pageerror', error => errors.push(error.message)); await runtime.authenticateOnly(page)
    const fixture = originalEditPackage(), imported = await importReaderPackage(page, fixture)
    await imported.dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
    await expect(imported.dialog.getByText('操作角色：作者', { exact: true })).toBeVisible()
    await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    const href = `${runtime.origin}/?reader=${encodeURIComponent(JSON.stringify({ course: fixture.course, lesson: fixture.lessons[0], block: fixture.blocks[0], view: 'lesson' }))}`
    await page.goto(href); await editor(page).getByRole('button', { name: '编辑此精确文本块', exact: true }).click()
    const create = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/api/v1/drafts'))
    await editor(page).getByRole('button', { name: '从此准确修订明确创建编辑稿', exact: true }).click()
    const createdResponse = await create; expect(createdResponse.status()).toBe(201)
    const created: DraftCreated = await createdResponse.json(), id = created.draft_id
    await readDraft(page, id)
    const enter = editor(page).getByRole('button', { name: '核验已保存精确编辑稿并进入审核', exact: true })
    await editor(page).getByLabel('本机标题', { exact: true }).fill('发布后的原创合成编辑标题')
    await editor(page).getByLabel('本机正文', { exact: true }).fill('原创合成编辑发布正文，仅验证软件流程。\n')
    await expect(enter).toBeDisabled()
    const patch = page.waitForResponse(r => r.request().method() === 'PATCH' && r.url().endsWith(`/api/v1/drafts/${id}`))
    await editor(page).getByRole('button', { name: '明确提交本机标题与正文', exact: true }).click()
    expect((await patch).status()).toBe(200); await expect(enter).toBeDisabled()
    await readDraft(page, id); await expect(enter).toBeEnabled(); await enter.click()
    const draft: EditDraftSnapshot = await page.request.get(`/api/v1/draft-edits/${id}`).then(r => r.json())
    expect(draft.owner).toBe('authoring_edit'); expect(draft.candidate.draft_revision).toBe(2)
    const panel = editor(page).getByRole('region', { name: '候选审核与原命令恢复', exact: true })
    await expect(panel.getByText(draft.candidate.candidate_sha256, { exact: true })).toBeVisible()
    await panel.getByLabel('本次审核备注', { exact: true }).fill('合成浏览器软件验收，不作真实数学、来源或教学批准。')
    await panel.getByLabel('我已核对候选 ID、修订、哈希与本次检查范围，明确创建审核任务。', { exact: true }).check()
    const reviewing = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/api/v1/drafts/${id}/review`))
    await panel.getByRole('button', { name: '明确创建本次审核任务', exact: true }).click()
    const reviewResponse = await reviewing; expect(reviewResponse.status()).toBe(202); const review = await reviewResponse.json()
    const read = panel.getByRole('button', { name: '另行读取当前审核回执', exact: true })
    await expect(read).toBeEnabled(); await read.click()
    const decision = panel.getByRole('region', { name: '明确人工审核决定', exact: true })
    await decision.getByLabel('数学审核决定').selectOption('NOT_APPLICABLE')
    await decision.getByLabel('来源审核决定').selectOption('APPROVED')
    await decision.getByLabel('审核理由').fill('明确合成判断：原创纯文本无数学断言，核对合成来源。仅作软件验收。')
    await decision.getByLabel('我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。', { exact: true }).check()
    const deciding = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/api/v1/reviews/${review.id}/decision`))
    await decision.getByRole('button', { name: '明确保存这次人工审核决定', exact: true }).click()
    const decided = await deciding; expect(decided.status()).toBe(200); const human: StoredReviewReceipt = await decided.json()
    await expect(read).toBeEnabled(); await read.click()
    const publication = panel.getByRole('region', { name: '编辑稿发布与恢复', exact: true })
    await publication.getByRole('button', { name: '选择此审核并重新读取编辑发布基准', exact: true }).click()
    const basis = publication.getByRole('region', { name: '本次编辑发布基准', exact: true })
    await expect(basis).toContainText(draft.candidate.candidate_sha256)
    for (const box of await basis.getByRole('group', { name: '逐条确认此块警告' }).getByRole('checkbox').all()) await box.check()
    await basis.getByLabel('我已核对准确编辑稿、原块与所选人工审核，明确发布为原块下一修订。', { exact: true }).check()
    await editor(page).getByRole('button', { name: '收起文本编辑', exact: true }).click()
    await page.getByRole('dialog', { name: '保留本机编辑', exact: true }).getByRole('button', { name: '返回编辑', exact: true }).click()
    await expect(basis.getByRole('checkbox').last()).toBeChecked()
    for (const width of [1440, 390]) {
      await page.setViewportSize({ width, height: 900 }); await basis.scrollIntoViewIfNeeded()
      expect(await editor(page).evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true)
      await page.screenshot({ path: info.outputPath(`edit-publication-basis-${width}.png`) })
    }
    await page.setViewportSize({ width: 1440, height: 900 })
    const commands: { key: string; body: DraftPublishWrite }[] = []; let original!: ContentRef, dropped = false
    await page.route(`**/api/v1/drafts/${id}/publish`, async route => {
      commands.push({ key: route.request().headers()['idempotency-key'], body: route.request().postDataJSON() })
      if (commands.length === 1) { const response = await route.fetch(); expect(response.status()).toBe(201); original = await response.json(); await route.abort('failed'); dropped = true }
      else await route.continue()
    })
    await basis.getByRole('button', { name: '明确发布这一编辑稿', exact: true }).click()
    await expect.poll(() => dropped).toBe(true)
    await expect(publication.getByText('发布结果未知，原 key 与完整命令保留', { exact: true })).toBeVisible()
    const retained = (await journal(page)).map(value => JSON.parse(value)); expect(retained).toHaveLength(1)
    expect(retained[0].basis.owner).toBe('authoring_edit'); expect(retained[0].body).toEqual(commands[0].body); expect(retained[0].ack).toBeNull()
    expect(original.id).toBe(fixture.blocks[0].id); expect(original.revision).toBe(2); expect(original.sha256).not.toBe(draft.candidate.candidate_sha256)
    // Actual IndexedDB abort while persisting the received replay ACK.
    await page.evaluate(() => {
      const original = IDBDatabase.prototype.transaction
      Object.assign(window, { restorePublicationIdb: () => { IDBDatabase.prototype.transaction = original } })
      IDBDatabase.prototype.transaction = function (...args: Parameters<IDBDatabase['transaction']>) {
        const tx = original.apply(this, args)
        if (this.name === 'learning-workbench.edit-publication-commands.v1' && args[1] === 'readwrite') queueMicrotask(() => tx.abort())
        return tx
      }
    })
    const replay = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith(`/api/v1/drafts/${id}/publish`))
    await publication.getByRole('button', { name: `显式回放原编辑发布命令 ${commands[0].key}`, exact: true }).click()
    const ackResponse = await replay; expect(ackResponse.status()).toBe(201); expect(await ackResponse.json()).toEqual(original)
    await expect(publication.getByText(/原发布命令或回执尚未安全落盘/)).toBeVisible(); expect(commands[1]).toEqual(commands[0])
    expect((await journal(page)).map(value => JSON.parse(value))[0].ack).toBeNull()
    await page.getByRole('button', { name: '导入', exact: true }).click()
    const roleDialog = page.getByRole('dialog', { name: '导入', exact: true })
    await roleDialog.getByRole('button', { name: '切换为学习者角色', exact: true }).click()
    await expect(roleDialog.getByText('操作角色：学习者', { exact: true })).toBeVisible()
    await roleDialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    await editor(page).getByRole('button', { name: '编辑此精确文本块', exact: true }).click()
    await editor(page).getByRole('button', { name: '打开编辑审核与发布恢复', exact: true }).click()
    await expect(publication.getByText(/原发布命令或回执尚未安全落盘/)).toBeVisible()
    expect(await publication.getByText(draft.candidate.candidate_sha256, { exact: true }).count()).toBe(0)
    await page.getByRole('button', { name: '关闭标签 原创合成编辑标题 · r1', exact: true }).click()
    const closeGuard = page.getByRole('dialog', { name: '保留文本编辑草稿', exact: true })
    await expect(closeGuard.getByRole('button', { name: '保留本机编辑并关闭标签', exact: true })).toBeDisabled()
    await closeGuard.getByRole('button', { name: '返回文本编辑', exact: true }).click()
    await page.evaluate(() => { (window as unknown as { restorePublicationIdb(): void }).restorePublicationIdb() })
    await page.getByRole('button', { name: '导入', exact: true }).click()
    await roleDialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
    await expect(roleDialog.getByText('操作角色：作者', { exact: true })).toBeVisible()
    await roleDialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    await editor(page).getByRole('button', { name: '编辑此精确文本块', exact: true }).click()
    await editor(page).getByRole('button', { name: '打开编辑审核与发布恢复', exact: true }).click()
    await publication.getByRole('button', { name: '保存原会话的编辑发布内存记录', exact: true }).click()
    await expect(publication.getByText('原发布 ACK 已保存', { exact: true })).toBeVisible()
    await expect(publication.getByRole('button', { name: `显式回放原编辑发布命令 ${commands[0].key}`, exact: true })).toBeDisabled()
    expect(commands).toHaveLength(2)
    await publication.getByRole('button', { name: `另行读取当前引用 ${original.id}`, exact: true }).click()
    await expect(publication.getByRole('region', { name: '另行读取的当前引用', exact: true })).toContainText(original.sha256)
    const saved = await page.request.get(`/api/v1/draft-edits/${id}`).then(r => r.json()); expect(saved.state).toBe('published')
    const lessonBefore = await page.request.get(`/api/v1/lessons/${fixture.lessons[0].id}?revision=1`).then(r => r.json())
    expect(lessonBefore.block_refs).toEqual(fixture.blocks)
    expect(await page.request.get(`/api/v1/blocks/${original.id}/body?revision=2`).then(r => r.text())).toBe(draft.payload.body_markdown)
    expect(await page.request.get(`/api/v1/blocks/${original.id}/body?revision=1`).then(r => r.text())).toBe(fixture.bodies[original.id])
    const durable = await journal(page), database = runtime.databaseIdentity()
    await runtime.closeBrowser(); await runtime.restartApiAfterBrowserClosed()
    const reopened = await runtime.openBrowser(playwright.chromium), restored = reopened.pages()[0]
    await restored.goto(href); await editor(restored).getByRole('button', { name: '编辑此精确文本块', exact: true }).click()
    await editor(restored).getByRole('button', { name: '打开编辑审核与发布恢复', exact: true }).click()
    await expect(editor(restored).getByRole('button', { name: `显式回放原编辑发布命令 ${commands[0].key}`, exact: true })).toBeDisabled()
    expect(await journal(restored)).toEqual(durable); expect(runtime.databaseIdentity()).toEqual(database)
    const restoredCurrent = await restored.request.get(`/api/v1/objects/${original.id}/current`).then(r => r.json()); expect(restoredCurrent).toEqual(original)
    expect(await restored.request.get(`/api/v1/lessons/${fixture.lessons[0].id}?revision=1`).then(r => r.json())).toEqual(lessonBefore)
    expect((await restored.request.get(`/api/v1/draft-edits/${id}?revision=2`).then(r => r.json())).state).toBe('published')
    expect(errors).toEqual([])
    writeFileSync(info.outputPath('edit-publication-flow.json'), JSON.stringify({ scope: 'Synthetic native editing, real SQLite/HTTP/IndexedDB, explicit Review and author decisions, publication, original-key replay, old parent pin and restart. No provider or real quality acceptance.', created, draft, human, commands, original, restoredCurrent, lessonBefore, retained, generations: runtime.generations.length, errors }, null, 2))
  } finally { await runtime.close() }
})
