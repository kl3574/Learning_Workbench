import type { ContentBlock, ContentRef, DraftCandidate, EditDraftSnapshot, StoredReviewReceipt, Warning } from '../../../../../packages/contracts/generated/api-types'
import { exactObject, sameValue } from '../providers/providerSchema'
import { editSnapshot, editText } from '../draftEditor/editSchema'
import { reviewReceipt } from '../draftReview/reviewSchema'
import { checkedPublication, publicationRef, type PublicationTarget } from '../draftPublication/publicationSchema'
import { canonical, digest } from '../retrieval/retrievalModel'

export type EditPublicationBasis = { owner: 'authoring_edit'; snapshot: EditDraftSnapshot; base: { metadata: ContentBlock; body_markdown: string };
  candidate: DraftCandidate; target: PublicationTarget; review: StoredReviewReceipt; warnings: Warning[] }
const invalid = (): never => { throw new Error('编辑稿发布基准与原块、准确候选、审核或目标引用不一致。') }
export function checkedEditBasis(value: EditPublicationBasis): EditPublicationBasis {
  if (!exactObject(value, ['owner', 'snapshot', 'base', 'candidate', 'target', 'review', 'warnings']) || value.owner !== 'authoring_edit'
      || !exactObject(value.base, ['metadata', 'body_markdown']) || !exactObject(value.target, ['object_id', 'object_revision', 'metadata_sha256'])) invalid()
  const snapshot = editSnapshot(value.snapshot), base = checkedPublication<ContentBlock>('ContentBlock', value.base.metadata), p = snapshot.payload
  if (snapshot.state !== 'draft' || base.kind !== 'text'
      || base.id !== snapshot.base_ref.id || base.revision !== snapshot.base_ref.revision
      || digest(canonical(base)) !== snapshot.base_ref.sha256 || typeof value.base.body_markdown !== 'string'
      || digest(value.base.body_markdown) !== base.body_sha256 || value.base.body_markdown.includes('\r')
      || base.body_path !== p.body_path || !sameValue(base.citations, p.citations)
      || !sameValue(value.candidate, snapshot.candidate) || !sameValue(value.warnings, snapshot.warnings)) invalid()
  editText({ title: base.title, body_markdown: value.base.body_markdown })
  const target = { ...base, revision: base.revision + 1, title: p.title, body_sha256: p.body_sha256 }
  publicationRef({ entity: 'block', id: value.target.object_id, revision: value.target.object_revision, sha256: value.target.metadata_sha256 })
  if (value.target.object_id !== target.id || value.target.object_revision !== target.revision || value.target.metadata_sha256 !== digest(canonical(target))) invalid()
  const review = reviewReceipt(value.review, value.review?.id, snapshot.candidate)
  if (review.structural !== 'PASS' || !['APPROVED', 'NOT_APPLICABLE'].includes(review.mathematical) || !['APPROVED', 'NOT_APPLICABLE'].includes(review.sources) || !review.decision_reason.trim() || review.revision! < 2) invalid()
  return structuredClone(value)
}
export function prepareEditBasis(snapshot: EditDraftSnapshot, base: { metadata: ContentBlock; body_markdown: string }, review: StoredReviewReceipt): EditPublicationBasis {
  const target = { ...base.metadata, revision: base.metadata.revision + 1, title: snapshot.payload.title, body_sha256: snapshot.payload.body_sha256 }
  return checkedEditBasis({ owner: 'authoring_edit', snapshot, base, candidate: snapshot.candidate, review, warnings: snapshot.warnings,
    target: { object_id: target.id, object_revision: target.revision, metadata_sha256: digest(canonical(target)) } })
}
export const matchesEditCandidate = (draft: EditDraftSnapshot, candidate: DraftCandidate) => sameValue(draft.candidate, candidate)
export const editTargetRef = (basis: EditPublicationBasis): ContentRef => publicationRef({ entity: 'block', id: basis.target.object_id, revision: basis.target.object_revision, sha256: basis.target.metadata_sha256 }, basis.target)
