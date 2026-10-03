// Controlled wire fixtures only: no physical runtime or human approval evidence.
import { vi } from 'vitest'
import type { AuthoringDraftView, AuthoringJobView, AuthoringBlockRef, NumericCheckView, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
import { reviewSession } from '../draftReview/reviewFixtures'
import { digest } from '../retrieval/retrievalModel'
import type { SinglePublicationPort } from './singlePublicationClient'
import { prepareSingleBasis } from './singlePublicationSchema'

export function singlePublicationFixture() {
  const workspace = `workspace_${crypto.randomUUID()}`, candidate = { draft_id: `draft_${crypto.randomUUID()}`, draft_revision: 1, entity: 'block' as const, candidate_sha256: 'a'.repeat(64) }
  const validation = { schema: 'PASS' as const, references: 'PASS' as const, symbol_declarations: 'PASS' as const, issues: [], mathematical: 'NOT_RUN' as const, sources: 'NOT_RUN' as const, independent_pedagogy: 'NOT_RUN' as const }
  const warning = { code: 'SOURCE_CONFIRM', message: '合成来源材料待确认', severity: 'warning' as const, locator: null }
  const draft: AuthoringDraftView = { owner: 'authoring', candidate, source_job_id: 'job_generation', state: 'draft', published_ref: null, base_ref: null,
    body_sha256: digest('原文 😀：x=3，x*2=6。\n'), payload: { version: 'worked-example-candidate-v1', kind: 'worked_example', title: '合成例题', body_markdown: '原文 😀：x=3，x*2=6。\n', symbols: [{ name: 'x', tex: 'x', domain: 'real', dimension: '1' }], declared_source_refs: [],
      numeric_plan: { version: 'finite-arithmetic-v1', seed: null, variables: [{ name: 'x', value: 3, unit: '1' }], assertions: [{ id: 'assertion_double', expression: 'x*2', expected: 6, atol: 0, rtol: 0, unit: '1' }] } },
    validation, numeric_check_ids: ['check_current'], warnings: [{ ...warning, code: 'AUTHORING_REVIEW_NOT_RUN', message: '原生成阶段显示说明' }] }
  const generation: AuthoringJobView = { summary: { id: draft.source_job_id, kind: 'authoring', status: 'completed', job_revision: 3, title: draft.payload.title, candidate, created_at: '2026-10-01T00:00:00Z', updated_at: '2026-10-01T00:00:01Z' },
    request: { topic: '合成主题', prerequisites: [], objectives: ['计算'], proof_policy: 'full', output_kind: 'worked_example', provider_id: 'provider_synthetic', source_refs: [] },
    preparation: { context_snapshot_id: 'context_synthetic', snapshot_sha256: 'b'.repeat(64), job_input_sha256: 'c'.repeat(64), prepared_input_sha256: 'd'.repeat(64), character_count: 200, materials: [], warnings: [warning] },
    proposal_id: 'proposal_synthetic', consent_id: 'consent_synthetic', provider_receipt_id: 'providerreceipt_synthetic', provider_outcome: 'completed', usage: { input_tokens: 1, output_tokens: 1 }, raw_answer: JSON.stringify(draft.payload), raw_refusal: null, validation, error_code: null }
  const numeric: NumericCheckView = { id: 'check_current', revision: 2, candidate, plan: structuredClone(draft.payload.numeric_plan),
    runtime: { evaluator_version: 'finite-arithmetic-v1', evaluator_sha256: 'b'.repeat(64), runtime_manifest_sha256: 'c'.repeat(64), python_version: 'synthetic-python', sandbox_version: 'synthetic-runtime', wall_seconds: 5, cpu_seconds: 2, memory_bytes: 268435456, output_bytes: 65536, evaluator_process_limit: 1 },
    operation_sha256: 'd'.repeat(64), decision: 'approve_once', created_at: '2026-10-01T00:00:02Z', expires_at: '2026-10-01T00:10:02Z', expired: true, job: { id: 'job_numeric', status: 'completed' }, job_revision: 4,
    result: { job_id: 'job_numeric', input_sha256: 'e'.repeat(64), operation_sha256: 'd'.repeat(64), outcome: 'passed', verdict: 'PASS', started_at: '2026-10-01T00:00:03Z', finished_at: '2026-10-01T00:00:04Z', exit_code: 0, assertions: [{ id: 'assertion_double', actual: 6, passed: true, error_code: null }], output_sha256: 'f'.repeat(64), result_sha256: '1'.repeat(64) },
    warnings: [{ ...warning, message: '同代码另一数值警告实例' }] }
  const receipt: StoredReviewReceipt = { id: 'review_synthetic', revision: 2, candidate, structural: 'PASS', mathematical: 'APPROVED', sources: 'NOT_APPLICABLE', independent_pedagogy: 'NOT_RUN', reviewer: 'human_synthetic', created_at: '2026-10-01T00:00:05Z', evidence_paths: ['/api/v1/artifacts/artifact_synthetic/download'], decision_reason: '合成受控人审理由，无真实质量批准' }
  const ack: AuthoringBlockRef = { entity: 'block', id: 'block_allocated_by_server', revision: 1, sha256: '2'.repeat(64) }
  const session = reviewSession(workspace)
  const port: SinglePublicationPort = { session: vi.fn(async () => structuredClone(session)), draft: vi.fn(async () => structuredClone(draft)), generation: vi.fn(async () => structuredClone(generation)), review: vi.fn(async () => structuredClone(receipt)), numeric: vi.fn(async () => structuredClone(numeric)), publish: vi.fn(async () => structuredClone(ack)), current: vi.fn(async () => structuredClone(ack)) }
  return { workspace, draft, generation, numeric, receipt, ack, session, port, basis: () => prepareSingleBasis(draft, generation, receipt, [numeric]) }
}
