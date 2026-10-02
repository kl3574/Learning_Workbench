// Synthetic typed fixtures for behavior tests; no human content approval.
import type { DraftCandidate, JobSnapshot, SessionResponse, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
export const reviewCandidate: DraftCandidate = { draft_id: 'draft_synthetic_review', draft_revision: 1, entity: 'block', candidate_sha256: 'a'.repeat(64) }
export const machineReceipt: StoredReviewReceipt = { id: 'review_synthetic', revision: 1, candidate: reviewCandidate,
  structural: 'PASS', mathematical: 'NOT_RUN', sources: 'NOT_RUN', independent_pedagogy: 'NOT_RUN',
  reviewer: 'machine:structural-only', created_at: '2026-01-01T00:00:00Z', evidence_paths: ['/api/v1/artifacts/artifact_synthetic/download'], decision_reason: '' }
export const reviewSession = (workspace: string): SessionResponse => ({ workspace_id: workspace, actor_session_id: 'session_fixture_reviewFixtures', role: 'author', csrf_token: 'synthetic-unused', active_independent_attempt_id: null, active_open_book_attempt_id: null })
export const safeReviewJob = (workspace: string): JobSnapshot => ({ id: machineReceipt.id, workspace_id: workspace, kind: 'draft_review', status: 'completed', revision: 3, created_at: machineReceipt.created_at, updated_at: machineReceipt.created_at, progress: { completed: 1, total: 1, label: '完成' }, result_refs: [], warnings: [], error: null })
