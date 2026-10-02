import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { isolateHistory, undo, undoDepth } from '@codemirror/commands'
import { afterEach, expect, test, vi } from 'vitest'
import { ApiError } from '../../api/client'
import type { ComponentProps, ComponentType } from 'react'
import { useWorkspacePolicy } from '../assessment/useWorkspacePolicy'
import type { LoadedBlock } from '../reader/contentClient'
import { reviewSession } from '../draftReview/reviewFixtures'
import { reviewClient } from '../draftReview/reviewClient'
import type { EditPort } from './editClient'
import { editBase, editFixture } from './editFixtures'
import { editBuffers, editCommands } from './editJournal'
import { DraftEditor } from './DraftEditor'
import { codeMirrorTestGeometry, replaceSource, sourceView } from './sourceEditorTestSupport'
codeMirrorTestGeometry()
afterEach(async () => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); await Promise.all([editBuffers.close(), editCommands.close()]) })
const block: LoadedBlock = { block_ref: editBase, block: { schema_version: '3.0.0', entity: 'block', id: editBase.id, revision: 1, kind: 'text', title: '合成原块', body_path: 'content/edit-synthetic.md', body_sha256: editFixture().payload.body_sha256, citations: [], concepts: [], depends_on: [] }, body: editFixture().payload.body_markdown, citations: [], unresolved_citation_ids: [], warnings: [], original_source: null }
test('three-way title/body stay visible and each resolution choice plus confirmation is required before a new local baseline', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`, old = editFixture(), server = editFixture(2, '服务端标题', '服务端正文')
  let reading = 0
  const port: EditPort = { verifyBase: vi.fn(async () => {}), session: async () => reviewSession(workspace), read: vi.fn(async (_id, revision) => ++reading === 1 || revision === 1 ? old : server), create: vi.fn(), patch: vi.fn(async () => { throw new ApiError(412, 'Changed') }) }
  render(<DraftEditor workspace={workspace} block={block} port={port} />)
  fireEvent.click(screen.getByRole('button', { name: '编辑此精确文本块' }))
  await waitFor(() => expect((screen.getByRole('button', { name: '从此准确修订明确创建编辑稿' }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.change(screen.getByLabelText('读取已有编辑稿 ID'), { target: { value: old.candidate.draft_id } })
  fireEvent.click(screen.getByRole('button', { name: '另行读取服务端草稿头' }))
  await screen.findByRole('region', { name: '当前本机编辑' })
  await waitFor(() => expect(screen.getByLabelText('本机标题').closest('fieldset')!.disabled).toBe(false))
  fireEvent.change(screen.getByLabelText('本机标题'), { target: { value: '本机标题' } })
  replaceSource(screen.getByLabelText('本机正文'), '本机正文')
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
  expect(sourceView(screen.getByLabelText('本机正文')).state.doc.toString()).toBe('服务端正文')
  fireEvent.click(screen.getByRole('button', { name: '收起文本编辑' }))
  await screen.findByRole('dialog', { name: '保留本机编辑' })
  expect(port.patch).toHaveBeenCalledTimes(1)
})

test('an external open-book policy poll hides an already open editor without an access broadcast', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`
  let session = reviewSession(workspace)
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(session))))
  const port: EditPort = { verifyBase: vi.fn(async () => {}), session: async () => reviewSession(workspace), read: vi.fn(async () => editFixture()), create: vi.fn(), patch: vi.fn() }
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
  const port: EditPort = { verifyBase: vi.fn(async () => {}), session: async () => reviewSession(workspace), read: vi.fn(async () => editFixture()), create: vi.fn(), patch: vi.fn() }
  const view = render(<DraftEditor workspace={workspace} block={block} port={port} onState={onState} />)
  fireEvent.click(screen.getByRole('button', { name: '编辑此精确文本块' }))
  await screen.findByRole('button', { name: '从此准确修订明确创建编辑稿' })
  fireEvent.change(screen.getByLabelText('读取已有编辑稿 ID'), { target: { value: 'draft_edit_synthetic' } })
  fireEvent.click(screen.getByRole('button', { name: '另行读取服务端草稿头' }))
  await screen.findByLabelText('本机正文')
  await waitFor(() => expect(screen.getByLabelText('本机标题').closest('fieldset')!.disabled).toBe(false))
  vi.spyOn(editBuffers, 'save').mockRejectedValueOnce(new Error('Synthetic interrupted local storage'))
  replaceSource(screen.getByLabelText('本机正文'), '仅页面内存保留的工作')
  await screen.findByRole('button', { name: '重试保存本机工作副本' })
  view.unmount()
  expect(onState).toHaveBeenLastCalledWith({ dirty: true, safe: true, closeSafe: false })
  const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event); expect(event.defaultPrevented).toBe(true)
  render(<DraftEditor workspace={workspace} block={block} port={port} />)
  fireEvent.click(screen.getByRole('button', { name: '编辑此精确文本块' }))
  const recover = await screen.findByRole('button', { name: '核验原会话与精确基准，恢复内存副本' })
  await waitFor(() => expect((recover as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(recover)
  await screen.findByText('本机工作副本已保存；不代表已同步到服务端。')
  expect(sourceView(screen.getByLabelText('本机正文')).state.doc.toString()).toBe('仅页面内存保留的工作')
})

test('a different session may explicitly discard isolated memory without seeing it or deleting saved records', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`
  let session = reviewSession(workspace)
  const port: EditPort = { verifyBase: vi.fn(async () => {}), session: async () => session, read: vi.fn(async () => editFixture()), create: vi.fn(), patch: vi.fn() }
  const view = render(<DraftEditor workspace={workspace} block={block} port={port} />)
  fireEvent.click(screen.getByRole('button', { name: '编辑此精确文本块' })); await screen.findByLabelText('读取已有编辑稿 ID')
  fireEvent.change(screen.getByLabelText('读取已有编辑稿 ID'), { target: { value: 'draft_edit_synthetic' } })
  fireEvent.click(screen.getByRole('button', { name: '另行读取服务端草稿头' }))
  await screen.findByLabelText('本机正文'); await screen.findByText('本机工作副本已保存；不代表已同步到服务端。')
  const saved = await editBuffers.load(workspace)
  vi.spyOn(editBuffers, 'save').mockRejectedValueOnce(new Error('Synthetic quota'))
  replaceSource(screen.getByLabelText('本机正文'), '不得向新会话显示的本机内存正文')
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

test('real Review dirty and unsafe states fence CM input and existing undo history, then restore editing', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`, saved = editFixture(), session = reviewSession(workspace)
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(session))))
  const reviewSessionRead = vi.spyOn(reviewClient, 'session').mockResolvedValue(session)
  const port: EditPort = { verifyBase: vi.fn(async () => {}), session: async () => session, read: vi.fn(async () => saved), create: vi.fn(), patch: vi.fn() }
  render(<DraftEditor workspace={workspace} block={block} port={port} />)
  fireEvent.click(screen.getByRole('button', { name: '编辑此精确文本块' }))
  await screen.findByLabelText('读取已有编辑稿 ID')
  fireEvent.change(screen.getByLabelText('读取已有编辑稿 ID'), { target: { value: saved.candidate.draft_id } })
  fireEvent.click(screen.getByRole('button', { name: '另行读取服务端草稿头' }))
  const enter = await screen.findByRole('button', { name: '核验已保存精确编辑稿并进入审核' })
  await waitFor(() => expect((enter as HTMLButtonElement).disabled).toBe(false))
  const view = sourceView(screen.getByLabelText('本机正文')), original = saved.payload.body_markdown
  await waitFor(() => expect(view.state.readOnly).toBe(false))
  // Two isolated real transactions return to the exact saved text while retaining
  // a nonempty undo stack; a blocked undo must not silently modify local storage.
  for (const text of [original + '\n本机撤销探针', original]) act(() => view.dispatch({
    changes: { from: 0, to: view.state.doc.length, insert: text }, annotations: isolateHistory.of('full'), userEvent: 'input',
  }))
  await waitFor(() => expect((enter as HTMLButtonElement).disabled).toBe(false))
  expect(undoDepth(view.state)).toBe(2)
  fireEvent.click(enter)
  const note = await screen.findByLabelText('本次审核备注')
  await waitFor(() => expect(view.state.readOnly).toBe(false))
  const durable = await editBuffers.load(workspace)
  const assertBlocked = () => {
    expect(view.state.readOnly).toBe(true)
    expect(view.contentDOM.getAttribute('contenteditable')).toBe('false')
    replaceSource(view.contentDOM, '不得写入的正文')
    act(() => { expect(undo(view)).toBe(false) })
    expect(view.state.doc.toString()).toBe(original)
    expect(undoDepth(view.state)).toBe(2)
  }
  fireEvent.change(note, { target: { value: '尚未提交的准确候选审核表单' } })
  await waitFor(() => expect(view.state.readOnly).toBe(true)); assertBlocked()
  expect(await editBuffers.load(workspace)).toEqual(durable)
  fireEvent.change(note, { target: { value: '' } })
  await waitFor(() => expect(view.state.readOnly).toBe(false))
  let release!: () => void
  reviewSessionRead.mockImplementationOnce(() => new Promise(resolve => { release = () => resolve(session) }))
  fireEvent.click(screen.getByRole('button', { name: '刷新审核权限与本机恢复记录' }))
  await waitFor(() => expect(reviewSessionRead).toHaveBeenCalledTimes(2))
  assertBlocked(); expect(await editBuffers.load(workspace)).toEqual(durable)
  await act(async () => release())
  await waitFor(() => expect(view.state.readOnly).toBe(false))
  act(() => { expect(undo(view)).toBe(true) })
  expect(view.state.doc.toString()).toBe(original + '\n本机撤销探针')
  await waitFor(() => expect(view.state.readOnly).toBe(false))
  replaceSource(view.contentDOM, '恢复后可继续编辑 🧠\n\\alpha\n')
  await waitFor(async () => expect(Object.values(await editBuffers.load(workspace)).some(value => JSON.parse(value.text).local.body_markdown === '恢复后可继续编辑 🧠\n\\alpha\n')).toBe(true))
  expect(port.patch).not.toHaveBeenCalled()
})
