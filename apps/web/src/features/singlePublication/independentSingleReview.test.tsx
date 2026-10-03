import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { SinglePublicationPanel } from './SinglePublicationPanel'
import { singlePublicationFixture } from './singlePublicationFixtures'
import { discardSinglePublicationForms, discardSinglePublicationMemory, recoverableSinglePublicationForms } from './singlePublicationMemory'
import { singlePublicationCommandStore } from './singlePublicationCommands'
const workspaces: string[] = []
afterEach(async () => { cleanup(); vi.restoreAllMocks(); for (const workspace of workspaces.splice(0)) { discardSinglePublicationForms(workspace); discardSinglePublicationMemory(workspace) }; await singlePublicationCommandStore.close() })
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(accept => { resolve = accept }); return { resolve, promise } }
async function setup() {
  const f = singlePublicationFixture(); workspaces.push(f.workspace)
  const props = { workspace: f.workspace, paused: false, blocked: false, draft: f.draft, receipt: f.receipt, port: f.port }
  const view = render(<SinglePublicationPanel {...props} />)
  const prepare = await screen.findByRole('button', { name: '选择此审核并重新读取生成发布基准' })
  await waitFor(() => expect((prepare as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(prepare)
  const region = await screen.findByRole('region', { name: '本次生成发布基准' })
  const boxes = within(region).getAllByRole('checkbox') as HTMLInputElement[]
  boxes.forEach(box => fireEvent.click(box))
  return { f, props, view, boxes, forms: () => recoverableSinglePublicationForms(f.workspace, f.session.actor_session_id) }
}
test('independent: edits accepted while submit awaits the first ledger read survive consumption of its original form', async () => {
  const { f, boxes, forms } = await setup()
  const gate = deferred<Awaited<ReturnType<typeof singlePublicationCommandStore.load>>>()
  const load = vi.spyOn(singlePublicationCommandStore, 'load').mockReturnValueOnce(gate.promise)
  fireEvent.click(screen.getByRole('button', { name: '明确发布这一生成例题' }))
  await waitFor(() => expect(load).toHaveBeenCalledTimes(1))
  expect(boxes[1].disabled).toBe(false)
  fireEvent.click(boxes[1]); fireEvent.click(boxes[2])
  expect(forms()).toHaveLength(1)
  expect(forms()[0]).toMatchObject({ selected: [0], confirmed: false })
  await act(async () => gate.resolve({}))
  await screen.findByText('原生成发布 ACK 已保存')
  expect(f.port.publish).toHaveBeenCalledTimes(1)
  expect(vi.mocked(f.port.publish).mock.calls[0][1].acknowledged_warning_codes).toEqual(['SOURCE_CONFIRM'])
  // The original click may complete. It must not delete subsequently accepted local choices.
  expect(forms()).toHaveLength(1)
  expect(forms()[0]).toMatchObject({ selected: [0], confirmed: false })
})
test('independent: first ledger load failure retains exact unsent choices and sends no write', async () => {
  const { f, forms } = await setup(), before = forms()
  vi.spyOn(singlePublicationCommandStore, 'load').mockRejectedValueOnce(new Error('synthetic initial IDB read failure'))
  fireEvent.click(screen.getByRole('button', { name: '明确发布这一生成例题' }))
  await screen.findByText(/本次发布操作未确认或记录无法核验/)
  expect(forms()).toEqual(before); expect(f.port.publish).not.toHaveBeenCalled()
  expect(await singlePublicationCommandStore.load(f.workspace)).toEqual({})
})
test('independent: late fresh-candidate read after Policy hides original form and does not submit', async () => {
  const { f, props, view, forms } = await setup(), before = forms()
  const gate = deferred<typeof f.draft>()
  vi.mocked(f.port.draft).mockReturnValueOnce(gate.promise)
  fireEvent.click(screen.getByRole('button', { name: '核验并恢复原生成发布表单' }))
  await waitFor(() => expect(f.port.draft).toHaveBeenCalledTimes(2))
  view.rerender(<SinglePublicationPanel {...props} paused draft={null} receipt={null} />)
  await act(async () => gate.resolve(f.draft))
  expect(screen.queryByRole('region', { name: '本次生成发布基准' })).toBeNull()
  expect(screen.queryByText(f.receipt.decision_reason)).toBeNull()
  expect(forms()).toEqual(before); expect(f.port.publish).not.toHaveBeenCalled()
})
