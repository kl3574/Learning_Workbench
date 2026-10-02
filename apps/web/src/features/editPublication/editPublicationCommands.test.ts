import 'fake-indexeddb/auto'
import { afterEach, expect, test } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { publicationDraft, publicationReceipt, publicationRef, base } from './editPublicationFixtures'
import { prepareEditBasis } from './editPublicationSchema'
import { decodeEditPublicationCommand, makeEditPublicationCommand, persistEditPublicationCommand, readEditPublicationCommand, sameEditPublicationActorPage } from './editPublicationCommands'
import { canonical, digest } from '../retrieval/retrievalModel'

const stores: DraftStore[] = []
afterEach(async () => { await Promise.all(stores.splice(0).map(value => value.close())) })
test('existing exact dependency refs and order stay bound to the original base and publication journal', async () => {
  const refs = ['second', 'first'].map(id => ({ entity: 'block' as const, id: `synthetic_${id}`, revision: 1, sha256: 'a'.repeat(64) }))
  const source = { ...base, metadata: { ...base.metadata, depends_on: refs } }, snapshot = structuredClone(publicationDraft)
  snapshot.base_ref.sha256 = digest(canonical(source.metadata)); snapshot.payload.base_ref = snapshot.base_ref
  snapshot.candidate.candidate_sha256 = digest(canonical(snapshot.payload))
  const review = { ...publicationReceipt, candidate: snapshot.candidate }
  const basis = prepareEditBasis(snapshot, source, review), workspace = `workspace_${crypto.randomUUID()}`
  const command = makeEditPublicationCommand(workspace, 0, basis, [0, 1])
  const store = new DraftStore({ name: `publication_${crypto.randomUUID()}` }); stores.push(store)
  await persistEditPublicationCommand(command, store)
  expect(readEditPublicationCommand((await store.load(workspace))[command.command_id], workspace)).toEqual(command)
  expect(command.basis.base.metadata.depends_on).toEqual(refs)
  expect(Object.keys(command.body).sort()).toEqual(['acknowledged_warning_codes', 'expected_content_sha256', 'expected_revision', 'review_receipt_id'])
  const reordered = { ...source, metadata: { ...source.metadata, depends_on: [...refs].reverse() } }
  expect(() => prepareEditBasis(snapshot, reordered, review)).toThrow()
  expect(() => prepareEditBasis(snapshot, { ...source, metadata: { ...source.metadata, concepts: ['synthetic_concept'] } }, review)).toThrow()
})
test('original four-field publication command survives IndexedDB reopening and cannot acquire a different request or ACK', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`, name = `publication_${crypto.randomUUID()}`
  const store = new DraftStore({ name }); stores.push(store)
  const basis = prepareEditBasis(publicationDraft, base, publicationReceipt)
  const command = makeEditPublicationCommand(workspace, 3, basis, [0, 1])
  expect(command.body).toEqual({ expected_revision: 3, expected_content_sha256: publicationDraft.candidate.candidate_sha256, review_receipt_id: publicationReceipt.id, acknowledged_warning_codes: ['SOURCE_CONFIRM'] })
  await persistEditPublicationCommand(command, store)
  await store.close()
  const reopened = new DraftStore({ name }); stores.push(reopened)
  expect(readEditPublicationCommand((await reopened.load(workspace))[command.command_id], workspace)).toEqual(command)
  const acknowledged = { ...command, ack: publicationRef }
  await persistEditPublicationCommand(acknowledged, reopened)
  expect(await persistEditPublicationCommand(command, reopened)).toEqual(acknowledged)
  await expect(persistEditPublicationCommand({ ...command, body: { ...command.body, review_receipt_id: 'review_other' } }, reopened)).rejects.toThrow()
  await expect(persistEditPublicationCommand({ ...acknowledged, ack: { ...publicationRef, revision: 1 } }, reopened)).rejects.toThrow()
  expect(sameEditPublicationActorPage(command, 3)).toBe(true)
  expect(sameEditPublicationActorPage(command, 4)).toBe(false)
  expect(sameEditPublicationActorPage({ ...command, origin: { ...command.origin, page_id: 'page_previous' } }, 3)).toBe(false)
})

test('conflicting immutable body stays in real IndexedDB and prevents command admission', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`, store = new DraftStore({ name: `publication_${crypto.randomUUID()}` }); stores.push(store)
  const command = makeEditPublicationCommand(workspace, 1, prepareEditBasis(publicationDraft, base, publicationReceipt), [0, 1])
  await persistEditPublicationCommand(command, store)
  const changed = { ...command, basis: { ...command.basis, review: { ...command.basis.review, decision_reason: 'Synthetic conflicting basis' } } }
  await store.save(workspace, command.command_id, JSON.stringify(changed), 0)
  const before = (await store.load(workspace))[command.command_id]
  expect(before.conflicts).toHaveLength(1)
  await expect(persistEditPublicationCommand(command, store)).rejects.toThrow()
  expect((await store.load(workspace))[command.command_id]).toEqual(before)
})

