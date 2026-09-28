import { execFileSync } from 'node:child_process'
import { writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { expect, test, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { DraftCreated, DraftPatched, DraftPatchWrite, EditDraftSnapshot } from '../../packages/contracts/generated/api-types'
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
const panel = (page: Page) => page.getByRole('region', { name: '文本块编辑与恢复', exact: true })
const submit = (page: Page) => panel(page).getByRole('button', { name: '明确提交本机标题与正文', exact: true })
async function open(page: Page, href: string) {
  await page.goto(href)
  await panel(page).getByRole('button', { name: '编辑此精确文本块', exact: true }).click()
  await expect(panel(page).getByRole('button', { name: '从此准确修订明确创建编辑稿', exact: true })).toBeEnabled()
}
async function read(page: Page, id: string) {
  await panel(page).getByLabel('读取已有编辑稿 ID', { exact: true }).fill(id)
  await panel(page).getByRole('button', { name: '另行读取服务端草稿头', exact: true }).click()
  await expect(panel(page).getByLabel('本机标题', { exact: true })).toBeEditable()
}
async function change(page: Page, title: string, body: string) {
  await panel(page).getByLabel('本机标题', { exact: true }).fill(title)
  await panel(page).getByLabel('本机正文', { exact: true }).fill(body)
  await expect(submit(page)).toBeEnabled()
}
test('real editor retains IndexedDB originals through competing tabs, 412 resolution, lost ACK, browser and API restart', async ({ playwright }, info) => {
  test.setTimeout(120_000)
  const runtime = await RestartRuntime.start(), errors: string[] = [], writes: { method: string; path: string; body: unknown }[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), a = context.pages()[0]
    await runtime.authenticateOnly(a)
    const fixture = originalEditPackage(), imported = await importReaderPackage(a, fixture)
    await imported.dialog.getByRole('button', { name: '切换为作者角色', exact: true }).click()
    await expect(imported.dialog.getByText('操作角色：作者', { exact: true })).toBeVisible()
    await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    const href = `${runtime.origin}/?reader=${encodeURIComponent(JSON.stringify({ course: fixture.course, lesson: fixture.lessons[0], block: fixture.blocks[0], view: 'lesson' }))}`
    await open(a, href)
    const creating = a.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/api/v1/drafts'))
    await panel(a).getByRole('button', { name: '从此准确修订明确创建编辑稿', exact: true }).click()
    const createdResponse = await creating; expect(createdResponse.status()).toBe(201)
    const created: DraftCreated = await createdResponse.json(), id = created.draft_id
    await read(a, id)
    const b = await context.newPage(); await open(b, href); await read(b, id)
    for (const p of [a, b]) { p.on('pageerror', e => errors.push(e.message)); p.on('request', r => { const path = new URL(r.url()).pathname; if (r.method() === 'PATCH' && path === `/api/v1/drafts/${id}`) writes.push({ method: r.method(), path, body: r.postDataJSON() }) }) }
    await change(a, '甲标签服务器新标题', '甲标签服务器新正文\n')
    await change(b, '乙标签本机标题', '乙标签本机正文 🧠\n')
    const savingA = a.waitForResponse(r => r.request().method() === 'PATCH' && r.url().endsWith(`/api/v1/drafts/${id}`))
    await submit(a).click(); expect((await savingA).status()).toBe(200)
    const savingB = b.waitForResponse(r => r.request().method() === 'PATCH' && r.url().endsWith(`/api/v1/drafts/${id}`))
    await submit(b).click(); expect((await savingB).status()).toBe(412)
    let conflict = panel(b).getByRole('region', { name: '三方冲突恢复', exact: true })
    await expect(conflict.getByLabel('基准标题', { exact: true })).toHaveValue('原创合成编辑标题')
    await expect(conflict.getByLabel('本地待同步正文', { exact: true })).toHaveValue('乙标签本机正文 🧠\n')
    await expect(conflict.getByLabel('服务端当前标题', { exact: true })).toHaveValue('甲标签服务器新标题')
    const originalCommands = await b.evaluate(async () => {
      const db = await new Promise<IDBDatabase>((yes, no) => { const r = indexedDB.open('learning-workbench.edit-commands.v1', 1); r.onsuccess = () => yes(r.result); r.onerror = () => no(r.error) })
      try { return await new Promise<string[]>((yes, no) => { const t = db.transaction('drafts', 'readonly'); const r = t.objectStore('drafts').getAll(); r.onsuccess = () => yes(r.result.map((x: { text: string }) => x.text)); r.onerror = () => no(r.error) }) } finally { db.close() }
    })
    const rejected = originalCommands.map(x => JSON.parse(x)).find(c => c.rejection === 412)
    expect(rejected.operation.local.body_markdown).toBe('乙标签本机正文 🧠\n')
    await b.reload(); await panel(b).getByRole('button', { name: '编辑此精确文本块', exact: true }).click()
    await panel(b).getByRole('button', { name: `读取原冲突三方内容 ${rejected.key}`, exact: true }).click()
    conflict = panel(b).getByRole('region', { name: '三方冲突恢复', exact: true })
    await expect(conflict.getByLabel('本地待同步正文', { exact: true })).toHaveValue('乙标签本机正文 🧠\n')
    for (const width of [1440, 390]) {
      await b.setViewportSize({ width, height: 900 }); await conflict.scrollIntoViewIfNeeded()
      expect(await panel(b).evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true)
      await b.screenshot({ path: info.outputPath(`editor-conflict-${width}.png`) })
    }
    await b.setViewportSize({ width: 1440, height: 900 })
    await conflict.getByLabel('标题解决方式', { exact: true }).selectOption('server')
    await conflict.getByLabel('正文解决方式', { exact: true }).selectOption('local')
    const resolveButton = conflict.getByRole('button', { name: '保存解决结果到本机，暂不提交', exact: true })
    await expect(resolveButton).toBeDisabled()
    await conflict.getByRole('checkbox').check(); await resolveButton.click()
    await expect(conflict).toHaveCount(0); expect(writes).toHaveLength(2)
    const resolving = b.waitForResponse(r => r.request().method() === 'PATCH' && r.url().endsWith(`/api/v1/drafts/${id}`))
    await submit(b).click(); const resolved = await resolving; expect(resolved.status()).toBe(200); expect((await resolved.json() as DraftPatched).revision).toBe(3)
    const current = await b.request.get(`/api/v1/draft-edits/${id}`).then(r => r.json()) as EditDraftSnapshot
    expect(current.candidate.draft_revision).toBe(3); expect(current.payload.title).toBe('甲标签服务器新标题'); expect(current.payload.body_markdown).toBe('乙标签本机正文 🧠\n')
    expect((writes[2].body as DraftPatchWrite).expected_revision).toBe(2)
    await read(b, id); await change(b, '丢失 ACK 的原命令标题', '保留原 key 的正文\n')
    const lostCommands: { key: string; body: DraftPatchWrite }[] = []; let dropped = false
    await b.route(`**/api/v1/drafts/${id}`, async route => {
      if (route.request().method() !== 'PATCH') return route.continue()
      lostCommands.push({ key: route.request().headers()['idempotency-key'], body: route.request().postDataJSON() })
      if (lostCommands.length === 1) { const actual = await route.fetch(); expect(actual.status()).toBe(200); expect((await actual.json()).revision).toBe(4); await route.abort('failed'); dropped = true }
      else await route.continue()
    })
    await submit(b).click(); await expect.poll(() => dropped).toBe(true)
    await expect(panel(b).getByText(/结果未知，完整原命令保留/)).toBeVisible()
    const replay = b.waitForResponse(r => r.request().method() === 'PATCH' && r.url().endsWith(`/api/v1/drafts/${id}`))
    await panel(b).getByRole('button', { name: `显式回放原编辑命令 ${lostCommands[0].key}`, exact: true }).click()
    expect((await replay).status()).toBe(200); expect(lostCommands).toHaveLength(2); expect(lostCommands[1]).toEqual(lostCommands[0])
    await expect(panel(b).getByText(new RegExp(`历史 ACK：草稿 ${id} r4`))).toBeVisible()
    const database = runtime.databaseIdentity()
    await runtime.closeBrowser(); await runtime.restartApiAfterBrowserClosed()
    const restored = await runtime.openBrowser(playwright.chromium), page = restored.pages()[0]
    await open(page, href)
    await expect(panel(page).getByRole('button', { name: `显式回放原编辑命令 ${lostCommands[0].key}`, exact: true })).toBeDisabled()
    await read(page, id); await expect(panel(page).getByLabel('本机标题', { exact: true })).toHaveValue('丢失 ACK 的原命令标题')
    expect(runtime.databaseIdentity()).toEqual(database)
    const history = await page.request.get(`/api/v1/draft-edits/${id}?revision=1`); expect(history.status()).toBe(200); expect((await history.json()).payload.title).toBe('原创合成编辑标题')
    const official = await page.request.get(`/api/v1/blocks/${fixture.blocks[0].id}/body?revision=1`); expect(await official.text()).toBe(fixture.bodies[fixture.blocks[0].id])
    await page.getByRole('button', { name: '导入', exact: true }).click()
    const dialog = page.getByRole('dialog', { name: '导入', exact: true }); await dialog.getByRole('button', { name: '切换为学习者角色', exact: true }).click()
    await expect(dialog.getByText('操作角色：学习者', { exact: true })).toBeVisible(); await dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
    await expect(panel(page).getByLabel('本机正文', { exact: true })).toHaveCount(0)
    expect((await page.request.get(`/api/v1/draft-edits/${id}`)).status()).toBe(403)
    expect(errors).toEqual([])
    writeFileSync(info.outputPath('editor-flow.json'), JSON.stringify({ scope: 'Real synthetic Import/SQLite/HTTP/IndexedDB, two pages, exact 412 recovery, original ACK replay, browser/API restart and role denial; no provider or content approval', created, current, rejected, writes, lostCommands, generations: runtime.generations.length, originalContentUnchanged: true, errors }, null, 2))
  } finally { await runtime.close() }
})
