import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor, render, screen, fireEvent } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { ApiError, getSessionGeneration, request } from '../../api/client'
import { commandStore, makeCommand, persist, readCommand, decode } from './commands'
import { artifacts, basis, readView, receipt, page } from './schema'
import { discard, recoverable } from './memory'
import { ack, original, listing, targetRef, targetId, eventId, portFor, session, body } from './fixtures'
import { useContentImpacts } from './useContentImpacts'
import { ContentImpactsPanel } from './ContentImpactsPanel'
const spaces: string[] = []
afterEach(async () => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); for (const workspace of spaces.splice(0)) discard(workspace); await commandStore.close() })
function fixture() { const workspace = `workspace_${crypto.randomUUID()}`; spaces.push(workspace); const port = portFor(workspace); port.list = vi.fn(port.list); port.current = vi.fn(port.current); port.read = vi.fn(port.read); port.decide = vi.fn(port.decide); port.session = vi.fn(port.session); return { workspace, port } }
async function prepared() { const f = fixture(), h = renderHook(() => useContentImpacts(f.workspace, false, f.port)); await waitFor(() => expect(h.result.current.ready).toBe(true)); await act(() => h.result.current.discover()); await act(() => h.result.current.read(eventId)); await act(() => h.result.current.read(eventId, targetId)); act(() => h.result.current.adopt()); return { ...f, h } }
function deferred<T>() { let resolve!: (v: T) => void; const promise = new Promise<T>(r => { resolve = r }); return { promise, resolve } }

test('strict event facts, target current ref, CAS and original receipt binding reject substitution', () => {
  const frozen = basis({ target_id: targetId, view: { ...original, target_decision_head: 0 }, current_ref: targetRef }), command = makeCommand('workspace_synthetic', 0, frozen, body())
  for (const bad of [{ ...original, extra: true }, { ...original, old_ref: original.new_ref }, { ...original, affected_ids: [targetId] }, { ...original, pending_target_ids: ['note_unknown'] }]) expect(() => readView(bad, eventId)).toThrow()
  expect(() => basis({ ...frozen, target_id: 'note_synthetic' })).toThrow()
  for (const bad of [{ ...command, extra: true }, { ...command, body: { ...body(), expected_decision_revision: true } }, { ...command, body: { ...body(), expected_event_snapshot_sha256: '0'.repeat(64) } }, { ...command, body: { ...body(), reason: ' ' } }, { ...command, body: { ...body(), evidence_artifact_ids: ['artifact_a', 'artifact_a'] } }]) expect(() => decode(JSON.stringify(bad), command.workspace_id)).toThrow()
  for (const bad of [{ ...ack(body()), decision_revision: 3 }, { ...ack(body()), target_metadata_sha256: '0'.repeat(64) }, { ...ack(body()), receipt_sha256: '0'.repeat(64) }, { ...ack(body()), decision: 'new_revision_required' }, { ...ack(body()), evidence_artifacts: [{ id: 'artifact_other', sha256: 'a'.repeat(64) }] }]) expect(() => receipt(bad, frozen, body())).toThrow()
  expect(() => artifacts('artifact_a\nartifact_a')).toThrow(); expect(() => artifacts('https://example.com')).toThrow(); expect(() => artifacts(Array.from({ length: 33 }, (_, i) => `artifact_${i}`).join('\n'))).toThrow(); expect(artifacts('')).toEqual([])
})

