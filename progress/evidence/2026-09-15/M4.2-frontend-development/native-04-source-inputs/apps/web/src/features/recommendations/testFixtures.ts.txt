import { vi } from 'vitest'
import type { ContentRef, MutationAck, RecommendationPage, RecommendationView } from '../../../../../packages/contracts/generated/api-types'
import { ApiError } from '../../api/client'
import type { DecisionEnvelope } from './decisionDrafts'
export const testRef = (entity: ContentRef['entity'], id: string, revision = 1): ContentRef => ({ entity, id, revision, sha256: 'a'.repeat(64) })
export function testRecommendation(id = 'recommendation_original'): RecommendationView {
  return { id, target_ref: testRef('lesson', 'lesson_original'), target_title: '合成建议目标', action: 'read', reason_codes: ['user_goal'], explanation: '受控单测目标与该小节概念映射相符；未审材料不承诺诊断效果。', evidence_refs: [], activity_refs: [], profile_basis: { revision: 2, goals: ['合成单测目标'], goal_concept_ids: ['concept_original'], self_assessments: [] }, route_basis: null, prerequisite_gaps: [], navigation_options: [{ kind: 'reader', course_ref: testRef('course', 'course_a'), lesson_ref: testRef('lesson', 'lesson_original'), block_ref: null }, { kind: 'reader', course_ref: testRef('course', 'course_b', 2), lesson_ref: testRef('lesson', 'lesson_original'), block_ref: null }], estimated_minutes: null, rule_version: 'recommendations-unit-test', generated_at: '2026-09-15T00:00:00Z', staleness: 'current', decision: 'pending', decision_revision: 1, decision_sha256: '1'.repeat(64), decision_reason: null }
}
export function testPage(items = [testRecommendation()]): RecommendationPage {
  return { items, next_cursor: null, projection_state: 'ready', warnings: [{ code: 'UNREVIEWED_MATERIAL_ONLY', message: '受控单测材料尚未审核。', severity: 'warning', locator: null }], snapshot_id: 'snapshot_original', generated_at: '2026-09-15T00:00:00Z', rule_version: 'recommendations-unit-test', rule_parameters: { review_after_days: 3, calibration: 'uncalibrated' } }
}
// A bounded application-port fixture, not evidence of a real browser/API run.
export function decisionFixture(initial = testRecommendation()) {
  let current = structuredClone(initial)
  const receipts = new Map<string, { input: string; ack: MutationAck }>()
  const read = vi.fn(async (id: string) => { if (id !== current.id) throw new ApiError(404, 'recommendation missing'); return structuredClone(current) })
  const save = vi.fn(async (value: DecisionEnvelope): Promise<MutationAck> => {
    const input = JSON.stringify({ id: value.base.id, hash: value.base.decision_sha256, fields: value.fields })
    const previous = receipts.get(value.command_id)
    if (previous) { if (previous.input !== input) throw new ApiError(409, 'command identity changed'); return structuredClone(previous.ack) }
    if (value.base.decision_sha256 !== current.decision_sha256) throw new ApiError(412, 'decision revision conflict')
    if (current.staleness === 'stale') throw new ApiError(409, 'recommendation basis stale')
    const applied = current.decision !== value.fields.decision || current.decision_reason !== value.fields.reason
    if (applied) current = { ...current, decision: value.fields.decision, decision_reason: value.fields.reason, decision_revision: current.decision_revision + 1, decision_sha256: String(current.decision_revision + 1).repeat(64) }
    const ack = { id: current.id, revision: current.decision_revision, applied }
    receipts.set(value.command_id, { input, ack }); return structuredClone(ack)
  })
  const inspect = vi.fn(async (id: string) => testPage([await read(id)]))
  return { port: { read, save, inspect }, read, save, inspect, current: () => structuredClone(current), external: (item: RecommendationView) => { current = structuredClone(item) } }
}
