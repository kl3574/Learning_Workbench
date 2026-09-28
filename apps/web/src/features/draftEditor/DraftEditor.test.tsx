import 'fake-indexeddb/auto'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { ApiError } from '../../api/client'
import type { ComponentProps, ComponentType } from 'react'
import { useWorkspacePolicy } from '../assessment/useWorkspacePolicy'
import type { LoadedBlock } from '../reader/contentClient'
import { reviewSession } from '../draftReview/reviewFixtures'
import type { EditPort } from './editClient'
import { editBase, editFixture } from './editFixtures'
import { editBuffers, editCommands } from './editJournal'
import { DraftEditor } from './DraftEditor'
afterEach(async () => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); await Promise.all([editBuffers.close(), editCommands.close()]) })
const block: LoadedBlock = { block_ref: editBase, block: { schema_version: '3.0.0', entity: 'block', id: editBase.id, revision: 1, kind: 'text', title: '合成原块', body_path: 'content/edit-synthetic.md', body_sha256: editFixture().payload.body_sha256, citations: [], concepts: [], depends_on: [] }, body: editFixture().payload.body_markdown, citations: [], unresolved_citation_ids: [], warnings: [], original_source: null }
test('three-way title/body stay visible and each resolution choice plus confirmation is required before a new local baseline', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`, old = editFixture(), server = editFixture(2, '服务端标题', '服务端正文')
  let reading = 0
  const port: EditPort = { session: async () => reviewSession(workspace), read: vi.fn(async (_id, revision) => ++reading === 1 || revision === 1 ? old : server), create: vi.fn(), patch: vi.fn(async () => { throw new ApiError(412, 'Changed') }) }
  render(<DraftEditor workspace={workspace} block={block} port={port} />)
  fireEvent.click(screen.getByRole('button', { name: '编辑此精确文本块' }))
  await waitFor(() => expect((screen.getByRole('button', { name: '从此准确修订明确创建编辑稿' }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.change(screen.getByLabelText('读取已有编辑稿 ID'), { target: { value: old.candidate.draft_id } })
  fireEvent.click(screen.getByRole('button', { name: '另行读取服务端草稿头' }))
  await screen.findByRole('region', { name: '当前本机编辑' })
  await waitFor(() => expect(screen.getByLabelText('本机标题').closest('fieldset')!.disabled).toBe(false))
  fireEvent.change(screen.getByLabelText('本机标题'), { target: { value: '本机标题' } })
  fireEvent.change(screen.getByLabelText('本机正文'), { target: { value: '本机正文' } })
  const submit = screen.getByRole('button', { name: '明确提交本机标题与正文' }) as HTMLButtonElement
  await waitFor(() => expect(submit.disabled).toBe(false)); fireEvent.click(submit)
  const conflict = await screen.findByRole('region', { name: '三方冲突恢复' })
  expect((within(conflict).getByLabelText('基准标题') as HTMLInputElement).value).toBe(old.payload.title)
  expect((within(conflict).getByLabelText('本地待同步正文') as HTMLTextAreaElement).value).toBe('本机正文')
  expect((within(conflict).getByLabelText('服务端当前正文') as HTMLTextAreaElement).value).toBe('服务端正文')
  const resolve = within(conflict).getByRole('button', { name: '保存解决结果到本机，暂不提交' }) as HTMLButtonElement
  expect(resolve.disabled).toBe(true)
  fireEvent.change(within(conflict).getByLabelText('标题解决方式'), { target: { value: 'local' } })
  fireEvent.change(within(conflict).getByLabelText('正文解决方式'), { target: { value: 'server' } })
  expect(resolve.disabled).toBe(true)
  fireEvent.click(within(conflict).getByRole('checkbox'))
  fireEvent.click(resolve)
  await waitFor(() => expect(screen.queryByRole('region', { name: '三方冲突恢复' })).toBeNull())
  expect(port.patch).toHaveBeenCalledTimes(1)
  expect((screen.getByLabelText('本机标题') as HTMLInputElement).value).toBe('本机标题')
  expect((screen.getByLabelText('本机正文') as HTMLTextAreaElement).value).toBe('服务端正文')
  fireEvent.click(screen.getByRole('button', { name: '收起文本编辑' }))
  await screen.findByRole('dialog', { name: '保留本机编辑' })
  expect(port.patch).toHaveBeenCalledTimes(1)
})

test('an external open-book policy poll hides an already open editor without an access broadcast', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`
  let session = reviewSession(workspace)
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(session))))
  const port: EditPort = { session: async () => reviewSession(workspace), read: vi.fn(async () => editFixture()), create: vi.fn(), patch: vi.fn() }
  const Controlled: ComponentType<ComponentProps<typeof DraftEditor> & { paused: boolean }> = DraftEditor
  function Harness() {
    const policy = useWorkspacePolicy(workspace)
    return <Controlled workspace={workspace} block={block} port={port} paused={!policy.known || !!policy.independentId || !!policy.openBookId} />
  }
  render(<Harness />)
  fireEvent.click(screen.getByRole('button', { name: '编辑此精确文本块' }))
  await screen.findByRole('button', { name: '从此准确修订明确创建编辑稿' })
  fireEvent.change(screen.getByLabelText('读取已有编辑稿 ID'), { target: { value: 'draft_edit_synthetic' } })
  fireEvent.click(screen.getByRole('button', { name: '另行读取服务端草稿头' }))
  await screen.findByLabelText('本机正文')
  session = { ...session, active_open_book_attempt_id: 'attempt_external_open_book' }
  await waitFor(() => expect(screen.queryByLabelText('本机正文')).toBeNull(), { timeout: 3000 })
  expect(port.patch).not.toHaveBeenCalled()
})

