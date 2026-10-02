import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { reviewSession } from '../draftReview/reviewFixtures'
import { RestorePanel } from './RestorePanel'
import { base, current, createAck, publicationDraft, publicationReceipt, publicationRef } from './restoreFixtures'
import type { RestorePort } from './restoreClient'
import { restoreCreateCommandStore } from './restoreCreateCommands'
import { discardRestoreCreateMemory, recoverableRestoreCreateMemory } from './restoreCreateMemory'
const workspaces: string[] = []
afterEach(async () => { cleanup(); vi.restoreAllMocks(); workspaces.splice(0).forEach(workspace => discardRestoreCreateMemory(workspace)); await restoreCreateCommandStore.close() })
test('a failed first journal write preserves the exact form and held command; policy hiding and unmount retain close protection until explicit memory save', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`, onState = vi.fn(); workspaces.push(workspace)
  const port: RestorePort = { session: vi.fn(async () => reviewSession(workspace)), current: vi.fn(async () => publicationDraft.base_ref),
    source: vi.fn(async ref => structuredClone(ref.revision === 1 ? base : current)), create: vi.fn(async () => structuredClone(createAck)),
    draft: vi.fn(async () => structuredClone(publicationDraft)), review: vi.fn(async () => publicationReceipt), publish: vi.fn(async () => publicationRef) }
  const props = { workspace, blockId: base.metadata.id, selectedSource: publicationDraft.source_ref, paused: false, port, onState }
  const view = render(<RestorePanel {...props} />)
  const prepare = await screen.findByRole('button', { name: '重新读取当前基准并核验所选历史原件' })
  fireEvent.click(prepare); await screen.findByRole('region', { name: '恢复创建的准确基准' })
  await waitFor(() => expect((screen.getByLabelText('本次恢复理由') as HTMLTextAreaElement).disabled).toBe(false))
  const reason = '仅保留本页原理由 🧠 e\u0301\n\\alpha\n\n'
  fireEvent.change(screen.getByLabelText('本次恢复理由'), { target: { value: reason } })
  fireEvent.click(screen.getByRole('checkbox')); vi.spyOn(restoreCreateCommandStore, 'save').mockRejectedValueOnce(new Error('Synthetic quota'))
  fireEvent.click(screen.getByRole('button', { name: '明确创建本次历史恢复稿' }))
  await screen.findByText(/恢复创建命令或 ACK 尚未落盘/)
  await screen.findByText(/本次恢复操作未确认或记录无法核验/)
  expect((screen.getByLabelText('本次恢复理由') as HTMLTextAreaElement).value).toBe(reason)
  expect(port.create).not.toHaveBeenCalled(); expect(recoverableRestoreCreateMemory(workspace, reviewSession(workspace).csrf_token)[0].body.reason).toBe(reason)
  expect(onState).toHaveBeenLastCalledWith({ dirty: true, safe: true, closeSafe: false })
  view.rerender(<RestorePanel {...props} paused />)
  expect(screen.queryByLabelText('本次恢复理由')).toBeNull(); expect(screen.queryByLabelText('历史来源完整正文')).toBeNull()
  expect(screen.queryByText(publicationDraft.source_ref.sha256, { exact: false })).toBeNull()
  view.unmount(); expect(onState).toHaveBeenLastCalledWith({ dirty: true, safe: true, closeSafe: false })
  const close = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(close); expect(close.defaultPrevented).toBe(true)
  render(<RestorePanel {...props} />)
  const save = await screen.findByRole('button', { name: '保存原会话的恢复创建内存记录' }); fireEvent.click(save)
  await waitFor(() => expect(screen.queryByText(/恢复创建命令或 ACK 尚未落盘/)).toBeNull())
  expect(port.create).not.toHaveBeenCalled()
  const records = Object.values(await restoreCreateCommandStore.load(workspace)).map(value => JSON.parse(value.text))
  expect(records).toHaveLength(1); expect(records[0].body.reason).toBe(reason); expect(records[0].ack).toBeNull()
  await act(async () => {})
})
