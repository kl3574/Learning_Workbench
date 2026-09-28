// Explicit synthetic decisions, not approval of real learning material.
import type { ImportDraftSnapshot, StoredReviewReceipt, ContentRef } from '../../../../../packages/contracts/generated/api-types'
import { machineReceipt } from '../draftReview/reviewFixtures'
// Golden metadata digest from the Python ContentBlock canonical owner.
export const publicationHash = '025a7ea4a4b9aa985376fe3e7b215891369cd40e3a527d54c79ca3ef8f840555'
export const publicationDraft: ImportDraftSnapshot = {
  id: 'draft_synthetic_publication', kind: 'block', revision: 1, base_ref: null, state: 'draft', candidate_sha256: publicationHash,
  payload: { metadata: { schema_version: '3.0.0', id: 'block_synthetic_publication', revision: 1, entity: 'block', kind: 'text', title: '原创合成纯文本', body_path: 'bodies/synthetic.md', body_sha256: 'bb38e9b1deee77b850bcad76fb2169614a61608392f75ced7cb85f299857a955', concepts: [], citations: [], depends_on: [] }, body_markdown: 'Synthetic original plain text.\n', source_id: 'source_synthetic_publication', citations: [] },
  warnings: [
    { code: 'SOURCE_CONFIRM', message: 'Synthetic first source warning', locator: 'line:1', severity: 'warning' },
    { code: 'SOURCE_CONFIRM', message: 'Synthetic second source warning', locator: 'line:2', severity: 'warning' },
  ],
}
export const publicationReceipt: StoredReviewReceipt = { ...machineReceipt, revision: 2,
  candidate: { draft_id: publicationDraft.id, draft_revision: 1, entity: 'block', candidate_sha256: publicationHash },
  mathematical: 'NOT_APPLICABLE', sources: 'APPROVED', reviewer: 'author:synthetic', decision_reason: 'Synthetic original plain text; no mathematical claim; original source inspected.' }
export const publicationRef: ContentRef = { entity: 'block', id: 'block_synthetic_publication', revision: 1, sha256: publicationHash }
