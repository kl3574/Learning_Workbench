import 'fake-indexeddb/auto'
import { afterEach, expect, test } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { singlePublicationFixture } from './singlePublicationFixtures'
import { checkedSingleBasis, singleAcknowledgedCodes, singleSnapshot } from './singlePublicationSchema'
import { decodeSinglePublicationCommand, makeSinglePublicationCommand, persistSinglePublicationCommand, readSinglePublicationCommand, sameSinglePublicationActorPage } from './singlePublicationCommands'

const stores: DraftStore[] = []
afterEach(async () => { await Promise.all(stores.splice(0).map(store => store.close())) })
test('unknown new object has current null; durable four fields and original r1 ACK never acquire current or another candidate', async () => {
  const f = singlePublicationFixture(), name = `singlepub_${crypto.randomUUID()}`, store = new DraftStore({ name }); stores.push(store)
  const command = makeSinglePublicationCommand(f.workspace, 3, f.basis(), [0, 1])
  expect(command.basis.target).toEqual({ entity: 'block', revision: 1, current: null })
  expect(command.body).toEqual({ expected_revision: 1, expected_content_sha256: f.draft.candidate.candidate_sha256, review_receipt_id: f.receipt.id, acknowledged_warning_codes: ['SOURCE_CONFIRM'] })
  expect(command.body.acknowledged_warning_codes).not.toContain('AUTHORING_REVIEW_NOT_RUN')
  await persistSinglePublicationCommand(command, store); await store.close()
  const reopened = new DraftStore({ name }); stores.push(reopened)
  expect(readSinglePublicationCommand((await reopened.load(f.workspace))[command.command_id], f.workspace)).toEqual(command)
  const acknowledged = { ...command, ack: f.ack }; await persistSinglePublicationCommand(acknowledged, reopened)
  expect(await persistSinglePublicationCommand(command, reopened)).toEqual(acknowledged)
  for (const changed of [{ ...acknowledged, ack: { ...f.ack, id: 'block_other' } }, { ...command, body: { ...command.body, review_receipt_id: 'review_other' } }, { ...command, origin: { ...command.origin, access_generation: 4 } }]) await expect(persistSinglePublicationCommand(changed, reopened)).rejects.toThrow()
  expect(sameSinglePublicationActorPage(command, 3)).toBe(true); expect(sameSinglePublicationActorPage(command, 4)).toBe(false)
  expect(sameSinglePublicationActorPage({ ...command, origin: { ...command.origin, page_id: 'page_previous' } }, 3)).toBe(false)
  expect(f.ack.sha256).not.toEqual(command.basis.candidate.candidate_sha256)
})
test('all warning instances, actual numeric pass and explicit decisions are required; a newer pending check cannot be skipped', () => {
  const f = singlePublicationFixture()
  for (const selected of [[], [0], [1], [0, 1, 1], [0, 1, 2]]) expect(() => singleAcknowledgedCodes(f.basis(), selected)).toThrow()
  const bad = [() => { f.receipt.mathematical = 'NOT_APPLICABLE' }, () => { f.receipt.decision_reason = '' }, () => { f.numeric.result!.exit_code = 1 }, () => { f.numeric.result!.started_at = null }, () => { f.numeric.result!.assertions[0].actual = null }, () => { f.numeric.job!.status = 'running' }, () => { f.numeric.result!.operation_sha256 = 'b'.repeat(64) }, () => { f.numeric.candidate = { ...f.numeric.candidate, draft_id: 'draft_other' } }]
  for (const fault of bad) { const before = structuredClone({ receipt: f.receipt, numeric: f.numeric }); fault(); expect(() => f.basis()).toThrow(); Object.assign(f.receipt, before.receipt); Object.assign(f.numeric, before.numeric) }
  const basis = f.basis(), pending = { ...f.numeric, id: 'check_newer', revision: 1, decision: 'pending' as const, job: null, job_revision: null, result: null }
  basis.snapshot.numeric_check_ids.push(pending.id); basis.checks.push(pending); basis.warnings.push(...pending.warnings)
  expect(() => checkedSingleBasis(basis)).toThrow()
})
test('single strict basis rejects wrong owners, source/body drift, extra request fields and non-r1 ACK', () => {
  const f = singlePublicationFixture(), command = makeSinglePublicationCommand(f.workspace, 0, f.basis(), [0, 1])
  for (const bad of [{ ...command, extra: true }, { ...command, body: { ...command.body, expected_review_revision: 2 } }, { ...command, basis: { ...command.basis, owner: 'authoring_group' } }, { ...command, basis: { ...command.basis, target: { entity: 'block', revision: 1, current: f.ack } } }, { ...command, ack: { ...f.ack, revision: 2 } }, { ...command, ack: { ...f.ack, entity: 'lesson' } }]) expect(() => decodeSinglePublicationCommand(JSON.stringify(bad), f.workspace)).toThrow()
  expect(() => singleSnapshot({ ...f.draft, payload: { ...f.draft.payload, body_markdown: `${f.draft.payload.body_markdown} ` } })).toThrow()
  expect(() => singleSnapshot({ ...f.draft, state: 'published', published_ref: null })).toThrow()
  expect(() => checkedSingleBasis({ ...f.basis(), generation: { ...f.generation, summary: { ...f.generation.summary, id: 'job_other' } } })).toThrow()
})
test('conflicting immutable journal records stay retained and denied; write guard denies before mutation', async () => {
  const f = singlePublicationFixture(), store = new DraftStore({ name: `singlepub_${crypto.randomUUID()}` }); stores.push(store)
  const command = makeSinglePublicationCommand(f.workspace, 0, f.basis(), [0, 1])
  await expect(persistSinglePublicationCommand(command, store, { allowed: () => false, signal: new AbortController().signal })).rejects.toThrow(); expect(await store.load(f.workspace)).toEqual({})
  await persistSinglePublicationCommand(command, store)
  await store.save(f.workspace, command.command_id, JSON.stringify({ ...command, basis: { ...command.basis, review: { ...f.receipt, decision_reason: 'different' } } }), 0)
  const before = (await store.load(f.workspace))[command.command_id]; expect(before.conflicts).toHaveLength(1)
  await expect(persistSinglePublicationCommand(command, store)).rejects.toThrow(); expect((await store.load(f.workspace))[command.command_id]).toEqual(before)
})
