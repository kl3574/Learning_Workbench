import 'fake-indexeddb/auto'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { AssessmentResult } from '@review/features/grading/AssessmentResult'
import { gradingJob, gradingResult, gradingSnapshot } from '@review/features/grading/grading.testdata'
const calls = vi.hoisted(() => ({ request: vi.fn(), generation: 0 }))
vi.mock('@review/api/client', () => ({ getSessionGeneration: () => calls.generation, subscribeSessionAccess: () => () => {}, request: (...args: unknown[]) => calls.request(...args), ApiError: class extends Error { status = 409 } }))
vi.mock('@review/shared/Markdown', () => ({ Markdown: ({ children }: { children: string }) => <p>{children}</p> }))
afterEach(cleanup)
test.each(['failed', 'cancelled'] as const)('an existing grade must permit explicit recovery after regrade job becomes %s', async (status) => {
  const originalGrade = gradingResult()
  originalGrade.status = 'graded'
  originalGrade.items[0] = { ...originalGrade.items[0], score: 0.5, status: 'graded', feedback_markdown: 'Real prior score from the bounded response fixture', solution_markdown: null }
  calls.request.mockImplementation(async (route: string) => route.endsWith('/session') ? { workspace_id: 'workspace_original', role: 'author' } : route.includes('/jobs/') ? gradingJob(status) : { id: 'job_original', status, last_completed_result: originalGrade })
  render(<AssessmentResult workspace="workspace_original" snapshot={{ ...gradingSnapshot(), status: 'needs_review', grading_revision: 1, grading_status: status }} changed={() => {}} onState={() => {}} />)
  await screen.findByRole('heading', { name: status === 'failed' ? '评分任务失败' : '评分任务已取消' })
  await waitFor(() => expect(screen.getByText('本机复核草稿存储可用', { exact: true })).toBeTruthy())
  const button = screen.getByRole('button', { name: '填写人工复核', exact: true }) as HTMLButtonElement
  await waitFor(() => expect(button.disabled, 'Actual author has no editable/recovery baseline after a failed/cancelled regrade, despite prior grading_revision=1 remaining immutable on server').toBe(false))
})
