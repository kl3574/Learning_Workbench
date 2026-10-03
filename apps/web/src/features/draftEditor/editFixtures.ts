// Original synthetic text only; no provider or human content approval.
import type { ContentRef, EditDraftSnapshot } from '../../../../../packages/contracts/generated/api-types'
import { canonical, digest } from '../retrieval/retrievalModel'
export const editBase: ContentRef = { entity: 'block', id: 'block_edit_synthetic', revision: 1, sha256: 'a'.repeat(64) }
export function editFixture(revision = 1, title = '基准合成标题', body = '基准合成正文。\n'): EditDraftSnapshot {
  const payload = { version: 'text-block-edit-v1' as const, entity: 'block' as const, kind: 'text' as const, base_ref: editBase,
    body_path: 'content/edit-synthetic.md', citations: [], title, body_markdown: body, body_sha256: digest(body), base_material_sha256: 'b'.repeat(64) }
  return { owner: 'authoring_edit', candidate: { draft_id: 'draft_edit_synthetic', draft_revision: revision, entity: 'block', candidate_sha256: digest(canonical(payload)) },
    base_ref: editBase, base_material_sha256: payload.base_material_sha256, payload, warnings: [], state: 'draft' }
}
