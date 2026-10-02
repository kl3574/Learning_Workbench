import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { SinglePublicationPanel } from './SinglePublicationPanel'
import { singlePublicationFixture } from './singlePublicationFixtures'
import { discardSinglePublicationForms, discardSinglePublicationMemory } from './singlePublicationMemory'
import { singlePublicationCommandStore } from './singlePublicationCommands'
const workspaces: string[] = []
const fixture = () => { const f = singlePublicationFixture(); workspaces.push(f.workspace); return f }
afterEach(async () => { cleanup(); vi.restoreAllMocks(); for (const workspace of workspaces.splice(0)) { discardSinglePublicationForms(workspace); discardSinglePublicationMemory(workspace) }; await singlePublicationCommandStore.close() })
const button = (name: string) => screen.getByRole('button', { name }) as HTMLButtonElement
async function prepare(f: ReturnType<typeof fixture>) {
  const onState = vi.fn(), onDraftRead = vi.fn(), props = { workspace: f.workspace, paused: false, blocked: false, draft: f.draft, receipt: f.receipt, port: f.port, onState, onDraftRead }
  const view = render(<SinglePublicationPanel {...props} />)
  await waitFor(() => expect(button('选择此审核并重新读取生成发布基准').disabled).toBe(false)); fireEvent.click(button('选择此审核并重新读取生成发布基准'))
  await screen.findByRole('region', { name: '本次生成发布基准' }); return { view, props, onState, onDraftRead }
}
test('every warning instance and separate final confirmation precede publish; ACK never auto-reads GET/current', async () => {
  const f = fixture(), p = await prepare(f), basis = screen.getByRole('region', { name: '本次生成发布基准' }), boxes = within(basis).getAllByRole('checkbox')
  expect(boxes).toHaveLength(3); expect(button('明确发布这一生成例题').disabled).toBe(true)
  fireEvent.click(boxes[0]); fireEvent.click(boxes[2]); expect(button('明确发布这一生成例题').disabled).toBe(true)
  await waitFor(() => expect(p.onState.mock.lastCall?.[0].dirty).toBe(true))
  fireEvent.click(boxes[1]); expect(button('明确发布这一生成例题').disabled).toBe(false); fireEvent.click(button('明确发布这一生成例题'))
  await screen.findByText('原生成发布 ACK 已保存'); expect(f.port.publish).toHaveBeenCalledTimes(1)
  expect(vi.mocked(f.port.publish).mock.calls[0][1]).toEqual({ expected_revision: 1, expected_content_sha256: f.draft.candidate.candidate_sha256, review_receipt_id: f.receipt.id, acknowledged_warning_codes: ['SOURCE_CONFIRM'] })
  expect(f.port.current).not.toHaveBeenCalled(); expect(f.port.draft).toHaveBeenCalledTimes(1); expect(p.onDraftRead).not.toHaveBeenCalled()
  vi.mocked(f.port.draft).mockResolvedValueOnce({ ...f.draft, state: 'published', published_ref: f.ack })
  fireEvent.click(button(`另行读取该候选发布状态 ${f.draft.candidate.draft_id}`)); await screen.findByText('本次 GET 候选状态：published'); expect(p.onDraftRead).toHaveBeenCalledTimes(1)
  expect(f.port.current).not.toHaveBeenCalled(); expect(screen.getByText(/父章节和课程仍保留原引用/)).toBeTruthy()
})
test('unsubmitted confirmation survives unmount, stays isolated under lost permission, and explicit exact recovery resets final consent', async () => {
  const f = fixture(), first = await prepare(f)
  screen.getAllByRole('checkbox').forEach(box => fireEvent.click(box)); expect(button('明确发布这一生成例题').disabled).toBe(false); first.view.unmount()
  const view = render(<SinglePublicationPanel {...first.props} paused />)
  await screen.findByText(/未提交的发布确认保留在原会话/); expect(screen.queryByRole('region', { name: '本次生成发布基准' })).toBeNull(); expect(screen.queryByText(f.receipt.decision_reason)).toBeNull(); expect(f.port.publish).not.toHaveBeenCalled()
  view.rerender(<SinglePublicationPanel {...first.props} />); await screen.findByRole('button', { name: '核验并恢复原生成发布表单' })
  fireEvent.click(button('核验并恢复原生成发布表单')); await screen.findByRole('region', { name: '本次生成发布基准' })
  const boxes = within(screen.getByRole('region', { name: '本次生成发布基准' })).getAllByRole('checkbox') as HTMLInputElement[]
  expect(boxes.map(box => box.checked)).toEqual([true, true, false]); expect(button('明确发布这一生成例题').disabled).toBe(true); expect(f.port.publish).not.toHaveBeenCalled()
  act(() => first.onState.mock.lastCall?.[0].discardForms()); await waitFor(() => expect(first.onState.mock.lastCall?.[0].dirty).toBe(false))
})
test('published candidate and mathematics NOT_APPLICABLE cannot prepare new publication', async () => {
  const f = fixture(), props = { workspace: f.workspace, paused: false, blocked: false, port: f.port, receipt: f.receipt }
  const view = render(<SinglePublicationPanel {...props} draft={{ ...f.draft, state: 'published', published_ref: f.ack }} />)
  await screen.findByRole('button', { name: '选择此审核并重新读取生成发布基准' }); expect(button('选择此审核并重新读取生成发布基准').disabled).toBe(true)
  view.rerender(<SinglePublicationPanel {...props} draft={f.draft} receipt={{ ...f.receipt, mathematical: 'NOT_APPLICABLE' }} />)
  await waitFor(() => expect(button('选择此审核并重新读取生成发布基准').disabled).toBe(true)); expect(f.port.draft).not.toHaveBeenCalled(); expect(f.port.publish).not.toHaveBeenCalled()
})

test('latest physical BLOCKED projection explains missing actual PASS and admits no publication basis or POST', async () => {
  const f = fixture(); f.numeric.result = { ...f.numeric.result!, verdict: 'BLOCKED', outcome: 'environment_unavailable', exit_code: 1, assertions: [] }
  render(<SinglePublicationPanel workspace={f.workspace} paused={false} blocked={false} draft={f.draft} receipt={f.receipt} port={f.port} />)
  await waitFor(() => expect(button('选择此审核并重新读取生成发布基准').disabled).toBe(false)); fireEvent.click(button('选择此审核并重新读取生成发布基准'))
  await screen.findByText(/当前最新数值结果为 BLOCKED/); expect(screen.queryByRole('region', { name: '本次生成发布基准' })).toBeNull(); expect(f.port.publish).not.toHaveBeenCalled()
})
