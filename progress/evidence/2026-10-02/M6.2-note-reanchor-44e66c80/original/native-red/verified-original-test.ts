import { writeFileSync } from 'node:fs'
import { expect, test, type Locator, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import type { ContentRef, Note, RetrievalQueryView } from '../../packages/contracts/generated/api-types'
import { RestartRuntime } from './restartRuntime'
import { publishEditedBlock } from './contentImpactsData'

async function openRetrieval(page: Page) {
  await page.keyboard.press('Control+Shift+P')
  await page.getByRole('dialog', { name: '命令面板', exact: true }).getByRole('button', { name: '检索材料', exact: false }).click()
  return page.getByRole('dialog', { name: '检索材料', exact: true })
}
async function query(page: Page, dialog: Locator, text: string): Promise<RetrievalQueryView> {
  await dialog.getByLabel('检索词', { exact: true }).fill(text)
  const reading = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/retrieval/query'))
  await dialog.getByRole('button', { name: '查询所选材料', exact: true }).click(); const response = await reading; expect(response.status()).toBe(200); return response.json()
}
async function rebuild(page: Page, dialog: Locator) {
  const writing = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/index/rebuild'))
  await dialog.getByRole('button', { name: '明确按已读描述重建索引', exact: true }).click(); const response = await writing; expect(response.status()).toBe(202)
  const ack = await response.json(); await expect(dialog.getByRole('region', { name: '所选范围索引状态' })).toContainText('索引已就绪', { timeout: 30_000 })
  await expect(dialog.getByRole('region', { name: '实际索引任务' })).toContainText('任务当前读回：已完成'); return { body: response.request().postDataJSON(), ack }
}
async function note(page: Page, id: string): Promise<Note> {
  const response = await page.request.get('/api/v1/notes?limit=100'); expect(response.status()).toBe(200)
  const value = (await response.json()).items.find((item: Note) => item.id === id); expect(value).toBeTruthy(); return value
}

test('actual UI edit publication stales the original Note, explicit new-source reanchor and old-scope rebuild preserve historical bytes and parent pins', async ({ playwright }, info) => {
  test.setTimeout(180_000)
  const runtime = await RestartRuntime.start(), errors: string[] = [], writes: { method: string; path: string; body: unknown }[] = []
  try {
    const context = await runtime.openBrowser(playwright.chromium), page = context.pages()[0]; await runtime.authenticateOnly(page)
    page.on('pageerror', error => errors.push(error.message))
    page.on('request', r => { const path = new URL(r.url()).pathname; if (['POST', 'PATCH'].includes(r.method()) && (/\/notes(?:\/[^/]+)?$/.test(path) || /\/drafts(?:\/[^/]+(?:\/review|\/publish)?)?$/.test(path) || /\/reviews\/[^/]+\/decision$/.test(path) || path.endsWith('/index/rebuild'))) writes.push({ method: r.method(), path, body: r.postDataJSON() }) })
    const notes = page.getByRole('dialog', { name: '笔记', exact: true }), markdown = '旧笔记原文 🧠 e\u0301\n手工重锚只改准确引用，不改本文。'
    let original!: Note, originalRef!: ContentRef, initialQuery!: RetrievalQueryView, initialRebuild!: Awaited<ReturnType<typeof rebuild>>
    const evidenceBefore = await page.request.get('/api/v1/learning/evidence').then(r => r.json())
    const publication = await publishEditedBlock(page, runtime, async fixture => {
      const block = page.locator(`#block-${fixture.blocks[0].id}-r1`)
      await block.getByText('原始 Markdown 与精确选文', { exact: true }).click()
      const source = block.getByRole('textbox', { name: '原始 Markdown：原创合成编辑标题', exact: true }); await source.focus(); await page.keyboard.press('Control+A')
      await page.getByRole('button', { name: '为当前选文记笔记', exact: true }).click(); await notes.getByRole('button', { name: '用当前选文新建笔记', exact: true }).click()
      await notes.getByLabel('笔记正文').fill(markdown)
      const writing = page.waitForResponse(r => r.request().method() === 'POST' && r.url().endsWith('/notes'))
      await notes.getByRole('button', { name: '保存笔记到服务端', exact: true }).click(); const response = await writing; expect(response.status()).toBe(201); originalRef = await response.json()
      await expect(notes.getByText('笔记已保存到服务端', { exact: true })).toBeVisible(); original = await note(page, originalRef.id)
      expect(original.anchor.ref).toEqual(fixture.blocks[0]); expect(original.anchor.exact_quote).toBe(fixture.bodies[fixture.blocks[0].id]); expect(original.anchor_state).toBe('exact')
      await notes.getByRole('button', { name: '关闭笔记', exact: true }).click()
      const retrieval = await openRetrieval(page); await expect(retrieval.getByRole('radio', { name: /只查当前内容块/ })).toBeChecked()
      initialRebuild = await rebuild(page, retrieval); initialQuery = await query(page, retrieval, '冲突')
      expect(initialQuery.scope_refs).toEqual([fixture.blocks[0]]); expect(initialQuery.hits[0].text).toBe(fixture.bodies[fixture.blocks[0].id])
      await retrieval.getByRole('button', { name: '关闭检索材料', exact: true }).click()
    })
    const stale = await note(page, original.id)
    expect(stale.anchor_state).toBe('stale'); expect(stale.anchor).toEqual(original.anchor); expect(stale.markdown).toBe(markdown); expect(stale.revision).toBe(original.revision + 1)
    await page.getByRole('button', { name: '查看笔记', exact: true }).click()
    await notes.getByRole('button', { name: new RegExp('旧笔记原文.*stale') }).click(); await expect(notes.getByText(`锚点：${original.anchor.ref.id} · 修订 1 · stale`, { exact: true })).toBeVisible()
    const notePatchesBefore = writes.filter(w => w.method === 'PATCH' && /\/notes\//.test(w.path)).length
    await notes.getByRole('button', { name: '读取此块当前修订以手工重锚', exact: true }).click()
    const reanchor = notes.getByRole('region', { name: '手工选择新的笔记锚点', exact: true })
    await expect(reanchor).toContainText(publication.published.sha256)
    const newBody = await page.request.get(`/api/v1/blocks/${publication.published.id}/body?revision=2`).then(r => r.text())
    const freshSource = reanchor.getByRole('textbox', { name: '当前准确修订的完整原文', exact: true }); await expect(freshSource).toHaveValue(newBody)
    await freshSource.focus(); await page.keyboard.press('Control+A')
    await expect(reanchor.getByRole('button', { name: '将这份准确新选文采用到本机笔记', exact: true })).toBeEnabled()
    expect(await note(page, original.id)).toEqual(stale); expect(writes.filter(w => w.method === 'PATCH' && /\/notes\//.test(w.path))).toHaveLength(notePatchesBefore)
    await reanchor.getByRole('button', { name: '将这份准确新选文采用到本机笔记', exact: true }).click()
    await expect(notes.getByText(`锚点：${original.anchor.ref.id} · 修订 2 · exact`, { exact: true })).toBeVisible()
    expect(await note(page, original.id)).toEqual(stale)
    const updating = page.waitForResponse(r => r.request().method() === 'PATCH' && r.url().endsWith(`/notes/${original.id}`))
    await notes.getByRole('button', { name: '保存笔记到服务端', exact: true }).click(); const updatedResponse = await updating; expect(updatedResponse.status()).toBe(200)
    await expect(notes.getByText('笔记已保存到服务端', { exact: true })).toBeVisible(); const updated = await note(page, original.id)
    expect(updated.revision).toBe(stale.revision + 1); expect(updated.anchor.ref).toEqual(publication.published); expect(updated.anchor.exact_quote).toBe(newBody)
    expect(updated.anchor.start_codepoint).toBe(0); expect(updated.anchor.end_codepoint).toBe([...newBody].length); expect(updated.anchor.prefix).toBe(''); expect(updated.anchor.suffix).toBe(''); expect(updated.markdown).toBe(markdown); expect(updated.anchor_state).toBe('exact')
    for (const width of [1440, 390]) { await page.setViewportSize({ width, height: 900 }); expect(await notes.evaluate(el => el.scrollWidth <= el.clientWidth + 1)).toBe(true); await page.screenshot({ path: info.outputPath(`note-manual-reanchor-${width}.png`) }) }
    await page.setViewportSize({ width: 1440, height: 900 }); await notes.getByRole('button', { name: '关闭笔记', exact: true }).click()
    const retrieval = await openRetrieval(page); await retrieval.getByRole('button', { name: '刷新范围与任务', exact: true }).click()
    await expect(retrieval.getByRole('region', { name: '所选范围索引状态' })).toContainText('原索引需要重新核验')
    const staleQuery = await query(page, retrieval, '冲突'); expect(staleQuery.index_state).toBe('stale'); expect(staleQuery.hits).toEqual([]); expect(staleQuery.scope_refs).toEqual(initialQuery.scope_refs)
    expect(writes.filter(w => w.path.endsWith('/index/rebuild'))).toHaveLength(1)
    const secondRebuild = await rebuild(page, retrieval), historical = await query(page, retrieval, '冲突')
    expect(historical.scope_refs).toEqual(initialQuery.scope_refs); expect(historical.hits[0].ref).toEqual(original.anchor.ref); expect(historical.hits[0].current_ref).toEqual(publication.published); expect(historical.hits[0].text).toBe(initialQuery.hits[0].text)
    expect((await query(page, retrieval, '复核流程')).result_state).toBe('no_match')
    await expect(retrieval.getByText(/HISTORICAL_REVISION/).first()).toBeVisible(); await page.screenshot({ path: info.outputPath('old-scope-rebuilt-original-body.png') })
    const parentResponse = await page.request.get(`/api/v1/lessons/${publication.fixture.lessons[0].id}?revision=1`); expect(parentResponse.status()).toBe(200); const parent = await parentResponse.json(); expect(parent.block_refs).toEqual(publication.fixture.blocks)
    const evidenceAfter = await page.request.get('/api/v1/learning/evidence').then(r => r.json()); expect(evidenceAfter).toEqual(evidenceBefore)
    expect(await page.request.get(`/api/v1/blocks/${original.anchor.ref.id}/body?revision=1`).then(r => r.text())).toBe(original.anchor.exact_quote)
    expect(errors).toEqual([])
    writeFileSync(info.outputPath('note-reanchor-and-historical-retrieval.json'), JSON.stringify({ scope: 'Actual UI import, original Note and index, Edit/Review/explicit synthetic human decision/publication, immutable stale anchor readback, explicit fresh-source selection and local adoption then CAS Note PATCH, stale old scope and explicit rebuild retaining old ref/body. No SQL publication injection, no Provider. Synthetic pure text has no pre-existing grades/private answers; evidence remains empty, not a claim about a populated grading corpus.', publication, originalRef, original, stale, updated, initialRebuild, initialQuery, staleQuery, secondRebuild, historical, parent, evidenceBefore, evidenceAfter, writes, errors }, null, 2))
  } finally { await runtime.close() }
})
