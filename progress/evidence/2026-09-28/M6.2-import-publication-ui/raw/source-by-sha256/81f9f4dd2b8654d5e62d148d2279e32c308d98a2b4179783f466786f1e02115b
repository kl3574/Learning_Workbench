import 'fake-indexeddb/auto'
import { afterEach, expect, test } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { publicationDraft, publicationReceipt, publicationRef } from './publicationFixtures'
import { preparePublicationBasis } from './publicationSchema'
import { decodePublicationCommand, makePublicationCommand, persistPublicationCommand, readPublicationCommand, samePublicationActorPage } from './publicationCommands'

const stores: DraftStore[] = []
afterEach(async () => { await Promise.all(stores.splice(0).map(value => value.close())) })
test('original four-field publication command survives IndexedDB reopening and cannot acquire a different request or ACK', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`, name = `publication_${crypto.randomUUID()}`
  const store = new DraftStore({ name }); stores.push(store)
  const basis = preparePublicationBasis(publicationDraft, publicationReceipt)
  const command = makePublicationCommand(workspace, 3, basis, [0, 1])
  expect(command.body).toEqual({ expected_revision: 1, expected_content_sha256: publicationRef.sha256, review_receipt_id: publicationReceipt.id, acknowledged_warning_codes: ['SOURCE_CONFIRM'] })
  await persistPublicationCommand(command, store)
  await store.close()
  const reopened = new DraftStore({ name }); stores.push(reopened)
  expect(readPublicationCommand((await reopened.load(workspace))[command.command_id], workspace)).toEqual(command)
  const acknowledged = { ...command, ack: publicationRef }
  await persistPublicationCommand(acknowledged, reopened)
  expect(await persistPublicationCommand(command, reopened)).toEqual(acknowledged)
  await expect(persistPublicationCommand({ ...command, body: { ...command.body, review_receipt_id: 'review_other' } }, reopened)).rejects.toThrow()
  await expect(persistPublicationCommand({ ...acknowledged, ack: { ...publicationRef, revision: 2 } }, reopened)).rejects.toThrow()
  expect(samePublicationActorPage(command, 3)).toBe(true)
  expect(samePublicationActorPage(command, 4)).toBe(false)
  expect(samePublicationActorPage({ ...command, origin: { ...command.origin, page_id: 'page_previous' } }, 3)).toBe(false)
})

test('conflicting immutable body stays in real IndexedDB and prevents command admission', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`, store = new DraftStore({ name: `publication_${crypto.randomUUID()}` }); stores.push(store)
  const command = makePublicationCommand(workspace, 1, preparePublicationBasis(publicationDraft, publicationReceipt), [0, 1])
  await persistPublicationCommand(command, store)
  const changed = { ...command, basis: { ...command.basis, review: { ...command.basis.review, decision_reason: 'Synthetic conflicting basis' } } }
  await store.save(workspace, command.command_id, JSON.stringify(changed), 0)
  const before = (await store.load(workspace))[command.command_id]
  expect(before.conflicts).toHaveLength(1)
  await expect(persistPublicationCommand(command, store)).rejects.toThrow()
  expect((await store.load(workspace))[command.command_id]).toEqual(before)
})

test('warning instances, explicit human decisions, metadata identity and strict original body cannot be bypassed', () => {
  const basis = preparePublicationBasis(publicationDraft, publicationReceipt)
  for (const selected of [[], [0], [1], [0, 1, 1], [0, 1, 2]]) expect(() => makePublicationCommand('workspace_synthetic', 0, basis, selected)).toThrow()
  for (const receipt of [{ ...publicationReceipt, mathematical: 'NOT_RUN' }, { ...publicationReceipt, sources: 'NOT_APPLICABLE' }, { ...publicationReceipt, decision_reason: '' }, { ...publicationReceipt, candidate: { ...publicationReceipt.candidate, draft_id: 'draft_other' } }]) expect(() => preparePublicationBasis(publicationDraft, receipt as typeof publicationReceipt)).toThrow()
  const invalidHash = { ...publicationDraft, candidate_sha256: 'b'.repeat(64) }
  expect(() => preparePublicationBasis(invalidHash, publicationReceipt)).toThrow()
  expect(() => preparePublicationBasis({ ...publicationDraft, warnings: [{ code: 'BAD_SOURCE', message: 'Synthetic error', locator: null, severity: 'error' }] }, publicationReceipt)).not.toThrow()
  const blocked = preparePublicationBasis({ ...publicationDraft, warnings: [{ code: 'BAD_SOURCE', message: 'Synthetic error', locator: null, severity: 'error' }] }, publicationReceipt)
  expect(() => makePublicationCommand('workspace_synthetic', 0, blocked, [])).toThrow()
  const command = makePublicationCommand('workspace_synthetic', 0, basis, [0, 1])
  for (const bad of [{ ...command, extra: true }, { ...command, body: { ...command.body, expected_review_revision: 2 } }, { ...command, body: { ...command.body, acknowledged_warning_codes: ['SOURCE_CONFIRM', 'SOURCE_CONFIRM'] } }]) expect(() => decodePublicationCommand(JSON.stringify(bad), 'workspace_synthetic')).toThrow()
})
