import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor, render, screen, fireEvent } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { commandStore } from './commands'
import { discard, recoverable } from './memory'
import { discardForms } from './formMemory'
import { listing, targetRef, targetId, eventId, portFor, session } from './fixtures'
import { useContentImpacts } from './useContentImpacts'
import { ContentImpactsPanel } from './ContentImpactsPanel'
const spaces: string[] = []
afterEach(async () => { cleanup(); vi.restoreAllMocks(); for (const workspace of spaces.splice(0)) { discard(workspace); discardForms(workspace) }; await commandStore.close() })
function fixture() { const workspace = `workspace_${crypto.randomUUID()}`; spaces.push(workspace); const port = portFor(workspace); port.list = vi.fn(port.list); port.current = vi.fn(port.current); port.read = vi.fn(port.read); port.decide = vi.fn(port.decide); port.session = vi.fn(port.session); return { workspace, port } }
function deferred<T>() { let resolve!: (v: T) => void; const promise = new Promise<T>(r => { resolve = r }); return { promise, resolve } }
async function prepared() { const f = fixture(), h = renderHook(({ paused }) => useContentImpacts(f.workspace, paused, f.port), { initialProps: { paused: false } }); await waitFor(() => expect(h.result.current.ready).toBe(true)); await act(() => h.result.current.discover()); await act(() => h.result.current.read(eventId)); await act(() => h.result.current.read(eventId, targetId)); act(() => h.result.current.adopt()); return { ...f, h } }

