// Original synthetic fixture; tests do not grant real content-quality approval.
import type { ContentBlock, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
import { editFixture } from '../draftEditor/editFixtures'
import { machineReceipt } from '../draftReview/reviewFixtures'
import { canonical, digest } from '../retrieval/retrievalModel'
import { editTargetRef, prepareEditBasis } from './editPublicationSchema'
export const base = { metadata: { schema_version: '3.0.0', entity: 'block', id: 'block_edit_synthetic', revision: 1, kind: 'text', title: '原合成标题', body_path: 'content/edit-synthetic.md', body_sha256: digest('原合成正文。\n'), concepts: [], citations: [], depends_on: [] } as ContentBlock, body_markdown: '原合成正文。\n' }
export const publicationDraft = editFixture(3, '已保存合成标题', '已保存合成正文。\n')
publicationDraft.base_ref = { entity: 'block', id: base.metadata.id, revision: 1, sha256: digest(canonical(base.metadata)) }
publicationDraft.payload.base_ref = publicationDraft.base_ref
publicationDraft.candidate.candidate_sha256 = digest(canonical(publicationDraft.payload))
publicationDraft.warnings = [0, 1].map(index => ({ code: 'SOURCE_CONFIRM', severity: 'warning' as const, message: `合成警告 ${index}`, locator: null }))
export const publicationReceipt: StoredReviewReceipt = { ...machineReceipt, candidate: publicationDraft.candidate, revision: 2, mathematical: 'NOT_APPLICABLE', sources: 'APPROVED', decision_reason: '合成测试，无真实质量验收。' }
export const publicationRef = editTargetRef(prepareEditBasis(publicationDraft, base, publicationReceipt))
