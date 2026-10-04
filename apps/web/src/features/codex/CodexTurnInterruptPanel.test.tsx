import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { IDBFactory } from 'fake-indexeddb'
import { afterEach, expect, test, vi } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { CodexTurnPanel } from './CodexTurnPanel'
import { actor, codexSession, deferred, session, workspace } from './bootstrapTestFixtures'
import { ApiError } from '../../api/client'
import { heldTurnCommands, heldTurnForms, releaseTurnCommand, releaseTurnForm } from './turnMemory'
import { readTurnCommand } from './turnCommands'
import { turnControl, turnPort } from './turnTestFixtures'

const stores: DraftStore[] = []
const local = () => {
 const store = new DraftStore({ name: crypto.randomUUID(), factory: new IDBFactory() })
 stores.push(store); return store
}
afterEach(async () => {
 cleanup()
 heldTurnCommands(workspace).forEach(releaseTurnCommand)
 heldTurnForms(workspace).forEach(releaseTurnForm)
 await Promise.all(stores.splice(0).map(v => v.close()))
})
const current = () => ({ ...codexSession(), revision: 4, active_turn_id: turnControl().id })
const ack = () => ({ id: current().id, turn_id: turnControl().id, status: 'interrupt_requested' as const })
const enabled = async (text: string) => waitFor(() => expect((screen.getByText(text) as HTMLButtonElement).disabled).toBe(false))
async function readBasis() {
 fireEvent.change(screen.getByLabelText('已建立的 session ID'), { target: { value: current().id } })
 fireEvent.click(screen.getByText('独立读取当前 session'))
 await screen.findByLabelText('独立 GET 当前 session')
 await enabled('读取回合控制 turn_test')
 fireEvent.click(screen.getByText('读取回合控制 turn_test'))
 await screen.findByLabelText('当前回合控制 turn_test')
 await enabled('明确中断会话回合 turn_test')
}
test.each(['learner', 'independent', 'open_book'] as const)('explicit session interrupt under %s saves the complete current-session basis/body/key before one POST', async mode => {
 const store = local(), formStore = local()
 const port = { ...turnPort(), interrupt: vi.fn(async (id: string, body: { turn_id: string; expected_session_revision: number }, key: string) => {
  const saved = JSON.parse((await store.load(workspace))[key].text)
  expect(saved.kind).toBe('interrupt'); expect(saved.actor_session_id).toBe(actor)
  expect(saved.session_id).toBe(id); expect(saved.body).toEqual(body)
  expect(saved.basis).toEqual({ session: current(), turn: turnControl() }); expect(saved.ack).toBeNull()
  return ack()
 }) }
 vi.mocked(port.current).mockResolvedValue(current())
 vi.mocked(port.session).mockResolvedValue({ ...session(), role: mode === 'learner' ? 'learner' : 'author',
  active_independent_attempt_id: mode === 'independent' ? 'attempt_test' : null,
  active_open_book_attempt_id: mode === 'open_book' ? 'attempt_open' : null })
 render(<CodexTurnPanel workspace={workspace} writeAdmitted={false} port={port} store={store} formStore={formStore} />)
 expect(port.interrupt).not.toHaveBeenCalled()
 fireEvent.click(screen.getByText('读取回合记录与权限'))
 await screen.findByText(/已读取本机记录/)
 await readBasis()
 expect(screen.queryByLabelText('回合原文')).toBeNull()
 fireEvent.click(screen.getByText('明确中断会话回合 turn_test'))
 await screen.findByText(/中断原 ACK 已保存/)
 expect(port.interrupt).toHaveBeenCalledExactlyOnceWith(current().id, { turn_id: 'turn_test', expected_session_revision: 4 }, expect.any(String))
 expect(port.cancel).not.toHaveBeenCalled(); expect(port.prepare).not.toHaveBeenCalled()
 expect(port.current).toHaveBeenCalledOnce(); expect(port.control).toHaveBeenCalledOnce()
 expect(screen.queryByLabelText('独立 GET 当前 session')).toBeNull()
 expect(screen.queryByLabelText('当前回合控制 turn_test')).toBeNull()
})
test('lost interrupt ACK survives remount and only explicit replay sends its original session revision/body/key', async () => {
 const store = local(), formStore = local(), port = { ...turnPort(), interrupt: vi.fn(async (_id: string, _body: { turn_id: string; expected_session_revision: number }, _key: string) => ack()) }
 vi.mocked(port.current).mockResolvedValue(current())
 vi.mocked(port.session).mockResolvedValue({ ...session(), role: 'learner' })
 port.interrupt.mockRejectedValueOnce(new Error('Lost synthetic interrupt ACK'))
 const view = render(<CodexTurnPanel workspace={workspace} writeAdmitted={false} port={port} store={store} formStore={formStore} />)
 fireEvent.click(screen.getByText('读取回合记录与权限')); await screen.findByText(/已读取本机记录/)
 await readBasis(); fireEvent.click(screen.getByText('明确中断会话回合 turn_test'))
 await screen.findByText(/操作结果或本机保存尚未确认/)
 const call = port.interrupt.mock.calls[0], original = readTurnCommand((await store.load(workspace))[call[2]], workspace)
 expect(original.ack).toBeNull(); expect(original.body).toEqual({ turn_id: 'turn_test', expected_session_revision: 4 })
 view.unmount()
 render(<CodexTurnPanel workspace={workspace} writeAdmitted={false} port={port} store={store} formStore={formStore} />)
 expect(port.interrupt).toHaveBeenCalledOnce()
 fireEvent.click(screen.getByText('读取回合记录与权限')); await screen.findByText(/已读取本机记录/)
 expect(port.interrupt).toHaveBeenCalledOnce()
 fireEvent.click(screen.getByText(`显式回放回合原 key ${call[2]}`))
 await screen.findByText(/中断原 ACK 已保存/)
 expect(port.interrupt.mock.calls[1]).toEqual(call)
 expect(port.current).toHaveBeenCalledOnce(); expect(port.control).toHaveBeenCalledOnce()
})

