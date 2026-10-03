import type { ContentRef, ContentRestoreDraftSnapshot, DraftCandidate, StoredReviewReceipt, Warning } from '../../../../../packages/contracts/generated/api-types'
import { exactObject, sameValue } from '../providers/providerSchema'
import { reviewReceipt } from '../draftReview/reviewSchema'
import { publicationRef, type PublicationTarget } from '../draftPublication/publicationSchema'
import { canonical, digest } from '../retrieval/retrievalModel'
import { restoreMaterial, restoreSnapshot, type RestoreMaterial } from './restoreSchema'

export type RestorePublicationBasis = { owner: 'authoring_restore'; snapshot: ContentRestoreDraftSnapshot; source: RestoreMaterial;
  candidate: DraftCandidate; target: PublicationTarget; review: StoredReviewReceipt; warnings: Warning[] }
export function checkedRestoreBasis(value: RestorePublicationBasis): RestorePublicationBasis {
  const bad = () => { throw new Error('恢复发布没有绑定完整历史原件、独立恢复候选和本次人审。') }
  if (!exactObject(value, ['owner', 'snapshot', 'source', 'candidate', 'target', 'review', 'warnings']) || value.owner !== 'authoring_restore'
      || !exactObject(value.source, ['metadata', 'body_markdown']) || !exactObject(value.target, ['object_id', 'object_revision', 'metadata_sha256'])) bad()
  const snapshot = restoreSnapshot(value.snapshot), source = restoreMaterial(value.source, snapshot.source_ref)
  if (snapshot.state !== 'draft' || !sameValue(source.metadata, { ...snapshot.proposed_block, revision: snapshot.source_ref.revision })
      || source.body_markdown !== snapshot.body_markdown || !sameValue(value.candidate, snapshot.candidate) || !sameValue(value.warnings, snapshot.warnings)) bad()
  const target = snapshot.proposed_block
  publicationRef({ entity: 'block', id: value.target.object_id, revision: value.target.object_revision, sha256: value.target.metadata_sha256 })
  if (value.target.object_id !== target.id || value.target.object_revision !== target.revision || value.target.metadata_sha256 !== digest(canonical(target))) bad()
  const review = reviewReceipt(value.review, value.review?.id, snapshot.candidate)
  if (review.structural !== 'PASS' || !['APPROVED', 'NOT_APPLICABLE'].includes(review.mathematical) || !['APPROVED', 'NOT_APPLICABLE'].includes(review.sources) || !review.decision_reason.trim() || review.revision! < 2) bad()
  return structuredClone(value)
}
export function prepareRestoreBasis(snapshot: ContentRestoreDraftSnapshot, source: RestoreMaterial, review: StoredReviewReceipt): RestorePublicationBasis {
  const block = snapshot.proposed_block
  return checkedRestoreBasis({ owner: 'authoring_restore', snapshot, source, candidate: snapshot.candidate, review, warnings: snapshot.warnings,
    target: { object_id: block.id, object_revision: block.revision, metadata_sha256: digest(canonical(block)) } })
}
export const matchesRestoreCandidate = (draft: ContentRestoreDraftSnapshot, candidate: DraftCandidate) => sameValue(draft.candidate, candidate)
export const restoreTargetRef = (basis: RestorePublicationBasis): ContentRef => publicationRef({ entity: 'block', id: basis.target.object_id, revision: basis.target.object_revision, sha256: basis.target.metadata_sha256 }, basis.target)
