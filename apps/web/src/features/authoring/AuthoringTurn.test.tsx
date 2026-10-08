import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { IDBFactory } from 'fake-indexeddb'
import { afterEach, expect, test, vi } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { AuthoringPanel } from './AuthoringPanel'
import type { AuthoringPort } from './authoringClient'
import { actor, bootstrapPort, codexSession, deferred, preparation, session, workspace } from '../codex/bootstrapTestFixtures'
import { heldTurnCommands, heldTurnForms, releaseTurnCommand, releaseTurnForm } from '../codex/turnMemory'
import { turnBody, turnPort, turnPreparation } from '../codex/turnTestFixtures'
import { persistBootstrapCommand, prepareCommand } from '../codex/bootstrapCommands'
const stores: DraftStore[] = []
const db = () => { const store = new DraftStore({ name: crypto.randomUUID(), factory: new IDBFactory() }); stores.push(store); return store }
afterEach(async () => { cleanup(); heldTurnCommands(workspace).forEach(releaseTurnCommand); heldTurnForms(workspace).forEach(releaseTurnForm); await Promise.all(stores.splice(0).map(v => v.close())) })
const authoring = (): AuthoringPort => {
 const unexpected = vi.fn(async (): Promise<never> => { throw new Error('Unexpected academic operation') })
 return { session: vi.fn(async () => session()), list: vi.fn(async () => ({ items: [], next_cursor: null })), prepare: unexpected, read: unexpected, draft: unexpected, preview: unexpected, numeric: unexpected, decide: unexpected, job: unexpected, cancel: unexpected }
}
test('bootstrap selection passes only a session ID; turn preparation still requires independent current GET and keeps bootstrap bytes intact', async () => {
 const port = authoring(), bootstrap = bootstrapPort(), turn = turnPort(), bootstrapStore = db(), turnStore = db(), formStore = db()
 const original = prepareCommand(workspace, actor)
 if (original.kind !== 'prepare') throw new Error('Expected prepare')
 await persistBootstrapCommand({ ...original, ack: preparation() }, bootstrapStore)
 const before = await bootstrapStore.load(workspace)
 vi.mocked(bootstrap.preparation).mockResolvedValue(preparation('consumed'))
 render(<AuthoringPanel workspace={workspace} paused={false} currentBlock={null} port={port} bootstrap={bootstrap} bootstrapStore={bootstrapStore} turn={turn} turnStore={turnStore} turnFormStore={formStore} onState={() => {}} />)
 fireEvent.click(screen.getByText('读取本地会话记录')); await screen.findByText('读取准备当前状态 preparation_test')
 fireEvent.click(screen.getByText('读取准备当前状态 preparation_test')); await screen.findByText(`用于回合准备 ${codexSession().id}`)
 fireEvent.click(screen.getByText(`用于回合准备 ${codexSession().id}`))
 fireEvent.click(screen.getByText('读取回合记录与权限')); await screen.findByText(/已读取本机记录/)
 fireEvent.click(screen.getByText(`选择已核验会话 ${codexSession().id}`))
 fireEvent.change(screen.getByLabelText('回合原文'), { target: { value: turnBody().message } })
 fireEvent.change(screen.getByLabelText('Provider ID'), { target: { value: turnBody().provider_id } })
 expect((screen.getByText('明确准备回合并预约 Job') as HTMLButtonElement).disabled).toBe(true)
 expect(turn.current).not.toHaveBeenCalled(); expect(turn.prepare).not.toHaveBeenCalled()
 fireEvent.click(screen.getByText('独立读取当前 session')); await screen.findByLabelText('独立 GET 当前 session')
 fireEvent.click(screen.getByText('明确准备回合并预约 Job')); await screen.findByText(/准备原 ACK 已保存/)
 expect(turn.prepare).toHaveBeenCalledOnce(); expect(await bootstrapStore.load(workspace)).toEqual(before)
 expect(bootstrap.create).not.toHaveBeenCalled(); expect(bootstrap.decide).not.toHaveBeenCalled(); expect(bootstrap.prepare).not.toHaveBeenCalled()
})
test('parent navigation guard preserves dirty/safe/isolated and does not discard late turn facts with other forms', async () => {
 const port = authoring(), turn = turnPort(), pending = deferred<ReturnType<typeof turnPreparation>>(), changed = vi.fn(), store = db(), formStore = db()
 vi.mocked(turn.prepare).mockReturnValue(pending.promise)
 const view = render(<AuthoringPanel workspace={workspace} paused={false} currentBlock={null} port={port} turn={turn} turnStore={store} turnFormStore={formStore} onState={changed} />)
 await waitFor(() => expect(changed.mock.calls.at(-1)?.[0].safe).toBe(true))
 fireEvent.click(screen.getByText('读取回合记录与权限')); await screen.findByText(/已读取本机记录/)
 fireEvent.change(screen.getByLabelText('已建立的 session ID'), { target: { value: codexSession().id } })
 fireEvent.click(screen.getByText('独立读取当前 session')); await screen.findByLabelText('独立 GET 当前 session')
 fireEvent.change(screen.getByLabelText('回合原文'), { target: { value: turnBody().message } })
 fireEvent.change(screen.getByLabelText('Provider ID'), { target: { value: turnBody().provider_id } })
 await waitFor(() => expect(changed.mock.calls.at(-1)?.[0]).toMatchObject({ dirty: true, safe: true, isolated: false }))
 fireEvent.click(screen.getByText('明确准备回合并预约 Job')); await waitFor(() => expect(turn.prepare).toHaveBeenCalledOnce())
 expect(changed.mock.calls.at(-1)?.[0].safe).toBe(false)
 view.rerender(<AuthoringPanel workspace={workspace} paused currentBlock={null} port={port} turn={turn} turnStore={store} turnFormStore={formStore} onState={changed} />)
 await act(async () => pending.resolve(turnPreparation()))
 await waitFor(() => expect(changed.mock.calls.at(-1)?.[0]).toMatchObject({ dirty: true, safe: false, isolated: true, isolationLabel: '保留本地会话隔离内存，丢弃临时表单并前往角色控制' }))
 act(() => changed.mock.calls.at(-1)?.[0].discardForms())
 expect(heldTurnCommands(workspace)[0].ack).toEqual(turnPreparation())
 expect(turn.prepare).toHaveBeenCalledOnce(); expect(screen.queryByLabelText('回合原文')).toBeNull()
})
