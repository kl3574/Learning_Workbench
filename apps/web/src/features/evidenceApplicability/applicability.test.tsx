import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor, render, screen, fireEvent } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { ApiError, getSessionGeneration, request } from '../../api/client'
import { commandStore, makeCommand, persist, readCommand, decode } from './commands'
import { artifacts, basis, readView, receipt } from './schema'
import { discard, recoverable } from './memory'
import { ack, original, evidenceId, eventId, portFor, session } from './fixtures'
import { useApplicability } from './useApplicability'
import { ApplicabilityPanel } from './ApplicabilityPanel'
const spaces: string[] = []
afterEach(async () => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); for (const workspace of spaces.splice(0)) discard(workspace); await commandStore.close() })
function fixture() { const workspace = `workspace_${crypto.randomUUID()}`; spaces.push(workspace); const port = portFor(workspace); port.read = vi.fn(port.read); port.decide = vi.fn(port.decide); port.session = vi.fn(port.session); return { workspace, port } }
async function prepared() { const f = fixture(), h = renderHook(() => useApplicability(f.workspace, false, f.port)); await waitFor(() => expect(h.result.current.ready).toBe(true)); await act(() => h.result.current.read(evidenceId)); await act(() => h.result.current.read(evidenceId, eventId)); act(() => h.result.current.adopt()); return { ...f, h } }
function deferred<T>() { let resolve!: (v: T) => void; const promise = new Promise<T>(r => { resolve = r }); return { promise, resolve } }

test('strict source/owner pins, selected event, CAS/body and original ACK binding reject substitution', () => {
  const frozen = basis({ event_id: eventId, view: { ...original, event_decision_head: 0 } }), body = { event_id: eventId, expected_decision_revision: 0, expected_current_basis_sha256: original.current_basis_sha256, decision: 'usable' as const, reason: 'Synthetic explicit judgment', evidence_artifact_ids: [] }
  const command = makeCommand('workspace_synthetic', 0, frozen, body)
  for (const bad of [{ ...original, extra: true }, { ...original, original_evidence: { ...original.original_evidence, id: 'other' } }, { ...original, question_ref: original.concept_ref }, { ...original, relevant_event_ids: [eventId, eventId] }]) expect(() => readView(bad, evidenceId)).toThrow()
  expect(() => basis({ ...frozen, event_id: 'outbox_fake' })).toThrow()
  for (const bad of [{ ...command, extra: true }, { ...command, body: { ...body, expected_decision_revision: true } }, { ...command, body: { ...body, expected_current_basis_sha256: '0'.repeat(64) } }, { ...command, body: { ...body, reason: ' ' } }, { ...command, body: { ...body, evidence_artifact_ids: ['artifact_a', 'artifact_a'] } }]) expect(() => decode(JSON.stringify(bad), command.workspace_id)).toThrow()
  for (const bad of [{ ...ack(body), decision_revision: 3 }, { ...ack(body), grading_revision: 2 }, { ...ack(body), current_basis_sha256: '0'.repeat(64) }, { ...ack(body), decision: 'confirmed_stale' }, { ...ack(body), evidence_artifacts: [{ id: 'artifact_other', sha256: 'a'.repeat(64) }] }]) expect(() => receipt(bad, frozen, body)).toThrow()
  expect(() => artifacts('artifact_a\nartifact_a')).toThrow(); expect(() => artifacts('https://example.com')).toThrow(); expect(() => artifacts(Array.from({ length: 33 }, (_, i) => `artifact_${i}`).join('\n'))).toThrow(); expect(artifacts('')).toEqual([])
})

test('read-only selection never adopts new basis; 412 preserves original and explicit correction uses a new key', async () => {
  const { h, port } = await prepared(), frozen = h.result.current.frozen
  vi.mocked(port.read).mockResolvedValueOnce({ ...original, current_basis_sha256: '2'.repeat(64), event_decision_head: 1 })
  await act(() => h.result.current.read(evidenceId, eventId)); expect(h.result.current.frozen).toEqual(frozen)
  vi.mocked(port.decide).mockRejectedValueOnce(new ApiError(412, 'stale', 'REVISION_MISMATCH'))
  await act(() => h.result.current.submit('usable', 'Original explicit judgment', []))
  const old = h.result.current.commands[0]; expect(old.body.expected_decision_revision).toBe(0); expect(old.rejection?.status).toBe(412)
  expect(h.result.current.frozen).toBeNull(); await act(() => h.result.current.submit('usable', 'No implicit basis', [])); expect(port.decide).toHaveBeenCalledTimes(1)
  act(() => h.result.current.adopt()); await act(() => h.result.current.submit('confirmed_stale', 'Explicit correction', []))
  expect(port.decide).toHaveBeenCalledTimes(2); const current = h.result.current.commands.find(c => c.ack)!
  expect(current.command_id).not.toBe(old.command_id); expect(current.body.expected_decision_revision).toBe(1); expect(h.result.current.commands.find(c => c.command_id === old.command_id)).toEqual(old)
  expect(h.result.current.reading?.value.applicability).toBe('pending_review')
})

