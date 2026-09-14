import 'fake-indexeddb/auto'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterAll, afterEach, beforeAll, expect, test, vi } from 'vitest'
import type { AssessmentGradingJob, RegradeRequest } from '../../../../../packages/contracts/generated/api-types'
import { AssessmentResult } from './AssessmentResult'
import { gradingJob, gradingResult, gradingSnapshot } from './grading.testdata'
const transport = vi.hoisted(() => vi.fn())
vi.mock('../../api/client', () => ({ request: (...args: unknown[]) => transport(...args), getSessionGeneration: () => 0, subscribeSessionAccess: () => () => {}, ApiError: class extends Error { status = 409 } }))
vi.mock('../../shared/Markdown', () => ({ Markdown: ({ children }: { children: string }) => <p>{children}</p> }))
// JSDOM does not implement the native modal methods; browser behavior is covered by native tests.
beforeAll(() => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value(this: HTMLDialogElement) { this.setAttribute('open', '') } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value(this: HTMLDialogElement) { this.removeAttribute('open') } })
})
afterEach(cleanup)
afterAll(() => { vi.restoreAllMocks(); Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal'); Reflect.deleteProperty(HTMLDialogElement.prototype, 'close') })
test.each(['failed', 'cancelled'] as const)('a %s regrade retains the real previous score and allows a new explicit command with its grading revision', async status => {
  const id = `attempt_${status}`, previous = gradingResult(id)
  previous.status = 'graded'; previous.items[0] = { ...previous.items[0], status: 'graded', score: 0.5, feedback_markdown: '上一版冻结的合成复核依据' }
  const pending: AssessmentGradingJob = { id: 'job_original', status, last_completed_result: previous }
  const commands: RegradeRequest[] = []
  transport.mockImplementation(async (route: string, body: unknown) => {
    if (route.endsWith('/session')) return { workspace_id: 'workspace_original', role: 'author' }
    if (route.includes('/jobs/')) return gradingJob(status)
    if (route.endsWith('/regrade')) { commands.push(body as RegradeRequest); return { id: 'job_recovery', status: 'queued' } }
    return pending
  })
  render(<AssessmentResult workspace="workspace_original" snapshot={{ ...gradingSnapshot(id), grading_revision: 1, grading_status: status, status: 'graded' }} changed={() => {}} onState={() => {}} />)
  await screen.findByRole('heading', { name: status === 'failed' ? '评分任务失败' : '评分任务已取消' })
  const retained = await screen.findByRole('region', { name: '上次已完成评分' })
  expect(retained.textContent).toContain('上次已完成评分（本次任务尚未完成）'); expect(retained.textContent).toContain('0.5 / 2')
  expect(screen.queryByRole('region', { name: '当前评分结果' })).toBeNull()
  const begin = screen.getByRole('button', { name: '填写人工复核' }) as HTMLButtonElement
  await waitFor(() => expect(begin.disabled).toBe(false)); fireEvent.click(begin)
  fireEvent.change(screen.getByLabelText('人工复核理由'), { target: { value: '基于上一版真实评分重新复核' } })
  fireEvent.click(screen.getByRole('checkbox', { name: '复核第 1 题' }))
  fireEvent.change(screen.getByLabelText('第 1 题人工分数'), { target: { value: '0.25' } })
  fireEvent.change(screen.getByLabelText('第 1 题复核依据'), { target: { value: '原创受控界面测试的新依据' } })
  const submit = screen.getByRole('button', { name: '提交人工复核' }) as HTMLButtonElement
  await waitFor(() => expect(submit.disabled).toBe(false)); fireEvent.click(submit); fireEvent.click(screen.getByRole('button', { name: '确认提交人工分数与依据' }))
  await waitFor(() => expect(commands).toHaveLength(1)); expect(commands[0]).toMatchObject({ expected_grading_revision: 1, item_reviews: [{ question_id: 'question_original', score: 0.25 }] })
  expect(previous.items[0].score).toBe(0.5)
  await waitFor(() => expect(screen.queryByText('本机复核草稿保存中…', { exact: true })).toBeNull())
})