test('independent: unknown session cannot load protected journal, discover, or read', async () => {
  const { workspace, port } = fixture(), d = deferred<ReturnType<typeof session>>(); vi.mocked(port.session).mockReturnValueOnce(d.promise); const load = vi.spyOn(commandStore, 'load')
  const h = renderHook(() => useContentImpacts(workspace, false, port)); await act(() => h.result.current.discover()); await act(() => h.result.current.read(eventId)); expect(load).not.toHaveBeenCalled(); expect(port.list).not.toHaveBeenCalled(); expect(port.read).not.toHaveBeenCalled()
  await act(async () => { d.resolve(session(workspace)) }); await waitFor(() => expect(h.result.current.ready).toBe(true))
})
test.each(['list', 'current'] as const)('independent: delayed %s cannot repopulate paused scope', async operation => {
  const { h, port } = await prepared(), d = deferred<unknown>(); let pending!: Promise<void>
  if (operation === 'list') vi.mocked(port.list).mockReturnValueOnce(d.promise as ReturnType<typeof port.list>); else vi.mocked(port.current).mockReturnValueOnce(d.promise as ReturnType<typeof port.current>)
  act(() => { pending = operation === 'list' ? h.result.current.discover() : h.result.current.read(eventId, targetId) }); await waitFor(() => expect(h.result.current.busy).toBe(true)); h.rerender({ paused: true })
  await act(async () => { d.resolve(operation === 'list' ? { items: [listing], next_cursor: null } : targetRef); await pending })
  expect(h.result.current.ready).toBe(false); expect(h.result.current.listing).toBeNull(); expect(h.result.current.reading).toBeNull(); expect(h.result.current.frozen).toBeNull(); expect(h.result.current.commands).toEqual([])
})
test('independent: invalid limits never send, duplicate continuation does not replace prior page', async () => {
  const { h, port } = await prepared(), count = vi.mocked(port.list).mock.calls.length
  for (const limit of [0, -1, 101, 1.5, Number.NaN]) await act(() => h.result.current.discover(null, limit)); expect(port.list).toHaveBeenCalledTimes(count)
  vi.mocked(port.list).mockResolvedValueOnce({ items: [listing], next_cursor: 'cursor_original' }); await act(() => h.result.current.discover(null, 1)); const first = h.result.current.listing
  vi.mocked(port.list).mockResolvedValueOnce({ items: [listing], next_cursor: null }); await act(() => h.result.current.discover(null, 1, true)); expect(h.result.current.listing).toEqual(first); expect(h.result.current.error).toContain('第一页')
})
test('independent: discovery cannot release undurable ACK memory or its exit protection', async () => {
  const { h, port, workspace } = await prepared(), save = commandStore.save.bind(commandStore)
  vi.spyOn(commandStore, 'save').mockImplementation(async (...args) => { if (JSON.parse(args[2]).ack) throw new Error('independent IDB ACK abort'); return save(...args) })
  await act(() => h.result.current.submit('no_revision_needed', '独立原理由\n保持 Unicode α', [])); const held = recoverable(workspace, session(workspace).csrf_token); expect(held[0].ack).not.toBeNull()
  await act(() => h.result.current.discover(null, 1)); expect(recoverable(workspace, session(workspace).csrf_token)).toEqual(held); expect(port.decide).toHaveBeenCalledTimes(1)
  const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event); expect(event.defaultPrevented).toBe(true)
})
test('independent: unsubmitted human reason survives a Policy pause without explicit discard', async () => {
  const { workspace, port } = fixture(), view = render(<ContentImpactsPanel workspace={workspace} paused={false} port={port} />)
  fireEvent.click(await screen.findByRole('button', { name: '从第一页读取内容变更' })); fireEvent.click(await screen.findByRole('button', { name: `查看影响详情 ${eventId}` })); fireEvent.click(await screen.findByRole('button', { name: `读取对象当前依据 ${targetId}` })); fireEvent.click(await screen.findByRole('button', { name: '采用本次对象依据准备决定' }))
  fireEvent.change(screen.getByLabelText('决定理由'), { target: { value: '尚未提交的原始理由 α\n不应静默丢失' } }); view.rerender(<ContentImpactsPanel workspace={workspace} paused={true} port={port} />); expect(screen.queryByLabelText('决定理由')).toBeNull()
  view.rerender(<ContentImpactsPanel workspace={workspace} paused={false} port={port} />); await screen.findByRole('button', { name: '从第一页读取内容变更' });
  expect(screen.queryByLabelText('决定理由')).toBeNull(); fireEvent.click(screen.getByRole('button', { name: '重新核验权限与当前依据，恢复原会话表单' })); await screen.findByLabelText('决定理由'); expect((screen.getByLabelText('决定理由') as HTMLTextAreaElement).value).toBe('尚未提交的原始理由 α\n不应静默丢失'); expect(port.decide).not.toHaveBeenCalled()
})

