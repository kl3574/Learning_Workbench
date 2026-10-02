// Synthetic non-text historical material; no real content-quality approval.
import type { ContentBlock, ContentRestoreDraftSnapshot, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
import { machineReceipt } from '../draftReview/reviewFixtures'
import { canonical, digest } from '../retrieval/retrievalModel'
import { prepareRestoreBasis, restoreTargetRef } from './restorePublicationSchema'
export const base = { metadata: { schema_version: '3.0.0', entity: 'block', id: 'block_restore_synthetic', revision: 1, kind: 'theorem', title: '原始合成定理', body_path: 'content/restore.md', body_sha256: digest('原始 🧠 e\u0301\n\\alpha\n\n'), concepts: [], citations: [], depends_on: [] } as ContentBlock, body_markdown: '原始 🧠 e\u0301\n\\alpha\n\n' }
export const current = { metadata: { ...base.metadata, revision: 2, title: '当前合成摘要', kind: 'summary' as const, body_sha256: digest('当前摘要。\n') }, body_markdown: '当前摘要。\n' }
export const publicationDraft: ContentRestoreDraftSnapshot = { owner: 'authoring_restore', candidate: { draft_id: 'restore_synthetic', draft_revision: 1, entity: 'block', candidate_sha256: 'a'.repeat(64) },
  source_ref: { entity: 'block', id: base.metadata.id, revision: 1, sha256: digest(canonical(base.metadata)) }, base_ref: { entity: 'block', id: base.metadata.id, revision: 2, sha256: digest(canonical(current.metadata)) },
  reason: '明确合成历史恢复，不作教学批准。', proposed_block: { ...base.metadata, revision: 3 }, body_markdown: base.body_markdown, source_material_sha256: 'b'.repeat(64),
  warnings: [0, 1].map(index => ({ code: 'SOURCE_CONFIRM', severity: 'warning', message: `合成警告 ${index}`, locator: null })), state: 'draft', published_ref: null }
export const publicationReceipt: StoredReviewReceipt = { ...machineReceipt, candidate: publicationDraft.candidate, revision: 2, mathematical: 'APPROVED', sources: 'APPROVED', decision_reason: '合成测试，无真实质量验收。' }
export const publicationRef = restoreTargetRef(prepareRestoreBasis(publicationDraft, base, publicationReceipt))
export const createBody = { source_ref: publicationDraft.source_ref, expected_current_ref: publicationDraft.base_ref, reason: publicationDraft.reason }
export const createAck = { candidate: publicationDraft.candidate, source_ref: publicationDraft.source_ref, base_ref: publicationDraft.base_ref, state: 'draft' as const }
