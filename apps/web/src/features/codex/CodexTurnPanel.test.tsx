import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { IDBFactory } from 'fake-indexeddb'
import { afterEach, expect, test, vi } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { actor, codexSession, deferred, session, workspace } from './bootstrapTestFixtures'
import { CodexTurnPanel } from './CodexTurnPanel'
import { turnBody, turnControl, turnPort, turnPreparation } from './turnTestFixtures'
import { ApiError, request } from '../../api/client'
import { heldTurnCommands, heldTurnForms, releaseTurnCommand, releaseTurnForm } from './turnMemory'
import { decodeTurnCommand, persistTurnCommand, readTurnCommand, turnPrepareCommand } from './turnCommands'
import type { TurnPort } from './turnClient'
const stores: DraftStore[] = []
const local = () => { const value = new DraftStore({ name: `turn-test-${crypto.randomUUID()}`, factory: new IDBFactory() }); stores.push(value); return value }
afterEach(async () => {
 cleanup()
 for (const space of [workspace, 'workspace_other']) {
  heldTurnCommands(space).forEach(releaseTurnCommand); heldTurnForms(space).forEach(releaseTurnForm)
 }
 await Promise.all(stores.splice(0).map(value => value.close()))
 vi.unstubAllGlobals()
})
const enabled = async (label: string) => waitFor(() => expect((screen.getByText(label) as HTMLButtonElement).disabled).toBe(false))
const refresh = async () => { fireEvent.click(screen.getByText('读取回合记录与权限')); await enabled('读取回合记录与权限'); await screen.findByText(/已读取本机记录/) }
async function enter() {
 fireEvent.click(screen.getByText('读取回合记录与权限'))
 await waitFor(() => expect(screen.getByLabelText('回合原文')).toBeTruthy())
 await waitFor(() => expect((screen.getByLabelText('已建立的 session ID') as HTMLInputElement).disabled).toBe(false))
 fireEvent.change(screen.getByLabelText('已建立的 session ID'), { target: { value: codexSession().id } })
 fireEvent.click(screen.getByText('独立读取当前 session'))
 await screen.findByLabelText('独立 GET 当前 session')
 fireEvent.change(screen.getByLabelText('回合原文'), { target: { value: turnBody().message } })
 fireEvent.change(screen.getByLabelText('Provider ID'), { target: { value: turnBody().provider_id } })
}
test('explicit preparation persists original actor/key/body/current GET basis before POST; ACK is not current', async () => {
 const port = turnPort(), store = local(), formStore = local()
 vi.mocked(port.prepare).mockImplementation(async (id, body, key) => {
  const records = await store.load(workspace), command = JSON.parse(records[key].text)
  expect(command.actor_session_id).toBe(actor); expect(command.session_id).toBe(id)
  expect(command.body).toEqual(turnBody()); expect(command.basis).toEqual(codexSession()); expect(command.ack).toBeNull()
  return turnPreparation(body)
 })
 render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} />)
 expect(port.session).not.toHaveBeenCalled(); expect(port.prepare).not.toHaveBeenCalled()
 await enter()
 await waitFor(() => expect((screen.getByText('明确准备回合并预约 Job') as HTMLButtonElement).disabled).toBe(false))
 fireEvent.click(screen.getByText('明确准备回合并预约 Job'))
 await waitFor(() => expect(port.prepare).toHaveBeenCalledTimes(1))
 await screen.findByText(/准备原 ACK 已保存/)
 expect(port.current).toHaveBeenCalledTimes(1)
 expect(port.preparation).not.toHaveBeenCalled(); expect(port.cancel).not.toHaveBeenCalled()
 expect(screen.queryByLabelText('当前回合准备详情')).toBeNull()
})

