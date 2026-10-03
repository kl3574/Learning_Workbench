import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { ContentImpactsPanel } from './ContentImpactsPanel'
import { commandStore } from './commands'
import { discard } from './memory'
import { discardForms, ownForm } from './formMemory'
import { eventId, targetId, portFor, session } from './fixtures'
const spaces: string[] = []
afterEach(async () => { cleanup(); vi.restoreAllMocks(); for (const workspace of spaces.splice(0)) { discard(workspace); discardForms(workspace) }; await commandStore.close() })
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done }); return { promise, resolve } }
test('independent: editing while submit waits for journal read must retain the newer unsent reason', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`; spaces.push(workspace)
  const port = portFor(workspace); port.decide = vi.fn(port.decide)
  render(<ContentImpactsPanel workspace={workspace} paused={false} port={port} />)
  fireEvent.click(await screen.findByRole('button', { name: '从第一页读取内容变更' }))
  fireEvent.click(await screen.findByRole('button', { name: `查看影响详情 ${eventId}` }))
  fireEvent.click(await screen.findByRole('button', { name: `读取对象当前依据 ${targetId}` }))
  fireEvent.click(await screen.findByRole('button', { name: '采用本次对象依据准备决定' }))
  fireEvent.change(screen.getByLabelText('本次人工决定'), { target: { value: 'no_revision_needed' } })
  fireEvent.change(screen.getByLabelText('决定理由'), { target: { value: 'Original sent reason' } })
  fireEvent.click(screen.getByRole('checkbox'))
  const pending = deferred<Awaited<ReturnType<typeof commandStore.load>>>()
  const load = vi.spyOn(commandStore, 'load').mockImplementationOnce(() => pending.promise)
  fireEvent.click(screen.getByRole('button', { name: '明确保存内容决定' }))
  await waitFor(() => expect(load).toHaveBeenCalledTimes(1))
  const latest = 'Newer unsent reason α\nPreserve after original ACK'
  expect((screen.getByLabelText('决定理由') as HTMLTextAreaElement).disabled).toBe(false)
  fireEvent.change(screen.getByLabelText('决定理由'), { target: { value: latest } })
  expect(ownForm(workspace, session(workspace).csrf_token)?.value.reason).toBe(latest)
  await act(async () => { pending.resolve({}) })
  await waitFor(() => expect(port.decide).toHaveBeenCalledTimes(1))
  await waitFor(() => expect(Object.keys(vi.mocked(port.decide).mock.calls)).toHaveLength(1))
  await screen.findByText('原决定回执已保存。它记录当时的判断；请另行读取当前对象状态，修订和其他复核不会自动完成。')
  expect(vi.mocked(port.decide).mock.calls[0][1].reason).toBe('Original sent reason')
  expect(ownForm(workspace, session(workspace).csrf_token)?.value.reason).toBe(latest)
  const persisted = Object.values(await commandStore.load(workspace)); expect(persisted).toHaveLength(1)
  expect(JSON.parse(persisted[0].text).body.reason).toBe('Original sent reason')
})
