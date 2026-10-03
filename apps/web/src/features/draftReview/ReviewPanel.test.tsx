import 'fake-indexeddb/auto'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { ReviewPort } from './reviewClient'
import { ReviewPanel } from './ReviewPanel'
import { reviewCandidate, machineReceipt, reviewSession, safeReviewJob } from './reviewFixtures'
import { discardReviewForms, pendingReviewForms, type ReviewPanelState } from './reviewFormMemory'
import { reviewCommandStore, reviewControlStore, reviewJobStore } from './reviewCommands'
HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', '') }
HTMLDialogElement.prototype.close = function () { this.removeAttribute('open') }

const workspaces: string[] = []
afterEach(async () => { cleanup(); for (const workspace of workspaces.splice(0)) discardReviewForms(workspace, 'authoring_single'); vi.restoreAllMocks(); await Promise.all([reviewCommandStore.close(), reviewControlStore.close(), reviewJobStore.close()]) })
function fixture() {
  const workspace = `workspace_${crypto.randomUUID()}`
  workspaces.push(workspace)
  const port: ReviewPort = { candidate: vi.fn(async () => structuredClone(reviewCandidate)), session: vi.fn(async () => reviewSession(workspace)),
    create: vi.fn(async () => ({ id: machineReceipt.id, status: 'queued' as const })), read: vi.fn(async () => structuredClone(machineReceipt)),
    decide: vi.fn(async (_id, body) => ({ ...machineReceipt, revision: 2, mathematical: body.mathematical, sources: body.sources, decision_reason: body.reason, reviewer: 'synthetic_current_author' })),
    job: vi.fn(async () => safeReviewJob(workspace)), cancel: vi.fn(async () => ({ ...safeReviewJob(workspace), status: 'cancelled' as const })),
    artifact: vi.fn(async () => { throw new Error('Unexpected automatic artifact download') }),
  }
  return { workspace, port }
}