test('read-only selection never adopts new basis; 412 preserves original and explicit correction uses a new key', async () => {
  const { h, port } = await prepared(), frozen = h.result.current.frozen
  vi.mocked(port.read).mockResolvedValueOnce({ ...original, target_decision_head: 1 })
  await act(() => h.result.current.read(eventId, targetId)); expect(h.result.current.frozen).toEqual(frozen)
  vi.mocked(port.decide).mockRejectedValueOnce(new ApiError(412, 'stale', 'REVISION_MISMATCH'))
  await act(() => h.result.current.submit('no_revision_needed', 'Original explicit judgment', []))
  const old = h.result.current.commands[0]; expect(old.body.expected_decision_revision).toBe(0); expect(old.rejection?.status).toBe(412)
  expect(h.result.current.frozen).toBeNull(); await act(() => h.result.current.submit('no_revision_needed', 'No implicit basis', [])); expect(port.decide).toHaveBeenCalledTimes(1)
  act(() => h.result.current.adopt()); expect(h.result.current.frozen).toBeNull()
  vi.mocked(port.read).mockResolvedValueOnce({ ...original, target_decision_head: 1 }); await act(() => h.result.current.read(eventId, targetId))
  act(() => h.result.current.adopt()); await act(() => h.result.current.submit('new_revision_required', 'Explicit correction', []))
  expect(port.decide).toHaveBeenCalledTimes(2); const current = h.result.current.commands.find(c => c.ack)!
  expect(current.command_id).not.toBe(old.command_id); expect(current.body.expected_decision_revision).toBe(1); expect(h.result.current.commands.find(c => c.command_id === old.command_id)).toEqual(old)
  expect(h.result.current.reading?.value.pending_target_ids).toEqual([targetId])
})

test('lost ACK retains one durable original; no duplicate key, explicit replay only, current remains separately read', async () => {
  const { h, port, workspace } = await prepared()
  vi.mocked(port.decide).mockImplementationOnce(async (_id, body, key) => { expect(readCommand((await commandStore.load(workspace))[key], workspace).body).toEqual(body); throw new Error('Response lost') })
  await act(() => h.result.current.submit('no_revision_needed', 'Keep original', [])); const pending = h.result.current.commands[0]
  act(() => h.result.current.adopt()); await act(() => h.result.current.submit('no_revision_needed', 'Replacement forbidden', [])); expect(port.decide).toHaveBeenCalledTimes(1)
  await act(() => h.result.current.execute(pending)); expect(vi.mocked(port.decide).mock.calls[1]).toEqual(vi.mocked(port.decide).mock.calls[0]); expect(h.result.current.commands[0].ack?.decision_revision).toBe(1)
  expect(h.result.current.reading?.value.target_decision_head).toBe(0); expect(h.result.current.reading?.value.pending_target_ids).toEqual([targetId])
})

test.each(['before_http', 'after_ack'] as const)('IDB failure %s survives unmount, hides under other session, saves original without HTTP after role-cycle', async mode => {
  const { h, port, workspace } = await prepared(), save = commandStore.save.bind(commandStore); let aborted = false
  vi.spyOn(commandStore, 'save').mockImplementation(async (...args) => { const value = JSON.parse(args[2]); if (!aborted && (mode === 'before_http' || value.ack)) { aborted = true; throw new Error('IDB abort') }; return save(...args) })
  await act(() => h.result.current.submit('no_revision_needed', 'Original memory', [])); expect(h.result.current.pendingMemory).toBe(true)
  const held = recoverable(workspace, session(workspace).csrf_token)[0]; h.unmount()
  vi.mocked(port.session).mockResolvedValue({ ...session(workspace), csrf_token: 'another-session' })
  const next = renderHook(() => useContentImpacts(workspace, false, port)); await waitFor(() => expect(next.result.current.ready).toBe(true)); expect(next.result.current.canSaveMemory).toBe(false)
  await act(() => next.result.current.saveMemory()); expect(next.result.current.pendingMemory).toBe(true)
  vi.mocked(port.session).mockResolvedValue(session(workspace)); vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(session(workspace)))))
  await act(() => request('POST /api/v1/session/role', { role: 'author' }, { 'Idempotency-Key': 'synthetic_generation' }))
  await waitFor(() => expect(next.result.current.canSaveMemory).toBe(true)); await act(() => next.result.current.saveMemory())
  expect(next.result.current.pendingMemory).toBe(false); expect(readCommand((await commandStore.load(workspace))[held.command_id], workspace)).toEqual(held); expect(next.result.current.canReplay(held)).toBe(false)
  await act(() => next.result.current.execute(held)); expect(port.decide).toHaveBeenCalledTimes(mode === 'before_http' ? 0 : 1)
})

