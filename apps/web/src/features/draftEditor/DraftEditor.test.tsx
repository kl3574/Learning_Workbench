import 'fake-indexeddb/auto'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { ApiError } from '../../api/client'
import type { LoadedBlock } from '../reader/contentClient'
import { reviewSession } from '../draftReview/reviewFixtures'
import type { EditPort } from './editClient'
import { editBase, editFixture } from './editFixtures'
import { editBuffers, editCommands } from './editJournal'
import { DraftEditor } from './DraftEditor'
afterEach(async () => { cleanup(); await Promise.all([editBuffers.close(), editCommands.close()]) })
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
