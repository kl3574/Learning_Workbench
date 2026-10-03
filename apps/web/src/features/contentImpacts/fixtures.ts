// Original synthetic software fixtures; no academic certification.
import type { ContentImpactView as View, ContentImpactSummary as Summary, ImpactObjectDecisionReceipt as Receipt, ImpactObjectDecisionWrite as Write } from '../../../../../packages/contracts/generated/api-types'
import type { ImpactPort } from './client'
import { digest, eventFacts } from './schema'
export const eventId = 'outbox_synthetic_impact', targetId = 'lesson_synthetic', blockId = 'block_synthetic'
export const targetRef = { entity: 'lesson' as const, id: targetId, revision: 1, sha256: 'c'.repeat(64) }
export const original: View = { event_id: eventId, old_ref: { entity: 'block', id: blockId, revision: 1, sha256: 'a'.repeat(64) }, new_ref: { entity: 'block', id: blockId, revision: 2, sha256: 'b'.repeat(64) }, reason: 'content_revision_published', evidence_version: 'owner_frozen_v1', event_snapshot_sha256: 'd'.repeat(64), affected_ids: [blockId, targetId, 'note_synthetic'], exact_dependency_refs: [targetRef], conservative_only_ids: [], pending_target_ids: [targetId], action_required_target_ids: [], target_decision_head: null, decisions: [], next_cursor: null }
export const listing: Summary = { ...eventFacts(original), pending_target_ids: original.pending_target_ids, action_required_target_ids: [] }
export const session = (workspace: string) => ({ workspace_id: workspace, actor_session_id: 'session_impact_fixture', role: 'author' as const, csrf_token: 'synthetic-impact-page-only', active_independent_attempt_id: null, active_open_book_attempt_id: null })
export function ack(body: Write): Receipt {
  const result = { event_id: eventId, target_id: body.target_id, decision_revision: body.expected_decision_revision + 1, classification: body.observed_ref.revision === 1 ? 'exact_ref' as const : 'id_only_candidate' as const, observed_ref: body.observed_ref, target_metadata_sha256: body.observed_ref.sha256, target_body_sha256: null, event_snapshot_sha256: body.expected_event_snapshot_sha256, decision: body.decision, reason: body.reason, evidence_artifacts: body.evidence_artifact_ids.map(id => ({ id, sha256: 'e'.repeat(64) })), actor_session_id: 'session_synthetic', decided_at: '2026-10-02T00:00:00Z', request_sha256: digest(body) }
  return { ...result, receipt_sha256: digest(result) }
}
export const body = (revision = 0): Write => ({ target_id: targetId, observed_ref: targetRef, expected_event_snapshot_sha256: original.event_snapshot_sha256!, expected_decision_revision: revision, decision: 'no_revision_needed', reason: 'Explicit original synthetic judgment.', evidence_artifact_ids: [] })
export const portFor = (workspace: string): ImpactPort => ({ session: async () => session(workspace), list: async () => ({ items: [listing], next_cursor: null }), read: async (_id, target) => ({ ...original, target_decision_head: target ? 0 : null }), current: async () => targetRef, decide: async (_id, body) => ack(body) })
