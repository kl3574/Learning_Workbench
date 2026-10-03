import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { ApiError, getSessionGeneration, request } from '../../api/client'
import { reviewSession } from '../draftReview/reviewFixtures'
import { editBase, editFixture } from './editFixtures'
import { decodeBuffer, editBuffers, editCommands, readCommand, persistCommand, type EditCommand } from './editJournal'
import type { EditPort } from './editClient'
import { useDraftEditor } from './useDraftEditor'
afterEach(async () => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); await Promise.all([editBuffers.close(), editCommands.close()]) })
function fixture() {
  const workspace = `workspace_${crypto.randomUUID()}`
  const port: EditPort = { verifyBase: vi.fn(async () => {}), session: vi.fn(async () => reviewSession(workspace)), read: vi.fn(async () => editFixture()),
    create: vi.fn(async () => ({ draft_id: 'draft_edit_synthetic', revision: 1, base_ref: editBase, state: 'draft' as const })),
    patch: vi.fn(async () => ({ draft_id: 'draft_edit_synthetic', revision: 2, validation_warnings: [] })) }
  return { workspace, port }
}
test('patch is sent only after exact original command and local baseline are durable', async () => {
  const { workspace, port } = fixture()
  vi.mocked(port.patch).mockImplementation(async (id, body, key) => {
    const saved = readCommand((await editCommands.load(workspace))[key], workspace)
    expect(saved.operation.kind).toBe('patch')
    if (saved.operation.kind !== 'patch') throw new Error('Expected patch')
    expect(saved.operation.body).toEqual(body); expect(saved.operation.baseline).toEqual(editFixture()); expect(saved.ack).toBeNull()
    return { draft_id: id, revision: 2, validation_warnings: [] }
  })
  const h = renderHook(() => useDraftEditor(workspace, editBase, false, port))
  await waitFor(() => expect(h.result.current.ready).toBe(true))
  await act(() => h.result.current.read('draft_edit_synthetic'))
  act(() => h.result.current.update({ title: '本机标题', body_markdown: '本机正文\n' }))
  await waitFor(() => expect(h.result.current.saving).toBe(false))
  await act(() => h.result.current.submit())
  expect(port.patch).toHaveBeenCalledTimes(1); expect(h.result.current.commands[0].ack?.revision).toBe(2)
  expect(h.result.current.buffer?.baseline.candidate.draft_revision).toBe(1)
})
test('412 preserves baseline and local command, reads exact historical and current snapshots, then requires explicit resolution and new submit', async () => {
  const { workspace, port } = fixture(), old = editFixture(), server = editFixture(2, '另一个标签标题', '服务端当前正文\n')
  vi.mocked(port.patch).mockRejectedValueOnce(new ApiError(412, 'Changed', 'REVISION_CONFLICT'))
  const h = renderHook(() => useDraftEditor(workspace, editBase, false, port))
  await waitFor(() => expect(h.result.current.ready).toBe(true))
  await act(() => h.result.current.read(old.candidate.draft_id))
  const local = { title: '本机未同步标题', body_markdown: '本机未同步正文\n' }
  act(() => h.result.current.update(local)); await waitFor(() => expect(h.result.current.saving).toBe(false))
  vi.mocked(port.read).mockImplementation(async (_id, revision) => revision === 1 ? old : server)
  await act(() => h.result.current.submit())
  expect(h.result.current.commands[0].rejection).toBe(412)
  expect(h.result.current.conflict).toMatchObject({ base: old, local, server })
  expect(vi.mocked(port.read).mock.calls.slice(1)).toEqual([[old.candidate.draft_id, 1], [old.candidate.draft_id]])
  expect(h.result.current.buffer?.baseline).toEqual(old)
  const original = structuredClone(h.result.current.commands[0])
  await act(() => h.result.current.resolve(local))
  expect(port.patch).toHaveBeenCalledTimes(1)
  expect(h.result.current.buffer?.baseline).toEqual(server)
  vi.mocked(port.patch).mockResolvedValueOnce({ draft_id: old.candidate.draft_id, revision: 3, validation_warnings: [] })
  await act(() => h.result.current.submit())
  const calls = vi.mocked(port.patch).mock.calls
  expect(calls).toHaveLength(2); expect(calls[1][1].expected_revision).toBe(2); expect(calls[1][2]).not.toBe(calls[0][2])
  expect(readCommand((await editCommands.load(workspace))[original.key], workspace)).toEqual(original)
})

