// Strict Python NumericCheckResult serialization; synthetic protocol fact, not an executed sandbox result.
import { expect, test } from 'vitest'
import { numericPreview, numericDecisionReceipt } from './restoreNumericFixtures'
import { restoreNumericCheck } from './restoreNumericSchema'
const result = {"assertions":[{"actual":3.0,"error_code":null,"id":"assert_sum","passed":true}],"exit_code":0,"finished_at":"2026-10-02T00:01:01Z","input_sha256":"2222222222222222222222222222222222222222222222222222222222222222","job_id":"numeric_job_synthetic","operation_sha256":"ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff","outcome":"passed","output_sha256":"3333333333333333333333333333333333333333333333333333333333333333","result_sha256":"8e2af85b8e53707fa4b12893384de8ed22aa10e4cad900cf1586392c3be422db","started_at":"2026-10-02T00:01:00Z","verdict":"PASS"}
test('Python canonical numeric result survives actual JSON number decoding', () => {
  const current = { ...numericPreview, revision: 2, decision: 'approve_once', job: { ...numericDecisionReceipt.job, status: 'completed' }, job_revision: 3, result }
  expect(() => restoreNumericCheck(JSON.parse(JSON.stringify(current)))).not.toThrow()
})
