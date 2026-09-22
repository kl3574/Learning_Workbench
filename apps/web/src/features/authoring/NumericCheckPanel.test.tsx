import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { NumericCheckView } from '../../../../../packages/contracts/generated/api-types'
import { NumericCheckPanel } from './NumericCheckPanel'
afterEach(cleanup)
const value: NumericCheckView = { id: 'check_original', revision: 1, candidate: { draft_id: 'draft_example', draft_revision: 1, entity: 'block', candidate_sha256: 'a'.repeat(64) }, plan: { version: 'finite-arithmetic-v1', seed: null, variables: [{ name: 'x', value: 3, unit: 'm' }], assertions: [{ id: 'assertion_original', expression: 'x * 2', expected: 6, unit: 'm', atol: 0, rtol: 0 }] }, runtime: { evaluator_version: 'finite-arithmetic-v1', evaluator_sha256: 'b'.repeat(64), runtime_manifest_sha256: 'c'.repeat(64), python_version: '3.12 test fixture', sandbox_version: 'test fixture only', wall_seconds: 5, cpu_seconds: 2, memory_bytes: 268435456, output_bytes: 65536, evaluator_process_limit: 1 }, operation_sha256: 'd'.repeat(64), decision: 'pending', created_at: '2026-09-16T00:00:00Z', expires_at: '2026-09-16T00:10:00Z', expired: false, job: null, job_revision: null, result: null, warnings: [] }
test('confirmation belongs to the exact numeric operation and cannot approve a replacement preview', () => {
  const decide = vi.fn(), props = { value, busy: false, decide, refresh: vi.fn() }, view = render(<NumericCheckPanel {...props} />)
  expect((screen.getByRole('button', { name: '明确批准本次数值执行' }) as HTMLButtonElement).disabled).toBe(true)
  fireEvent.click(screen.getByRole('checkbox')); expect((screen.getByRole('button', { name: '明确批准本次数值执行' }) as HTMLButtonElement).disabled).toBe(false)
  view.rerender(<NumericCheckPanel {...props} value={{ ...value, id: 'check_replacement', operation_sha256: 'e'.repeat(64) }} />)
  expect((screen.getByRole('button', { name: '明确批准本次数值执行' }) as HTMLButtonElement).disabled).toBe(true)
  expect(decide).not.toHaveBeenCalled()
})
test('expired previews can only be declined; raw operation hash and original revision are preserved', () => {
  const decide = vi.fn(); render(<NumericCheckPanel value={{ ...value, expired: true }} busy={false} decide={decide} refresh={vi.fn()} />)
  expect((screen.getByRole('button', { name: '明确批准本次数值执行' }) as HTMLButtonElement).disabled).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: '明确拒绝本次数值执行' }))
  expect(decide).toHaveBeenCalledWith({ decision: 'decline', expected_revision: 1, operation_sha256: 'd'.repeat(64) })
  expect(screen.getByText(/不检查维度相容/)).toBeTruthy()
})