test('memory retention permits control navigation but keeps the exact tab close-unsafe after panel removal', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`, onState = vi.fn()
  const port: EditPort = { session: async () => reviewSession(workspace), read: vi.fn(async () => editFixture()), create: vi.fn(), patch: vi.fn() }
  const view = render(<DraftEditor workspace={workspace} block={block} port={port} onState={onState} />)
  fireEvent.click(screen.getByRole('button', { name: '编辑此精确文本块' }))
  await screen.findByRole('button', { name: '从此准确修订明确创建编辑稿' })
  fireEvent.change(screen.getByLabelText('读取已有编辑稿 ID'), { target: { value: 'draft_edit_synthetic' } })
  fireEvent.click(screen.getByRole('button', { name: '另行读取服务端草稿头' }))
  await screen.findByLabelText('本机正文')
  await waitFor(() => expect(screen.getByLabelText('本机标题').closest('fieldset')!.disabled).toBe(false))
  vi.spyOn(editBuffers, 'save').mockRejectedValueOnce(new Error('Synthetic interrupted local storage'))
  fireEvent.change(screen.getByLabelText('本机正文'), { target: { value: '仅页面内存保留的工作' } })
  await screen.findByRole('button', { name: '重试保存本机工作副本' })
  view.unmount()
  expect(onState).toHaveBeenLastCalledWith({ dirty: true, safe: true, closeSafe: false })
  const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event); expect(event.defaultPrevented).toBe(true)
  render(<DraftEditor workspace={workspace} block={block} port={port} />)
  fireEvent.click(screen.getByRole('button', { name: '编辑此精确文本块' }))
  const recover = await screen.findByRole('button', { name: '核验原会话与精确基准，恢复内存副本' })
  await waitFor(() => expect((recover as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(recover)
  await screen.findByText('本机工作副本已保存；不代表已同步到服务端。')
  expect((screen.getByLabelText('本机正文') as HTMLTextAreaElement).value).toBe('仅页面内存保留的工作')
})

test('a different session may explicitly discard isolated memory without seeing it or deleting saved records', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`
  let session = reviewSession(workspace)
  const port: EditPort = { session: async () => session, read: vi.fn(async () => editFixture()), create: vi.fn(), patch: vi.fn() }
  const view = render(<DraftEditor workspace={workspace} block={block} port={port} />)
  fireEvent.click(screen.getByRole('button', { name: '编辑此精确文本块' })); await screen.findByLabelText('读取已有编辑稿 ID')
  fireEvent.change(screen.getByLabelText('读取已有编辑稿 ID'), { target: { value: 'draft_edit_synthetic' } })
  fireEvent.click(screen.getByRole('button', { name: '另行读取服务端草稿头' }))
  await screen.findByLabelText('本机正文'); await screen.findByText('本机工作副本已保存；不代表已同步到服务端。')
  const saved = await editBuffers.load(workspace)
  vi.spyOn(editBuffers, 'save').mockRejectedValueOnce(new Error('Synthetic quota'))
  fireEvent.change(screen.getByLabelText('本机正文'), { target: { value: '不得向新会话显示的本机内存正文' } })
  await screen.findByRole('button', { name: '重试保存本机工作副本' }); view.unmount()
  session = { ...session, csrf_token: 'synthetic_other_memory_session' }
  render(<DraftEditor workspace={workspace} block={block} port={port} />)
  fireEvent.click(screen.getByRole('button', { name: '编辑此精确文本块' }))
  const recover = await screen.findByRole('button', { name: '核验原会话与精确基准，恢复内存副本' })
  expect((recover as HTMLButtonElement).disabled).toBe(true)
  expect(screen.queryByLabelText('本机正文')).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: '放弃此块未落盘的隔离内存' }))
  fireEvent.click(screen.getByRole('button', { name: '取消放弃' }))
  expect(screen.getByText(/有尚未落盘的文字隔离保留在本页内存中/)).toBeDefined()
  fireEvent.click(screen.getByRole('button', { name: '放弃此块未落盘的隔离内存' }))
  fireEvent.click(screen.getByRole('button', { name: '确认放弃隔离文字' }))
  expect(screen.queryByText(/有尚未落盘的文字隔离保留在本页内存中/)).toBeNull()
  expect(await editBuffers.load(workspace)).toEqual(saved); expect(port.patch).not.toHaveBeenCalled()
})
