import 'fake-indexeddb/auto'
import { afterEach, expect, test } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { publicationDraft, publicationReceipt, publicationRef, base } from './restoreFixtures'
import { prepareRestoreBasis } from './restorePublicationSchema'
import { decodeRestorePublicationCommand, makeRestorePublicationCommand, persistRestorePublicationCommand, readRestorePublicationCommand, sameRestorePublicationActorPage } from './restorePublicationCommands'

const stores: DraftStore[] = []
afterEach(async () => { await Promise.all(stores.splice(0).map(value => value.close())) })
test('original four-field publication command survives IndexedDB reopening and cannot acquire a different request or ACK', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`, name = `publication_${crypto.randomUUID()}`
  const store = new DraftStore({ name }); stores.push(store)
  const basis = prepareRestoreBasis(publicationDraft, base, publicationReceipt)
  const command = makeRestorePublicationCommand(workspace, 3, basis, [0, 1])
  expect(command.body).toEqual({ expected_revision: 1, expected_content_sha256: publicationDraft.candidate.candidate_sha256, review_receipt_id: publicationReceipt.id, acknowledged_warning_codes: ['SOURCE_CONFIRM'] })
  await persistRestorePublicationCommand(command, store)
  await store.close()
  const reopened = new DraftStore({ name }); stores.push(reopened)
  expect(readRestorePublicationCommand((await reopened.load(workspace))[command.command_id], workspace)).toEqual(command)
  const acknowledged = { ...command, ack: publicationRef }
  await persistRestorePublicationCommand(acknowledged, reopened)
  expect(await persistRestorePublicationCommand(command, reopened)).toEqual(acknowledged)
  await expect(persistRestorePublicationCommand({ ...command, body: { ...command.body, review_receipt_id: 'review_other' } }, reopened)).rejects.toThrow()
  await expect(persistRestorePublicationCommand({ ...acknowledged, ack: { ...publicationRef, revision: 1 } }, reopened)).rejects.toThrow()
  expect(sameRestorePublicationActorPage(command, 3)).toBe(true)
  expect(sameRestorePublicationActorPage(command, 4)).toBe(false)
  expect(sameRestorePublicationActorPage({ ...command, origin: { ...command.origin, page_id: 'page_previous' } }, 3)).toBe(false)
})

test('conflicting immutable body stays in real IndexedDB and prevents command admission', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`, store = new DraftStore({ name: `publication_${crypto.randomUUID()}` }); stores.push(store)
  const command = makeRestorePublicationCommand(workspace, 1, prepareRestoreBasis(publicationDraft, base, publicationReceipt), [0, 1])
  await persistRestorePublicationCommand(command, store)
  const changed = { ...command, basis: { ...command.basis, review: { ...command.basis.review, decision_reason: 'Synthetic conflicting basis' } } }
  await store.save(workspace, command.command_id, JSON.stringify(changed), 0)
  const before = (await store.load(workspace))[command.command_id]
  expect(before.conflicts).toHaveLength(1)
  await expect(persistRestorePublicationCommand(command, store)).rejects.toThrow()
  expect((await store.load(workspace))[command.command_id]).toEqual(before)
})

test('warning instances, explicit human decisions, metadata identity and strict original body cannot be bypassed', () => {
  const basis = prepareRestoreBasis(publicationDraft, base, publicationReceipt)
  for (const selected of [[], [0], [1], [0, 1, 1], [0, 1, 2]]) expect(() => makeRestorePublicationCommand('workspace_synthetic', 0, basis, selected)).toThrow()
  for (const receipt of [{ ...publicationReceipt, mathematical: 'NOT_RUN' }, { ...publicationReceipt, sources: 'NOT_RUN' }, { ...publicationReceipt, decision_reason: '' }, { ...publicationReceipt, candidate: { ...publicationReceipt.candidate, draft_id: 'draft_other' } }]) expect(() => prepareRestoreBasis(publicationDraft, base, receipt as typeof publicationReceipt)).toThrow()
  const invalidHash = { ...publicationDraft, candidate: { ...publicationDraft.candidate, candidate_sha256: 'b'.repeat(64) } }
  expect(() => prepareRestoreBasis(invalidHash, base, publicationReceipt)).toThrow()
  expect(() => prepareRestoreBasis({ ...publicationDraft, warnings: [{ code: 'BAD_SOURCE', message: 'Synthetic error', locator: null, severity: 'error' }] }, base, publicationReceipt)).not.toThrow()
  const blocked = prepareRestoreBasis({ ...publicationDraft, warnings: [{ code: 'BAD_SOURCE', message: 'Synthetic error', locator: null, severity: 'error' }] }, base, publicationReceipt)
  expect(() => makeRestorePublicationCommand('workspace_synthetic', 0, blocked, [])).toThrow()
  const command = makeRestorePublicationCommand('workspace_synthetic', 0, basis, [0, 1])
  for (const bad of [{ ...command, extra: true }, { ...command, body: { ...command.body, expected_review_revision: 2 } }, { ...command, body: { ...command.body, acknowledged_warning_codes: ['SOURCE_CONFIRM', 'SOURCE_CONFIRM'] } }]) expect(() => decodeRestorePublicationCommand(JSON.stringify(bad), 'workspace_synthetic')).toThrow()
})


test('restore basis is owner-specific, binds full base metadata/body and predicts base+1 independently of draft revision', () => {
  expect(publicationDraft.candidate.draft_revision).toBe(1); expect(publicationRef.revision).toBe(3)
  expect(publicationRef.sha256).not.toBe(publicationDraft.candidate.candidate_sha256)
  for (const bad of [{ ...base, body_markdown: 'damaged' }, { ...base, metadata: { ...base.metadata, title: 'damaged' } }]) expect(() => prepareRestoreBasis(publicationDraft, bad, publicationReceipt)).toThrow()
  const command = makeRestorePublicationCommand('workspace_synthetic', 0, prepareRestoreBasis(publicationDraft, base, publicationReceipt), [0, 1])
  for (const bad of [{ ...command, basis: { ...command.basis, owner: 'import' } }, { ...command, basis: { ...command.basis, snapshot: { ...publicationDraft, state: 'published' } } }, { ...command, basis: { ...command.basis, target: { ...command.basis.target, object_revision: 2 } } }]) expect(() => decodeRestorePublicationCommand(JSON.stringify(bad), 'workspace_synthetic')).toThrow()
})
