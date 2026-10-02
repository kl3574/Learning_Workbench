import 'fake-indexeddb/auto'
import { afterEach, expect, test, vi } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { numericBody, numericDecision, numericDecisionReceipt, numericPreview } from './restoreNumericFixtures'
import { decodeRestoreNumericCommand, makeRestoreNumericCommand, persistRestoreNumericCommand, readRestoreNumericCommand, sameRestoreNumericActorPage, type RestoreNumericCommand } from './restoreNumericStore'
import { discardRestoreNumericMemory, pendingRestoreNumericMemory, recoverableRestoreNumericMemory, releaseRestoreNumericMemory, retainRestoreNumericMemory } from './restoreNumericMemory'

const stores: DraftStore[] = [], workspaces: string[] = []
afterEach(async () => {
  vi.restoreAllMocks()
  workspaces.splice(0).forEach(workspace => discardRestoreNumericMemory(workspace))
  await Promise.all(stores.splice(0).map(store => store.close()))
})
function fixture(kind: 'preview' | 'decision' = 'preview') {
  const workspace = `workspace_${crypto.randomUUID()}`, name = `numeric_${crypto.randomUUID()}`
  workspaces.push(workspace)
  const store = new DraftStore({ name }); stores.push(store)
  const input = kind === 'preview' ? { kind, draft_id: numericBody.candidate.draft_id, body: numericBody }
    : { kind, draft_id: numericBody.candidate.draft_id, check_id: numericPreview.id, body: numericDecision }
  const command = makeRestoreNumericCommand(workspace, 'actor_original', 3, input)
  const acknowledged = decodeRestoreNumericCommand(JSON.stringify({ ...command, ack: kind === 'preview' ? numericPreview : numericDecisionReceipt }), workspace)
  return { workspace, name, store, command, acknowledged }
}
test.each(['preview', 'decision'] as const)('%s persists its original route identity, body and immutable ACK through actual IDB reopening', async kind => {
  const f = fixture(kind)
  await persistRestoreNumericCommand(f.command, f.store)
  await f.store.close()
  const reopened = new DraftStore({ name: f.name }); stores.push(reopened)
  expect(readRestoreNumericCommand((await reopened.load(f.workspace))[f.command.command_id], f.workspace)).toEqual(f.command)
  await persistRestoreNumericCommand(f.acknowledged, reopened)
  expect(await persistRestoreNumericCommand(f.command, reopened)).toEqual(f.acknowledged)
  const before = await reopened.load(f.workspace)
  const other = structuredClone(f.acknowledged)
  if (other.kind === 'preview') other.ack!.id = 'numeric_different'
  else other.ack!.job!.id = 'job_different'
  await expect(persistRestoreNumericCommand(other, reopened)).rejects.toThrow()
  expect(await reopened.load(f.workspace)).toEqual(before)
  const text = before[f.command.command_id].text
  for (const forbidden of ['csrf_token', 'cookie', 'authorization', 'session_secret']) expect(text).not.toContain(forbidden)
})
test.each(['owner', 'workspace', 'actor', 'page', 'generation', 'kind', 'body', 'ack', 'extra', 'old_journal'] as const)('strict journal rejects a %s replacement and keeps original bytes', async fault => {
  const f = fixture()
  await persistRestoreNumericCommand(f.acknowledged, f.store)
  const before = await f.store.load(f.workspace), value = structuredClone(f.acknowledged)
  if (fault === 'owner') Object.assign(value, { owner: 'authoring_single' })
  if (fault === 'workspace') value.workspace_id = 'workspace_other'
  if (fault === 'actor') value.origin.actor_session_id = 'actor_other'
  if (fault === 'page') value.origin.page_id = 'page_other'
  if (fault === 'generation') value.origin.access_generation++
  if (fault === 'kind') Object.assign(value, { kind: 'numeric_preview' })
  if (fault === 'body' && value.kind === 'preview') value.body.material.reason += ' altered'
  if (fault === 'ack' && value.kind === 'preview') value.ack!.candidate.candidate_sha256 = '0'.repeat(64)
  if (fault === 'extra') Object.assign(value, { csrf_token: 'synthetic-forbidden' })
  if (fault === 'old_journal') Object.assign(value, { origin: { page_id: value.origin.page_id, access_generation: 3 } })
  if (fault === 'workspace') expect(() => decodeRestoreNumericCommand(JSON.stringify(value), f.workspace)).toThrow()
  else await expect(persistRestoreNumericCommand(value, f.store)).rejects.toThrow()
  expect(await f.store.load(f.workspace)).toEqual(before)
})
test('original owner access admission never inherits a prior page, actor or access generation', () => {
  const f = fixture()
  expect(sameRestoreNumericActorPage(f.command, 'actor_original', 3)).toBe(true)
  expect(sameRestoreNumericActorPage(f.command, 'actor_other', 3)).toBe(false)
  expect(sameRestoreNumericActorPage(f.command, 'actor_original', 4)).toBe(false)
  expect(sameRestoreNumericActorPage({ ...f.command, origin: { ...f.command.origin, page_id: 'page_previous' } }, 'actor_original', 3)).toBe(false)
})
test('two actual IndexedDB writers keep both incompatible bodies and refuse reconciliation', async () => {
  const f = fixture()
  await persistRestoreNumericCommand(f.command, f.store)
  const different = structuredClone(f.command)
  if (different.kind !== 'preview') throw new Error('fixture')
  different.body.material.reason += ' changed'
  const conflict = await f.store.save(f.workspace, f.command.command_id, JSON.stringify(different), 0)
  expect(conflict.kind).toBe('conflict')
  const before = await f.store.load(f.workspace)
  expect(before[f.command.command_id].conflicts).toHaveLength(1)
  expect(() => readRestoreNumericCommand(before[f.command.command_id], f.workspace)).toThrow()
  await expect(persistRestoreNumericCommand(f.command, f.store)).rejects.toThrow()
  expect(await f.store.load(f.workspace)).toEqual(before)
})
test.each(['preview', 'decision'] as const)('%s ACK aborted after IDB put remains only in isolated page memory, then explicitly persists', async kind => {
  const f = fixture(kind)
  await persistRestoreNumericCommand(f.command, f.store)
  retainRestoreNumericMemory(f.acknowledged, 'original-session-handle')
  const prototype = IDBObjectStore.prototype, put = prototype.put
  vi.spyOn(prototype, 'put').mockImplementationOnce(function (this: IDBObjectStore, ...args: Parameters<IDBObjectStore['put']>) {
    const request = put.apply(this, args); this.transaction.abort(); return request
  })
  await expect(persistRestoreNumericCommand(f.acknowledged, f.store)).rejects.toThrow()
  expect(readRestoreNumericCommand((await f.store.load(f.workspace))[f.command.command_id], f.workspace)).toEqual(f.command)
  expect(recoverableRestoreNumericMemory(f.workspace, 'another-session')).toEqual([])
  expect(recoverableRestoreNumericMemory(f.workspace, 'original-session-handle')).toEqual([f.acknowledged])
  expect(pendingRestoreNumericMemory(f.workspace, f.command.draft_id)).toBe(true)
  const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event); expect(event.defaultPrevented).toBe(true)
  releaseRestoreNumericMemory(f.command.command_id, 'another-session')
  expect(pendingRestoreNumericMemory(f.workspace)).toBe(true)
  const recovered = recoverableRestoreNumericMemory(f.workspace, 'original-session-handle')[0]
  await persistRestoreNumericCommand(recovered, f.store)
  releaseRestoreNumericMemory(f.command.command_id, 'original-session-handle')
  expect(pendingRestoreNumericMemory(f.workspace)).toBe(false)
  expect(readRestoreNumericCommand((await f.store.load(f.workspace))[f.command.command_id], f.workspace)).toEqual(f.acknowledged)
})
test('revocation while loading blocks a later transaction without changing original pending command', async () => {
  const f = fixture(), abort = new AbortController()
  await persistRestoreNumericCommand(f.command, f.store)
  const load = f.store.load.bind(f.store), before = await load(f.workspace)
  vi.spyOn(f.store, 'load').mockImplementationOnce(async workspace => { const value = await load(workspace); abort.abort(); return value })
  await expect(persistRestoreNumericCommand(f.acknowledged, f.store, { allowed: () => !abort.signal.aborted, signal: abort.signal })).rejects.toThrow()
  expect(await load(f.workspace)).toEqual(before)
})
test('memory preserves a received ACK against a late pending value and refuses conflicting receipts', () => {
  const f = fixture('decision')
  retainRestoreNumericMemory(f.acknowledged, 'session_original')
  retainRestoreNumericMemory(f.command, 'session_original')
  const receipt = recoverableRestoreNumericMemory(f.workspace, 'session_original')[0]
  expect(receipt).toEqual(f.acknowledged)
  expect(() => retainRestoreNumericMemory(f.command, 'session_other')).toThrow()
  const different = structuredClone(f.acknowledged) as RestoreNumericCommand
  if (different.kind !== 'decision') throw new Error('fixture')
  different.ack!.job!.id = 'job_other'
  expect(() => retainRestoreNumericMemory(different, 'session_original')).toThrow()
  expect(recoverableRestoreNumericMemory(f.workspace, 'session_original')).toEqual([f.acknowledged])
})
