import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { ReviewPanel } from '../draftReview/ReviewPanel'
import type { ReviewPort } from '../draftReview/reviewClient'
import { safeReviewJob } from '../draftReview/reviewFixtures'
import { discardReviewForms } from '../draftReview/reviewFormMemory'
import { singlePublicationFixture } from './singlePublicationFixtures'
import { discardSinglePublicationForms, discardSinglePublicationMemory } from './singlePublicationMemory'
const workspaces: string[] = []
afterEach(() => { cleanup(); vi.unstubAllGlobals(); for (const workspace of workspaces.splice(0)) { discardReviewForms(workspace, 'authoring_single'); discardSinglePublicationForms(workspace); discardSinglePublicationMemory(workspace) } })
function fixture() {
  const f = singlePublicationFixture(); workspaces.push(f.workspace)
  const job = { ...safeReviewJob(f.workspace), id: f.receipt.id }
  const port: ReviewPort = { session: f.port.session, candidate: vi.fn(async () => f.draft.candidate), create: vi.fn(), read: f.port.review, decide: vi.fn(), job: vi.fn(async () => job), cancel: vi.fn(), artifact: vi.fn() }
  vi.stubGlobal('fetch', vi.fn(async (path: string) => {
    const value = path === '/api/v1/session' ? f.session : path.includes('/authoring/drafts/') ? f.draft : path.includes('/authoring/jobs/') ? f.generation : path.includes('/numeric-checks/') ? f.numeric : path.includes('/reviews/') ? f.receipt : null
    if (!value) throw new Error('Unexpected route in read-only preparation')
    return new Response(JSON.stringify(value))
  }))
  return { ...f, port }
}
test('named single Review branch retains its separate publish confirmation and exposes explicit discard with original unsent Review reason', async () => {
  const f = fixture(), onState = vi.fn()
  render(<ReviewPanel workspace={f.workspace} paused={false} candidate={f.draft.candidate} singleDraft={f.draft} port={f.port} onState={onState} />)
  fireEvent.change(screen.getByLabelText('已有服务端审核 ID'), { target: { value: f.receipt.id } })
  const select = screen.getByRole('button', { name: '读取这个审核任务' }) as HTMLButtonElement
  await waitFor(() => expect(select.disabled).toBe(false)); fireEvent.click(select)
  const read = await screen.findByRole('button', { name: '另行读取当前审核回执' }) as HTMLButtonElement; await waitFor(() => expect(read.disabled).toBe(false)); fireEvent.click(read)
  await waitFor(() => expect((screen.getByRole('button', { name: '选择此审核并重新读取生成发布基准' }) as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(screen.getByRole('button', { name: '选择此审核并重新读取生成发布基准' }))
  const basis = await screen.findByRole('region', { name: '本次生成发布基准' }); await waitFor(() => expect((within(basis).getAllByRole('checkbox')[0] as HTMLInputElement).disabled).toBe(false))
  within(basis).getAllByRole('checkbox').forEach(box => fireEvent.click(box))
  const reason = screen.getByLabelText('审核理由') as HTMLTextAreaElement; await waitFor(() => expect(reason.matches(':disabled')).toBe(false)); fireEvent.change(reason, { target: { value: 'UNSENT_SYNTHETIC_REASON' } })
  await waitFor(() => expect(onState.mock.lastCall?.[0].dirty).toBe(true))
  act(() => onState.mock.lastCall?.[0].discardForms())
  await waitFor(() => expect(reason.value).toBe('')); expect((within(basis).getAllByRole('checkbox').at(-1) as HTMLInputElement).checked).toBe(false)
  expect(f.port.decide).not.toHaveBeenCalled(); expect(vi.mocked(fetch).mock.calls.every(([, init]) => init?.method === 'GET')).toBe(true)
})
test('group Review entry has no single publication controls without the named single DTO branch', async () => {
  const f = fixture(); render(<ReviewPanel workspace={f.workspace} paused={false} candidate={{ ...f.draft.candidate, entity: 'lesson' }} formOwner="authoring_group" port={f.port} />)
  await screen.findByRole('button', { name: '明确创建本次审核任务' }); expect(screen.queryByRole('region', { name: '生成例题发布与恢复' })).toBeNull()
})
