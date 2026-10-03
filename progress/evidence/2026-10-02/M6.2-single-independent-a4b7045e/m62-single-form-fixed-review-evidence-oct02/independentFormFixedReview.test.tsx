import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { SinglePublicationPanel } from './SinglePublicationPanel'
import { singlePublicationFixture } from './singlePublicationFixtures'
import { discardSinglePublicationForms, discardSinglePublicationMemory, recoverableSinglePublicationForms, recoverableSinglePublicationMemory } from './singlePublicationMemory'
import { readSinglePublicationCommand, singlePublicationCommandStore } from './singlePublicationCommands'
const workspaces: string[] = []
afterEach(async () => { cleanup(); vi.restoreAllMocks(); for (const workspace of workspaces.splice(0)) { discardSinglePublicationForms(workspace); discardSinglePublicationMemory(workspace) }; await singlePublicationCommandStore.close() })
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(accept => { resolve = accept }); return { resolve, promise } }
async function setup() {
  const f = singlePublicationFixture(); workspaces.push(f.workspace)
  render(<SinglePublicationPanel workspace={f.workspace} paused={false} blocked={false} draft={f.draft} receipt={f.receipt} port={f.port} />)
  const prepare = await screen.findByRole('button', { name: '选择此审核并重新读取生成发布基准' })
  await waitFor(() => expect((prepare as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(prepare)
  const region = await screen.findByRole('region', { name: '本次生成发布基准' })
  const boxes = within(region).getAllByRole('checkbox') as HTMLInputElement[]
  boxes.forEach(box => fireEvent.click(box))
  return { f, boxes, forms: () => recoverableSinglePublicationForms(f.workspace, f.session.actor_session_id), memory: () => recoverableSinglePublicationMemory(f.workspace, f.session.actor_session_id) }
}
async function clickReady(name: string) {
  const button = await screen.findByRole('button', { name, exact: true })
  await waitFor(() => expect(button.matches(':disabled')).toBe(false)); fireEvent.click(button)
}
test('independent fixed: later identical-value confirmation remains a new version after original send', async () => {
  const { f, boxes, forms } = await setup(), original = forms()[0]
  const gate = deferred<Awaited<ReturnType<typeof singlePublicationCommandStore.load>>>()
  vi.spyOn(singlePublicationCommandStore, 'load').mockReturnValueOnce(gate.promise)
  fireEvent.click(screen.getByRole('button', { name: '明确发布这一生成例题' }))
  expect(boxes[2].matches(':disabled')).toBe(false)
  fireEvent.click(boxes[2]); fireEvent.click(boxes[2]); const later = forms()[0]
  expect(later.selected).toEqual(original.selected); expect(later.confirmed).toBe(original.confirmed); expect(later.version).toBeGreaterThan(original.version)
  await act(async () => gate.resolve({})); await screen.findByText('原生成发布 ACK 已保存')
  expect(forms()).toEqual([later]); expect(f.port.publish).toHaveBeenCalledTimes(1)
})
test('independent fixed: failed original IDB write preserves later UI input and exact command; save only sends zero then explicit replay sends once', async () => {
  const { f, boxes, forms, memory } = await setup()
  const gate = deferred<Awaited<ReturnType<typeof singlePublicationCommandStore.load>>>()
  vi.spyOn(singlePublicationCommandStore, 'load').mockReturnValueOnce(gate.promise)
  vi.spyOn(singlePublicationCommandStore, 'save').mockRejectedValueOnce(new Error('independent original write failure'))
  fireEvent.click(screen.getByRole('button', { name: '明确发布这一生成例题' }))
  expect(boxes[1].matches(':disabled')).toBe(false); fireEvent.click(boxes[1]); fireEvent.click(boxes[2]); const later = forms()[0]
  await act(async () => gate.resolve({})); await screen.findByText(/原发布命令或回执尚未落盘/)
  expect(forms()).toEqual([later]); expect(f.port.publish).not.toHaveBeenCalled(); expect(memory()).toHaveLength(1)
  const original = memory()[0]
  expect(original.body).toEqual({ expected_revision: 1, expected_content_sha256: f.draft.candidate.candidate_sha256, review_receipt_id: f.receipt.id, acknowledged_warning_codes: ['SOURCE_CONFIRM'] })
  expect(original.ack).toBeNull(); expect(await singlePublicationCommandStore.load(f.workspace)).toEqual({})
  await clickReady('保存原会话的生成发布内存记录')
  await waitFor(() => expect(memory()).toEqual([]))
  expect(f.port.publish).not.toHaveBeenCalled(); expect(forms()).toEqual([later])
  const rows = await singlePublicationCommandStore.load(f.workspace)
  expect(Object.keys(rows)).toEqual([original.command_id]); expect(readSinglePublicationCommand(rows[original.command_id], f.workspace)).toEqual(original)
  await clickReady(`显式回放原生成发布命令 ${original.command_id}`)
  await screen.findByText('原生成发布 ACK 已保存')
  expect(f.port.publish).toHaveBeenCalledTimes(1); expect(vi.mocked(f.port.publish).mock.calls[0]).toEqual([f.draft.candidate.draft_id, original.body, original.command_id])
  expect(forms()).toEqual([later]); const saved = readSinglePublicationCommand((await singlePublicationCommandStore.load(f.workspace))[original.command_id], f.workspace)
  expect(saved).toEqual({ ...original, ack: f.ack })
})
test('independent fixed: failed ACK IDB write retains original ACK and later choices; explicit save does not POST again', async () => {
  const { f, boxes, forms, memory } = await setup()
  const gate = deferred<Awaited<ReturnType<typeof singlePublicationCommandStore.load>>>(), save = singlePublicationCommandStore.save.bind(singlePublicationCommandStore)
  vi.spyOn(singlePublicationCommandStore, 'load').mockReturnValueOnce(gate.promise)
  const write = vi.spyOn(singlePublicationCommandStore, 'save').mockImplementation(async (...args) => { if (JSON.parse(args[2]).ack) throw new Error('independent ACK write failure'); return save(...args) })
  fireEvent.click(screen.getByRole('button', { name: '明确发布这一生成例题' }))
  fireEvent.click(boxes[1]); fireEvent.click(boxes[2]); const later = forms()[0]
  await act(async () => gate.resolve({})); await screen.findByText(/原发布命令或回执尚未落盘/)
  expect(f.port.publish).toHaveBeenCalledTimes(1); expect(forms()).toEqual([later]); expect(memory()).toHaveLength(1)
  const originalWithAck = memory()[0]; expect(originalWithAck.ack).toEqual(f.ack)
  const rows = await singlePublicationCommandStore.load(f.workspace)
  expect(readSinglePublicationCommand(rows[originalWithAck.command_id], f.workspace)).toEqual({ ...originalWithAck, ack: null })
  write.mockRestore(); await clickReady('保存原会话的生成发布内存记录')
  await waitFor(() => expect(memory()).toEqual([]))
  expect(f.port.publish).toHaveBeenCalledTimes(1); expect(forms()).toEqual([later])
  expect(readSinglePublicationCommand((await singlePublicationCommandStore.load(f.workspace))[originalWithAck.command_id], f.workspace)).toEqual(originalWithAck)
  expect(vi.mocked(f.port.publish).mock.calls[0]).toEqual([f.draft.candidate.draft_id, originalWithAck.body, originalWithAck.command_id])
})