test('unknown preparation survives remount and only explicitly replays original actor/key/body/basis', async () => {
 const port = turnPort(), store = local(), formStore = local()
 vi.mocked(port.prepare).mockRejectedValueOnce(new Error('lost synthetic ACK'))
 const view = render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} />)
 await enter(); fireEvent.click(screen.getByText('明确准备回合并预约 Job'))
 await screen.findByText(/操作结果或本机保存尚未确认/)
 const original = vi.mocked(port.prepare).mock.calls[0], command = readTurnCommand((await store.load(workspace))[original[2]], workspace)
 if (command.kind !== 'prepare') throw new Error('Expected original preparation')
 expect(command.ack).toBeNull(); expect(command.body.message).toBe(turnBody().message)
 view.unmount()
 render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} />)
 expect(port.prepare).toHaveBeenCalledTimes(1)
 await refresh(); expect(port.prepare).toHaveBeenCalledTimes(1)
 fireEvent.click(screen.getByText(`显式回放回合原 key ${original[2]}`))
 await screen.findByText(/准备原 ACK 已保存/)
 expect(vi.mocked(port.prepare).mock.calls[1]).toEqual(original)
 expect(port.current).toHaveBeenCalledTimes(1)
})

test.each([412, 409])('HTTP %s retains original readonly basis; reading a new current never edits or resends the command', async status => {
 const port = turnPort(), store = local(), formStore = local()
 vi.mocked(port.prepare).mockRejectedValueOnce(new ApiError(status, 'private provider body', 'CODEX_SOURCE_CHANGED'))
 render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} />)
 await enter(); fireEvent.click(screen.getByText('明确准备回合并预约 Job'))
 await screen.findByText(status === 412 ? /版本已变化（412）/ : /操作绑定冲突（409）/)
 const call = vi.mocked(port.prepare).mock.calls[0]
 vi.mocked(port.current).mockResolvedValue({ ...codexSession(), revision: 9, active_turn_id: 'turn_existing' })
 fireEvent.click(screen.getByText('独立读取当前 session')); await screen.findByLabelText('独立 GET 当前 session')
 const command = readTurnCommand((await store.load(workspace))[call[2]], workspace)
 if (command.kind !== 'prepare') throw new Error('Expected original preparation')
 expect(command.basis.revision).toBe(2); expect(command.error?.status).toBe(status)
 expect(port.prepare).toHaveBeenCalledTimes(1); expect(screen.queryByText(/private provider body/)).toBeNull()
 expect((screen.getByText('明确准备回合并预约 Job') as HTMLButtonElement).disabled).toBe(true)
})

test.each(['learner', 'independent', 'open_book'] as const)('safe session/page/control/cancel remain available under %s, protected form and detail do not', async mode => {
 const port = turnPort(), store = local(), formStore = local()
 vi.mocked(port.session).mockResolvedValue({ ...session(), role: mode === 'learner' ? 'learner' : 'author', active_independent_attempt_id: mode === 'independent' ? 'attempt_test' : null, active_open_book_attempt_id: mode === 'open_book' ? 'attempt_open' : null })
 vi.mocked(port.cancel).mockImplementation(async (id, revision, key) => {
  const command = readTurnCommand((await store.load(workspace))[key], workspace)
  expect(command.kind).toBe('cancel'); expect(command.actor_session_id).toBe(actor)
  expect(command.basis).toEqual(turnControl()); expect(command.body).toEqual({ expected_revision: revision })
  return { id, status: 'cancelled' }
 })
 render(<CodexTurnPanel workspace={workspace} writeAdmitted={false} port={port} store={store} formStore={formStore} />)
 await refresh(); expect(screen.queryByLabelText('回合原文')).toBeNull()
 fireEvent.change(screen.getByLabelText('已建立的 session ID'), { target: { value: codexSession().id } })
 fireEvent.click(screen.getByText('独立读取当前 session')); await screen.findByLabelText('独立 GET 当前 session')
 fireEvent.click(screen.getByText('读取安全回合分页')); await screen.findByLabelText('安全回合分页')
 fireEvent.click(screen.getByText('读取回合控制 turn_test')); await screen.findByLabelText('当前回合控制 turn_test')
 fireEvent.click(screen.getByText('明确取消回合 Job job_turn_test')); await screen.findByText(/取消原 ACK 已保存/)
 expect(port.cancel).toHaveBeenCalledTimes(1); expect(port.prepare).not.toHaveBeenCalled(); expect(port.preparation).not.toHaveBeenCalled()
})