function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(yes => { resolve = yes }); return { promise, resolve } }
test('refresh retains local blank input and original baseline; resume clones a verified history without changing the saved copy', async () => {
  const { workspace, port } = fixture()
  const first = renderHook(() => useDraftEditor(workspace, editBase, false, port))
  await waitFor(() => expect(first.result.current.ready).toBe(true))
  await act(() => first.result.current.read('draft_edit_synthetic'))
  act(() => first.result.current.update({ title: '', body_markdown: '尚未完成的本机正文' }))
  await waitFor(() => expect(first.result.current.saving).toBe(false))
  const saved = structuredClone(first.result.current.buffer!)
  expect(decodeBuffer((await editBuffers.load(workspace))[saved.id].text, workspace)).toEqual(saved)
  first.unmount()
  const second = renderHook(() => useDraftEditor(workspace, editBase, false, port))
  await waitFor(() => expect(second.result.current.buffers).toHaveLength(1))
  await act(() => second.result.current.restore(saved))
  expect(second.result.current.buffer?.local).toEqual(saved.local)
  expect(second.result.current.buffer?.id).not.toBe(saved.id)
  expect(second.result.current.buffer?.baseline).toEqual(editFixture())
  expect(vi.mocked(port.read).mock.calls.at(-1)).toEqual(['draft_edit_synthetic', 1])
  await act(() => second.result.current.submit()); expect(port.patch).not.toHaveBeenCalled()
  expect(decodeBuffer((await editBuffers.load(workspace))[saved.id].text, workspace)).toEqual(saved)
})
test('two mounted tabs keep separate local work and observe actual competing server revision without automatic rebase', async () => {
  const { workspace, port } = fixture(); let head = editFixture()
  vi.mocked(port.read).mockImplementation(async (_id, revision) => revision === 1 ? editFixture() : head)
  vi.mocked(port.patch).mockImplementation(async (_id, body) => {
    if (body.expected_revision !== head.candidate.draft_revision) throw new ApiError(412, 'Changed')
    head = editFixture(head.candidate.draft_revision + 1, String(body.patches[0].value), String(body.patches[1].value))
    return { draft_id: head.candidate.draft_id, revision: head.candidate.draft_revision, validation_warnings: [] }
  })
  const a = renderHook(() => useDraftEditor(workspace, editBase, false, port)), b = renderHook(() => useDraftEditor(workspace, editBase, false, port))
  await waitFor(() => { expect(a.result.current.ready).toBe(true); expect(b.result.current.ready).toBe(true) })
  await act(async () => { await a.result.current.read('draft_edit_synthetic'); await b.result.current.read('draft_edit_synthetic') })
  act(() => { a.result.current.update({ title: '标签甲', body_markdown: '甲' }); b.result.current.update({ title: '标签乙', body_markdown: '乙' }) })
  await waitFor(() => { expect(a.result.current.saving).toBe(false); expect(b.result.current.saving).toBe(false) })
  expect(a.result.current.buffer?.id).not.toBe(b.result.current.buffer?.id)
  await act(() => a.result.current.submit()); await act(() => b.result.current.submit())
  expect(head.payload.title).toBe('标签甲'); expect(b.result.current.conflict?.local.title).toBe('标签乙')
  expect(Object.values(await editBuffers.load(workspace)).map(r => decodeBuffer(r.text, workspace).local.title).sort()).toEqual(['标签乙', '标签甲'].sort())
})
test('lost ACK keeps original key and body; same page explicit replay works while previous-page unknown commands remain read-only', async () => {
  const { workspace, port } = fixture()
  vi.mocked(port.patch).mockRejectedValueOnce(new Error('Synthetic response lost'))
  const h = renderHook(() => useDraftEditor(workspace, editBase, false, port))
  await waitFor(() => expect(h.result.current.ready).toBe(true)); await act(() => h.result.current.read('draft_edit_synthetic'))
  act(() => h.result.current.update({ title: '待同步', body_markdown: '正文' })); await waitFor(() => expect(h.result.current.saving).toBe(false))
  await act(() => h.result.current.submit()); const original = h.result.current.commands[0]
  await act(() => h.result.current.submit()); expect(port.patch).toHaveBeenCalledTimes(1)
  await act(() => h.result.current.execute(original)); expect(vi.mocked(port.patch).mock.calls[1]).toEqual(vi.mocked(port.patch).mock.calls[0])
  const older: EditCommand = { version: 1, workspace, key: 'editcmd_previous', page: 'page_previous', access: original.access, base_ref: original.base_ref, operation: original.operation, ack: null, rejection: null }
  await persistCommand(older)
  await act(() => h.result.current.refresh()); await act(() => h.result.current.execute(older))
  expect(port.patch).toHaveBeenCalledTimes(2); expect(h.result.current.canReplay(older)).toBe(false)
  expect(h.result.current.error).toContain('只读保留')
})
test('failed durable storage prevents an HTTP write and keeps current local text', async () => {
  const { workspace, port } = fixture(), h = renderHook(() => useDraftEditor(workspace, editBase, false, port))
  await waitFor(() => expect(h.result.current.ready).toBe(true)); await act(() => h.result.current.read('draft_edit_synthetic'))
  act(() => h.result.current.update({ title: '未确认保存', body_markdown: '保留文字' })); await waitFor(() => expect(h.result.current.saving).toBe(false))
  vi.spyOn(editCommands, 'save').mockRejectedValueOnce(new Error('Synthetic IDB failure'))
  await act(() => h.result.current.submit())
  expect(port.patch).not.toHaveBeenCalled(); expect(h.result.current.buffer?.local.body_markdown).toBe('保留文字')
  expect(await editCommands.load(workspace)).toEqual({})
})
test.each(['body', 'candidate', 'history', 'owner', 'base'] as const)('bad %s in snapshot is rejected before it becomes an editable baseline', async kind => {
  const { workspace, port } = fixture(), bad = editFixture()
  if (kind === 'body') bad.payload.body_markdown += 'tampered'
  if (kind === 'candidate') bad.candidate.candidate_sha256 = '0'.repeat(64)
  if (kind === 'history') bad.candidate.draft_revision = 2
  if (kind === 'owner') Object.assign(bad, { owner: 'import' })
  if (kind === 'base') bad.base_ref = { ...editBase, revision: 2 }
  vi.mocked(port.read).mockResolvedValueOnce(bad)
  const h = renderHook(() => useDraftEditor(workspace, editBase, false, port))
  await waitFor(() => expect(h.result.current.ready).toBe(true)); await act(() => h.result.current.read('draft_edit_synthetic', 1))
  expect(h.result.current.buffer).toBeNull(); expect(h.result.current.error).toContain('无法核验'); expect(await editBuffers.load(workspace)).toEqual({})
})
test('current Policy hides protected buffers and late ACK after access generation changes cannot rewrite the original', async () => {
  const { workspace, port } = fixture(), pending = deferred<Awaited<ReturnType<EditPort['patch']>>>()
  vi.mocked(port.patch).mockReturnValueOnce(pending.promise)
  const h = renderHook(() => useDraftEditor(workspace, editBase, false, port))
  await waitFor(() => expect(h.result.current.ready).toBe(true)); await act(() => h.result.current.read('draft_edit_synthetic'))
  act(() => h.result.current.update({ title: '待保存', body_markdown: '正文' })); await waitFor(() => expect(h.result.current.saving).toBe(false))
  let sending!: Promise<void>; act(() => { sending = h.result.current.submit() })
  await waitFor(() => expect(port.patch).toHaveBeenCalledTimes(1)); const original = h.result.current.commands[0], generation = getSessionGeneration()
  vi.mocked(port.session).mockResolvedValue({ ...reviewSession(workspace), active_independent_attempt_id: 'attempt_synthetic' })
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(reviewSession(workspace)))))
  await act(() => request('POST /api/v1/session/role', { role: 'learner' }, { 'Idempotency-Key': 'synthetic_role' }))
  expect(getSessionGeneration()).toBeGreaterThan(generation)
  await act(async () => { pending.resolve({ draft_id: 'draft_edit_synthetic', revision: 2, validation_warnings: [] }); await sending })
  expect(h.result.current.ready).toBe(false); expect(h.result.current.buffer).toBeNull(); expect(h.result.current.commands).toEqual([])
  expect(readCommand((await editCommands.load(workspace))[original.key], workspace)).toEqual(original)
  vi.mocked(port.session).mockResolvedValue(reviewSession(workspace))
  await act(() => request('POST /api/v1/session/role', { role: 'author' }, { 'Idempotency-Key': 'synthetic_author' }))
  await waitFor(() => expect(h.result.current.ready).toBe(true))
  expect(h.result.current.canReplay(original)).toBe(true)
  expect(port.patch).toHaveBeenCalledTimes(1) // Restoration never posts automatically.
  await act(() => h.result.current.execute(original))
  expect(port.patch).toHaveBeenCalledTimes(2)
  expect(vi.mocked(port.patch).mock.calls[1]).toEqual(vi.mocked(port.patch).mock.calls[0])
  expect(vi.mocked(port.read).mock.calls.at(-1)).toEqual(['draft_edit_synthetic', 1])
  expect(readCommand((await editCommands.load(workspace))[original.key], workspace)).toEqual({ ...original, ack: { draft_id: 'draft_edit_synthetic', revision: 2, validation_warnings: [] } })
})
test('published exact drafts are read-only and a denied 412 history read leaves the original command intact', async () => {
  const { workspace, port } = fixture(), h = renderHook(() => useDraftEditor(workspace, editBase, false, port))
  vi.mocked(port.read).mockResolvedValueOnce({ ...editFixture(), state: 'published' })
  await waitFor(() => expect(h.result.current.ready).toBe(true)); await act(() => h.result.current.read('draft_edit_synthetic'))
  act(() => h.result.current.update({ title: '不能写入', body_markdown: 'x' })); await act(() => h.result.current.submit())
  expect(port.patch).not.toHaveBeenCalled(); expect(h.result.current.buffer?.local.title).toBe(editFixture().payload.title)
  await act(() => h.result.current.read('draft_edit_synthetic'))
  act(() => h.result.current.update({ title: '冲突候选', body_markdown: '待保留' })); await waitFor(() => expect(h.result.current.saving).toBe(false))
  vi.mocked(port.patch).mockRejectedValueOnce(new ApiError(412, 'Changed')); vi.mocked(port.read).mockRejectedValue(new ApiError(403, 'Denied', 'POLICY_DENIED'))
  await act(() => h.result.current.submit()); expect(h.result.current.conflict).toBeNull(); expect(h.result.current.ready).toBe(false)
  const commands = Object.values(await editCommands.load(workspace)).map(r => readCommand(r, workspace)); expect(commands[0].rejection).toBe(412)
})

