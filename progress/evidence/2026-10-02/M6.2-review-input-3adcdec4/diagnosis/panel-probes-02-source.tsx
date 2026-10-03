import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { ReviewPanel } from './ReviewPanel'
import type { ReviewPort } from './reviewClient'
import { machineReceipt, reviewSession, safeReviewJob } from './reviewFixtures'
import { discardReviewForms, originalReviewForms } from './reviewFormMemory'
import { reviewCommandStore, reviewControlStore, reviewJobStore } from './reviewCommands'
import { publicationCommandStore } from '../draftPublication/publicationCommands'
import { publicationReceipt } from '../draftPublication/publicationFixtures'
import { request } from '../../api/client'
const workspaces: string[] = []
afterEach(async () => { cleanup(); for (const workspace of workspaces.splice(0)) discardReviewForms(workspace, 'import'); vi.restoreAllMocks(); vi.unstubAllGlobals(); await Promise.all([reviewCommandStore.close(), reviewControlStore.close(), reviewJobStore.close(), publicationCommandStore.close()]) })
const deferred = <T,>() => { let resolve!: (v: T) => void; const promise = new Promise<T>(r => { resolve = r }); return { resolve, promise } }
function fixture() {
  const workspace = `workspace_${crypto.randomUUID()}`; workspaces.push(workspace)
  const candidate = publicationReceipt.candidate, receipt = { ...machineReceipt, candidate }
  const port: ReviewPort = { candidate: vi.fn(async () => structuredClone(candidate)), session: vi.fn(async () => reviewSession(workspace)),
    create: vi.fn(async () => ({ id: receipt.id, status: 'queued' as const })), read: vi.fn(async () => structuredClone(receipt)),
    decide: vi.fn(async () => { throw new Error('No automatic decision allowed') }),
    job: vi.fn(async () => safeReviewJob(workspace)), cancel: vi.fn(async () => ({ ...safeReviewJob(workspace), status: 'cancelled' as const })),
    artifact: vi.fn(async () => { throw new Error('No artifact read allowed') }),
  }
  const props = { workspace, paused: false, candidate, formOwner: 'import' as const, port, formScope: 'import' }
  const forms = () => originalReviewForms(workspace, 'import', reviewSession(workspace).actor_session_id)
  return { workspace, candidate, receipt, port, props, forms }
}
async function enabled(label: string) {
  const input = await screen.findByLabelText(label)
  await waitFor(() => expect((input as HTMLTextAreaElement).disabled).toBe(false))
  return input
}
async function createThenRead(f: ReturnType<typeof fixture>) {
  fireEvent.click(await enabled('我已核对候选 ID、修订、哈希与本次检查范围，明确创建审核任务。'))
  fireEvent.click(screen.getByRole('button', { name: '明确创建本次审核任务' }))
  const read = await screen.findByRole('button', { name: '另行读取当前审核回执' })
  await waitFor(() => expect((read as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(read)
  await enabled('审核理由')
  expect(f.forms()).toHaveLength(1)
  expect(f.forms()[0].value).toMatchObject({ note: '', confirmed: true })
}

for (const transition of ['Policy pause', 'access generation'] as const) test(`actual Review Panel (independent Publication excluded): confirmed blank form is replaced synchronously and ${transition} cannot restore old value`, async () => {
  const f = fixture(), view = render(<ReviewPanel {...f.props} />)
  await createThenRead(f)
  fireEvent.change(await enabled('本次审核备注'), { target: { value: '尚未提交的原创备注 🧠\né' } })
  expect(f.forms()[0].value).toMatchObject({ note: '尚未提交的原创备注 🧠\né', confirmed: true })
  fireEvent.change(await enabled('审核理由'), { target: { value: '尚未提交的原创人工理由' } })
  fireEvent.change(await enabled('数学审核决定'), { target: { value: 'REJECTED' } })
  expect(f.forms()).toHaveLength(2)
  expect(f.forms()[0].value).toMatchObject({ note: '尚未提交的原创备注 🧠\né' })
  expect(f.forms()[1].value).toMatchObject({ reason: '尚未提交的原创人工理由', mathematical: 'REJECTED' })
  if (transition === 'Policy pause') {
    view.rerender(<ReviewPanel {...f.props} paused candidate={null} />)
    expect(screen.queryByLabelText('本次审核备注')).toBeNull()
    view.rerender(<ReviewPanel {...f.props} candidate={null} />)
  } else {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(reviewSession(f.workspace)))))
    await act(() => request('POST /api/v1/session/role', { role: 'author' }, { 'Idempotency-Key': 'independent_synthetic_generation_change' }))
  }
  const recover = await screen.findByRole('button', { name: '核验原会话与准确基准，恢复临时审核表单' })
  await waitFor(() => expect((recover as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(recover)
  const region = await screen.findByRole('region', { name: '恢复的临时审核表单 1' })
  expect((within(region).getByLabelText('本次审核备注') as HTMLTextAreaElement).value).toBe('尚未提交的原创备注 🧠\né')
  const reason = screen.getByRole('region', { name: '恢复的临时审核表单 2' })
  expect((within(reason).getByLabelText('审核理由') as HTMLTextAreaElement).value).toBe('尚未提交的原创人工理由')
  expect(f.forms()[0].value).toMatchObject({ note: '尚未提交的原创备注 🧠\né' })
  expect(f.port.create).toHaveBeenCalledTimes(1); expect(f.port.decide).not.toHaveBeenCalled()
})

test('late Review read across Policy cannot overwrite retained note; original actor can recover after remount', async () => {
  const f = fixture(), view = render(<ReviewPanel {...f.props} />)
  await createThenRead(f)
  fireEvent.change(await enabled('本次审核备注'), { target: { value: 'ORIGINAL_UNSENT_NOTE' } })
  fireEvent.change(await enabled('审核理由'), { target: { value: 'ORIGINAL_UNSENT_REASON' } })
  const delayed = deferred<typeof f.receipt>()
  vi.mocked(f.port.read).mockReturnValueOnce(delayed.promise)
  fireEvent.click(screen.getByRole('button', { name: '重新读取审核回执' }))
  expect((screen.getByLabelText('本次审核备注') as HTMLTextAreaElement).disabled).toBe(true)
  view.rerender(<ReviewPanel {...f.props} paused candidate={null} />)
  await act(async () => delayed.resolve(f.receipt))
  expect(screen.queryByLabelText('本次审核备注')).toBeNull()
  expect(f.forms()[0].value).toMatchObject({ note: 'ORIGINAL_UNSENT_NOTE' })
  view.unmount()
  render(<ReviewPanel {...f.props} candidate={null} />)
  const recover = await screen.findByRole('button', { name: '核验原会话与准确基准，恢复临时审核表单' })
  await waitFor(() => expect((recover as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(recover)
  await screen.findByDisplayValue('ORIGINAL_UNSENT_NOTE'); expect(screen.getByDisplayValue('ORIGINAL_UNSENT_REASON')).toBeTruthy()
  expect(f.port.create).toHaveBeenCalledTimes(1); expect(f.port.decide).not.toHaveBeenCalled()
})
