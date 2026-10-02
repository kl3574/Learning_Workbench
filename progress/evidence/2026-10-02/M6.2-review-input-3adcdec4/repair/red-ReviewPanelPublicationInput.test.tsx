import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { ReviewPanel } from './ReviewPanel'
import type { ReviewPort } from './reviewClient'
import { machineReceipt, reviewSession, safeReviewJob } from './reviewFixtures'
import { discardReviewForms, originalReviewForms, type ReviewPanelState } from './reviewFormMemory'
import { reviewCommandStore, reviewControlStore, reviewJobStore } from './reviewCommands'
import { publicationClient } from '../draftPublication/publicationClient'
import { publicationCommandStore } from '../draftPublication/publicationCommands'
import { publicationDraft, publicationReceipt } from '../draftPublication/publicationFixtures'

const workspaces: string[] = []
afterEach(async () => {
  cleanup(); for (const workspace of workspaces.splice(0)) discardReviewForms(workspace, 'import')
  vi.restoreAllMocks()
  await Promise.all([reviewCommandStore.close(), reviewControlStore.close(), reviewJobStore.close(), publicationCommandStore.close()])
})
function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(accept => { resolve = accept })
  return { promise, resolve }
}
async function publicationReady() {
  await waitFor(() => expect(screen.queryByText('正在核验或当前权限不允许发布；本机原命令保留，保护内容已收起。')).toBeNull())
  await waitFor(() => expect((screen.getByRole('button', { name: '重新核验发布权限与本机记录' }) as HTMLButtonElement).disabled).toBe(false))
}

for (const recovered of [false, true]) test(`${recovered ? 'recovered' : 'current'} Review input stays local during Publication read while every submission and parent close stay blocked`, async () => {
  const workspace = `workspace_${crypto.randomUUID()}`; workspaces.push(workspace)
  const candidate = publicationReceipt.candidate, receipt = { ...machineReceipt, candidate }
  const port: ReviewPort = {
    candidate: vi.fn(async () => structuredClone(candidate)), session: vi.fn(async () => reviewSession(workspace)),
    create: vi.fn(async () => ({ id: receipt.id, status: 'queued' as const })), read: vi.fn(async () => structuredClone(receipt)),
    decide: vi.fn(async () => { throw new Error('No automatic decision allowed') }),
    job: vi.fn(async () => safeReviewJob(workspace)), cancel: vi.fn(async () => ({ ...safeReviewJob(workspace), status: 'cancelled' as const })),
    artifact: vi.fn(async () => { throw new Error('No automatic artifact read allowed') }),
  }
  const session = vi.spyOn(publicationClient, 'session').mockImplementation(async () => reviewSession(workspace))
  const states: ReviewPanelState[] = [], onState = (state: ReviewPanelState) => states.push(state)
  const props = { workspace, paused: false, candidate, importDraft: publicationDraft, port, formScope: 'import', onState }
  const view = render(<ReviewPanel {...props} />)
  await screen.findByLabelText('本次审核备注'); await publicationReady()
  fireEvent.change(screen.getByLabelText('已有服务端审核 ID'), { target: { value: receipt.id } })
  fireEvent.click(screen.getByRole('button', { name: '读取这个审核任务' }))
  const read = await screen.findByRole('button', { name: '另行读取当前审核回执' })
  await waitFor(() => expect((read as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(read)
  await screen.findByLabelText('审核理由'); await publicationReady()
  fireEvent.change(screen.getByLabelText('本次审核备注'), { target: { value: 'Original note 🧠' } })
  fireEvent.change(screen.getByLabelText('审核理由'), { target: { value: 'Original reason é' } })
  if (recovered) {
    view.rerender(<ReviewPanel {...props} paused candidate={null} importDraft={null} />)
    expect(screen.queryByDisplayValue('Original note 🧠')).toBeNull()
    view.rerender(<ReviewPanel {...props} />)
    await publicationReady()
    const recover = screen.getByRole('button', { name: '核验原会话与准确基准，恢复临时审核表单' })
    await waitFor(() => expect((recover as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(recover)
    await screen.findByRole('region', { name: '恢复的临时审核表单 2' })
  }
  const gate = deferred<ReturnType<typeof reviewSession>>()
  session.mockReturnValueOnce(gate.promise)
  const priorReads = session.mock.calls.length
  fireEvent.click(screen.getByRole('button', { name: '重新核验发布权限与本机记录' }))
  await waitFor(() => expect(session.mock.calls.length).toBe(priorReads + 1))
  await waitFor(() => expect(states.at(-1)?.safe).toBe(false))
  const note = screen.getByLabelText('本次审核备注') as HTMLTextAreaElement
  const reason = screen.getByLabelText('审核理由') as HTMLTextAreaElement
  expect(note.disabled).toBe(false); expect(reason.disabled).toBe(false)
  fireEvent.change(note, { target: { value: 'Continuing note 🧠\né' } })
  fireEvent.change(reason, { target: { value: 'Continuing explicit reason' } })
  fireEvent.change(screen.getByLabelText('数学审核决定'), { target: { value: 'REJECTED' } })
  fireEvent.change(screen.getByLabelText('来源审核决定'), { target: { value: 'REJECTED' } })
  fireEvent.click(screen.getByLabelText('我已核对候选 ID、修订、哈希与本次检查范围，明确创建审核任务。'))
  fireEvent.click(screen.getByLabelText('我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。'))
  const create = screen.getByRole('button', { name: '明确创建本次审核任务' }), decide = screen.getByRole('button', { name: '明确保存这次人工审核决定' })
  expect((create as HTMLButtonElement).disabled).toBe(true); expect((decide as HTMLButtonElement).disabled).toBe(true)
  fireEvent.click(create); fireEvent.click(decide)
  expect(port.create).not.toHaveBeenCalled(); expect(port.decide).not.toHaveBeenCalled()
  const forms = originalReviewForms(workspace, 'import', reviewSession(workspace).actor_session_id)
  expect(forms).toHaveLength(2)
  expect(forms[0].value).toMatchObject({ note: 'Continuing note 🧠\né' })
  expect(forms[1].value).toMatchObject({ reason: 'Continuing explicit reason' })
  // Local edit availability must not weaken the actual Review Policy boundary,
  // including a late successful response from the subordinate Publication read.
  view.rerender(<ReviewPanel {...props} paused candidate={null} importDraft={null} />)
  await act(async () => gate.resolve(reviewSession(workspace)))
  expect(screen.queryByLabelText('本次审核备注')).toBeNull(); expect(screen.queryByLabelText('审核理由')).toBeNull()
  view.rerender(<ReviewPanel {...props} />); await publicationReady()
  const recover = screen.getByRole('button', { name: '核验原会话与准确基准，恢复临时审核表单' })
  await waitFor(() => expect((recover as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(recover)
  const original = await screen.findByRole('region', { name: '恢复的临时审核表单 1' })
  expect((within(original).getByLabelText('本次审核备注') as HTMLTextAreaElement).value).toBe('Continuing note 🧠\né')
  expect((screen.getByLabelText('审核理由') as HTMLTextAreaElement).value).toBe('Continuing explicit reason')
  expect(port.create).not.toHaveBeenCalled(); expect(port.decide).not.toHaveBeenCalled()
})
