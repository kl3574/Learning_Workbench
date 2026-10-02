import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { ApiError, getSessionGeneration } from '../../api/client'
import { reviewSession } from '../draftReview/reviewFixtures'
import { base, current, createAck, createBody, publicationDraft, publicationReceipt, publicationRef } from './restoreFixtures'
import type { RestorePort } from './restoreClient'
import { makeRestoreCreateCommand, persistRestoreCreateCommand, readRestoreCreateCommand, restoreCreateCommandStore } from './restoreCreateCommands'
import { discardRestoreCreateMemory } from './restoreCreateMemory'
import { useRestoreDrafts } from './useRestoreDrafts'

const workspaces: string[] = []
afterEach(async () => { cleanup(); vi.restoreAllMocks(); workspaces.splice(0).forEach(workspace => discardRestoreCreateMemory(workspace)); await restoreCreateCommandStore.close() })
function fixture() {
  const workspace = `workspace_${crypto.randomUUID()}`; workspaces.push(workspace)
  const port: RestorePort = { session: vi.fn(async () => reviewSession(workspace)), current: vi.fn(async () => publicationDraft.base_ref),
    source: vi.fn(async ref => structuredClone(ref.revision === 1 ? base : current)), create: vi.fn(async () => structuredClone(createAck)),
    draft: vi.fn(async () => structuredClone(publicationDraft)), review: vi.fn(async () => publicationReceipt), publish: vi.fn(async () => publicationRef) }
  return { workspace, port }
}
async function prepared() {
  const { workspace, port } = fixture(), hook = renderHook(() => useRestoreDrafts(workspace, false, base.metadata.id, port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.prepare(publicationDraft.source_ref))
  expect(hook.result.current.basis?.current).toEqual(current)
  return { workspace, port, hook }
}
test('selected history and independently read current create a durable exact original; ACK is not an automatic draft read', async () => {
  const { workspace, port, hook } = await prepared()
  vi.mocked(port.create).mockImplementationOnce(async (body, key) => {
    const command = readRestoreCreateCommand((await restoreCreateCommandStore.load(workspace))[key], workspace)
    expect(command.body).toEqual(body); expect(body).toEqual(createBody); expect(command.ack).toBeNull()
    throw new Error('Synthetic lost ACK after actual server commit')
  })
  await act(() => hook.result.current.create(createBody.reason))
  const original = hook.result.current.commands[0]; expect(original.ack).toBeNull(); expect(port.draft).not.toHaveBeenCalled()
  await act(() => hook.result.current.prepare(publicationDraft.source_ref)); await act(() => hook.result.current.create(createBody.reason))
  expect(port.create).toHaveBeenCalledTimes(1)
  await act(() => hook.result.current.execute(original)); expect(vi.mocked(port.create).mock.calls[1]).toEqual(vi.mocked(port.create).mock.calls[0])
  expect(hook.result.current.commands[0].ack).toEqual(createAck); expect(hook.result.current.draft).toBeNull()
  await act(() => hook.result.current.read(createAck.candidate.draft_id)); expect(hook.result.current.draft).toEqual(publicationDraft)
})
test('failed initial IDB save stops before HTTP, retains the entire reason, and memory recovery only saves the original', async () => {
  const { workspace, port, hook } = await prepared()
  vi.spyOn(restoreCreateCommandStore, 'save').mockRejectedValueOnce(new Error('Synthetic quota'))
  await act(() => hook.result.current.create(createBody.reason))
  expect(port.create).not.toHaveBeenCalled(); expect(hook.result.current.pendingMemory).toBe(true)
  await act(() => hook.result.current.saveMemory())
  expect(hook.result.current.pendingMemory).toBe(false); expect(hook.result.current.commands[0].body).toEqual(createBody)
  expect(readRestoreCreateCommand(Object.values(await restoreCreateCommandStore.load(workspace))[0], workspace).ack).toBeNull()
  expect(port.create).not.toHaveBeenCalled()
})
test('received ACK stays isolated across unmount and another session until the original session explicitly saves it', async () => {
  const { workspace, port, hook } = await prepared(), save = restoreCreateCommandStore.save.bind(restoreCreateCommandStore)
  vi.spyOn(restoreCreateCommandStore, 'save').mockImplementation(async (...args) => { if (JSON.parse(args[2]).ack) throw new Error('Synthetic ACK transaction abort'); return save(...args) })
  await act(() => hook.result.current.create(createBody.reason)); expect(hook.result.current.pendingMemory).toBe(true); hook.unmount(); vi.restoreAllMocks()
  vi.mocked(port.session).mockResolvedValue({ ...reviewSession(workspace), csrf_token: 'other-session' })
  const other = renderHook(() => useRestoreDrafts(workspace, false, base.metadata.id, port))
  await waitFor(() => expect(other.result.current.ready).toBe(true)); expect(other.result.current.canSaveMemory).toBe(false)
  await act(() => other.result.current.saveMemory()); expect(other.result.current.pendingMemory).toBe(true)
  vi.mocked(port.session).mockResolvedValue(reviewSession(workspace)); await act(() => other.result.current.refresh()); await act(() => other.result.current.saveMemory())
  expect(other.result.current.commands[0].ack).toEqual(createAck); expect(port.create).toHaveBeenCalledTimes(1)
})
test('previous-page Restore records remain read-only even with a current valid author session', async () => {
  const { workspace, port } = fixture(), command = makeRestoreCreateCommand(workspace, getSessionGeneration(), createBody)
  command.origin.page_id = 'page_previous'; await persistRestoreCreateCommand(command)
  const hook = renderHook(() => useRestoreDrafts(workspace, false, base.metadata.id, port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.execute(command)); expect(port.create).not.toHaveBeenCalled(); expect(hook.result.current.canReplay(command)).toBe(false)
  await act(() => hook.result.current.prepare(publicationDraft.source_ref)); await act(() => hook.result.current.create(createBody.reason))
  expect(port.create).not.toHaveBeenCalled(); expect(hook.result.current.commands).toEqual([command])
})
test.each(['body', 'hash', 'current_id', 'not_historical'] as const)('bad selected history/current is rejected before create: %s', async fault => {
  const { workspace, port } = fixture()
  if (fault === 'body') vi.mocked(port.source).mockResolvedValueOnce({ ...base, body_markdown: 'bad bytes' })
  if (fault === 'hash') vi.mocked(port.source).mockResolvedValueOnce({ ...base, metadata: { ...base.metadata, title: 'wrong metadata' } })
  if (fault === 'current_id') vi.mocked(port.current).mockResolvedValueOnce({ ...publicationDraft.base_ref, id: 'block_other' })
  if (fault === 'not_historical') vi.mocked(port.current).mockResolvedValueOnce(publicationDraft.source_ref)
  const hook = renderHook(() => useRestoreDrafts(workspace, false, base.metadata.id, port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true)); await act(() => hook.result.current.prepare(publicationDraft.source_ref))
  expect(hook.result.current.basis).toBeNull(); await act(() => hook.result.current.create(createBody.reason)); expect(port.create).not.toHaveBeenCalled()
})
test('412 preserves exact old source/current and a policy pause hides all already read protected payload', async () => {
  const { workspace, port } = fixture(); vi.mocked(port.create).mockRejectedValueOnce(new ApiError(412, 'Synthetic current race'))
  const hook = renderHook(({ paused }) => useRestoreDrafts(workspace, paused, base.metadata.id, port), { initialProps: { paused: false } })
  await waitFor(() => expect(hook.result.current.ready).toBe(true)); await act(() => hook.result.current.prepare(publicationDraft.source_ref)); await act(() => hook.result.current.create(createBody.reason))
  expect(hook.result.current.commands[0].rejection?.status).toBe(412); expect(hook.result.current.commands[0].body).toEqual(createBody)
  hook.rerender({ paused: true }); expect(hook.result.current.ready).toBe(false); expect(hook.result.current.basis).toBeNull(); expect(hook.result.current.commands).toEqual([])
  expect(Object.values(await restoreCreateCommandStore.load(workspace))).toHaveLength(1)
})
test('known create ACK cannot be relabeled by a different candidate hash, reason or owner on later GET', async () => {
  const { port, hook } = await prepared(); await act(() => hook.result.current.create(createBody.reason))
  for (const value of [{ ...publicationDraft, candidate: { ...publicationDraft.candidate, candidate_sha256: 'c'.repeat(64) } }, { ...publicationDraft, reason: 'changed' }, { ...publicationDraft, owner: 'authoring_edit' }]) {
    vi.mocked(port.draft).mockResolvedValueOnce(value as typeof publicationDraft)
    await act(() => hook.result.current.read(createAck.candidate.draft_id)); expect(hook.result.current.draft).toBeNull()
  }
})

test('a current block scope cannot replay another block or workspace original', async () => {
  const { workspace, port, hook } = await prepared()
  const foreign = makeRestoreCreateCommand(workspace, getSessionGeneration(), { ...createBody,
    source_ref: { ...createBody.source_ref, id: 'block_other' }, expected_current_ref: { ...createBody.expected_current_ref, id: 'block_other' } })
  const otherWorkspace = makeRestoreCreateCommand('workspace_other', getSessionGeneration(), createBody)
  for (const command of [foreign, otherWorkspace]) {
    expect(hook.result.current.canReplay(command)).toBe(false)
    await act(() => hook.result.current.execute(command))
  }
  expect(port.create).not.toHaveBeenCalled(); expect(await restoreCreateCommandStore.load(workspace)).toEqual({})
})
