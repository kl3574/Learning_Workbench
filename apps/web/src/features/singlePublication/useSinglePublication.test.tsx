import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { ContentRef } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, getSessionGeneration, request } from '../../api/client'
import { singlePublicationFixture } from './singlePublicationFixtures'
import { makeSinglePublicationCommand, persistSinglePublicationCommand, readSinglePublicationCommand, singlePublicationCommandStore } from './singlePublicationCommands'
import { discardSinglePublicationForms, discardSinglePublicationMemory } from './singlePublicationMemory'
import { useSinglePublication } from './useSinglePublication'
const workspaces: string[] = []
const fixture = () => { const f = singlePublicationFixture(); workspaces.push(f.workspace); return f }
afterEach(async () => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); for (const workspace of workspaces.splice(0)) { discardSinglePublicationMemory(workspace); discardSinglePublicationForms(workspace) }; await singlePublicationCommandStore.close() })
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done }); return { promise, resolve } }
async function ready(f: ReturnType<typeof fixture>) {
  const hook = renderHook(() => useSinglePublication(f.workspace, false, 'selected', f.port, f.draft.candidate.draft_id))
  await waitFor(() => expect(hook.result.current.ready).toBe(true)); await act(() => hook.result.current.prepare(f.draft, f.receipt)); expect(hook.result.current.basis).not.toBeNull(); return hook
}
test('unknown response replays exactly the persisted four fields; successful ACK, publication GET and later current remain separate', async () => {
  const f = fixture(); vi.mocked(f.port.publish).mockImplementationOnce(async (_id, body, key) => {
    const stored = readSinglePublicationCommand((await singlePublicationCommandStore.load(f.workspace))[key], f.workspace)
    expect(stored.body).toEqual(body); expect(stored.ack).toBeNull(); throw new Error('synthetic lost response after commit')
  })
  const hook = await ready(f); expect(f.port.generation).toHaveBeenCalledWith(f.draft.source_job_id); expect(f.port.current).not.toHaveBeenCalled()
  await act(() => hook.result.current.publish([0, 1])); const original = hook.result.current.commands[0]; expect(original.ack).toBeNull()
  await act(() => hook.result.current.prepare(f.draft, f.receipt)); await act(() => hook.result.current.publish([0, 1])); expect(f.port.publish).toHaveBeenCalledTimes(1)
  await act(() => hook.result.current.execute(original)); expect(vi.mocked(f.port.publish).mock.calls[1]).toEqual(vi.mocked(f.port.publish).mock.calls[0])
  const confirmed = hook.result.current.commands[0]; expect(confirmed.ack).toEqual(f.ack); expect(hook.result.current.publicationRead).toBeNull(); expect(hook.result.current.currentRead).toBeNull()
  vi.mocked(f.port.draft).mockResolvedValueOnce({ ...f.draft, state: 'published', published_ref: f.ack }); await act(() => hook.result.current.readPublication(f.draft.candidate, f.ack))
  expect(hook.result.current.publicationRead?.published_ref).toEqual(f.ack)
  vi.mocked(f.port.current).mockResolvedValueOnce({ ...f.ack, revision: 2, sha256: '3'.repeat(64) }); await act(() => hook.result.current.readCurrent(confirmed))
  expect(hook.result.current.currentRead?.ref.revision).toBe(2); expect(hook.result.current.commands[0].ack).toEqual(f.ack)
})
test('failed original journal write sends zero POST and saving held command sends no HTTP', async () => {
  const f = fixture(), hook = await ready(f)
  vi.spyOn(singlePublicationCommandStore, 'save').mockRejectedValueOnce(new Error('synthetic quota'))
  await act(() => hook.result.current.publish([0, 1])); expect(f.port.publish).not.toHaveBeenCalled(); expect(hook.result.current.pendingMemory).toBe(true)
  expect(await singlePublicationCommandStore.load(f.workspace)).toEqual({}); expect(hook.result.current.basis?.candidate).toEqual(f.draft.candidate)
  await act(() => hook.result.current.saveMemory()); expect(hook.result.current.pendingMemory).toBe(false); expect(hook.result.current.commands).toHaveLength(1); expect(f.port.publish).not.toHaveBeenCalled()
})
test('received ACK survives failed IDB write and unmount; a different actor cannot save it, original actor saves without replay', async () => {
  const f = fixture(), hook = await ready(f), save = singlePublicationCommandStore.save.bind(singlePublicationCommandStore)
  vi.spyOn(singlePublicationCommandStore, 'save').mockImplementation(async (...args) => { if (JSON.parse(args[2]).ack) throw new Error('synthetic ACK write failure'); return save(...args) })
  await act(() => hook.result.current.publish([0, 1])); expect(hook.result.current.pendingMemory).toBe(true); expect(hook.result.current.commands[0].ack).toBeNull(); hook.unmount(); vi.restoreAllMocks()
  f.session.actor_session_id = 'session_other'
  const next = renderHook(() => useSinglePublication(f.workspace, false, 'selected', f.port)); await waitFor(() => expect(next.result.current.ready).toBe(true))
  expect(next.result.current.canSaveMemory).toBe(false); await act(() => next.result.current.saveMemory()); expect(next.result.current.pendingMemory).toBe(true)
  f.session.actor_session_id = 'session_fixture_reviewFixtures'; f.session.csrf_token = 'csrf_rotated_same_actor'
  await act(() => next.result.current.refresh()); await act(() => next.result.current.saveMemory()); expect(next.result.current.commands[0].ack).toEqual(f.ack); expect(next.result.current.pendingMemory).toBe(false); expect(f.port.publish).toHaveBeenCalledTimes(1)
})
test('late ACK after access generation change remains in original actor memory; old access key cannot replay', async () => {
  const f = fixture(), delayed = deferred<ContentRef>(); vi.mocked(f.port.publish).mockReturnValueOnce(delayed.promise)
  const hook = await ready(f); let sending!: Promise<void>; act(() => { sending = hook.result.current.publish([0, 1]) }); await waitFor(() => expect(f.port.publish).toHaveBeenCalledTimes(1))
  const original = hook.result.current.commands[0]
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(f.session))))
  await act(() => request('POST /api/v1/session/role', { role: 'author' }, { 'Idempotency-Key': 'synthetic_generation_change' }))
  await act(async () => { delayed.resolve(f.ack); await sending }); await waitFor(() => expect(hook.result.current.ready).toBe(true))
  const persisted = readSinglePublicationCommand((await singlePublicationCommandStore.load(f.workspace))[original.command_id], f.workspace)
  expect(persisted).toEqual(original); expect(hook.result.current.pendingMemory).toBe(true); expect(hook.result.current.canReplay(persisted)).toBe(false)
  await act(() => hook.result.current.saveMemory()); expect(hook.result.current.commands[0].ack).toEqual(f.ack)
  await act(() => hook.result.current.execute(hook.result.current.commands[0])); expect(f.port.publish).toHaveBeenCalledTimes(1)
})
test('previous page unknown original prevents replacing its key and cannot be automatically or explicitly replayed', async () => {
  const f = fixture(), command = makeSinglePublicationCommand(f.workspace, getSessionGeneration(), f.basis(), [0, 1]); command.origin.page_id = 'page_previous'
  await persistSinglePublicationCommand(command); const hook = await ready(f)
  expect(f.port.publish).not.toHaveBeenCalled(); await act(() => hook.result.current.execute(command)); await act(() => hook.result.current.publish([0, 1]))
  expect(f.port.publish).not.toHaveBeenCalled(); expect(hook.result.current.commands).toEqual([command])
})
test('permission rejection hides academic data while preserving durable unknown original', async () => {
  const f = fixture(), hook = await ready(f); vi.mocked(f.port.publish).mockRejectedValueOnce(new ApiError(403, 'synthetic denied', 'POLICY_DENIED'))
  await act(() => hook.result.current.publish([0, 1])); expect(hook.result.current.ready).toBe(false); expect(hook.result.current.basis).toBeNull(); expect(hook.result.current.commands).toEqual([])
  const rows = Object.values(await singlePublicationCommandStore.load(f.workspace)); expect(rows).toHaveLength(1); expect(readSinglePublicationCommand(rows[0], f.workspace).ack).toBeNull()
})
test.each(['new_review', 'new_numeric', 'published'])('changed %s basis preserves original form and cannot inherit confirmation', async fault => {
  const f = fixture(), hook = await ready(f); act(() => hook.result.current.retainForm([0, 1], true)); const form = hook.result.current.forms[0]
  if (fault === 'new_review') f.receipt.revision = 3
  if (fault === 'new_numeric') f.draft.numeric_check_ids.push('check_newer')
  if (fault === 'published') { f.draft.state = 'published'; f.draft.published_ref = f.ack }
  await act(() => hook.result.current.recoverForm(form)); expect(hook.result.current.basis).toBeNull(); expect(hook.result.current.forms[0]).toEqual(form); expect(f.port.publish).not.toHaveBeenCalled()
})
test('unsent confirmations are private to original actor; exact recovery resets final confirmation without POST', async () => {
  const f = fixture(), hook = await ready(f); act(() => hook.result.current.retainForm([0, 1], true)); const original = hook.result.current.forms[0]; hook.unmount()
  f.session.actor_session_id = 'session_other'
  const next = renderHook(() => useSinglePublication(f.workspace, false, 'selected', f.port)); await waitFor(() => expect(next.result.current.ready).toBe(true)); expect(next.result.current.pendingForms).toBe(true); expect(next.result.current.forms).toEqual([])
  await act(() => next.result.current.recoverForm(original)); expect(next.result.current.basis).toBeNull()
  await act(() => next.result.current.prepare(f.draft, f.receipt)); act(() => next.result.current.retainForm([0], false))
  f.session.actor_session_id = 'session_fixture_reviewFixtures'; await act(() => next.result.current.refresh()); expect(next.result.current.forms).toEqual([original])
  await act(() => next.result.current.recoverForm(original)); expect(next.result.current.basis?.candidate).toEqual(f.draft.candidate); expect(next.result.current.forms[0].confirmed).toBe(false); expect(next.result.current.forms[0].selected).toEqual([0, 1]); expect(f.port.publish).not.toHaveBeenCalled()
})
test('an inconsistent GET publication association cannot replace original ACK, and a later ACK mismatch stays rejected', async () => {
  const f = fixture(), hook = await ready(f); await act(() => hook.result.current.publish([0, 1])); const original = hook.result.current.commands[0]
  vi.mocked(f.port.draft).mockResolvedValueOnce({ ...f.draft, state: 'published', published_ref: { ...f.ack, id: 'block_other' } })
  await act(() => hook.result.current.readPublication(f.draft.candidate, f.ack)); expect(hook.result.current.publicationRead).toBeNull()
  vi.mocked(f.port.publish).mockResolvedValueOnce({ ...f.ack, sha256: '3'.repeat(64) }); await act(() => hook.result.current.execute(original)); expect(hook.result.current.commands[0]).toEqual(original)
})
test('delayed ledger lookup or candidate selection cannot publish an earlier selected basis', async () => {
  const f = fixture(), hook = await ready(f), delayed = deferred<Awaited<ReturnType<typeof singlePublicationCommandStore.load>>>()
  vi.spyOn(singlePublicationCommandStore, 'load').mockReturnValueOnce(delayed.promise)
  let sending!: Promise<void>; act(() => { sending = hook.result.current.publish([0, 1]) })
  await act(() => hook.result.current.prepare(f.draft, f.receipt)); await act(async () => { delayed.resolve({}); await sending }); expect(f.port.publish).not.toHaveBeenCalled()
})
test('draft-scoped publication rejects foreign preparation and replay without an HTTP read or write', async () => {
  const f = fixture(), command = makeSinglePublicationCommand(f.workspace, getSessionGeneration(), f.basis(), [0, 1])
  const hook = renderHook(() => useSinglePublication(f.workspace, false, 'selected', f.port, 'draft_other')); await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.prepare(f.draft, f.receipt)); await act(() => hook.result.current.execute(command)); await act(() => hook.result.current.readCurrent({ ...command, ack: f.ack }))
  expect(hook.result.current.basis).toBeNull(); expect(f.port.draft).not.toHaveBeenCalled(); expect(f.port.publish).not.toHaveBeenCalled(); expect(f.port.current).not.toHaveBeenCalled()
})