test('unsent Unicode and precise chosen block survive reload; current reader change cannot replace the frozen choice', async () => {
 const port = turnPort(), store = local(), formStore = local(), ref = { entity: 'block' as const, id: 'block_original', revision: 1, sha256: 'a'.repeat(64) }
 const view = render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} currentBlock={ref} />)
 await enter(); fireEvent.click(screen.getByText('选择当前完整公开块'))
 await waitFor(() => expect(heldTurnForms(workspace)).toHaveLength(0))
 view.rerender(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} currentBlock={{ ...ref, id: 'block_other', revision: 2 }} />)
 expect(screen.getByLabelText('本次精确材料引用').textContent).toContain('block_original')
 view.unmount()
 render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} />)
 await refresh(); expect(port.prepare).not.toHaveBeenCalled()
 fireEvent.click(screen.getByText(/恢复原表单/))
 await screen.findByText(/原表单已核验并恢复/)
 expect((screen.getByLabelText('回合原文') as HTMLTextAreaElement).value).toBe(turnBody().message)
 expect(JSON.parse(screen.getByLabelText('本次精确材料引用').textContent!)).toEqual([ref])
 expect(screen.queryByLabelText('独立 GET 当前 session')).toBeNull()
 fireEvent.click(screen.getByText('独立读取当前 session')); await screen.findByLabelText('独立 GET 当前 session')
 fireEvent.click(screen.getByText('明确准备回合并预约 Job')); await screen.findByText(/准备原 ACK 已保存/)
 expect(vi.mocked(port.prepare).mock.calls[0][1]).toEqual({ ...turnBody(), context_refs: [ref] })
})

test.each(['admission', 'workspace', 'port', 'store', 'unmount'] as const)('late ACK after %s change is isolated under original actor and never delivered as current', async change => {
 const port = turnPort(), store = local(), formStore = local(), response = deferred<Awaited<ReturnType<TurnPort['prepare']>>>()
 vi.mocked(port.prepare).mockReturnValue(response.promise)
 const changed = vi.fn(), view = render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} onState={changed} />)
 await enter(); fireEvent.click(screen.getByText('明确准备回合并预约 Job'))
 await waitFor(() => expect(port.prepare).toHaveBeenCalledTimes(1))
 if (change === 'unmount') view.unmount()
 else view.rerender(<CodexTurnPanel workspace={change === 'workspace' ? 'workspace_other' : workspace} writeAdmitted={change !== 'admission'} port={change === 'port' ? turnPort() : port} store={change === 'store' ? local() : store} formStore={formStore} onState={changed} />)
 await act(async () => { response.resolve(turnPreparation()) })
 expect(heldTurnCommands(workspace)).toHaveLength(1)
 expect(heldTurnCommands(workspace)[0].ack).toEqual(turnPreparation())
 expect(screen.queryByText(/准备原 ACK 已保存/)).toBeNull(); expect(screen.queryByLabelText('当前回合准备详情')).toBeNull()
 expect(port.prepare).toHaveBeenCalledTimes(1)
 if (change === 'admission') {
  expect(changed).toHaveBeenLastCalledWith({ dirty: true, safe: false, isolated: true })
  vi.mocked(port.session).mockResolvedValue({ ...session(), role: 'learner' })
  await refresh(); expect(screen.queryByLabelText('回合原文')).toBeNull(); expect(screen.queryByText(/核对回合原命令/)).toBeNull()
  fireEvent.click(screen.getByText('仅保存原回合本机事实')); await screen.findByText(/仅保存原 actor/)
  expect(heldTurnCommands(workspace)).toHaveLength(0)
  const saved = Object.values(await store.load(workspace)).map(v => readTurnCommand(v, workspace))[0]
  expect(saved.actor_session_id).toBe(actor); expect(saved.ack).toEqual(turnPreparation()); expect(port.prepare).toHaveBeenCalledTimes(1)
 }
})