test('late ACK after permission generation change cannot relabel old durable command', async () => {
  const { h, port, workspace } = await prepared(), pending = deferred<ReturnType<typeof ack>>()
  vi.mocked(port.decide).mockReturnValueOnce(pending.promise)
  let sending!: Promise<void>; act(() => { sending = h.result.current.submit('no_revision_needed', 'Awaiting original', []) }); await waitFor(() => expect(port.decide).toHaveBeenCalledTimes(1))
  const old = h.result.current.commands[0]; vi.mocked(port.session).mockResolvedValue({ ...session(workspace), role: 'learner' }); vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(session(workspace)))))
  await act(() => request('POST /api/v1/session/role', { role: 'learner' }, { 'Idempotency-Key': 'change' }))
  await act(async () => { pending.resolve(ack(old.body)); await sending })
  expect(h.result.current.ready).toBe(false); expect(h.result.current.commands).toEqual([]); expect(h.result.current.reading).toBeNull(); expect(h.result.current.frozen).toBeNull(); expect(readCommand((await commandStore.load(workspace))[old.command_id], workspace)).toEqual(old)
})

test('old page origin and unresolved receipt never permit replacement-key replay', async () => {
  const { h, port, workspace } = await prepared(), frozen = h.result.current.frozen!
  const c = makeCommand(workspace, getSessionGeneration(), frozen, { ...body(), reason: 'Old page original' }); c.origin.page_id = 'page_previous'; await persist(c)
  await act(() => h.result.current.execute(c)); await act(() => h.result.current.submit('new_revision_required', 'New key forbidden', [])); expect(port.decide).not.toHaveBeenCalled()
})

test('delayed command ledger cannot send a discarded or newly selected frozen basis', async () => {
  const { h, port } = await prepared(), delayed = deferred<Record<string, never>>()
  vi.spyOn(commandStore, 'load').mockReturnValueOnce(delayed.promise)
  let operation!: Promise<void>; act(() => { operation = h.result.current.submit('no_revision_needed', 'Old form', []) }); act(() => h.result.current.clearBasis()); act(() => h.result.current.adopt())
  await act(async () => { delayed.resolve({}); await operation }); expect(port.decide).not.toHaveBeenCalled()
})

test('list pagination keeps submitted filter/limit and rejects duplicate pages or invented IDs', async () => {
  const { h, port } = await prepared(); const calls = vi.mocked(port.read).mock.calls.length
  await act(() => h.result.current.read('outbox_invented')); await act(() => h.result.current.read(eventId, 'target_invented')); expect(port.read).toHaveBeenCalledTimes(calls)
  vi.mocked(port.list).mockResolvedValueOnce({ items: [listing], next_cursor: 'actual_cursor' })
  await act(() => h.result.current.discover(original.old_ref.id, 1))
  await act(() => h.result.current.discover('other_filter', 1, true)); expect(port.list).toHaveBeenCalledTimes(2)
  vi.mocked(port.list).mockResolvedValueOnce({ items: [{ ...listing, event_id: 'outbox_second' }], next_cursor: null })
  await act(() => h.result.current.discover(original.old_ref.id, 1, true))
  expect(vi.mocked(port.list).mock.lastCall).toEqual([original.old_ref.id, 1, 'actual_cursor']); expect(h.result.current.listing?.items).toHaveLength(2)
  expect(() => page({ items: [listing, listing], next_cursor: null }, null, 20)).toThrow()
  expect(() => page({ items: [listing], next_cursor: null }, 'different', 20)).toThrow()
})

test('real panel separates list, detail, target current, explicit adoption and human confirmation', async () => {
  const { workspace, port } = fixture(); render(<ContentImpactsPanel workspace={workspace} paused={false} port={port} />)
  await screen.findByRole('button', { name: '从第一页读取内容变更' }); expect(port.list).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: '从第一页读取内容变更' })); await screen.findByRole('button', { name: `查看影响详情 ${eventId}` }); fireEvent.click(screen.getByRole('button', { name: `查看影响详情 ${eventId}` }))
  await screen.findByRole('button', { name: `读取对象当前依据 ${targetId}` }); fireEvent.click(screen.getByRole('button', { name: `读取对象当前依据 ${targetId}` })); await screen.findByRole('button', { name: '采用本次对象依据准备决定' }); fireEvent.click(screen.getByRole('button', { name: '采用本次对象依据准备决定' }))
  expect((screen.getByLabelText('本次人工决定') as HTMLSelectElement).value).toBe(''); expect((screen.getByRole('button', { name: '明确保存内容决定' }) as HTMLButtonElement).disabled).toBe(true); expect(port.decide).not.toHaveBeenCalled()
})

