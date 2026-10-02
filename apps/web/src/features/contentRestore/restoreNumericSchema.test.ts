import { expect, test } from 'vitest'
import { numericBody, numericBoundSnapshot, numericDecision, numericDecisionReceipt, numericMaterial, numericPreview, numericSnapshot } from './restoreNumericFixtures'
import { checkedRestoreNumeric, restoreNumericCheck, restoreNumericDecisionAck, restoreNumericMaterial, restoreNumericPreviewAck, restoreNumericSnapshot } from './restoreNumericSchema'
import { canonical, digest } from '../retrieval/retrievalModel'

test('generated models keep explicit null discovery and exact Unicode codepoint material', () => {
  expect(restoreNumericSnapshot(numericSnapshot)).toEqual(numericSnapshot)
  expect(restoreNumericSnapshot(numericBoundSnapshot)).toEqual(numericBoundSnapshot)
  expect(restoreNumericMaterial(numericMaterial, numericSnapshot)).toEqual(numericMaterial)
  expect(restoreNumericCheck(numericPreview, numericPreview.id, numericBoundSnapshot)).toEqual(numericPreview)
  expect(restoreNumericPreviewAck(numericPreview, numericBody)).toEqual(numericPreview)
  expect(restoreNumericDecisionAck(numericDecisionReceipt, numericPreview.id, numericDecision)).toEqual(numericDecisionReceipt)
})
test.each(['missing', 'extra', 'bool', 'infinity', 'empty', 'surrogate', 'huge_span'] as const)('generated material shape rejects %s', fault => {
  const value = structuredClone(numericMaterial)
  const raw: unknown = fault === 'missing' ? { ...value, reason: undefined } : fault === 'extra' ? { ...value, runtime: {} } : value
  if (fault === 'bool') Object.assign(value.variable_bindings[0].value_source, { start_codepoint: true })
  if (fault === 'infinity') value.plan.variables[0].value = Infinity
  if (fault === 'empty') value.reason = ' \n '
  if (fault === 'surrogate') value.reason = '\ud800'
  if (fault === 'huge_span') value.variable_bindings[0].value_source.end_codepoint += 513
  expect(() => restoreNumericMaterial(raw, numericSnapshot)).toThrow()
})
test.each(['utf16', 'number', 'quote', 'normalization', 'missing_binding', 'extra_binding', 'duplicate_symbol', 'duplicate_assertion', 'wrong_symbol'] as const)('material relationships reject %s without normalizing the saved source', fault => {
  const value = structuredClone(numericMaterial), span = value.variable_bindings[0].value_source
  if (fault === 'utf16') { span.start_codepoint++; span.end_codepoint++ }
  if (fault === 'number') value.plan.variables[0].value = 5
  if (fault === 'quote') span.quote = '9'
  if (fault === 'normalization') {
    const start = [...numericSnapshot.body_markdown.slice(0, numericSnapshot.body_markdown.indexOf('e\u0301'))].length
    Object.assign(value.assertion_bindings[0].expression_source, { start_codepoint: start, end_codepoint: start + 2, quote: 'é' })
  }
  if (fault === 'missing_binding') value.variable_bindings = []
  if (fault === 'extra_binding') value.variable_bindings.push({ ...value.variable_bindings[0], variable_name: 'y' })
  if (fault === 'duplicate_symbol') value.symbols.push(value.symbols[0])
  if (fault === 'duplicate_assertion') value.plan.assertions.push(value.plan.assertions[0])
  if (fault === 'wrong_symbol') value.symbols[0].name = 'y'
  expect(() => restoreNumericMaterial(value, numericSnapshot)).toThrow()
})
test.each(['01', '+2', '2 ', ' 2', '2\n', '2m', '2%', '\\frac{2}{1}', 'π', '1e999'] as const)('source quote %s is not an accepted finite JSON number', quote => {
  const value = structuredClone(numericMaterial), snapshot = { ...numericSnapshot, body_markdown: quote }
  Object.assign(value.variable_bindings[0].value_source, { start_codepoint: 0, end_codepoint: [...quote].length, quote })
  expect(() => restoreNumericMaterial(value, snapshot)).toThrow()
})
test.each(['missing_null', 'orphan_check', 'orphan_material', 'foreign_candidate', 'foreign_body', 'other_kind', 'duplicate_checks'] as const)('snapshot discovery rejects %s', fault => {
  const value = structuredClone(numericBoundSnapshot)
  if (fault === 'missing_null') Object.assign(value, { numeric_material: undefined })
  if (fault === 'orphan_check') Object.assign(value, { numeric_material: null })
  if (fault === 'orphan_material') value.numeric_check_ids = []
  if (fault === 'foreign_candidate') value.numeric_material.candidate = { ...value.numeric_material.candidate, draft_id: 'foreign_draft' }
  if (fault === 'foreign_body') value.numeric_material.body_sha256 = '0'.repeat(64)
  if (fault === 'other_kind') Object.assign(value.proposed_block, { kind: 'theorem' })
  if (fault === 'duplicate_checks') value.numeric_check_ids.push(value.numeric_check_ids[0])
  expect(() => restoreNumericSnapshot(value)).toThrow()
})
test.each(['owner', 'id', 'plan', 'material', 'decision', 'runtime', 'expiry', 'job_revision'] as const)('checked state rejects %s mismatch', fault => {
  const value = structuredClone(numericPreview)
  if (fault === 'owner') Object.assign(value, { owner: 'authoring_single' })
  if (fault === 'id') value.id = 'check_foreign'
  if (fault === 'plan') value.plan.variables[0].value = 9
  if (fault === 'material') value.numeric_material_sha256 = '0'.repeat(64)
  if (fault === 'decision') value.decision = 'approve_once'
  if (fault === 'runtime') Object.assign(value.runtime, { wall_seconds: true })
  if (fault === 'expiry') value.expires_at = '2026-10-02T00:11:00Z'
  if (fault === 'job_revision') value.job_revision = 2
  expect(() => restoreNumericCheck(value, numericPreview.id, numericBoundSnapshot)).toThrow()
})
test('current GET is separate from the original preview/decision ACK', () => {
  const current = { ...numericPreview, revision: 2, decision: 'decline' as const, expired: true }
  expect(restoreNumericCheck(current)).toEqual(current)
  expect(() => restoreNumericPreviewAck(current, numericBody)).toThrow()
  for (const value of [{ ...numericDecisionReceipt, id: 'wrong_check' }, { ...numericDecisionReceipt, revision: 3 },
    { ...numericDecisionReceipt, job: { ...numericDecisionReceipt.job, status: 'completed' } }]) {
    expect(() => restoreNumericDecisionAck(value, numericPreview.id, numericDecision)).toThrow()
  }
  expect(() => checkedRestoreNumeric('UnknownShape', {})).toThrow()
})
test('a synthetic terminal result must bind the exact original job, complete assertions and canonical facts', () => {
  const facts = { job_id: numericDecisionReceipt.job.id, input_sha256: '2'.repeat(64), operation_sha256: numericPreview.operation_sha256,
    outcome: 'passed' as const, verdict: 'PASS' as const, started_at: '2026-10-02T00:01:00Z', finished_at: '2026-10-02T00:01:01Z', exit_code: 0,
    assertions: [{ id: 'assert_sum', actual: 3, passed: true, error_code: null }], output_sha256: '3'.repeat(64) }
  const value = { ...numericPreview, revision: 2, decision: 'approve_once' as const, job: { ...numericDecisionReceipt.job, status: 'completed' as const }, job_revision: 3,
    result: { ...facts, result_sha256: digest(canonical(facts)) } }
  expect(restoreNumericCheck(value)).toEqual(value)
  for (const changed of [{ ...facts, exit_code: 1 }, { ...facts, assertions: [{ ...facts.assertions[0], actual: 4 }] },
    { ...facts, job_id: 'other_job' }, { ...facts, output_sha256: null }]) {
    expect(() => restoreNumericCheck({ ...value, result: { ...changed, result_sha256: digest(canonical(changed)) } })).toThrow()
  }
})