test('another actor cannot see or replay the original preparation, prompt, or form after refresh', async () => {
 const port = turnPort(), store = local(), formStore = local()
 vi.mocked(port.prepare).mockRejectedValue(new Error('unknown'))
 render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} />)
 await enter(); fireEvent.click(screen.getByText('明确准备回合并预约 Job')); await screen.findByText(/操作结果或本机保存尚未确认/)
 vi.mocked(port.session).mockResolvedValue({ ...session(), actor_session_id: 'actor_other' })
 await refresh()
 expect(screen.queryByText(/核对回合原命令/)).toBeNull(); expect(screen.queryByText(/恢复原表单/)).toBeNull()
 expect((screen.getByLabelText('回合原文') as HTMLTextAreaElement).value).toBe('')
 fireEvent.click(screen.getByText('独立读取当前 session')); await screen.findByLabelText('独立 GET 当前 session')
 expect((screen.getByText('明确准备回合并预约 Job') as HTMLButtonElement).disabled).toBe(true)
 fireEvent.click(screen.getByText('明确准备回合并预约 Job'))
 expect(port.prepare).toHaveBeenCalledTimes(1)
})

test('storage failure prevents every POST and preserves unsent form/original command in navigation isolation', async () => {
 const port = turnPort(), store = local(), formStore = local(), changed = vi.fn()
 vi.spyOn(store, 'save').mockRejectedValue(new Error('synthetic quota'))
 render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} onState={changed} />)
 await enter(); fireEvent.click(screen.getByText('明确准备回合并预约 Job')); await screen.findByText(/操作结果或本机保存尚未确认/)
 expect(port.prepare).not.toHaveBeenCalled(); expect(heldTurnCommands(workspace)[0].body).toEqual(turnBody())
 expect(changed).toHaveBeenLastCalledWith({ dirty: true, safe: false, isolated: true })
})

test('fresh permission check after durable command save blocks a changed actor before POST', async () => {
 const port = turnPort(), store = local(), formStore = local(), save = store.save.bind(store)
 vi.spyOn(store, 'save').mockImplementation(async (...args) => {
  const result = await save(...args); vi.mocked(port.session).mockResolvedValue({ ...session(), actor_session_id: 'actor_other' }); return result
 })
 render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} />)
 await enter(); fireEvent.click(screen.getByText('明确准备回合并预约 Job')); await screen.findByText(/当前权限或原 actor 已变化/)
 expect(port.prepare).not.toHaveBeenCalled(); expect(Object.keys(await store.load(workspace))).toHaveLength(1)
 expect(screen.queryByLabelText('回合原文')).toBeNull()
})

test('current preparation details are an explicit academic GET and honestly show unavailable', async () => {
 const port = turnPort(), store = local(), formStore = local()
 render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} />)
 await enter(); fireEvent.click(screen.getByText('明确准备回合并预约 Job')); await screen.findByText(/准备原 ACK 已保存/)
 expect(port.preparation).not.toHaveBeenCalled()
 fireEvent.click(screen.getByText('独立读取准备详情 turn_preparation_test'))
 const detail = await screen.findByLabelText('当前回合准备详情')
 expect(within(detail).getByText(/CODEX_INPUT_PROOF_UNAVAILABLE/)).toBeTruthy()
 expect(port.prepare).toHaveBeenCalledTimes(1)
 vi.mocked(port.preparation).mockRejectedValue(new ApiError(403, 'secret body', 'ASSESSMENT_ACTIVE'))
 fireEvent.click(screen.getByText('独立读取准备详情 turn_preparation_test')); await screen.findByText(/当前权限或原 actor 已变化/)
 expect(screen.queryByLabelText('当前回合准备详情')).toBeNull(); expect(screen.queryByLabelText('回合原文')).toBeNull()
 expect(screen.queryByText(/secret body/)).toBeNull()
})