test.each(['independent', 'open_book'] as const)('current %s assessment Policy forbids reading cached commands or issuing writes', async mode => {
  const { workspace, port } = fixture()
  vi.mocked(port.session).mockResolvedValue({ ...session(workspace), ...(mode === 'independent' ? { active_independent_attempt_id: 'attempt_real' } : { active_open_book_attempt_id: 'attempt_real' }) })
  const h = renderHook(() => useContentImpacts(workspace, false, port))
  await waitFor(() => expect(port.session).toHaveBeenCalled()); await waitFor(() => expect(h.result.current.busy).toBe(false))
  expect(h.result.current.ready).toBe(false); await act(() => h.result.current.read(eventId)); await act(() => h.result.current.submit('no_revision_needed', 'Cannot act', [])); expect(port.read).not.toHaveBeenCalled(); expect(port.decide).not.toHaveBeenCalled(); expect(h.result.current.commands).toEqual([])
})

test('a real Policy rejection clears previously displayed pins and pending form basis', async () => {
  const { h, port } = await prepared()
  vi.mocked(port.read).mockRejectedValueOnce(new ApiError(409, 'protected', 'ASSESSMENT_ACTIVE'))
  await act(() => h.result.current.read(eventId)); expect(h.result.current.reading).toBeNull(); expect(h.result.current.frozen).toBeNull(); expect(h.result.current.ready).toBe(false); expect(port.decide).not.toHaveBeenCalled()
})

test('journal keeps original ACK through reopening and refuses changed immutable body or conflicting ACK without persisting session secrets', async () => {
  const { h, workspace } = await prepared(); await act(() => h.result.current.submit('no_revision_needed', 'Original bound reason', ['artifact_synthetic']))
  const c = h.result.current.commands[0]; expect(c.ack).not.toBeNull(); await commandStore.close()
  expect(readCommand((await commandStore.load(workspace))[c.command_id], workspace)).toEqual(c)
  await expect(persist({ ...c, body: { ...c.body, reason: 'changed' } })).rejects.toThrow()
  await expect(persist({ ...c, ack: { ...c.ack!, actor_session_id: 'session_other' } })).rejects.toThrow()
  const raw = (await commandStore.load(workspace))[c.command_id].text
  expect(raw).not.toContain(session(workspace).csrf_token); expect(raw).not.toContain('csrf_token'); expect(raw).not.toContain('cookie')
})

test('history pagination preserves the bounded wire page separately from more than 100 accumulated receipts', async () => {
  const { h, port } = await prepared()
  const receipts = Array.from({ length: 101 }, (_, index) => ack({ ...body(index), reason: `Synthetic historical correction ${index}` }))
  vi.mocked(port.read).mockResolvedValueOnce({ ...original, target_decision_head: 101, decisions: receipts.slice(0, 100), next_cursor: 'cursor_from_server' })
  await act(() => h.result.current.read(eventId, targetId))
  vi.mocked(port.read).mockResolvedValueOnce({ ...original, target_decision_head: 101, decisions: receipts.slice(100) })
  await act(() => h.result.current.read(eventId, targetId, true))
  expect(h.result.current.reading?.history).toEqual(receipts); expect(h.result.current.reading?.value.decisions).toHaveLength(1)
  expect(h.result.current.frozen?.view.target_decision_head).toBe(0)
})

test('a newly observed different session cannot inherit this page command even without an access-counter notification', async () => {
  const { h, port, workspace } = await prepared()
  vi.mocked(port.decide).mockRejectedValueOnce(new Error('Original result unknown'))
  await act(() => h.result.current.submit('no_revision_needed', 'Original session-bound decision', [])); const c = h.result.current.commands[0]
  expect(h.result.current.canReplay(c)).toBe(true)
  vi.mocked(port.session).mockResolvedValue({ ...session(workspace), csrf_token: 'other-current-session' })
  await act(() => h.result.current.refresh()); expect(h.result.current.ready).toBe(true); expect(h.result.current.canReplay(c)).toBe(false)
  await act(() => h.result.current.execute(c)); expect(port.decide).toHaveBeenCalledTimes(1)
})