const words = { decision: 'new_revision_required' as const, reason: '原人工判断 α\n保留正文与理由', ids: 'artifact_original', confirmed: true }
test('form recovery requires fresh original-session permission on every role cycle and never writes', async () => {
  const { h, port } = await prepared(); act(() => h.result.current.changeForm(words)); const frozen = h.result.current.frozen
  for (let i = 0; i < 3; i++) {
    h.rerender({ paused: true }); expect(h.result.current.form).toBeNull(); expect(h.result.current.pendingForm).toBe(true)
    h.rerender({ paused: false }); await waitFor(() => expect(h.result.current.ready).toBe(true)); expect(h.result.current.form).toBeNull()
    const count = vi.mocked(port.session).mock.calls.length; await act(() => h.result.current.restoreForm()); expect(port.session).toHaveBeenCalledTimes(count + 1)
    expect(h.result.current.form).toEqual({ ...words, confirmed: false }); expect(h.result.current.frozen).toEqual(frozen)
  }
  expect(port.decide).not.toHaveBeenCalled()
})
test('a different same-workspace session cannot extract protected form but can see its safe existence', async () => {
  const { h, port, workspace } = await prepared(); act(() => h.result.current.changeForm(words))
  vi.mocked(port.session).mockResolvedValue({ ...session(workspace), csrf_token: 'another-session-memory-only', actor_session_id: 'session_other' }); await act(() => h.result.current.refresh())
  expect(h.result.current.ready).toBe(true); expect(h.result.current.pendingForm).toBe(true); expect(h.result.current.canRestoreForm).toBe(false); expect(h.result.current.form).toBeNull()
  await act(() => h.result.current.restoreForm()); expect(h.result.current.form).toBeNull(); expect(h.result.current.frozen).toBeNull(); expect(port.decide).not.toHaveBeenCalled()
})
test.each(['session', 'current'] as const)('late fresh %s cannot reveal a paused form', async phase => {
  const { h, port, workspace } = await prepared(); act(() => h.result.current.changeForm(words)); await act(() => h.result.current.refresh())
  const d = deferred<unknown>()
  if (phase === 'session') vi.mocked(port.session).mockReturnValueOnce(d.promise as ReturnType<typeof port.session>); else vi.mocked(port.current).mockReturnValueOnce(d.promise as ReturnType<typeof port.current>)
  let restoring!: Promise<void>; act(() => { restoring = h.result.current.restoreForm() }); await waitFor(() => expect(h.result.current.busy).toBe(true)); h.rerender({ paused: true })
  await act(async () => { d.resolve(phase === 'session' ? session(workspace) : targetRef); await restoring })
  expect(h.result.current.pendingForm).toBe(true); expect(h.result.current.form).toBeNull(); expect(h.result.current.frozen).toBeNull(); expect(port.decide).not.toHaveBeenCalled()
})
test('fresh changed target preserves original basis and words; only explicit discard permits a new adoption', async () => {
  const { h, port } = await prepared(); act(() => h.result.current.changeForm(words)); const frozen = h.result.current.frozen
  await act(() => h.result.current.refresh()); vi.mocked(port.current).mockResolvedValueOnce({ ...targetRef, revision: 2, sha256: '9'.repeat(64) }); await act(() => h.result.current.restoreForm())
  expect(h.result.current.frozen).toEqual(frozen); expect(h.result.current.form).toEqual({ ...words, confirmed: false }); expect(h.result.current.reading?.current_ref?.revision).toBe(2); expect(h.result.current.canSubmitForm).toBe(false)
  act(() => h.result.current.adopt()); expect(h.result.current.frozen).toEqual(frozen)
  act(() => h.result.current.clearBasis()); expect(h.result.current.pendingForm).toBe(false); act(() => h.result.current.adopt()); expect(h.result.current.frozen?.current_ref.revision).toBe(2); expect(h.result.current.form?.reason).toBe(''); expect(port.decide).not.toHaveBeenCalled()
})
test('protected forms survive component removal, isolate workspaces, and explicit discard leaves original commands intact', async () => {
  const first = await prepared(); act(() => first.h.result.current.changeForm(words)); first.h.unmount()
  const second = await prepared(); expect(second.h.result.current.form?.reason).toBe(''); act(() => second.h.result.current.changeForm({ ...words, reason: 'Another workspace' }))
  const again = renderHook(() => useContentImpacts(first.workspace, false, first.port)); await waitFor(() => expect(again.result.current.ready).toBe(true)); await act(() => again.result.current.restoreForm()); expect(again.result.current.form?.reason).toBe(words.reason)
  const before = await commandStore.load(first.workspace); act(() => again.result.current.clearBasis()); expect(await commandStore.load(first.workspace)).toEqual(before); expect(second.h.result.current.form?.reason).toBe('Another workspace')
})
test('explicit durable submission consumes temporary form only after the exact original has been saved', async () => {
  const { h, workspace } = await prepared(); act(() => h.result.current.changeForm({ ...words, ids: '' })); await act(() => h.result.current.submit(words.decision, words.reason, []))
  expect(h.result.current.pendingForm).toBe(false); const rows = Object.values(await commandStore.load(workspace)); expect(rows).toHaveLength(1); expect(JSON.parse(rows[0].text).body.reason).toBe(words.reason); expect(rows[0].text).not.toContain(session(workspace).csrf_token)
})