test('warning instances, explicit human decisions, metadata identity and strict original body cannot be bypassed', () => {
  const basis = prepareEditBasis(publicationDraft, base, publicationReceipt)
  for (const selected of [[], [0], [1], [0, 1, 1], [0, 1, 2]]) expect(() => makeEditPublicationCommand('workspace_synthetic', 0, basis, selected)).toThrow()
  for (const receipt of [{ ...publicationReceipt, mathematical: 'NOT_RUN' }, { ...publicationReceipt, sources: 'NOT_RUN' }, { ...publicationReceipt, decision_reason: '' }, { ...publicationReceipt, candidate: { ...publicationReceipt.candidate, draft_id: 'draft_other' } }]) expect(() => prepareEditBasis(publicationDraft, base, receipt as typeof publicationReceipt)).toThrow()
  const invalidHash = { ...publicationDraft, candidate: { ...publicationDraft.candidate, candidate_sha256: 'b'.repeat(64) } }
  expect(() => prepareEditBasis(invalidHash, base, publicationReceipt)).toThrow()
  expect(() => prepareEditBasis({ ...publicationDraft, warnings: [{ code: 'BAD_SOURCE', message: 'Synthetic error', locator: null, severity: 'error' }] }, base, publicationReceipt)).not.toThrow()
  const blocked = prepareEditBasis({ ...publicationDraft, warnings: [{ code: 'BAD_SOURCE', message: 'Synthetic error', locator: null, severity: 'error' }] }, base, publicationReceipt)
  expect(() => makeEditPublicationCommand('workspace_synthetic', 0, blocked, [])).toThrow()
  const command = makeEditPublicationCommand('workspace_synthetic', 0, basis, [0, 1])
  for (const bad of [{ ...command, extra: true }, { ...command, body: { ...command.body, expected_review_revision: 2 } }, { ...command, body: { ...command.body, acknowledged_warning_codes: ['SOURCE_CONFIRM', 'SOURCE_CONFIRM'] } }]) expect(() => decodeEditPublicationCommand(JSON.stringify(bad), 'workspace_synthetic')).toThrow()
})


test('edit basis is owner-specific, binds full base metadata/body and predicts base+1 independently of draft revision', () => {
  expect(publicationDraft.candidate.draft_revision).toBe(3); expect(publicationRef.revision).toBe(2)
  expect(publicationRef.sha256).not.toBe(publicationDraft.candidate.candidate_sha256)
  for (const bad of [{ ...base, body_markdown: 'damaged' }, { ...base, metadata: { ...base.metadata, title: 'damaged' } }]) expect(() => prepareEditBasis(publicationDraft, bad, publicationReceipt)).toThrow()
  const command = makeEditPublicationCommand('workspace_synthetic', 0, prepareEditBasis(publicationDraft, base, publicationReceipt), [0, 1])
  for (const bad of [{ ...command, basis: { ...command.basis, owner: 'import' } }, { ...command, basis: { ...command.basis, snapshot: { ...publicationDraft, state: 'published' } } }, { ...command, basis: { ...command.basis, target: { ...command.basis.target, object_revision: 3 } } }]) expect(() => decodeEditPublicationCommand(JSON.stringify(bad), 'workspace_synthetic')).toThrow()
})
