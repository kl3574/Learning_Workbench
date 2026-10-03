import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { reviewSession } from '../draftReview/reviewFixtures'
import { publicationDraft, publicationReceipt, publicationRef, base } from './restoreFixtures'
import { restorePublicationCommandStore, readRestorePublicationCommand } from './restorePublicationCommands'
import { makeRestorePublicationCommand, persistRestorePublicationCommand } from './restorePublicationCommands'
import { prepareRestoreBasis } from './restorePublicationSchema'
import { ApiError, getSessionGeneration, request } from '../../api/client'
import type { ContentRef } from '../../../../../packages/contracts/generated/api-types'
import type { RestorePort } from './restoreClient'
import { discardRestorePublicationMemory } from './restorePublicationMemory'
import { useRestorePublication } from './useRestorePublication'

afterEach(async () => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); await restorePublicationCommandStore.close() })
function fixture() {
  const workspace = `workspace_${crypto.randomUUID()}`
  const port: RestorePort = { session: vi.fn(async () => reviewSession(workspace)), create: vi.fn(), source: vi.fn(async () => structuredClone(base)), draft: vi.fn(async () => structuredClone(publicationDraft)), review: vi.fn(async () => structuredClone(publicationReceipt)), publish: vi.fn(async () => publicationRef), current: vi.fn(async () => publicationDraft.base_ref) }
  return { workspace, port }
}
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done }); return { promise, resolve } }
test('lost publication ACK retains the committed original body/key; explicit replay and fresh current remain distinct', async () => {
  const { workspace, port } = fixture()
  vi.mocked(port.publish).mockImplementationOnce(async (_id, body, key) => {
    const durable = readRestorePublicationCommand((await restorePublicationCommandStore.load(workspace))[key], workspace)
    expect(durable.body).toEqual(body); expect(durable.ack).toBeNull()
    throw new Error('Synthetic lost response after server commit')
  })
  const hook = renderHook(() => useRestorePublication(workspace, false, 'selection', port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.prepare(publicationDraft, publicationReceipt))
  expect(port.draft).toHaveBeenCalledTimes(1); expect(port.review).toHaveBeenCalledTimes(1)
  await act(() => hook.result.current.publish([0, 1]))
  const original = hook.result.current.commands[0]
  expect(original.ack).toBeNull(); expect(port.current).toHaveBeenCalledTimes(1)
  await act(() => hook.result.current.prepare(publicationDraft, publicationReceipt))
  await act(() => hook.result.current.publish([0, 1]))
  expect(port.publish).toHaveBeenCalledTimes(1)
  await act(() => hook.result.current.execute(original))
  expect(vi.mocked(port.publish).mock.calls[1]).toEqual(vi.mocked(port.publish).mock.calls[0])
  const confirmed = hook.result.current.commands[0]
  expect(confirmed.ack).toEqual(publicationRef); expect(hook.result.current.currentRead).toBeNull()
  vi.mocked(port.current).mockResolvedValueOnce({ ...publicationRef, revision: 4, sha256: 'c'.repeat(64) })
  await act(() => hook.result.current.readCurrent(confirmed))
  expect(hook.result.current.currentRead?.ref.revision).toBe(4)
  expect(hook.result.current.commands[0].ack?.revision).toBe(3)
})

test('a delayed ledger read cannot send an earlier basis after the user explicitly reads a new review', async () => {
  const { workspace, port } = fixture(), delayed = deferred<Record<string, never>>()
  const hook = renderHook(() => useRestorePublication(workspace, false, 'selection', port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.prepare(publicationDraft, publicationReceipt))
  vi.spyOn(restorePublicationCommandStore, 'load').mockReturnValueOnce(delayed.promise)
  let sending!: Promise<void>; act(() => { sending = hook.result.current.publish([0, 1]) })
  vi.mocked(port.review).mockResolvedValueOnce({ ...publicationReceipt, revision: 3, decision_reason: 'Synthetic later explicit decision' })
  await act(() => hook.result.current.prepare(publicationDraft, publicationReceipt))
  expect(hook.result.current.basis?.review.revision).toBe(3)
  await act(async () => { delayed.resolve({}); await sending })
  expect(port.publish).not.toHaveBeenCalled()
  expect(hook.result.current.basis?.review.revision).toBe(3)
})

test('failed durable storage causes zero HTTP writes and preserves the selected basis', async () => {
  const { workspace, port } = fixture()
  const hook = renderHook(() => useRestorePublication(workspace, false, 'selection', port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.prepare(publicationDraft, publicationReceipt))
  vi.spyOn(restorePublicationCommandStore, 'save').mockRejectedValueOnce(new Error('Synthetic IDB quota exceeded'))
  await act(() => hook.result.current.publish([0, 1]))
  expect(port.publish).not.toHaveBeenCalled(); expect(await restorePublicationCommandStore.load(workspace)).toEqual({})
  expect(hook.result.current.basis?.candidate).toEqual(publicationReceipt.candidate)
  expect(hook.result.current.pendingMemory).toBe(true)
  await act(() => hook.result.current.saveMemory())
  expect(hook.result.current.pendingMemory).toBe(false)
  expect(hook.result.current.commands).toHaveLength(1)
  expect(port.publish).not.toHaveBeenCalled()
  discardRestorePublicationMemory(workspace)
})

test('access generation change discards a late ACK without rewriting the durable original', async () => {
  const { workspace, port } = fixture(), delayed = deferred<ContentRef>()
  vi.mocked(port.publish).mockReturnValueOnce(delayed.promise)
  const hook = renderHook(() => useRestorePublication(workspace, false, 'selection', port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.prepare(publicationDraft, publicationReceipt))
  let sending!: Promise<void>; act(() => { sending = hook.result.current.publish([0, 1]) })
  await waitFor(() => expect(port.publish).toHaveBeenCalledTimes(1))
  const original = hook.result.current.commands[0]
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(reviewSession(workspace)))))
  await act(() => request('POST /api/v1/session/role', { role: 'author' }, { 'Idempotency-Key': 'synthetic_generation_change' }))
  await act(async () => { delayed.resolve(publicationRef); await sending })
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  const retained = readRestorePublicationCommand((await restorePublicationCommandStore.load(workspace))[original.command_id], workspace)
  expect(retained).toEqual(original); expect(retained.ack).toBeNull(); expect(hook.result.current.canReplay(retained)).toBe(false)
  await act(() => hook.result.current.execute(retained)); expect(port.publish).toHaveBeenCalledTimes(1)
})

test('previous page originals remain read-only and block a replacement key for unknown result', async () => {
  const { workspace, port } = fixture()
  const command = makeRestorePublicationCommand(workspace, getSessionGeneration(), prepareRestoreBasis(publicationDraft, base, publicationReceipt), [0, 1])
  command.origin.page_id = 'page_previous'
  await persistRestorePublicationCommand(command)
  const hook = renderHook(() => useRestorePublication(workspace, false, 'selection', port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.execute(hook.result.current.commands[0]))
  await act(() => hook.result.current.prepare(publicationDraft, publicationReceipt))
  await act(() => hook.result.current.publish([0, 1]))
  expect(port.publish).not.toHaveBeenCalled(); expect(hook.result.current.commands).toEqual([command])
})

test('permission rejection hides protected receipts and leaves the persisted original unknown', async () => {
  const { workspace, port } = fixture()
  vi.mocked(port.publish).mockRejectedValueOnce(new ApiError(403, 'Denied', 'POLICY_DENIED'))
  const hook = renderHook(() => useRestorePublication(workspace, false, 'selection', port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.prepare(publicationDraft, publicationReceipt))
  await act(() => hook.result.current.publish([0, 1]))
  expect(hook.result.current.ready).toBe(false); expect(hook.result.current.commands).toEqual([]); expect(hook.result.current.basis).toBeNull()
  const raw = Object.values(await restorePublicationCommandStore.load(workspace)); expect(raw).toHaveLength(1)
  expect(readRestorePublicationCommand(raw[0], workspace).ack).toBeNull()
})

test.each([{ ...publicationRef, id: 'block_other' }, { ...publicationRef, sha256: 'b'.repeat(64) }, { ...publicationRef, revision: 1 }, { ...publicationRef, extra: true }])('wrong publication reference remains unknown without fabricating success', async ack => {
  const { workspace, port } = fixture(); vi.mocked(port.publish).mockResolvedValueOnce(ack)
  const hook = renderHook(() => useRestorePublication(workspace, false, 'selection', port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.prepare(publicationDraft, publicationReceipt)); await act(() => hook.result.current.publish([0, 1]))
  expect(hook.result.current.commands[0].ack).toBeNull(); expect(hook.result.current.currentRead).toBeNull()
})

test('412 retains old source/base and cannot silently rebase or publish again after current advances', async () => {
  const { workspace, port } = fixture(); vi.mocked(port.publish).mockRejectedValueOnce(new ApiError(412, 'Synthetic changed current', 'RESTORE_CURRENT_CHANGED'))
  const hook = renderHook(() => useRestorePublication(workspace, false, 'selection', port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.prepare(publicationDraft, publicationReceipt)); await act(() => hook.result.current.publish([0, 1]))
  const old = hook.result.current.commands[0]; expect(old.rejection?.status).toBe(412)
  vi.mocked(port.current).mockResolvedValue({ ...publicationRef, sha256: 'c'.repeat(64) })
  await act(() => hook.result.current.prepare(publicationDraft, publicationReceipt))
  expect(hook.result.current.basis).toBeNull()
  await act(() => hook.result.current.publish([0, 1])); expect(port.publish).toHaveBeenCalledTimes(1)
  expect(hook.result.current.commands).toEqual([old]); expect(old.basis.snapshot.base_ref).toEqual(publicationDraft.base_ref)
})

test('candidate selection changes discard a delayed preparation and never carry warning confirmation across candidates', async () => {
  const { workspace, port } = fixture(), delayed = deferred<typeof publicationDraft>(); vi.mocked(port.draft).mockReturnValueOnce(delayed.promise)
  const hook = renderHook(({ selection }) => useRestorePublication(workspace, false, selection, port), { initialProps: { selection: 'first' } })
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  let preparing!: Promise<void>; act(() => { preparing = hook.result.current.prepare(publicationDraft, publicationReceipt) })
  hook.rerender({ selection: 'second' })
  await act(async () => { delayed.resolve(publicationDraft); await preparing })
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  expect(hook.result.current.basis).toBeNull(); expect(port.publish).not.toHaveBeenCalled()
})


test('received ACK survives failed IDB acknowledgement save and unmount, but another session cannot recover or send it', async () => {
  const { workspace, port } = fixture(), first = renderHook(() => useRestorePublication(workspace, false, 'selection', port))
  await waitFor(() => expect(first.result.current.ready).toBe(true)); await act(() => first.result.current.prepare(publicationDraft, publicationReceipt))
  const save = restorePublicationCommandStore.save.bind(restorePublicationCommandStore)
  vi.spyOn(restorePublicationCommandStore, 'save').mockImplementation(async (...args) => {
    if (JSON.parse(args[2]).ack) throw new Error('Synthetic received ACK save failure')
    return save(...args)
  })
  await act(() => first.result.current.publish([0, 1])); expect(first.result.current.pendingMemory).toBe(true)
  expect(first.result.current.commands[0].ack).toBeNull(); expect(port.publish).toHaveBeenCalledTimes(1)
  first.unmount(); vi.restoreAllMocks()
  vi.mocked(port.session).mockResolvedValue({ ...reviewSession(workspace), csrf_token: 'different-session' })
  const second = renderHook(() => useRestorePublication(workspace, false, 'selection', port))
  await waitFor(() => expect(second.result.current.ready).toBe(true))
  expect(second.result.current.canSaveMemory).toBe(false); expect(second.result.current.pendingMemory).toBe(true)
  await act(() => second.result.current.saveMemory()); expect(second.result.current.pendingMemory).toBe(true)
  vi.mocked(port.session).mockResolvedValue(reviewSession(workspace)); await act(() => second.result.current.refresh())
  await act(() => second.result.current.saveMemory())
  expect(second.result.current.pendingMemory).toBe(false); expect(second.result.current.commands[0].ack).toEqual(publicationRef)
  expect(port.publish).toHaveBeenCalledTimes(1); expect(second.result.current.currentRead).toBeNull()
})

test('a block-scoped publication panel rejects foreign preparation, replay and current reads', async () => {
  const { workspace, port } = fixture(), basis = prepareRestoreBasis(publicationDraft, base, publicationReceipt)
  const command = makeRestorePublicationCommand(workspace, getSessionGeneration(), basis, [0, 1])
  const hook = renderHook(() => useRestorePublication(workspace, false, 'selection', port, 'block_other'))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.prepare(publicationDraft, publicationReceipt))
  expect(hook.result.current.basis).toBeNull(); expect(port.draft).not.toHaveBeenCalled()
  expect(hook.result.current.canReplay(command)).toBe(false)
  await act(() => hook.result.current.execute(command)); await act(() => hook.result.current.readCurrent({ ...command, ack: publicationRef }))
  expect(port.publish).not.toHaveBeenCalled(); expect(port.current).not.toHaveBeenCalled()
})
