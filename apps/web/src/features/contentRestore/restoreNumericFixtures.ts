// Synthetic protocol fixtures. No real numeric execution or academic approval.
import type { RestoreNumericCheckView, RestoreNumericMaterialWrite } from '../../../../../packages/contracts/generated/restore-numeric-types'
import { canonical, digest } from '../retrieval/retrievalModel'
import { publicationDraft } from './restoreFixtures'

export const numericText = '🧮 原文 e\u0301\nGiven x=2, formula x+1 has expected 3. Symbol-only π is not a decimal.\n'
const span = (quote: string) => {
  const start = [...numericText.slice(0, numericText.indexOf(quote))].length
  return { start_codepoint: start, end_codepoint: start + [...quote].length, quote }
}
const metadata = { ...publicationDraft.proposed_block, revision: 1, kind: 'worked_example' as const, body_sha256: digest(numericText) }
export const numericSnapshot = { ...publicationDraft, candidate: { ...publicationDraft.candidate, entity: 'block' as const }, body_markdown: numericText,
  source_ref: { ...publicationDraft.source_ref, entity: 'block' as const, sha256: digest(canonical(metadata)) }, proposed_block: { ...metadata, revision: 3 } }
export const numericMaterial: RestoreNumericMaterialWrite = {
  version: 'restore-numeric-material-v1', symbols: [{ name: 'x', tex: 'x', domain: 'finite real', dimension: 'unitless' }],
  plan: { version: 'finite-arithmetic-v1', variables: [{ name: 'x', value: 2, unit: '1' }],
    assertions: [{ id: 'assert_sum', expression: 'x+1', expected: 3, atol: 0, rtol: 0, unit: '1' }], seed: null },
  variable_bindings: [{ variable_name: 'x', value_source: span('2') }],
  assertion_bindings: [{ assertion_id: 'assert_sum', expression_source: span('x+1'), expected_source: span('3') }],
  reason: 'Synthetic mapping only; no academic validation.',
}
export const numericBody = { candidate: numericSnapshot.candidate, material: numericMaterial }
export const numericPreview: RestoreNumericCheckView = {
  owner: 'authoring_restore', id: 'numeric_synthetic', revision: 1, candidate: numericSnapshot.candidate,
  numeric_material_sha256: 'c'.repeat(64), plan: numericMaterial.plan,
  runtime: { evaluator_version: 'finite-arithmetic-v1', evaluator_sha256: 'd'.repeat(64), runtime_manifest_sha256: 'e'.repeat(64),
    python_version: 'synthetic-no-execution', sandbox_version: 'synthetic-no-execution', wall_seconds: 5, cpu_seconds: 2,
    memory_bytes: 268435456, output_bytes: 65536, evaluator_process_limit: 1 },
  operation_sha256: 'f'.repeat(64), decision: 'pending', created_at: '2026-10-02T00:00:00Z', expires_at: '2026-10-02T00:10:00Z',
  expired: false, job: null, job_revision: null, result: null, warnings: [],
}
export const numericBoundSnapshot = { ...numericSnapshot, numeric_check_ids: [numericPreview.id], numeric_material: {
  owner: 'authoring_restore' as const, candidate: numericSnapshot.candidate, restore_record_sha256: '1'.repeat(64),
  source_ref: numericSnapshot.source_ref, source_material_sha256: numericSnapshot.source_material_sha256,
  body_sha256: metadata.body_sha256, material: numericMaterial, numeric_material_sha256: numericPreview.numeric_material_sha256,
} }
export const numericDecision = { expected_revision: 1, operation_sha256: numericPreview.operation_sha256, decision: 'approve_once' as const }
export const numericDecisionReceipt = { id: numericPreview.id, revision: 2, operation_sha256: numericPreview.operation_sha256,
  decision: 'approve_once' as const, applied: true as const, job: { id: 'numeric_job_synthetic', status: 'queued' as const } }
