import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { JobSnapshot } from '../../../../../packages/contracts/generated/api-types'
import { AuthoringControlList } from './AuthoringControlList'
afterEach(cleanup)
const job = (kind: string, id: string): JobSnapshot => ({ id, kind, workspace_id: 'workspace_authoring_test', status: 'running', revision: 3, created_at: '2026-09-16T00:00:00Z', updated_at: '2026-09-16T00:00:01Z', progress: { completed: 0, total: null, label: '禁止显示原主题' }, result_refs: [], warnings: [], error: { code: 'TEST_FAILURE', message: '禁止显示原错误正文', request_id: 'request_synthetic', retryable: false } })
test('both kinds remain cancellable without academic access; numeric controls reveal no protected association', () => {
  const generation = job('authoring', 'job_generation'), numeric = job('authoring_numeric_check', 'job_numeric'), cancel = vi.fn(), read = vi.fn()
  render(<AuthoringControlList jobs={[generation, numeric]} busy={false} academic={false} read={read} cancel={cancel} />)
  fireEvent.click(screen.getByRole('button', { name: '明确取消任务 job_numeric' }))
  expect(cancel).toHaveBeenCalledWith(numeric)
  expect(screen.getByText('job_generation · running · r3')).toBeTruthy()
  expect(screen.queryByText('禁止显示原主题')).toBeNull()
  expect(screen.queryByText('禁止显示原错误正文')).toBeNull()
  expect(screen.queryByRole('button', { name: /读取创作详情/ })).toBeNull()
  expect(read).not.toHaveBeenCalled()
})