test('uncommitted local text survives permission refresh and baseline replacement requests after IndexedDB failure', async () => {
  const { workspace, port } = fixture(), h = renderHook(() => useDraftEditor(workspace, editBase, false, port))
  await waitFor(() => expect(h.result.current.ready).toBe(true)); await act(() => h.result.current.read('draft_edit_synthetic'))
  const saved = structuredClone(h.result.current.buffer!)
  vi.spyOn(editBuffers, 'save').mockRejectedValueOnce(new Error('Synthetic quota failure'))
  act(() => h.result.current.update({ title: '仅内存中的新标题', body_markdown: '不得丢弃的尚未落盘正文' }))
  await waitFor(() => { expect(h.result.current.saving).toBe(false); expect(h.result.current.safe).toBe(false) })
  await act(() => h.result.current.refresh())
  await act(() => h.result.current.read('draft_edit_synthetic'))
  await act(() => h.result.current.restore(saved))
  expect(h.result.current.buffer?.local).toEqual({ title: '仅内存中的新标题', body_markdown: '不得丢弃的尚未落盘正文' })
  expect(port.read).toHaveBeenCalledTimes(1); expect(port.session).toHaveBeenCalledTimes(1)
  await act(async () => { await h.result.current.retrySave() })
  expect(h.result.current.safe).toBe(true)
  const retained = decodeBuffer((await editBuffers.load(workspace))[saved.id].text, workspace)
  expect(retained.local.body_markdown).toBe('不得丢弃的尚未落盘正文')
})

