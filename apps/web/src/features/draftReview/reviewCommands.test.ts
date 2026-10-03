import 'fake-indexeddb/auto'
import { afterEach, expect, test } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { decodeReviewCommand, makeReviewCommand, persistReviewCommand, readReviewCommand, sameReviewActorPage, type ReviewCommand } from './reviewCommands'
import { reviewReceipt } from './reviewSchema'
import { machineReceipt, reviewCandidate } from './reviewFixtures'

const stores: DraftStore[] = []
afterEach(async () => { await Promise.all(stores.splice(0).map(store => store.close())) })
function setup() {
  const workspace = `workspace_${crypto.randomUUID()}`, name = `review_commands_${crypto.randomUUID()}`
  const store = new DraftStore({ name }); stores.push(store)
  const command = makeReviewCommand(workspace, 4, { kind: 'create', candidate: reviewCandidate,
    body: { expected_revision: 1, checks: ['structure'], reviewer_note: 'Synthetic original exact text' } })
  return { workspace, name, store, command }
}

test('strict receipt requires explicit revision, exact candidate and no unexecuted teaching PASS', () => {
  const { revision: _, ...missing } = machineReceipt
  expect(() => reviewReceipt(missing, machineReceipt.id)).toThrow()
  expect(() => reviewReceipt({ ...machineReceipt, independent_pedagogy: 'PASS' }, machineReceipt.id)).toThrow()
  expect(() => reviewReceipt(machineReceipt, machineReceipt.id, { ...reviewCandidate, candidate_sha256: 'b'.repeat(64) })).toThrow()
  expect(() => reviewReceipt({ ...machineReceipt, extra: true }, machineReceipt.id)).toThrow()
})

test('real IndexedDB preserves exact original command across reopening without granting a new page replay', async () => {
  const { workspace, name, store, command } = setup()
  await persistReviewCommand(command, store)
  await store.close()
  const reopened = new DraftStore({ name }); stores.push(reopened)
  const restored = readReviewCommand((await reopened.load(workspace))[command.command_id], workspace)
  expect(restored).toEqual(command)
  expect(sameReviewActorPage(restored, 4)).toBe(true)
  expect(sameReviewActorPage(restored, 5)).toBe(false)
  expect(sameReviewActorPage({ ...restored, origin: { ...restored.origin, page_id: 'page_other' } }, 4)).toBe(false)
})

test('candidate basis and complete decision ACK relations are checked beyond wire schema', () => {
  const { workspace, command } = setup()
  expect(() => decodeReviewCommand(JSON.stringify({ ...command, body: { ...command.body, expected_revision: 2 } }), workspace)).toThrow()
  expect(() => decodeReviewCommand(JSON.stringify({ ...command, body: { ...command.body, checks: ['structure', 'structure'] } }), workspace)).toThrow()
  const decision = makeReviewCommand(workspace, 4, { kind: 'decision', review_id: machineReceipt.id, candidate: reviewCandidate,
    body: { expected_revision: 1, candidate_sha256: reviewCandidate.candidate_sha256, mathematical: 'REJECTED', sources: 'REJECTED', reason: 'Synthetic rejection', evidence_artifact_ids: [] } })
  const ack = { ...machineReceipt, revision: 2, mathematical: 'REJECTED', sources: 'REJECTED', decision_reason: 'Synthetic rejection' }
  expect(decodeReviewCommand(JSON.stringify({ ...decision, ack }), workspace).ack).toEqual(ack)
  for (const bad of [{ ...ack, revision: 3 }, { ...ack, mathematical: 'APPROVED' }, { ...ack, decision_reason: 'Changed' }, { ...ack, candidate: { ...reviewCandidate, draft_id: 'draft_other' } }]) {
    expect(() => decodeReviewCommand(JSON.stringify({ ...decision, ack: bad }), workspace)).toThrow()
  }
})

test('acknowledgement is durable and cannot be replaced by pending state or another original request', async () => {
  const { workspace, store, command } = setup()
  const confirmed = { ...command, ack: { id: machineReceipt.id, status: 'queued' } } as ReviewCommand
  await persistReviewCommand(command, store); await persistReviewCommand(confirmed, store)
  expect(await persistReviewCommand(command, store)).toEqual(confirmed)
  await expect(persistReviewCommand({ ...command, body: { ...command.body, reviewer_note: 'Changed request' } } as ReviewCommand, store)).rejects.toThrow()
  expect(readReviewCommand((await store.load(workspace))[command.command_id], workspace)).toEqual(confirmed)
})

test('conflicting immutable body is retained and blocks automatic conflict resolution', async () => {
  const { workspace, store, command } = setup()
  await persistReviewCommand(command, store)
  const different = { ...command, candidate: { ...reviewCandidate, candidate_sha256: 'b'.repeat(64) } }
  await store.save(workspace, command.command_id, JSON.stringify(different), 0)
  const original = (await store.load(workspace))[command.command_id]
  expect(original.conflicts).toHaveLength(1)
  expect(() => readReviewCommand(original, workspace)).toThrow()
  await expect(persistReviewCommand(command, store)).rejects.toThrow()
  expect((await store.load(workspace))[command.command_id]).toEqual(original)
})

test('revoked write guard prevents actual IDB command admission', async () => {
  const { workspace, store, command } = setup(), controller = new AbortController()
  controller.abort()
  await expect(persistReviewCommand(command, store, { allowed: () => true, signal: controller.signal })).rejects.toThrow()
  expect(await store.load(workspace)).toEqual({})
})
