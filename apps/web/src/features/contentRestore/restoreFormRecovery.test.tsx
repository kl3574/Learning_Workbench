import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { reviewSession } from '../draftReview/reviewFixtures'
import { RestorePanel } from './RestorePanel'
import { base, current, createAck, publicationDraft, publicationReceipt, publicationRef } from './restoreFixtures'
import type { RestorePort } from './restoreClient'
import { restoreCreateCommandStore } from './restoreCreateCommands'
import { discardRestoreForms, ownRestoreForm } from './restoreFormMemory'
const workspaces: string[] = []

afterEach(async () => { cleanup(); vi.restoreAllMocks(); workspaces.splice(0).forEach(workspace => discardRestoreForms(workspace, base.metadata.id)); await restoreCreateCommandStore.close() })

test('Policy hiding preserves unsubmitted restore reason and close protection without creating a command', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`, onState = vi.fn()
  workspaces.push(workspace)
  const port: RestorePort = { session: vi.fn(async () => reviewSession(workspace)), current: vi.fn(async () => publicationDraft.base_ref),
    source: vi.fn(async ref => structuredClone(ref.revision === 1 ? base : current)), create: vi.fn(async () => structuredClone(createAck)),
    draft: vi.fn(async () => structuredClone(publicationDraft)), review: vi.fn(async () => publicationReceipt), publish: vi.fn(async () => publicationRef) }
  const props = { workspace, blockId: base.metadata.id, selectedSource: publicationDraft.source_ref, paused: false, port, onState }
  const view = render(<RestorePanel {...props} />)
  fireEvent.click(await screen.findByRole('button', { name: '重新读取当前基准并核验所选历史原件' }))
  await screen.findByRole('region', { name: '恢复创建的准确基准' })
  const reason = '未提交恢复理由 🧠 e\u0301\n\\alpha\n\n'
  await waitFor(() => expect((screen.getByLabelText('本次恢复理由') as HTMLTextAreaElement).disabled).toBe(false))
  fireEvent.change(screen.getByLabelText('本次恢复理由'), { target: { value: reason } })
  expect(onState.mock.lastCall?.[0].dirty).toBe(true)
  view.rerender(<RestorePanel {...props} paused />)
  expect(screen.queryByLabelText('本次恢复理由')).toBeNull()
  await waitFor(() => expect(onState.mock.lastCall?.[0].dirty).toBe(true))
  expect(port.create).not.toHaveBeenCalled()
  expect(Object.keys(await restoreCreateCommandStore.load(workspace))).toHaveLength(0)
  view.rerender(<RestorePanel {...props} />)
  const restore = await screen.findByRole('button', { name: '重新核验并恢复原会话的恢复表单' })
  await waitFor(() => expect((restore as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(restore)
  await waitFor(() => expect((screen.getByRole('textbox', { name: '本次恢复理由' }) as HTMLTextAreaElement).value).toBe(reason))
  expect(port.create).not.toHaveBeenCalled()
})

async function prepareForm() {
  const workspace = `workspace_${crypto.randomUUID()}`, onState = vi.fn(); workspaces.push(workspace)
  const port: RestorePort = { session: vi.fn(async () => reviewSession(workspace)), current: vi.fn(async () => publicationDraft.base_ref),
    source: vi.fn(async ref => structuredClone(ref.revision === 1 ? base : current)), create: vi.fn(async () => structuredClone(createAck)),
    draft: vi.fn(async () => structuredClone(publicationDraft)), review: vi.fn(async () => publicationReceipt), publish: vi.fn(async () => publicationRef) }
  const props = { workspace, blockId: base.metadata.id, selectedSource: publicationDraft.source_ref, paused: false, port, onState }
  const view = render(<RestorePanel {...props} />)
  fireEvent.click(await screen.findByRole('button', { name: '重新读取当前基准并核验所选历史原件' }))
  await screen.findByRole('region', { name: '恢复创建的准确基准' })
  const reason = '保留最初理由 🧠 e\u0301\n\\alpha\n\n'
  await waitFor(() => expect((screen.getByLabelText('本次恢复理由') as HTMLTextAreaElement).disabled).toBe(false))
  fireEvent.change(screen.getByLabelText('本次恢复理由'), { target: { value: reason } }); fireEvent.click(screen.getByRole('checkbox'))
  return { workspace, port, props, view, reason }
}

test('same-session remount requires fresh reads, cancels confirmation and never automatically creates a draft', async () => {
  const { workspace, port, props, view, reason } = await prepareForm()
  view.unmount()
  const close = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(close); expect(close.defaultPrevented).toBe(true)
  render(<RestorePanel {...props} />)
  const restore = await screen.findByRole('button', { name: '重新核验并恢复原会话的恢复表单' })
  await waitFor(() => expect((restore as HTMLButtonElement).disabled).toBe(false))
  expect(screen.queryByRole('textbox', { name: '本次恢复理由' })).toBeNull()
  const sessions = vi.mocked(port.session).mock.calls.length, reads = vi.mocked(port.source).mock.calls.length
  fireEvent.click(restore)
  await waitFor(() => expect((screen.getByRole('textbox', { name: '本次恢复理由' }) as HTMLTextAreaElement).value).toBe(reason))
  expect(vi.mocked(port.session).mock.calls.length).toBe(sessions + 1); expect(vi.mocked(port.source).mock.calls.length).toBe(reads + 2)
  expect((screen.getByRole('checkbox') as HTMLInputElement).checked).toBe(false)
  expect(port.create).not.toHaveBeenCalled(); expect(Object.keys(await restoreCreateCommandStore.load(workspace))).toHaveLength(0)
})

test('another session cannot recover protected form payload and can only explicitly discard the local copy', async () => {
  const { port, props, view, reason } = await prepareForm()
  view.rerender(<RestorePanel {...props} paused />)
  vi.mocked(port.session).mockResolvedValue({ ...reviewSession(props.workspace), actor_session_id: 'another_actor', csrf_token: '9'.repeat(64) })
  view.rerender(<RestorePanel {...props} />)
  const restore = await screen.findByRole('button', { name: '重新核验并恢复原会话的恢复表单' })
  await screen.findByRole('textbox', { name: '读取已有恢复稿 ID' })
  expect((restore as HTMLButtonElement).disabled).toBe(true); expect(screen.queryByDisplayValue(reason)).toBeNull()
  expect(port.create).not.toHaveBeenCalled()
  fireEvent.click(screen.getByRole('button', { name: '明确放弃未提交恢复表单' }))
  fireEvent.click(screen.getByRole('button', { name: '确认放弃未提交恢复表单' }))
  await waitFor(() => expect(screen.queryByRole('button', { name: '重新核验并恢复原会话的恢复表单' })).toBeNull())
})

test('changed current keeps original reason and basis while disabling creation instead of rebasing', async () => {
  const { port, props, view, reason } = await prepareForm()
  view.rerender(<RestorePanel {...props} paused />)
  vi.mocked(port.current).mockResolvedValue({ ...publicationDraft.base_ref, revision: 3, sha256: 'c'.repeat(64) })
  view.rerender(<RestorePanel {...props} />)
  const restore = await screen.findByRole('button', { name: '重新核验并恢复原会话的恢复表单' })
  await waitFor(() => expect((restore as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(restore)
  await screen.findByText(/当前修订已变化。原理由和旧依据保留/)
  expect((screen.getByRole('textbox', { name: '本次恢复理由' }) as HTMLTextAreaElement).value).toBe(reason)
  fireEvent.click(screen.getByRole('checkbox'))
  expect((screen.getByRole('button', { name: '明确创建本次历史恢复稿' }) as HTMLButtonElement).disabled).toBe(true)
  expect(ownRestoreForm(props.workspace, props.blockId, reviewSession(props.workspace).csrf_token)?.basis.base_ref).toEqual(publicationDraft.base_ref)
  expect(port.create).not.toHaveBeenCalled()
})

test('input typed while submission waits on local read survives the original command acknowledgement', async () => {
  const { workspace, port, reason } = await prepareForm()
  const originalRows = await restoreCreateCommandStore.load(workspace)
  let resolve!: (rows: typeof originalRows) => void
  vi.spyOn(restoreCreateCommandStore, 'load').mockImplementationOnce(() => new Promise(done => { resolve = done }))
  fireEvent.click(screen.getByRole('button', { name: '明确创建本次历史恢复稿' }))
  const newer = '后续输入必须保留 🧠\n新理由\n'
  fireEvent.change(screen.getByRole('textbox', { name: '本次恢复理由' }), { target: { value: newer } })
  await act(async () => resolve(originalRows))
  await screen.findByText(/原创建 ACK 已保存/)
  expect(port.create).toHaveBeenCalledTimes(1)
  expect(vi.mocked(port.create).mock.calls[0][0].reason).toBe(reason)
  expect(ownRestoreForm(workspace, base.metadata.id, reviewSession(workspace).csrf_token)?.value.reason).toBe(newer)
  expect(screen.getByRole('button', { name: '重新核验并恢复原会话的恢复表单' })).toBeTruthy()
})

test('late permission read after a renewed Policy lock cannot restore protected text or start source reads', async () => {
  const { workspace, port, props, view, reason } = await prepareForm()
  view.rerender(<RestorePanel {...props} paused />); view.rerender(<RestorePanel {...props} />)
  const restore = await screen.findByRole('button', { name: '重新核验并恢复原会话的恢复表单' })
  await waitFor(() => expect((restore as HTMLButtonElement).disabled).toBe(false))
  let resolve!: (value: ReturnType<typeof reviewSession>) => void
  vi.mocked(port.session).mockImplementationOnce(() => new Promise(done => { resolve = done }))
  const reads = vi.mocked(port.current).mock.calls.length
  fireEvent.click(restore); view.rerender(<RestorePanel {...props} paused />)
  await act(async () => resolve(reviewSession(workspace)))
  expect(screen.queryByDisplayValue(reason)).toBeNull()
  expect(vi.mocked(port.current).mock.calls.length).toBe(reads)
  expect(ownRestoreForm(workspace, base.metadata.id, reviewSession(workspace).csrf_token)?.value.reason).toBe(reason)
  expect(port.create).not.toHaveBeenCalled()
})