test('access changes hide but retain an unsaved in-memory copy until protected exact-read recovery succeeds', async () => {
  const { workspace, port } = fixture(), h = renderHook(() => useDraftEditor(workspace, editBase, false, port))
  await waitFor(() => expect(h.result.current.ready).toBe(true)); await act(() => h.result.current.read('draft_edit_synthetic'))
  vi.spyOn(editBuffers, 'save').mockRejectedValueOnce(new Error('Synthetic quota failure'))
  act(() => h.result.current.update({ title: '仅内存标题', body_markdown: '失权后必须隐藏但不能丢失的正文' }))
  await waitFor(() => expect(h.result.current.safe).toBe(false))
  vi.mocked(port.session).mockResolvedValue({ ...reviewSession(workspace), role: 'learner' })
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(reviewSession(workspace)))))
  await act(() => request('POST /api/v1/session/role', { role: 'learner' }, { 'Idempotency-Key': 'synthetic_unsaved_role' }))
  await waitFor(() => expect(h.result.current.ready).toBe(false))
  expect(h.result.current.buffer).toBeNull(); expect(h.result.current.buffers).toEqual([])
  expect(h.result.current.safe).toBe(false)
  vi.mocked(port.session).mockResolvedValue(reviewSession(workspace))
  await act(() => request('POST /api/v1/session/role', { role: 'author' }, { 'Idempotency-Key': 'synthetic_unsaved_author' }))
  await waitFor(() => expect(h.result.current.ready).toBe(true))
  await act(() => h.result.current.recoverMemory())
  expect(h.result.current.buffer?.local.body_markdown).toBe('失权后必须隐藏但不能丢失的正文')
  expect(vi.mocked(port.read).mock.calls.at(-1)).toEqual(['draft_edit_synthetic', 1])
  expect(h.result.current.safe).toBe(true)
  expect(Object.values(await editBuffers.load(workspace)).map(r => decodeBuffer(r.text, workspace).local.body_markdown)).toContain('失权后必须隐藏但不能丢失的正文')
  expect(port.patch).not.toHaveBeenCalled()
})