test('stale session CAS keeps the original command; a fresh session read does not rewrite or resend it', async () => {
 const store = local(), formStore = local(), port = turnPort()
 vi.mocked(port.current).mockResolvedValue(current())
 vi.mocked(port.session).mockResolvedValue({ ...session(), role: 'learner' })
 vi.mocked(port.interrupt).mockRejectedValueOnce(new ApiError(412, 'not for display', 'REVISION_MISMATCH'))
 render(<CodexTurnPanel workspace={workspace} writeAdmitted={false} port={port} store={store} formStore={formStore} />)
 fireEvent.click(screen.getByText('读取回合记录与权限')); await screen.findByText(/已读取本机记录/)
 await readBasis(); fireEvent.click(screen.getByText('明确中断会话回合 turn_test'))
 await screen.findByText(/版本已变化（412）/)
 const call = vi.mocked(port.interrupt).mock.calls[0]
 vi.mocked(port.current).mockResolvedValue({ ...current(), revision: 9 })
 fireEvent.click(screen.getByText('独立读取当前 session')); await screen.findByLabelText('独立 GET 当前 session')
 const original = readTurnCommand((await store.load(workspace))[call[2]], workspace)
 expect(original.body).toEqual({ turn_id: 'turn_test', expected_session_revision: 4 })
 expect(original.error).toEqual({ status: 412, code: 'REVISION_MISMATCH' })
 expect(port.interrupt).toHaveBeenCalledOnce(); expect(screen.queryByText('not for display')).toBeNull()
})
test('late interrupt ACK remains the original actor fact after unmount; a new actor cannot replay it', async () => {
 const store = local(), formStore = local(), port = turnPort(), pending = deferred<ReturnType<typeof ack>>()
 vi.mocked(port.current).mockResolvedValue(current())
 vi.mocked(port.session).mockResolvedValue({ ...session(), role: 'learner' })
 vi.mocked(port.interrupt).mockImplementation(() => pending.promise)
 const view = render(<CodexTurnPanel workspace={workspace} writeAdmitted={false} port={port} store={store} formStore={formStore} />)
 fireEvent.click(screen.getByText('读取回合记录与权限')); await screen.findByText(/已读取本机记录/)
 await readBasis(); fireEvent.click(screen.getByText('明确中断会话回合 turn_test'))
 await waitFor(() => expect(port.interrupt).toHaveBeenCalledOnce())
 const call = vi.mocked(port.interrupt).mock.calls[0]
 view.unmount(); await act(async () => pending.resolve(ack()))
 expect(heldTurnCommands(workspace)[0].actor_session_id).toBe(actor)
 expect(heldTurnCommands(workspace)[0].ack).toEqual(ack())
 vi.mocked(port.session).mockResolvedValue({ ...session(), role: 'learner', actor_session_id: 'new_safe_actor' })
 render(<CodexTurnPanel workspace={workspace} writeAdmitted={false} port={port} store={store} formStore={formStore} />)
 fireEvent.click(screen.getByText('读取回合记录与权限')); await screen.findByText(/已读取本机记录/)
 expect((screen.getByText(`显式回放回合原 key ${call[2]}`) as HTMLButtonElement).disabled).toBe(true)
 expect(port.interrupt).toHaveBeenCalledOnce()
 expect(screen.getByText('其他 actor 的安全控制记录只读；不能接管或重放。')).toBeTruthy()
})