test.each([['工具调用上限', '17'], ['工具调用上限', '-1'], ['工具调用上限', '1e1'], ['回合 wall 秒数', '0'], ['回合 wall 秒数', '301'], ['回合 wall 秒数', ''], ['Provider ID', '../bad'], ['回合原文', ' \n ']])('invalid %s %s preserves form and cannot allocate/send a command', async (label, value) => {
 const port = turnPort(), store = local(), formStore = local()
 render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} />)
 await enter(); fireEvent.change(screen.getByLabelText(label), { target: { value } })
 expect((screen.getByText('明确准备回合并预约 Job') as HTMLButtonElement).disabled).toBe(true)
 expect((screen.getByLabelText(label) as HTMLInputElement).value).toBe(value)
 expect(port.prepare).not.toHaveBeenCalled(); expect(Object.keys(await store.load(workspace))).toHaveLength(0)
})

test('changed frozen body in a current preparation response cannot replace the original request', async () => {
 const port = turnPort(), store = local(), formStore = local()
 render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} />)
 await enter(); fireEvent.click(screen.getByText('明确准备回合并预约 Job')); await screen.findByText(/准备原 ACK 已保存/)
 vi.mocked(port.preparation).mockResolvedValue(turnPreparation({ ...turnBody(), message: 'different frozen request' }))
 fireEvent.click(screen.getByText('独立读取准备详情 turn_preparation_test'))
 await enabled('读取回合记录与权限')
 expect(screen.queryByLabelText('当前回合准备详情')).toBeNull()
 expect(screen.queryByText(/different frozen request/)).toBeNull()
})

test('access generation changes invalidate a pending current GET without automatic reads or POST', async () => {
 const port = turnPort(), store = local(), formStore = local(), pending = deferred<ReturnType<typeof codexSession>>()
 vi.mocked(port.current).mockReturnValue(pending.promise)
 render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} />)
 await refresh()
 fireEvent.change(screen.getByLabelText('已建立的 session ID'), { target: { value: codexSession().id } })
 fireEvent.click(screen.getByText('独立读取当前 session')); await waitFor(() => expect(port.current).toHaveBeenCalledOnce())
 vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(session()), { status: 200 })))
 await act(async () => { await request('POST /api/v1/session/role', { role: 'learner' }, { 'Idempotency-Key': 'synthetic_access_change' }) })
 await act(async () => pending.resolve(codexSession()))
 expect(screen.queryByLabelText('独立 GET 当前 session')).toBeNull()
 expect(screen.queryByLabelText('回合原文')).toBeNull(); expect(port.current).toHaveBeenCalledOnce(); expect(port.prepare).not.toHaveBeenCalled()
})

test('late ACK followed by a changed actual actor remains original isolated history with no protected delivery', async () => {
 const port = turnPort(), store = local(), formStore = local(), pending = deferred<ReturnType<typeof turnPreparation>>()
 vi.mocked(port.prepare).mockReturnValue(pending.promise)
 render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} />)
 await enter(); fireEvent.click(screen.getByText('明确准备回合并预约 Job')); await waitFor(() => expect(port.prepare).toHaveBeenCalledOnce())
 vi.mocked(port.session).mockResolvedValue({ ...session(), actor_session_id: 'actor_after_send' })
 await act(async () => pending.resolve(turnPreparation()))
 await screen.findByText(/当前权限或原 actor 已变化/)
 expect(heldTurnCommands(workspace)[0].actor_session_id).toBe(actor); expect(heldTurnCommands(workspace)[0].ack).toEqual(turnPreparation())
 expect(screen.queryByLabelText('回合原文')).toBeNull(); expect(screen.queryByText(/核对回合原命令/)).toBeNull()
 expect(port.prepare).toHaveBeenCalledOnce()
})