test.each(['legacy', 'stale_ref', 'changed_event'] as const)('explicit adoption respects %s without rewriting a frozen decision', async kind => {
  const { h, port } = await prepared(), frozen = h.result.current.frozen
  if (kind === 'legacy') {
    act(() => h.result.current.clearBasis())
    const old = { ...listing, evidence_version: 'legacy_unverified' as const, event_snapshot_sha256: null }
    vi.mocked(port.list).mockResolvedValueOnce({ items: [old], next_cursor: null }); await act(() => h.result.current.discover())
    vi.mocked(port.read).mockResolvedValueOnce({ ...original, evidence_version: 'legacy_unverified', event_snapshot_sha256: null, exact_dependency_refs: [], target_decision_head: 0 })
    await act(() => h.result.current.read(eventId, targetId)); act(() => h.result.current.adopt()); expect(h.result.current.frozen).toBeNull()
  } else {
    if (kind === 'stale_ref') vi.mocked(port.current).mockResolvedValueOnce({ ...targetRef, revision: 2, sha256: '9'.repeat(64) })
    else vi.mocked(port.read).mockResolvedValueOnce({ ...original, event_snapshot_sha256: '9'.repeat(64), target_decision_head: 0 })
    await act(() => h.result.current.read(eventId, targetId)); expect(h.result.current.frozen).toEqual(frozen)
    if (kind === 'changed_event') expect(h.result.current.reading?.value.event_snapshot_sha256).toBe(original.event_snapshot_sha256)
    else expect(h.result.current.reading?.current_ref?.revision).toBe(2)
  }
  expect(port.decide).not.toHaveBeenCalled()
})

test('history pagination accepts fresh current status and head while preserving member order and original basis', async () => {
  const { h, port } = await prepared(), first = ack(body()), second = ack(body(1))
  vi.mocked(port.read).mockResolvedValueOnce({ ...original, target_decision_head: 1, decisions: [first], next_cursor: 'real_history_cursor' })
  await act(() => h.result.current.read(eventId, targetId))
  vi.mocked(port.read).mockResolvedValueOnce({ ...original, target_decision_head: 2, pending_target_ids: [], action_required_target_ids: [targetId], decisions: [second] })
  await act(() => h.result.current.read(eventId, targetId, true))
  expect(h.result.current.reading?.history).toEqual([first, second]); expect(h.result.current.reading?.value.target_decision_head).toBe(2); expect(h.result.current.frozen?.view.target_decision_head).toBe(0)
})

test.each([401, 403, 409] as const)('access rejection %s hides list and target payload while preserving original durable decision', async status => {
  const { h, port, workspace } = await prepared(); await act(() => h.result.current.submit('no_revision_needed', 'Retained original', [])); const saved = await commandStore.load(workspace)
  vi.mocked(port.list).mockRejectedValueOnce(new ApiError(status, 'restricted', status === 409 ? 'ASSESSMENT_ACTIVE' : 'DENIED'))
  await act(() => h.result.current.discover()); expect(h.result.current.listing).toBeNull(); expect(h.result.current.reading).toBeNull(); expect(h.result.current.commands).toEqual([]); expect(await commandStore.load(workspace)).toEqual(saved)
})

test('unknown result from an old page is displayed but cannot produce an alternate key after a new read', async () => {
  const { h, workspace, port } = await prepared(), frozen = h.result.current.frozen!, old = makeCommand(workspace, getSessionGeneration(), frozen, body()); old.origin.page_id = 'page_old_browser'; await persist(old)
  await act(() => h.result.current.refresh()); await act(() => h.result.current.read(eventId, targetId)); act(() => h.result.current.adopt())
  await act(() => h.result.current.submit('new_revision_required', 'No duplicate while original is unknown', [])); expect(port.decide).not.toHaveBeenCalled(); expect((await commandStore.load(workspace))[old.command_id]).toBeTruthy()
})
