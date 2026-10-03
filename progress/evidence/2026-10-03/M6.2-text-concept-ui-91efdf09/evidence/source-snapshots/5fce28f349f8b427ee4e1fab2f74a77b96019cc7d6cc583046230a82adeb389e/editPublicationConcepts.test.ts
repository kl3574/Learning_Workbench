import 'fake-indexeddb/auto'
import { afterEach, expect, test } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { base, publicationDraft, publicationReceipt } from './editPublicationFixtures'
import { prepareEditBasis } from './editPublicationSchema'
import { decodeEditPublicationCommand, makeEditPublicationCommand, persistEditPublicationCommand, readEditPublicationCommand } from './editPublicationCommands'
import { canonical, digest } from '../retrieval/retrievalModel'

const stores: DraftStore[] = []
afterEach(async () => { await Promise.all(stores.splice(0).map(store => store.close())) })
function original() {
  const concepts = ['original_concept_second', 'original_concept_first']
  const depends_on = [{ entity: 'block' as const, id: 'original_source_second', revision: 2, sha256: 'a'.repeat(64) }, { entity: 'block' as const, id: 'original_source_first', revision: 1, sha256: 'b'.repeat(64) }]
  const source = { ...base, metadata: { ...base.metadata, concepts, depends_on } }, snapshot = structuredClone(publicationDraft)
  snapshot.base_ref.sha256 = digest(canonical(source.metadata)); snapshot.payload.base_ref = snapshot.base_ref
  snapshot.candidate.candidate_sha256 = digest(canonical(snapshot.payload))
  return { source, snapshot, review: { ...publicationReceipt, candidate: snapshot.candidate } }
}

test('concept IDs and exact dependency refs retain original order in the complete publication target and reopened journal', async () => {
  const { source, snapshot, review } = original(), basis = prepareEditBasis(snapshot, source, review)
  // Independently calculated with Python canonical JSON/SHA256 for the full expected r2 metadata.
  expect(basis.target.metadata_sha256).toBe('cf688782f05f41d731eed2de49ea94e2e9645b3fba1103e5f73a60dae0c63d5c')
  const workspace = `workspace_${crypto.randomUUID()}`, name = `concept_publication_${crypto.randomUUID()}`
  const command = makeEditPublicationCommand(workspace, 0, basis, [0, 1])
  const first = new DraftStore({ name }); stores.push(first)
  await persistEditPublicationCommand(command, first); await first.close()
  const reopened = new DraftStore({ name }); stores.push(reopened)
  const read = readEditPublicationCommand((await reopened.load(workspace))[command.command_id], workspace)
  expect(read).toEqual(command)
  expect(read.basis.base.metadata.concepts).toEqual(['original_concept_second', 'original_concept_first'])
  expect(read.basis.base.metadata.depends_on).toEqual(source.metadata.depends_on)
  expect(Object.keys(read.body).sort()).toEqual(['acknowledged_warning_codes', 'expected_content_sha256', 'expected_revision', 'review_receipt_id'])
})

test.each(['removed', 'reordered', 'substituted', 'dependency_reordered', 'body', 'metadata'] as const)('concept-bearing exact base rejects %s tampering with the original frozen hash', damage => {
  const { source, snapshot, review } = original(), changed = structuredClone(source)
  if (damage === 'removed') changed.metadata.concepts = []
  if (damage === 'reordered') changed.metadata.concepts.reverse()
  if (damage === 'substituted') changed.metadata.concepts[0] = 'different_concept'
  if (damage === 'dependency_reordered') changed.metadata.depends_on.reverse()
  if (damage === 'body') changed.body_markdown += 'Changed without a new base.'
  if (damage === 'metadata') changed.metadata.title = 'Changed without a new base.'
  expect(() => prepareEditBasis(snapshot, changed, review)).toThrow()
})

test('a retained concept-bearing publication command cannot drop metadata, replace the target hash or inject editable concept fields', () => {
  const { source, snapshot, review } = original(), workspace = 'workspace_concept_integrity'
  const command = makeEditPublicationCommand(workspace, 0, prepareEditBasis(snapshot, source, review), [0, 1])
  const altered = structuredClone(command)
  altered.basis.base.metadata.concepts.reverse()
  const unknownTarget = { ...command, basis: { ...command.basis, target: { ...command.basis.target, metadata_sha256: 'd'.repeat(64) } } }
  const injected = { ...command, body: { ...command.body, concepts: [] } }
  for (const invalid of [altered, unknownTarget, injected]) expect(() => decodeEditPublicationCommand(JSON.stringify(invalid), workspace)).toThrow()
})