test('pending local save survives component removal but a different session cannot recover its memory', async () => {
  const { workspace, port } = fixture(), pending = deferred<void>(), first = renderHook(() => useDraftEditor(workspace, editBase, false, port))
  await waitFor(() => expect(first.result.current.ready).toBe(true)); await act(() => first.result.current.read('draft_edit_synthetic'))
  const originalSave = editBuffers.save.bind(editBuffers)
  vi.spyOn(editBuffers, 'save').mockImplementationOnce(async (...args) => { await pending.promise; return originalSave(...args) })
  act(() => first.result.current.update({ title: '卸载前未落盘标题', body_markdown: '不得交给另一个会话的本机文字' }))
  expect(first.result.current.saving).toBe(true)
  first.unmount()
  await act(async () => { pending.resolve(); await pending.promise })
  vi.mocked(port.session).mockResolvedValue({ ...reviewSession(workspace), actor_session_id: 'session_distinct', csrf_token: 'synthetic_distinct_session_csrf' })
  const second = renderHook(() => useDraftEditor(workspace, editBase, false, port))
  await waitFor(() => expect(second.result.current.ready).toBe(true))
  expect(second.result.current.pendingMemory).toBe(true); expect(second.result.current.canRecoverMemory).toBe(false)
  expect(second.result.current.buffer).toBeNull(); expect(second.result.current.safe).toBe(false)
  await act(() => second.result.current.recoverMemory()); expect(port.read).toHaveBeenCalledTimes(1)
  vi.mocked(port.session).mockResolvedValue(reviewSession(workspace))
  await act(() => second.result.current.refresh())
  expect(second.result.current.canRecoverMemory).toBe(true)
  vi.mocked(port.read).mockRejectedValueOnce(new ApiError(403, 'Denied', 'POLICY_DENIED'))
  await act(() => second.result.current.recoverMemory())
  expect(second.result.current.buffer).toBeNull(); expect(second.result.current.pendingMemory).toBe(true)
  await act(() => second.result.current.refresh()); await act(() => second.result.current.recoverMemory())
  expect(second.result.current.buffer?.local.body_markdown).toBe('不得交给另一个会话的本机文字')
  expect(second.result.current.pendingMemory).toBe(false); expect(second.result.current.safe).toBe(true)
  expect(port.patch).not.toHaveBeenCalled()
})