test('candidate creation and human rejection each require their own explicit intent and exact basis', async () => {
  const { workspace, port } = fixture(), onState = vi.fn()
  render(<ReviewPanel workspace={workspace} paused={false} candidate={reviewCandidate} candidateState="draft" port={port} onState={onState} />)
  const create = await screen.findByRole('button', { name: '明确创建本次审核任务' })
  expect((create as HTMLButtonElement).disabled).toBe(true)
  expect(port.create).not.toHaveBeenCalled(); expect(port.decide).not.toHaveBeenCalled()
  fireEvent.change(screen.getByLabelText('本次审核备注'), { target: { value: 'Synthetic private note' } })
  fireEvent.click(screen.getByLabelText('我已核对候选 ID、修订、哈希与本次检查范围，明确创建审核任务。'))
  fireEvent.click(create)
  await waitFor(() => expect(port.create).toHaveBeenCalledTimes(1))
  expect(vi.mocked(port.create).mock.calls[0][0]).toBe(reviewCandidate.draft_id)
  expect(vi.mocked(port.create).mock.calls[0][1]).toEqual({ expected_revision: 1, checks: ['structure', 'numerical_examples', 'mathematics', 'sources'], reviewer_note: 'Synthetic private note' })
  const read = await screen.findByRole('button', { name: '另行读取当前审核回执' })
  await waitFor(() => expect((read as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(read)
  const decision = await screen.findByRole('region', { name: '明确人工审核决定' })
  const math = within(decision).getByLabelText('数学审核决定'), sources = within(decision).getByLabelText('来源审核决定')
  expect((math as HTMLSelectElement).value).toBe(''); expect((sources as HTMLSelectElement).value).toBe('')
  fireEvent.change(math, { target: { value: 'REJECTED' } }); fireEvent.change(sources, { target: { value: 'REJECTED' } })
  fireEvent.change(within(decision).getByLabelText('审核理由'), { target: { value: 'Synthetic explicit rejection, not real approval' } })
  const submit = within(decision).getByRole('button', { name: '明确保存这次人工审核决定' })
  expect((submit as HTMLButtonElement).disabled).toBe(true)
  expect(port.decide).not.toHaveBeenCalled()
  fireEvent.click(within(decision).getByLabelText('我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。')); fireEvent.click(submit)
  await waitFor(() => expect(port.decide).toHaveBeenCalledTimes(1))
  const body = vi.mocked(port.decide).mock.calls[0][1]
  expect(body).toEqual({ expected_revision: 1, candidate_sha256: reviewCandidate.candidate_sha256, mathematical: 'REJECTED', sources: 'REJECTED', reason: 'Synthetic explicit rejection, not real approval', evidence_artifact_ids: [] })
  expect('reviewer' in body).toBe(false)
  expect(port.artifact).not.toHaveBeenCalled()
})

test('a receipt for another candidate remains read-only and Policy pause removes private form content', async () => {
  const { workspace, port } = fixture()
  vi.mocked(port.read).mockResolvedValue({ ...machineReceipt, candidate: { ...reviewCandidate, candidate_sha256: 'b'.repeat(64) } })
  const view = render(<ReviewPanel workspace={workspace} paused={false} candidate={reviewCandidate} port={port} />)
  const input = await screen.findByLabelText('已有服务端审核 ID')
  await waitFor(() => expect((screen.getByRole('button', { name: '读取这个审核任务' }) as HTMLButtonElement).disabled).toBe(true))
  fireEvent.change(input, { target: { value: machineReceipt.id } })
  const select = screen.getByRole('button', { name: '读取这个审核任务' })
  await waitFor(() => expect((select as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(select)
  const read = await screen.findByRole('button', { name: '另行读取当前审核回执' })
  await waitFor(() => expect((read as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(read)
  await screen.findByRole('region', { name: '当前审核回执' })
  expect(screen.queryByRole('region', { name: '明确人工审核决定' })).toBeNull()
  fireEvent.change(screen.getByLabelText('本次审核备注'), { target: { value: 'PRIVATE_SYNTHETIC_FORM' } })
  view.rerender(<ReviewPanel workspace={workspace} paused candidate={null} port={port} />)
  expect(screen.queryByDisplayValue('PRIVATE_SYNTHETIC_FORM')).toBeNull()
  expect(screen.queryByRole('region', { name: '当前审核回执' })).toBeNull()
  expect(screen.getByRole('region', { name: '安全审核任务' })).toBeTruthy()
})

test('unsubmitted reason survives rereading the same receipt and does not carry into a new revision', async () => {
  const { workspace, port } = fixture()
  render(<ReviewPanel workspace={workspace} paused={false} candidate={reviewCandidate} port={port} />)
  await screen.findByRole('button', { name: '明确创建本次审核任务' })
  fireEvent.change(screen.getByLabelText('已有服务端审核 ID'), { target: { value: machineReceipt.id } })
  fireEvent.click(screen.getByRole('button', { name: '读取这个审核任务' }))
  const read = await screen.findByRole('button', { name: '另行读取当前审核回执' })
  await waitFor(() => expect((read as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(read)
  fireEvent.change(await screen.findByLabelText('审核理由'), { target: { value: 'SYNTHETIC_UNSUBMITTED_REASON' } })
  fireEvent.click(screen.getByRole('button', { name: '重新读取审核回执' }))
  await waitFor(() => expect((screen.getByLabelText('审核理由') as HTMLTextAreaElement).value).toBe('SYNTHETIC_UNSUBMITTED_REASON'))
  vi.mocked(port.read).mockResolvedValueOnce({ ...machineReceipt, revision: 2 })
  fireEvent.click(screen.getByRole('button', { name: '重新读取审核回执' }))
  await screen.findByRole('heading', { name: '实际审核回执 r2' })
  expect((screen.getByLabelText('审核理由') as HTMLTextAreaElement).value).toBe('')
  fireEvent.click(screen.getByRole('button', { name: '重新读取审核回执' }))
  await screen.findByRole('heading', { name: '实际审核回执 r1' })
  expect((screen.getByLabelText('审核理由') as HTMLTextAreaElement).value).toBe('SYNTHETIC_UNSUBMITTED_REASON')
  expect(port.decide).not.toHaveBeenCalled()
})

test('candidate switches retain the original note without applying it to a different candidate', async () => {
  const { workspace, port } = fixture()
  const view = render(<ReviewPanel workspace={workspace} paused={false} candidate={reviewCandidate} port={port} />)
  fireEvent.change(await screen.findByLabelText('本次审核备注'), { target: { value: 'SYNTHETIC_ORIGINAL_NOTE' } })
  view.rerender(<ReviewPanel workspace={workspace} paused={false} candidate={{ ...reviewCandidate, candidate_sha256: 'b'.repeat(64) }} port={port} />)
  expect((screen.getByLabelText('本次审核备注') as HTMLTextAreaElement).value).toBe('')
  view.rerender(<ReviewPanel workspace={workspace} paused={false} candidate={reviewCandidate} port={port} />)
  expect((screen.getByLabelText('本次审核备注') as HTMLTextAreaElement).value).toBe('SYNTHETIC_ORIGINAL_NOTE')
  expect(port.create).not.toHaveBeenCalled()
})

test('permission refresh explicitly discards forms while Policy revocation hides them until fresh recovery', async () => {
  const { workspace, port } = fixture()
  const view = render(<ReviewPanel workspace={workspace} paused={false} candidate={reviewCandidate} port={port} />)
  fireEvent.change(await screen.findByLabelText('本次审核备注'), { target: { value: 'SYNTHETIC_PENDING_NOTE' } })
  const leaving = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(leaving)
  expect(leaving.defaultPrevented).toBe(true)
  fireEvent.click(screen.getByRole('button', { name: '刷新审核权限与本机恢复记录' }))
  expect(port.session).toHaveBeenCalledTimes(1)
  fireEvent.click(screen.getByRole('button', { name: '返回保留审核表单' }))
  expect((screen.getByLabelText('本次审核备注') as HTMLTextAreaElement).value).toBe('SYNTHETIC_PENDING_NOTE')
  fireEvent.click(screen.getByRole('button', { name: '刷新审核权限与本机恢复记录' }))
  fireEvent.click(screen.getByRole('button', { name: '明确丢弃临时审核表单并刷新权限' }))
  await waitFor(() => expect(port.session).toHaveBeenCalledTimes(2))
  expect((await screen.findByLabelText('本次审核备注') as HTMLTextAreaElement).value).toBe('')
  fireEvent.change(screen.getByLabelText('本次审核备注'), { target: { value: 'SYNTHETIC_REVOKED_NOTE' } })
  fireEvent.click(screen.getByRole('button', { name: '刷新审核权限与本机恢复记录' }))
  view.rerender(<ReviewPanel workspace={workspace} paused candidate={null} port={port} />)
  expect(screen.queryByRole('dialog', { name: '刷新前保留审核表单' })).toBeNull()
  expect(screen.queryByDisplayValue('SYNTHETIC_REVOKED_NOTE')).toBeNull()
  view.rerender(<ReviewPanel workspace={workspace} paused={false} candidate={reviewCandidate} port={port} />)
  expect((await screen.findByLabelText('本次审核备注') as HTMLTextAreaElement).value).toBe('')
})


test('Policy hides but retains an unsubmitted note across unmount until explicit verified recovery', async () => {
  const { workspace, port } = fixture()
  const view = render(<ReviewPanel workspace={workspace} paused={false} candidate={reviewCandidate} port={port} />)
  fireEvent.change(await screen.findByLabelText('本次审核备注'), { target: { value: 'SYNTHETIC_RETAIN_ON_POLICY' } })
  view.rerender(<ReviewPanel workspace={workspace} paused candidate={null} port={port} />)
  expect(screen.queryByDisplayValue('SYNTHETIC_RETAIN_ON_POLICY')).toBeNull()
  view.unmount()
  const leaving = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(leaving)
  expect(leaving.defaultPrevented).toBe(true)
  expect(port.create).not.toHaveBeenCalled(); expect(port.decide).not.toHaveBeenCalled()
})


test('original actor explicitly recovers notes and reasons after Policy unmount with fresh candidate and Review reads, without writes', async () => {
  const { workspace, port } = fixture()
  const view = render(<ReviewPanel workspace={workspace} paused={false} candidate={reviewCandidate} port={port} />)
  fireEvent.change(await screen.findByLabelText('本次审核备注'), { target: { value: 'ORIGINAL_PRIVATE_NOTE' } })
  fireEvent.change(screen.getByLabelText('已有服务端审核 ID'), { target: { value: machineReceipt.id } })
  fireEvent.click(screen.getByRole('button', { name: '读取这个审核任务' }))
  const read = await screen.findByRole('button', { name: '另行读取当前审核回执' })
  await waitFor(() => expect((read as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(read)
  fireEvent.change(await screen.findByLabelText('审核理由'), { target: { value: 'ORIGINAL_PRIVATE_REASON' } })
  fireEvent.change(screen.getByLabelText('数学审核决定'), { target: { value: 'REJECTED' } })
  fireEvent.click(screen.getByLabelText('我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。'))
  view.rerender(<ReviewPanel workspace={workspace} paused candidate={null} port={port} />)
  expect(screen.queryByDisplayValue('ORIGINAL_PRIVATE_NOTE')).toBeNull()
  expect(screen.queryByDisplayValue('ORIGINAL_PRIVATE_REASON')).toBeNull()
  expect(pendingReviewForms(workspace)).toBe(true)
  view.unmount()
  render(<ReviewPanel workspace={workspace} paused={false} candidate={null} port={port} />)
  const recover = await screen.findByRole('button', { name: '核验原会话与准确基准，恢复临时审核表单' })
  expect(screen.queryByDisplayValue('ORIGINAL_PRIVATE_NOTE')).toBeNull()
  expect(port.candidate).not.toHaveBeenCalled()
  fireEvent.click(recover)
  await screen.findByDisplayValue('ORIGINAL_PRIVATE_NOTE')
  expect(screen.getByDisplayValue('ORIGINAL_PRIVATE_REASON')).toBeTruthy()
  expect(port.candidate).toHaveBeenCalledTimes(2)
  expect(port.read).toHaveBeenCalledTimes(2)
  expect((screen.getByLabelText('数学审核决定') as HTMLSelectElement).value).toBe('REJECTED')
  expect((screen.getByLabelText('我已核对准确候选与本回执，明确记录上述数学和来源决定及理由。') as HTMLInputElement).checked).toBe(false)
  expect(port.create).not.toHaveBeenCalled(); expect(port.decide).not.toHaveBeenCalled()
})

test('another actor cannot discover original payload; fresh original actor recovery keeps changed basis read-only', async () => {
  const { workspace, port } = fixture()
  const view = render(<ReviewPanel workspace={workspace} paused={false} candidate={reviewCandidate} port={port} />)
  fireEvent.change(await screen.findByLabelText('本次审核备注'), { target: { value: 'ORIGINAL_ACTOR_NOTE' } })
  view.unmount()
  vi.mocked(port.session).mockResolvedValue({ ...reviewSession(workspace), actor_session_id: 'session_other_actor' })
  const other = render(<ReviewPanel workspace={workspace} paused={false} candidate={null} port={port} />)
  fireEvent.click(await screen.findByRole('button', { name: '核验原会话与准确基准，恢复临时审核表单' }))
  await screen.findByText(/本次操作未确认或记录无法核验/)
  expect(port.candidate).not.toHaveBeenCalled(); expect(screen.queryByDisplayValue('ORIGINAL_ACTOR_NOTE')).toBeNull()
  other.unmount()
  vi.mocked(port.session).mockResolvedValue(reviewSession(workspace))
  vi.mocked(port.candidate!).mockResolvedValue({ ...reviewCandidate, draft_revision: 2, candidate_sha256: 'b'.repeat(64) })
  render(<ReviewPanel workspace={workspace} paused={false} candidate={null} port={port} />)
  fireEvent.click(await screen.findByRole('button', { name: '核验原会话与准确基准，恢复临时审核表单' }))
  const original = await screen.findByDisplayValue('ORIGINAL_ACTOR_NOTE')
  expect((original as HTMLTextAreaElement).disabled).toBe(true)
  expect(screen.getByText(/服务端候选或审核记录已变化/)).toBeTruthy()
  expect(port.create).not.toHaveBeenCalled()
})

test('late recovery does not reveal payload after Policy changes and explicit discard is scoped and stable', async () => {
  const { workspace, port } = fixture(), states: ReviewPanelState[] = []
  const onState = (state: ReviewPanelState) => states.push(state)
  const view = render(<ReviewPanel workspace={workspace} paused={false} candidate={reviewCandidate} port={port} onState={onState} />)
  fireEvent.change(await screen.findByLabelText('本次审核备注'), { target: { value: 'LATE_PRIVATE_NOTE' } })
  const discard = states.at(-1)!.discardForms
  view.rerender(<ReviewPanel workspace={workspace} paused candidate={null} port={port} onState={onState} />)
  view.rerender(<ReviewPanel workspace={workspace} paused={false} candidate={null} port={port} onState={onState} />)
  let finish!: (value: typeof reviewCandidate) => void
  vi.mocked(port.candidate!).mockImplementationOnce(() => new Promise(resolve => { finish = resolve }))
  fireEvent.click(await screen.findByRole('button', { name: '核验原会话与准确基准，恢复临时审核表单' }))
  await waitFor(() => expect(port.candidate).toHaveBeenCalledTimes(1))
  view.rerender(<ReviewPanel workspace={workspace} paused candidate={null} port={port} onState={onState} />)
  finish(reviewCandidate)
  await waitFor(() => expect(states.at(-1)?.safe).toBe(true))
  expect(screen.queryByDisplayValue('LATE_PRIVATE_NOTE')).toBeNull()
  expect(states.at(-1)?.discardForms).toBe(discard)
  expect(pendingReviewForms(workspace)).toBe(true)
  discard()
  expect(pendingReviewForms(workspace)).toBe(false)
  expect(port.create).not.toHaveBeenCalled(); expect(port.decide).not.toHaveBeenCalled()
})


test('changed Review revision preserves the old reason read-only without adopting a new decision basis', async () => {
  const { workspace, port } = fixture()
  const view = render(<ReviewPanel workspace={workspace} paused={false} candidate={reviewCandidate} port={port} />)
  await screen.findByLabelText('本次审核备注')
  fireEvent.change(screen.getByLabelText('已有服务端审核 ID'), { target: { value: machineReceipt.id } }); fireEvent.click(screen.getByRole('button', { name: '读取这个审核任务' }))
  const read = await screen.findByRole('button', { name: '另行读取当前审核回执' })
  await waitFor(() => expect((read as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(read)
  fireEvent.change(await screen.findByLabelText('审核理由'), { target: { value: 'ORIGINAL_RECEIPT_REASON' } })
  view.unmount()
  vi.mocked(port.read).mockResolvedValue({ ...machineReceipt, revision: 2, decision_reason: 'Other explicit server decision' })
  render(<ReviewPanel workspace={workspace} paused={false} candidate={null} port={port} />)
  fireEvent.click(await screen.findByRole('button', { name: '核验原会话与准确基准，恢复临时审核表单' }))
  expect((await screen.findByDisplayValue('ORIGINAL_RECEIPT_REASON') as HTMLTextAreaElement).disabled).toBe(true)
  expect(screen.getByText(/服务端候选或审核记录已变化/)).toBeTruthy()
  expect(port.decide).not.toHaveBeenCalled()
})
