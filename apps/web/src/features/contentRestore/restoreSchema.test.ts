import { expect, test } from 'vitest'
import type { ContentBlock } from '../../../../../packages/contracts/generated/api-types'
import { canonical, digest } from '../retrieval/retrievalModel'
import { publicationDraft, createBody, createAck } from './restoreFixtures'
import { restoreAck, restoreRequest, restoreSnapshot } from './restoreSchema'

test.each(['orientation', 'definition', 'theorem', 'proof', 'intuition', 'worked_example', 'boundary', 'summary', 'text', 'code', 'figure'] as ContentBlock['kind'][])('all ContentBlock kinds preserve full old metadata/body under the independent Restore snapshot: %s', kind => {
  const value = structuredClone(publicationDraft); value.proposed_block.kind = kind
  value.source_ref.sha256 = digest(canonical({ ...value.proposed_block, revision: value.source_ref.revision }))
  expect(restoreSnapshot(value)).toEqual(value)
  expect(restoreSnapshot(value).body_markdown).toBe('原始 🧠 e\u0301\n\\alpha\n\n')
})
test('create request/ACK are closed DTOs with exact historical/current binding and Unicode code-point reason bounds', () => {
  expect(restoreRequest({ ...createBody, reason: '🧠'.repeat(2000) }).reason.length).toBe(4000)
  for (const value of [{ ...createBody, reason: ' ' }, { ...createBody, reason: '🧠'.repeat(2001) }, { ...createBody, owner: 'authoring_restore' }, { ...createBody, expected_current_ref: createBody.source_ref }]) expect(() => restoreRequest(value)).toThrow()
  expect(restoreAck(createAck, createBody)).toEqual(createAck)
  for (const value of [{ ...createAck, source_ref: createAck.base_ref }, { ...createAck, owner: 'import_parse' }, { ...createAck, candidate: { ...createAck.candidate, draft_revision: 2 } }]) expect(() => restoreAck(value, createBody)).toThrow()
})
test('snapshot rejects alternate owners, public history corruption, mismatched published state and independently changed published metadata', () => {
  for (const value of [
    { ...publicationDraft, owner: 'authoring_edit' }, { ...publicationDraft, owner: 'import_parse' },
    { ...publicationDraft, body_markdown: publicationDraft.body_markdown.normalize('NFC') },
    { ...publicationDraft, proposed_block: { ...publicationDraft.proposed_block, kind: 'text' } },
    { ...publicationDraft, proposed_block: { ...publicationDraft.proposed_block, depends_on: [{ ...publicationDraft.base_ref, id: 'block_other' }] } },
    { ...publicationDraft, state: 'published' }, { ...publicationDraft, state: 'published', published_ref: publicationDraft.source_ref },
  ]) expect(() => restoreSnapshot(value)).toThrow()
})
