import type { ContentRef, EditDraftSnapshot } from '../../../../../packages/contracts/generated/api-types'
import { checkedProvider, exactObject, sameValue } from '../providers/providerSchema'
import { canonical, digest } from '../retrieval/retrievalModel'

export type EditText = { title: string; body_markdown: string }
export const checkedEdit = checkedProvider
const invalid = (): never => { throw new Error('编辑稿的准确身份、正文或基准无法核验。') }
export function editText(value: unknown, submitting = true): EditText {
  if (!exactObject(value, ['title', 'body_markdown']) || typeof value.title !== 'string' || submitting && !value.title.trim()
      || typeof value.body_markdown !== 'string' || submitting && value.body_markdown.includes('\r')) return invalid()
  for (const text of [value.title, value.body_markdown]) {
    if (Array.from(text).length > 400000 || new TextDecoder().decode(new TextEncoder().encode(text)) !== text) invalid()
  }
  if (new TextEncoder().encode(value.body_markdown).length > 2000000) invalid()
  return { title: value.title, body_markdown: value.body_markdown }
}
export const snapshotText = (value: EditDraftSnapshot): EditText => ({ title: value.payload.title, body_markdown: value.payload.body_markdown })
export function editSnapshot(raw: unknown, base?: ContentRef, id?: string, revision?: number): EditDraftSnapshot {
  const value = checkedEdit<EditDraftSnapshot>('EditDraftSnapshot', raw), p = value.payload
  if (value.owner !== 'authoring_edit' || value.candidate.entity !== 'block'
      || id && value.candidate.draft_id !== id || revision !== undefined && value.candidate.draft_revision !== revision
      || base && !sameValue(base, value.base_ref) || !sameValue(value.base_ref, p.base_ref)
      || value.base_material_sha256 !== p.base_material_sha256 || p.body_sha256 !== digest(p.body_markdown)
      || p.version !== 'text-block-edit-v1' || p.entity !== 'block' || p.kind !== 'text'
      || p.body_path.startsWith('private/') || p.body_path.includes('..') || p.body_path.startsWith('/')) invalid()
  editText(snapshotText(value))
  // This strict payload contains only strings, integer revisions, string arrays
  // and a ContentRef. Python canonical JSON and this canonical serializer agree;
  // no generic float/Content metadata equivalence is assumed.
  if (digest(canonical(p)) !== value.candidate.candidate_sha256) invalid()
  return value
}