test('review entry requires separately read exact saved head and never admits a local buffer or stale ACK', async () => {
  const { workspace, port } = fixture(), h = renderHook(() => useDraftEditor(workspace, editBase, false, port))
  await waitFor(() => expect(h.result.current.ready).toBe(true)); await act(() => h.result.current.read('draft_edit_synthetic'))
  act(() => h.result.current.update({ title: '仅本机文字', body_markdown: '未同步' }))
  await waitFor(() => expect(h.result.current.saving).toBe(false))
  await act(() => h.result.current.selectReview()); expect(h.result.current.reviewSnapshot).toBeNull(); expect(port.read).toHaveBeenCalledTimes(1)
  await act(() => h.result.current.read('draft_edit_synthetic'))
  await act(() => h.result.current.selectReview()); expect(h.result.current.reviewSnapshot).toEqual(editFixture())
  expect(vi.mocked(port.read).mock.calls.slice(-2)).toEqual([['draft_edit_synthetic', 1], ['draft_edit_synthetic']])
  act(() => h.result.current.update({ title: '新的本机文字', body_markdown: '候选须失效' }))
  expect(h.result.current.reviewSnapshot).toBeNull()
  await waitFor(() => expect(h.result.current.saving).toBe(false)); await act(() => h.result.current.read('draft_edit_synthetic'))
  vi.mocked(port.read).mockResolvedValueOnce(editFixture()).mockResolvedValueOnce(editFixture(2))
  await act(() => h.result.current.selectReview()); expect(h.result.current.reviewSnapshot).toBeNull(); expect(port.patch).not.toHaveBeenCalled()
})