test('lost ACK retains one durable original; no duplicate key, explicit replay only, current remains separately read', async () => {
  const { h, port, workspace } = await prepared()
  vi.mocked(port.decide).mockImplementationOnce(async (_id, body, key) => { expect(readCommand((await commandStore.load(workspace))[key], workspace).body).toEqual(body); throw new Error('Response lost') })
  await act(() => h.result.current.submit('usable', 'Keep original', [])); const pending = h.result.current.commands[0]
  act(() => h.result.current.adopt()); await act(() => h.result.current.submit('usable', 'Replacement forbidden', [])); expect(port.decide).toHaveBeenCalledTimes(1)
  await act(() => h.result.current.execute(pending)); expect(vi.mocked(port.decide).mock.calls[1]).toEqual(vi.mocked(port.decide).mock.calls[0]); expect(h.result.current.commands[0].ack?.decision_revision).toBe(1)
  expect(h.result.current.reading?.value.event_decision_head).toBe(0); expect(h.result.current.reading?.value.original_evidence.eligible).toBe(false)
})

test.each(['before_http', 'after_ack'] as const)('IDB failure %s survives unmount, hides under other session, saves original without HTTP after role-cycle', async mode => {
  const { h, port, workspace } = await prepared(), save = commandStore.save.bind(commandStore); let aborted = false
  vi.spyOn(commandStore, 'save').mockImplementation(async (...args) => { const value = JSON.parse(args[2]); if (!aborted && (mode === 'before_http' || value.ack)) { aborted = true; throw new Error('IDB abort') }; return save(...args) })
  await act(() => h.result.current.submit('usable', 'Original memory', [])); expect(h.result.current.pendingMemory).toBe(true)
  const held = recoverable(workspace, session(workspace).csrf_token)[0]; h.unmount()
  vi.mocked(port.session).mockResolvedValue({ ...session(workspace), csrf_token: 'another-session' })
  const next = renderHook(() => useApplicability(workspace, false, port)); await waitFor(() => expect(next.result.current.ready).toBe(true)); expect(next.result.current.canSaveMemory).toBe(false)
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
  let sending!: Promise<void>; act(() => { sending = h.result.current.submit('usable', 'Awaiting original', []) }); await waitFor(() => expect(port.decide).toHaveBeenCalledTimes(1))
  const old = h.result.current.commands[0]; vi.mocked(port.session).mockResolvedValue({ ...session(workspace), role: 'learner' }); vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(session(workspace)))))
  await act(() => request('POST /api/v1/session/role', { role: 'learner' }, { 'Idempotency-Key': 'change' }))
  await act(async () => { pending.resolve(ack(old.body)); await sending })
  expect(h.result.current.ready).toBe(false); expect(h.result.current.commands).toEqual([]); expect(h.result.current.reading).toBeNull(); expect(h.result.current.frozen).toBeNull(); expect(readCommand((await commandStore.load(workspace))[old.command_id], workspace)).toEqual(old)
})

test('old page origin and unresolved receipt never permit replacement-key replay', async () => {
  const { h, port, workspace } = await prepared(), frozen = h.result.current.frozen!
  const c = makeCommand(workspace, getSessionGeneration(), frozen, { event_id: eventId, expected_decision_revision: 0, expected_current_basis_sha256: original.current_basis_sha256, decision: 'usable', reason: 'Old page original', evidence_artifact_ids: [] }); c.origin.page_id = 'page_previous'; await persist(c)
  await act(() => h.result.current.execute(c)); await act(() => h.result.current.submit('confirmed_stale', 'New key forbidden', [])); expect(port.decide).not.toHaveBeenCalled()
})

test('delayed command ledger cannot send a discarded or newly selected frozen basis', async () => {
  const { h, port } = await prepared(), delayed = deferred<Record<string, never>>()
  vi.spyOn(commandStore, 'load').mockReturnValueOnce(delayed.promise)
  let operation!: Promise<void>; act(() => { operation = h.result.current.submit('usable', 'Old form', []) }); act(() => h.result.current.clearBasis()); act(() => h.result.current.adopt())
  await act(async () => { delayed.resolve({}); await operation }); expect(port.decide).not.toHaveBeenCalled()
})

test('pagination refuses changed basis and unknown event IDs have zero GETs', async () => {
  const { h, port } = await prepared(); const calls = vi.mocked(port.read).mock.calls.length
  await act(() => h.result.current.read(evidenceId, 'outbox_invented')); expect(port.read).toHaveBeenCalledTimes(calls)
  vi.mocked(port.read).mockResolvedValueOnce({ ...original, event_decision_head: 0, next_cursor: 'cursor_actual' }); await act(() => h.result.current.read(evidenceId, eventId))
  vi.mocked(port.read).mockResolvedValueOnce({ ...original, event_decision_head: 1 }); await act(() => h.result.current.read(evidenceId, eventId, true))
  expect(h.result.current.reading?.value.event_decision_head).toBe(0)
})

