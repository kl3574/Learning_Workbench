import type { AuthoringDraftView, AuthoringGroupDraftView, ContentRestoreDraftSnapshot, DraftCandidate, EditDraftSnapshot, ImportDraftSnapshot } from '../../../../../packages/contracts/generated/api-types'
import { sameValue } from '../providers/providerSchema'
import { request } from '../../api/client'
import { checkedReview } from './reviewSchema'
import type { ReviewFormOwner } from './reviewFormMemory'

// The original UI owner selects a real public reader; draft ID spelling never
// chooses the owner and an Edit snapshot is never fabricated as an Import.
export async function readReviewFormCandidate(owner: ReviewFormOwner, candidate: DraftCandidate): Promise<DraftCandidate> {
  const path = { id: candidate.draft_id }
  switch (owner) {
    case 'import': {
      const row = checkedReview<ImportDraftSnapshot>('ImportDraftSnapshot', await request('GET /api/v1/drafts/{id}', undefined, undefined, { path }))
      return checkedReview('DraftCandidate', { draft_id: row.id, draft_revision: row.revision, entity: row.kind, candidate_sha256: row.candidate_sha256 })
    }
    case 'edit': {
      const original = checkedReview<EditDraftSnapshot>('EditDraftSnapshot', await request('GET /api/v1/draft-edits/{id}', undefined, undefined, { path, query: { revision: candidate.draft_revision } }))
      if (!sameValue(original.candidate, candidate)) throw new Error('原精确编辑候选无法核验。')
      return checkedReview<EditDraftSnapshot>('EditDraftSnapshot', await request('GET /api/v1/draft-edits/{id}', undefined, undefined, { path })).candidate
    }
    case 'restore': return checkedReview<ContentRestoreDraftSnapshot>('ContentRestoreDraftSnapshot', await request('GET /api/v1/content/restore-drafts/{id}', undefined, undefined, { path })).candidate
    case 'authoring_single': return checkedReview<AuthoringDraftView>('AuthoringDraftView', await request('GET /api/v1/authoring/drafts/{id}', undefined, undefined, { path })).candidate
    case 'authoring_group': return checkedReview<AuthoringGroupDraftView>('AuthoringGroupDraftView', await request('GET /api/v1/authoring/draft-groups/{id}', undefined, undefined, { path })).candidate
  }
}