test.each(['create', 'patch'] as const)('same-actor previous-page %s command waits for current permission and exact material then explicitly replays original', async kind => {
  const { workspace, port } = fixture(), baseline = editFixture()
  const operation: EditCommand['operation'] = kind === 'create'
    ? { kind, body: { kind: 'block', base_ref: editBase, title: '原创建标题' } }
    : { kind, baseline, local: { title: '原标题', body_markdown: '原正文' }, body: { expected_revision: 1, patches: [{ field: 'title', value: '原标题' }, { field: 'body_markdown', value: '原正文' }] } }
  const original: EditCommand = { version: 2, workspace_id: workspace, actor_session_id: reviewSession(workspace).actor_session_id,
    key: `editcmd_${kind}_previous`, route: kind === 'create' ? 'POST /api/v1/drafts' : 'PATCH /api/v1/drafts/draft_edit_synthetic',
    page: 'page_previous', access: 0, base_ref: editBase, operation, ack: null, rejection: null }
  await persistCommand(original)
  const h = renderHook(() => useDraftEditor(workspace, editBase, false, port))
  await waitFor(() => expect(h.result.current.ready).toBe(true))
  expect(h.result.current.canReplay(original)).toBe(true)
  expect(port.create).not.toHaveBeenCalled(); expect(port.patch).not.toHaveBeenCalled()
  const gate = deferred<ReturnType<typeof reviewSession>>()
  vi.mocked(port.session).mockReturnValueOnce(gate.promise)
  let sending!: Promise<void>; act(() => { sending = h.result.current.execute(original) })
  expect(port.create).not.toHaveBeenCalled(); expect(port.patch).not.toHaveBeenCalled()
  await act(async () => { gate.resolve(reviewSession(workspace)); await sending })
  if (kind === 'create') { expect(port.verifyBase).toHaveBeenCalledWith(editBase); expect(port.create).toHaveBeenCalledExactlyOnceWith(operation.body, original.key) }
  else { expect(port.read).toHaveBeenCalledExactlyOnceWith(baseline.candidate.draft_id, 1); expect(port.patch).toHaveBeenCalledExactlyOnceWith(baseline.candidate.draft_id, operation.body, original.key) }
  const saved = readCommand((await editCommands.load(workspace))[original.key], workspace)
  expect({ ...saved, ack: null }).toEqual(original)
  expect(JSON.stringify(saved)).not.toContain(reviewSession(workspace).csrf_token)
})

test.each(['different_actor', 'learner', 'independent', 'open_book', 'unknown', 'material_conflict'] as const)('replay admission rejects %s without rewriting original or dispatching mutation', async condition => {
  const { workspace, port } = fixture(), baseline = editFixture()
  const original: EditCommand = { version: 2, workspace_id: workspace, actor_session_id: reviewSession(workspace).actor_session_id,
    key: 'editcmd_admission', route: 'PATCH /api/v1/drafts/draft_edit_synthetic', page: 'page_previous', access: 0,
    base_ref: editBase, operation: { kind: 'patch', baseline, local: { title: '原标题', body_markdown: '原正文' },
      body: { expected_revision: 1, patches: [{ field: 'title', value: '原标题' }, { field: 'body_markdown', value: '原正文' }] } }, ack: null, rejection: null }
  await persistCommand(original)
  const h = renderHook(() => useDraftEditor(workspace, editBase, false, port))
  await waitFor(() => expect(h.result.current.ready).toBe(true))
  const session = reviewSession(workspace)
  if (condition === 'different_actor') session.actor_session_id = 'session_another_actor'
  if (condition === 'learner') session.role = 'learner'
  if (condition === 'independent') session.active_independent_attempt_id = 'attempt_active'
  if (condition === 'open_book') session.active_open_book_attempt_id = 'attempt_open'
  if (condition === 'unknown') vi.mocked(port.session).mockRejectedValueOnce(new Error('Session unavailable'))
  else vi.mocked(port.session).mockResolvedValue(session)
  if (condition === 'material_conflict') vi.mocked(port.read).mockRejectedValueOnce(new ApiError(409, 'Stored baseline invalid', 'INTEGRITY_CONFLICT'))
  await act(() => h.result.current.execute(original))
  expect(port.patch).not.toHaveBeenCalled(); expect(port.create).not.toHaveBeenCalled()
  expect(readCommand((await editCommands.load(workspace))[original.key], workspace)).toEqual(original)
  if (condition !== 'material_conflict') { expect(h.result.current.ready).toBe(false); expect(h.result.current.commands).toEqual([]) }
  if (condition === 'different_actor') {
    await act(() => h.result.current.refresh())
    expect(h.result.current.ready).toBe(true); expect(h.result.current.canReplay(original)).toBe(false)
    await act(() => h.result.current.execute(original)); expect(port.patch).not.toHaveBeenCalled()
  }
})