test('unknown cancellation persists the original safe reader and revision across remount; original key replay needs no academic access', async () => {
 const port = turnPort(), store = local(), formStore = local()
 vi.mocked(port.session).mockResolvedValue({ ...session(), role: 'learner', actor_session_id: 'learner_cancel' })
 vi.mocked(port.cancel).mockRejectedValueOnce(new Error('lost cancel ACK'))
 const view = render(<CodexTurnPanel workspace={workspace} writeAdmitted={false} port={port} store={store} formStore={formStore} />)
 await refresh(); fireEvent.change(screen.getByLabelText('已建立的 session ID'), { target: { value: codexSession().id } })
 fireEvent.click(screen.getByText('读取安全回合分页')); await screen.findByLabelText('安全回合分页')
 fireEvent.click(screen.getByText('读取回合控制 turn_test')); await screen.findByLabelText('当前回合控制 turn_test')
 fireEvent.click(screen.getByText('明确取消回合 Job job_turn_test')); await screen.findByText(/操作结果或本机保存尚未确认/)
 const original = vi.mocked(port.cancel).mock.calls[0]
 view.unmount(); render(<CodexTurnPanel workspace={workspace} writeAdmitted={false} port={port} store={store} formStore={formStore} />)
 await refresh(); expect(port.cancel).toHaveBeenCalledOnce()
 fireEvent.click(screen.getByText(`显式回放回合原 key ${original[2]}`)); await screen.findByText(/取消原 ACK 已保存/)
 expect(vi.mocked(port.cancel).mock.calls[1]).toEqual(original)
 expect(port.control).toHaveBeenCalledOnce(); expect(port.preparation).not.toHaveBeenCalled()
})

test('failed form persistence protects navigation/unload, survives unmount in memory, and can be explicitly saved without POST', async () => {
 const port = turnPort(), store = local(), formStore = local(), changed = vi.fn(), save = vi.spyOn(formStore, 'save').mockRejectedValue(new Error('synthetic storage failure'))
 const view = render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} onState={changed} />)
 await enter(); await screen.findByText(/表单尚未全部保存/)
 expect(changed).toHaveBeenLastCalledWith({ dirty: true, safe: false, isolated: true })
 const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event); expect(event.defaultPrevented).toBe(true)
 view.unmount(); save.mockRestore()
 render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} />)
 await refresh(); fireEvent.click(screen.getByText('仅保存原回合本机事实')); await screen.findByText(/仅保存原 actor/)
 expect(heldTurnForms(workspace)).toHaveLength(0)
 fireEvent.click(screen.getByText(/恢复原表单/))
 await screen.findByText(/原表单已核验并恢复/)
 expect((screen.getByLabelText('回合原文') as HTMLTextAreaElement).value).toBe(turnBody().message)
 expect(port.prepare).not.toHaveBeenCalled(); expect(port.cancel).not.toHaveBeenCalled()
})

test.each(['unknown', 'failed', 'initializing'] as const)('bootstrap session %s cannot supply a preparation baseline', async status => {
 const port = turnPort(), store = local(), formStore = local()
 vi.mocked(port.current).mockResolvedValue(codexSession(status))
 render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} />)
 await enter(); expect((screen.getByText('明确准备回合并预约 Job') as HTMLButtonElement).disabled).toBe(true)
 expect(port.prepare).not.toHaveBeenCalled()
})

test('an ACK persisted by another view before explicit replay prevents POST and releases the weaker pending memory', async () => {
 const port = turnPort(), store = local(), formStore = local(), original = turnPrepareCommand(workspace, actor, codexSession(), turnBody()), changed = vi.fn()
 await persistTurnCommand(original, store)
 render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} store={store} formStore={formStore} onState={changed} />)
 await refresh()
 await persistTurnCommand(decodeTurnCommand(JSON.stringify({ ...original, ack: turnPreparation() }), workspace), store)
 fireEvent.click(screen.getByText(`显式回放回合原 key ${original.command_id}`)); await enabled('读取回合记录与权限')
 expect(port.prepare).not.toHaveBeenCalled(); expect(heldTurnCommands(workspace)).toHaveLength(0)
 expect(changed).toHaveBeenLastCalledWith({ dirty: false, safe: true, isolated: false })
})
