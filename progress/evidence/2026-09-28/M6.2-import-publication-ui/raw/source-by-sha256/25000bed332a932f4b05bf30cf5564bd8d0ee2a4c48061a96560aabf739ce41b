import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'
import type { ContentRef, DraftCandidate, ImportDraftSnapshot, StoredReviewReceipt, Warning } from '../../../../../packages/contracts/generated/api-types'
import { checkedProvider, exactObject, sameValue } from '../providers/providerSchema'
import { reviewReceipt } from '../draftReview/reviewSchema'

export type PublicationTarget = { object_id: string; object_revision: number; metadata_sha256: string }
export type PublicationBasis = { candidate: DraftCandidate; target: PublicationTarget; review: StoredReviewReceipt; warnings: Warning[] }
const invalid = (): never => { throw new Error('发布基准与准确 Import 文本块、原审核或引用不一致。') }
export function checkedPublication<T>(name: string, value: unknown): T {
  try { return checkedProvider<T>(name, value) } catch { return invalid() }
}
export function publicationRef(value: unknown, target?: PublicationTarget): ContentRef {
  const ref = checkedPublication<ContentRef>('ContentRef', value)
  if (ref.entity !== 'block' || target && (ref.id !== target.object_id || ref.revision !== target.object_revision || ref.sha256 !== target.metadata_sha256)) invalid()
  return ref
}
export function checkedBasis(value: PublicationBasis): PublicationBasis {
  if (!exactObject(value, ['candidate', 'target', 'review', 'warnings']) || !exactObject(value.target, ['object_id', 'object_revision', 'metadata_sha256'])) invalid()
  const candidate = checkedPublication<DraftCandidate>('DraftCandidate', value.candidate)
  const review = reviewReceipt(value.review, value.review?.id, candidate)
  publicationRef({ entity: 'block', id: value.target.object_id, revision: value.target.object_revision, sha256: value.target.metadata_sha256 })
  if (candidate.entity !== 'block' || candidate.draft_revision !== 1 || value.target.object_revision !== 1
      || value.target.metadata_sha256 !== candidate.candidate_sha256 || review.structural !== 'PASS'
      || review.mathematical !== 'NOT_APPLICABLE' || review.sources !== 'APPROVED' || !review.decision_reason.trim()
      || review.revision! < 2 || !Array.isArray(value.warnings)) invalid()
  value.warnings.forEach(warning => checkedPublication('Warning', warning))
  return structuredClone(value)
}
export function preparePublicationBasis(raw: ImportDraftSnapshot, receipt: StoredReviewReceipt): PublicationBasis {
  const draft = checkedPublication<ImportDraftSnapshot>('ImportDraftSnapshot', raw)
  if (draft.kind !== 'block' || draft.base_ref !== null || draft.state !== 'draft' || draft.revision !== 1 || !('metadata' in draft.payload)) return invalid()
  const metadata = draft.payload.metadata
  if (metadata.kind !== 'text' || metadata.revision !== 1 || metadata.concepts?.length || metadata.depends_on?.length) invalid()
  // This narrow ContentBlock has only strings, one integer and string arrays;
  // default fields are normalized by its generated contract. No float hashing.
  const normalized = { ...metadata, schema_version: metadata.schema_version ?? '3.0.0', entity: metadata.entity ?? 'block', concepts: metadata.concepts ?? [], citations: metadata.citations ?? [], depends_on: metadata.depends_on ?? [] }
  const canonical = JSON.stringify(Object.fromEntries(Object.entries(normalized).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0)))
  const digest = bytesToHex(sha256(new TextEncoder().encode(canonical)))
  if (digest !== draft.candidate_sha256) invalid()
  return checkedBasis({ candidate: { draft_id: draft.id, draft_revision: draft.revision, entity: draft.kind, candidate_sha256: draft.candidate_sha256 },
    target: { object_id: metadata.id, object_revision: metadata.revision, metadata_sha256: digest }, review: receipt, warnings: draft.warnings })
}
export function acknowledgedCodes(basis: PublicationBasis, selected: number[]): string[] {
  if (new Set(selected).size !== selected.length || selected.some(index => !Number.isSafeInteger(index) || basis.warnings[index]?.severity !== 'warning')
      || basis.warnings.some((warning, index) => warning.severity === 'error' || warning.severity === 'warning' && !selected.includes(index))) invalid()
  return [...new Set(basis.warnings.filter(warning => warning.severity === 'warning').map(warning => warning.code))]
}
export const matchesPublicationCandidate = (draft: ImportDraftSnapshot, candidate: DraftCandidate) => sameValue(candidate,
  { draft_id: draft.id, draft_revision: draft.revision, entity: draft.kind, candidate_sha256: draft.candidate_sha256 })
