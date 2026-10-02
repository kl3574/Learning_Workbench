import type { ContentBlock, ContentRef, ContentRestoreDraftCreateAck, ContentRestoreDraftCreateWrite, ContentRestoreDraftSnapshot } from '../../../../../packages/contracts/generated/api-types'
import { checkedProvider, exactObject, sameValue } from '../providers/providerSchema'
import { canonical, digest } from '../retrieval/retrievalModel'

export const checkedRestore = <T,>(name: string, value: unknown): T => checkedProvider<T>(name, value)
const invalid = (): never => { throw new Error('恢复身份、历史原件、当前基准或完整候选不一致。') }
export function restoreRequest(raw: unknown): ContentRestoreDraftCreateWrite {
  const value = checkedRestore<ContentRestoreDraftCreateWrite>('ContentRestoreDraftCreateWrite', raw), a = value.source_ref, b = value.expected_current_ref
  if (a.entity !== 'block' || b.entity !== 'block' || a.id !== b.id || a.revision >= b.revision || !value.reason.trim() || [...value.reason].length > 2000) invalid()
  return value
}
export function restoreAck(raw: unknown, request: ContentRestoreDraftCreateWrite): ContentRestoreDraftCreateAck {
  const value = checkedRestore<ContentRestoreDraftCreateAck>('ContentRestoreDraftCreateAck', raw)
  if (!sameValue(value.source_ref, request.source_ref) || !sameValue(value.base_ref, request.expected_current_ref)
      || value.candidate.entity !== 'block' || value.candidate.draft_revision !== 1) invalid()
  return value
}
export type RestoreMaterial = { metadata: ContentBlock; body_markdown: string }
export function restoreMaterial(value: RestoreMaterial, ref: ContentRef): RestoreMaterial {
  if (!exactObject(value, ['metadata', 'body_markdown'])) invalid()
  const block = checkedRestore<ContentBlock>('ContentBlock', value.metadata)
  if (ref.entity !== 'block' || block.id !== ref.id || block.revision !== ref.revision || digest(canonical(block)) !== ref.sha256
      || typeof value.body_markdown !== 'string' || digest(value.body_markdown) !== block.body_sha256 || block.body_path.startsWith('private/')) invalid()
  return value
}
export function restoreSnapshot(raw: unknown, id?: string): ContentRestoreDraftSnapshot {
  const value = checkedRestore<ContentRestoreDraftSnapshot>('ContentRestoreDraftSnapshot', raw), block = value.proposed_block
  restoreRequest({ source_ref: value.source_ref, expected_current_ref: value.base_ref, reason: value.reason })
  if (id && value.candidate.draft_id !== id || value.candidate.entity !== 'block' || value.candidate.draft_revision !== 1
      || block.id !== value.base_ref.id || block.revision !== value.base_ref.revision + 1
      || (value.state === 'published') !== (value.published_ref !== null)) invalid()
  restoreMaterial({ metadata: { ...block, revision: value.source_ref.revision }, body_markdown: value.body_markdown }, value.source_ref)
  if (value.published_ref && !sameValue(value.published_ref, { entity: 'block', id: block.id, revision: block.revision, sha256: digest(canonical(block)) })) invalid()
  // Candidate/source-material hashes cover retained server-only provenance and
  // dependency descriptions. Check their strict shape and cross-read identity;
  // do not claim this narrower response can reconstruct the server descriptor.
  return value
}