test('real panel separates explicit read/adopt/confirmation and never defaults usable', async () => {
  const { workspace, port } = fixture(); render(<ApplicabilityPanel workspace={workspace} paused={false} evidenceId={evidenceId} port={port} />)
  await waitFor(() => expect(screen.getByRole('button', { name: '读取所选原证据当前适用性' })).toBeTruthy()); expect(port.read).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: '读取所选原证据当前适用性' })); await screen.findByRole('button', { name: `读取事件决定基准 ${eventId}` }); fireEvent.click(screen.getByRole('button', { name: `读取事件决定基准 ${eventId}` })); await screen.findByRole('button', { name: '采用本次已读依据准备决定' }); fireEvent.click(screen.getByRole('button', { name: '采用本次已读依据准备决定' }))
  expect((screen.getByLabelText('明确适用性决定') as HTMLSelectElement).value).toBe(''); expect((screen.getByRole('button', { name: '明确保存适用性决定' }) as HTMLButtonElement).disabled).toBe(true)
  expect(port.decide).not.toHaveBeenCalled()
})

test.each(['independent', 'open_book'] as const)('current %s assessment Policy forbids reading cached commands or issuing writes', async mode => {
  const { workspace, port } = fixture()
  vi.mocked(port.session).mockResolvedValue({ ...session(workspace), ...(mode === 'independent' ? { active_independent_attempt_id: 'attempt_real' } : { active_open_book_attempt_id: 'attempt_real' }) })
  const h = renderHook(() => useApplicability(workspace, false, port))
  await waitFor(() => expect(port.session).toHaveBeenCalled()); await waitFor(() => expect(h.result.current.busy).toBe(false))
  expect(h.result.current.ready).toBe(false); await act(() => h.result.current.read(evidenceId)); await act(() => h.result.current.submit('usable', 'Cannot act', [])); expect(port.read).not.toHaveBeenCalled(); expect(port.decide).not.toHaveBeenCalled(); expect(h.result.current.commands).toEqual([])
})

test('a real Policy rejection clears previously displayed pins and pending form basis', async () => {
  const { h, port } = await prepared()
  vi.mocked(port.read).mockRejectedValueOnce(new ApiError(409, 'protected', 'ASSESSMENT_ACTIVE'))
  await act(() => h.result.current.read(evidenceId)); expect(h.result.current.reading).toBeNull(); expect(h.result.current.frozen).toBeNull(); expect(h.result.current.ready).toBe(false); expect(port.decide).not.toHaveBeenCalled()
})

test('journal keeps original ACK through reopening and refuses changed immutable body or conflicting ACK without persisting session secrets', async () => {
  const { h, workspace } = await prepared(); await act(() => h.result.current.submit('usable', 'Original bound reason', ['artifact_synthetic']))
  const c = h.result.current.commands[0]; expect(c.ack).not.toBeNull(); await commandStore.close()
  expect(readCommand((await commandStore.load(workspace))[c.command_id], workspace)).toEqual(c)
  await expect(persist({ ...c, body: { ...c.body, reason: 'changed' } })).rejects.toThrow()
  await expect(persist({ ...c, ack: { ...c.ack!, actor_session_id: 'session_other' } })).rejects.toThrow()
  const raw = (await commandStore.load(workspace))[c.command_id].text
  expect(raw).not.toContain(session(workspace).csrf_token); expect(raw).not.toContain('csrf_token'); expect(raw).not.toContain('cookie')
})

test('history pagination preserves the bounded wire page separately from more than 100 accumulated receipts', async () => {
  const { h, port } = await prepared()
  const receipts = Array.from({ length: 101 }, (_, index) => ack({ event_id: eventId, expected_decision_revision: index, expected_current_basis_sha256: original.current_basis_sha256, decision: 'usable', reason: `Synthetic historical correction ${index}`, evidence_artifact_ids: [] }))
  vi.mocked(port.read).mockResolvedValueOnce({ ...original, event_decision_head: 101, decisions: receipts.slice(0, 100), next_cursor: 'cursor_from_server' })
  await act(() => h.result.current.read(evidenceId, eventId))
  vi.mocked(port.read).mockResolvedValueOnce({ ...original, event_decision_head: 101, decisions: receipts.slice(100) })
  await act(() => h.result.current.read(evidenceId, eventId, true))
  expect(h.result.current.reading?.history).toEqual(receipts); expect(h.result.current.reading?.value.decisions).toHaveLength(1)
  expect(h.result.current.frozen?.view.event_decision_head).toBe(0)
})

test('a newly observed different session cannot inherit this page command even without an access-counter notification', async () => {
  const { h, port, workspace } = await prepared()
  vi.mocked(port.decide).mockRejectedValueOnce(new Error('Original result unknown'))
  await act(() => h.result.current.submit('usable', 'Original session-bound decision', [])); const c = h.result.current.commands[0]
  expect(h.result.current.canReplay(c)).toBe(true)
  vi.mocked(port.session).mockResolvedValue({ ...session(workspace), csrf_token: 'other-current-session' })
  await act(() => h.result.current.refresh()); expect(h.result.current.ready).toBe(true); expect(h.result.current.canReplay(c)).toBe(false)
  await act(() => h.result.current.execute(c)); expect(port.decide).toHaveBeenCalledTimes(1)
})
