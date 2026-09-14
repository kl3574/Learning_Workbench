import { expect, test, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { writeFileSync } from 'node:fs'
import type { Note } from '../../packages/contracts/generated/types'
import { RestartRuntime } from './restartRuntime'
import { importReaderPackage, originalReaderPackage } from './readerTestData'

async function createNote(page: Page, runtime: RestartRuntime, prefix: string) {
  await runtime.authenticateOnly(page)
  const fixture = originalReaderPackage(prefix)
  const imported = await importReaderPackage(page, fixture)
  await imported.dialog.getByRole('button', { name: '关闭导入', exact: true }).click()
  const target = { course: fixture.course, lesson: fixture.lessons[0], view: 'lesson' }
  await page.goto(`${runtime.origin}/?reader=${encodeURIComponent(JSON.stringify(target))}`)
  const definition = page.locator(`#block-${fixture.blocks[0].id}-r1`)
  await definition.getByText('原始 Markdown 与精确选文', { exact: true }).click()
  await definition.getByLabel('原始 Markdown：定义：残差与损失').focus()
  await page.keyboard.press('Control+a')
  await page.getByRole('button', { name: '为当前选文记笔记', exact: true }).click()
  const notes = page.getByRole('dialog', { name: '笔记', exact: true })
  await notes.getByRole('button', { name: '用当前选文新建笔记', exact: true }).click()
  await notes.getByLabel('笔记正文').fill('已确认的基准笔记')
  const created = page.waitForResponse(value => value.request().method() === 'POST' && value.url().endsWith('/api/v1/notes'))
  await notes.getByRole('button', { name: '保存笔记到服务端', exact: true }).click()
  const response = await created
  expect(response.status()).toBe(201)
  const ref = await response.json()
  await expect(notes.getByText('笔记已保存到服务端', { exact: true })).toBeVisible()
  const note: Note = (await page.request.get('/api/v1/notes').then(value => value.json())).items.find((item: Note) => item.id === ref.id)
  return { fixture, notes, ref, note }
}

test('a concurrent note move to another block remains recoverable by stable note ID after a real 412', async ({ playwright }, info) => {
  test.setTimeout(60_000)
  const runtime = await RestartRuntime.start()
  try {
    const context = await runtime.openBrowser(playwright.chromium)
    const page = context.pages()[0]
    const { fixture, notes, ref, note } = await createNote(page, runtime, 'anchormove')
    await notes.getByLabel('笔记正文').fill('本机未同步续写，需要比较新的锚点')
    await expect(notes.getByText('本机草稿已保留；尚未同步为服务端笔记。', { exact: true })).toBeVisible()
    const body = fixture.bodies[fixture.blocks[1].id]
    const moved = { ...note, revision: 2, anchor: { ref: fixture.blocks[1], exact_quote: body, start_codepoint: 0, end_codepoint: Array.from(body).length }, markdown: '另一写入者已经重新绑定证明块' }
    const updated = await page.evaluate(async ({ moved, ref }) => {
      const auth = await fetch('/api/v1/session').then(value => value.json())
      const response = await fetch(`/api/v1/notes/${ref.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': auth.csrf_token, 'Idempotency-Key': crypto.randomUUID(), 'If-Match': `"${ref.sha256}"` }, body: JSON.stringify(moved) })
      return { status: response.status, value: await response.json() }
    }, { moved, ref })
    expect(updated.status).toBe(200)
    const saving = page.waitForResponse(value => value.request().method() === 'PATCH' && value.url().endsWith(`/api/v1/notes/${ref.id}`))
    await notes.getByRole('button', { name: '保存笔记到服务端', exact: true }).click()
    const rejected = await saving
    writeFileSync(info.outputPath('moved-note-cas.json'), JSON.stringify({ remote_status: updated.status, remote_ref: updated.value, local_status: rejected.status(), remote_anchor: moved.anchor }, null, 2))
    expect(rejected.status()).toBe(412)
    await expect(notes.getByRole('heading', { name: '笔记版本冲突', exact: true })).toBeVisible()
    await notes.getByText('比较锚点与准确引用', { exact: true }).click()
    await expect(notes.locator('.note-conflict')).toContainText(fixture.blocks[1].id)
    await notes.getByRole('button', { name: '采用服务端笔记', exact: true }).click()
    await expect(notes.getByLabel('笔记正文')).toHaveValue(moved.markdown)
    await expect(notes.locator('.note-editor')).toContainText(fixture.blocks[1].id)
    expect((await page.request.get('/api/v1/notes').then(value => value.json())).items.find((item: Note) => item.id === ref.id).anchor).toEqual({ ...moved.anchor, prefix: '', suffix: '' })
  } finally { await runtime.close() }
})

test('soft deleting a server note preserves its unsynced local continuation for explicit recovery', async ({ playwright }, info) => {
  test.setTimeout(60_000)
  const runtime = await RestartRuntime.start()
  try {
    const context = await runtime.openBrowser(playwright.chromium)
    const page = context.pages()[0]
    const { notes, ref } = await createNote(page, runtime, 'deletiondraft')
    const continuation = '软删除前尚未同步的唯一续写 🧠，必须可恢复。'
    await notes.getByLabel('笔记正文').fill(continuation)
    await expect(notes.getByText('本机草稿已保留；尚未同步为服务端笔记。', { exact: true })).toBeVisible()
    await notes.getByRole('button', { name: '删除此笔记', exact: true }).click()
    const deleting = page.waitForResponse(value => value.request().method() === 'DELETE' && value.url().endsWith(`/api/v1/notes/${ref.id}`))
    await notes.getByRole('button', { name: '确认软删除笔记', exact: true }).click()
    const deleted = await deleting
    expect(deleted.status()).toBe(200)
    await expect(notes.getByText('笔记已从当前视图删除；历史引用保留。', { exact: true })).toBeVisible()
    const current = await page.request.get('/api/v1/notes').then(value => value.json())
    expect(current.items.some((item: Note) => item.id === ref.id)).toBe(false)
    writeFileSync(info.outputPath('deleted-note-current.json'), JSON.stringify({ deleted_status: deleted.status(), no_current_note: true, prior_ref: ref }, null, 2))
    await notes.getByRole('button', { name: `恢复本机笔记草稿 ${ref.id}`, exact: true }).click()
    await expect(notes.getByLabel('笔记正文')).toHaveValue(continuation)
    await expect(notes.getByRole('alert').first()).toBeVisible()
    expect((await page.request.get(`/api/v1/objects/${ref.id}/revisions`).then(value => value.json())).items).toContainEqual(expect.objectContaining({ ref }))
  } finally { await runtime.close() }
})
