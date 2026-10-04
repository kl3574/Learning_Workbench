import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { IDBFactory } from 'fake-indexeddb'
import { request } from '../../api/client'
import { DraftStore } from '../../workbench/DraftStore'
import { CodexTurnEventsPanel } from './CodexTurnEventsPanel'
import { CodexTurnPanel } from './CodexTurnPanel'
import { createCodexEventsClient, type CodexEventPort, type CodexTurnEvent } from './turnEventClient'
import { deferred, session, workspace } from './bootstrapTestFixtures'
import { turnPort } from './turnTestFixtures'

const stores: DraftStore[] = []
afterEach(async () => { cleanup(); vi.unstubAllGlobals(); await Promise.all(stores.splice(0).map(value => value.close())) })
const event = (seq: number, payload: CodexTurnEvent['payload']): CodexTurnEvent => ({ turn_id: 'turn_test', run_id: 'job_turn_test', seq, occurred_at: '2026-10-05T00:00:00Z', payload })
const fixture = () => {
 const controllers: ReadableStreamDefaultController<Uint8Array>[] = [], signals: AbortSignal[] = [], cancelled = vi.fn()
 const fetcher = vi.fn<typeof fetch>(async (_path, init) => {
  signals.push(init!.signal!)
  return new Response(new ReadableStream<Uint8Array>({ start(controller) { controllers.push(controller) }, cancel: cancelled }), { headers: { 'Content-Type': 'text/event-stream' } })
 })
 const port: CodexEventPort = { session: vi.fn(async () => session()), events: createCodexEventsClient(fetcher) }
 return { port, fetcher, signals, cancelled,
  send(value: CodexTurnEvent, index = controllers.length - 1) { controllers[index].enqueue(new TextEncoder().encode(`id: ${value.run_id}:${value.seq}\nevent: ${value.payload.type}\ndata: ${JSON.stringify(value)}\n\n`)) },
  close(index = controllers.length - 1) { controllers[index].close() },
 }
}
const props = { workspace, turn: 'turn_test', run: 'job_turn_test', admitted: true }
const connect = async (f: ReturnType<typeof fixture>, count = 1) => { fireEvent.click(screen.getByRole('button', { name: '明确连接回合事件 turn_test' })); await waitFor(() => expect(f.fetcher).toHaveBeenCalledTimes(count)) }
const text = async (expected: string) => waitFor(() => expect(screen.getByLabelText('Codex 事件原文').textContent).toBe(expected))

test('only explicit connect reads; raw text/IDs never initiate commands/details; original cursor requires explicit reconnect', async () => {
 const f = fixture(); render(<CodexTurnEventsPanel {...props} port={f.port} />)
 expect(f.port.session).not.toHaveBeenCalled(); expect(f.fetcher).not.toHaveBeenCalled()
 await connect(f)
 await act(async () => { f.send(event(1, { type: 'answer_delta', text: ' \n😀\t' })); f.send(event(2, { type: 'approval_required', approval_id: 'approval_test' })); f.send(event(3, { type: 'manifest_ready', manifest_id: 'manifest_test', manifest_sha256: 'a'.repeat(64) })) })
 await text(' \n😀\t'); await screen.findByText(/产物清单 ID manifest_test/)
 expect(f.fetcher).toHaveBeenCalledTimes(1); expect(screen.getByText(/审批 ID approval_test/)).toBeTruthy()
 fireEvent.click(screen.getByRole('button', { name: '断开此事件连接' }))
 expect(f.signals[0].aborted).toBe(true); await screen.findByText(/连接中断，任务状态未知/)
 expect(f.fetcher).toHaveBeenCalledTimes(1)
 fireEvent.click(screen.getByRole('button', { name: '从原游标明确重连 job_turn_test:3' }))
 await waitFor(() => expect(f.fetcher).toHaveBeenCalledTimes(2))
 expect(f.fetcher.mock.calls[1][0]).toBe('/api/v1/codex/turns/turn_test/events?after_seq=3')
 await act(async () => { f.send(event(4, { type: 'answer_delta', text: '\nend ' })); f.send(event(5, { type: 'terminal', outcome: 'completed', error_code: null })); f.close() })
 await text(' \n😀\t\nend '); await screen.findByText(/已观察终态事件：completed/)
 expect(f.fetcher.mock.calls.every(call => call[1]?.method === 'GET')).toBe(true)
})

test.each(['actor', 'learner', 'independent', 'open_book', 'workspace'] as const)('fresh %s change without a page notification rejects late answer and clears displayed text/cursor', async mode => {
 const f = fixture(); render(<CodexTurnEventsPanel {...props} port={f.port} />); await connect(f)
 await act(async () => f.send(event(1, { type: 'answer_delta', text: 'protected original' }))); await text('protected original')
 vi.mocked(f.port.session).mockResolvedValue({ ...session(), ...(mode === 'actor' ? { actor_session_id: 'actor_new' } : mode === 'learner' ? { role: 'learner' } : mode === 'independent' ? { active_independent_attempt_id: 'attempt_test' } : mode === 'open_book' ? { active_open_book_attempt_id: 'attempt_test' } : { workspace_id: 'workspace_other' }) })
 await act(async () => f.send(event(2, { type: 'answer_delta', text: 'late private' })))
 await screen.findByText(/事件显示已清除/)
 expect(screen.queryByLabelText('Codex 事件原文')).toBeNull(); expect(screen.queryByText(/本页已核游标/)).toBeNull()
 expect(f.signals[0].aborted).toBe(true); expect(f.fetcher).toHaveBeenCalledTimes(1)
})

test.each(['admission', 'workspace', 'turn', 'run', 'port'] as const)('render-scope %s change immediately isolates and aborts; no automatic new GET', async mode => {
 const f = fixture(), next = fixture(), view = render(<CodexTurnEventsPanel {...props} port={f.port} />); await connect(f)
 await act(async () => f.send(event(1, { type: 'answer_delta', text: 'protected original' }))); await text('protected original')
 view.rerender(<CodexTurnEventsPanel {...props} port={mode === 'port' ? next.port : f.port} admitted={mode !== 'admission'} workspace={mode === 'workspace' ? 'workspace_other' : workspace} turn={mode === 'turn' ? 'turn_other' : props.turn} run={mode === 'run' ? 'job_other' : props.run} />)
 expect(screen.queryByLabelText('Codex 事件原文')).toBeNull(); expect(f.signals[0].aborted).toBe(true)
 expect(f.fetcher).toHaveBeenCalledTimes(1); expect(next.fetcher).not.toHaveBeenCalled()
})

test('page access generation mutation aborts and clears display before the permission write settles', async () => {
 const f = fixture(), held = deferred<Response>(); render(<CodexTurnEventsPanel {...props} port={f.port} />); await connect(f)
 await act(async () => f.send(event(1, { type: 'answer_delta', text: 'protected original' }))); await text('protected original')
 vi.stubGlobal('fetch', vi.fn(() => held.promise))
 let role!: ReturnType<typeof request<'POST /api/v1/session/role'>>
 await act(async () => { role = request('POST /api/v1/session/role', { role: 'learner' }, { 'Idempotency-Key': 'event_permission_change' }) })
 expect(screen.queryByLabelText('Codex 事件原文')).toBeNull(); expect(f.signals[0].aborted).toBe(true)
 await act(async () => { held.resolve(new Response(JSON.stringify({ ...session(), role: 'learner' }))); await role })
 expect(f.fetcher).toHaveBeenCalledTimes(1)
})

test('pending fresh delivery cannot survive unmount/remount or explicit disconnect', async () => {
 const f = fixture(), held = deferred<ReturnType<typeof session>>(), view = render(<CodexTurnEventsPanel {...props} port={f.port} />); await connect(f)
 vi.mocked(f.port.session).mockImplementationOnce(() => held.promise)
 await act(async () => f.send(event(1, { type: 'answer_delta', text: 'held private' })))
 await waitFor(() => expect(f.port.session).toHaveBeenCalledTimes(2))
 fireEvent.click(screen.getByRole('button', { name: '断开此事件连接' }))
 view.unmount(); render(<CodexTurnEventsPanel {...props} port={f.port} />)
 await act(async () => held.resolve(session()))
 expect(screen.queryByLabelText('Codex 事件原文')).toBeNull(); expect(f.fetcher).toHaveBeenCalledTimes(1)
})

test('EOF without terminal stays unknown; reconnect with a different actor clears original cursor without a GET', async () => {
 const f = fixture(); render(<CodexTurnEventsPanel {...props} port={f.port} />); await connect(f)
 await act(async () => { f.send(event(1, { type: 'answer_delta', text: 'partial' })); f.close() }); await screen.findByText(/连接中断，任务状态未知/)
 expect(screen.queryByText(/已观察终态事件/)).toBeNull()
 vi.mocked(f.port.session).mockResolvedValue({ ...session(), actor_session_id: 'actor_other' })
 fireEvent.click(screen.getByRole('button', { name: '从原游标明确重连 job_turn_test:1' }))
 await screen.findByText(/事件显示已清除/); expect(f.fetcher).toHaveBeenCalledTimes(1)
})
test('double connect and late initial session cannot create a second stream after disconnect', async () => {
 const f = fixture(), held = deferred<ReturnType<typeof session>>()
 vi.mocked(f.port.session).mockImplementationOnce(() => held.promise)
 render(<CodexTurnEventsPanel {...props} port={f.port} />)
 const button = screen.getByRole('button', { name: '明确连接回合事件 turn_test' })
 fireEvent.click(button); fireEvent.click(button)
 expect(f.port.session).toHaveBeenCalledOnce()
 fireEvent.click(screen.getByRole('button', { name: '断开此事件连接' }))
 await act(async () => held.resolve(session()))
 expect(f.fetcher).not.toHaveBeenCalled(); expect(screen.queryByLabelText('Codex 事件原文')).toBeNull()
})
test.each(['learner', 'independent', 'open_book', 'workspace'] as const)('initial fresh %s is denied before any events GET', async mode => {
 const f = fixture()
 vi.mocked(f.port.session).mockResolvedValue({ ...session(), ...(mode === 'learner' ? { role: 'learner' } : mode === 'independent' ? { active_independent_attempt_id: 'attempt_test' } : mode === 'open_book' ? { active_open_book_attempt_id: 'attempt_test' } : { workspace_id: 'workspace_other' }) })
 render(<CodexTurnEventsPanel {...props} port={f.port} />)
 fireEvent.click(screen.getByRole('button', { name: '明确连接回合事件 turn_test' })); await screen.findByText(/事件显示已清除/)
 expect(f.fetcher).not.toHaveBeenCalled()
})

test('HTTP subject denial clears partial display despite cached author session; raw error never renders', async () => {
 const f = fixture(); render(<CodexTurnEventsPanel {...props} port={f.port} />); await connect(f)
 await act(async () => { f.send(event(1, { type: 'answer_delta', text: 'protected' })); f.close() }); await screen.findByText(/连接中断，任务状态未知/)
 f.fetcher.mockResolvedValueOnce(new Response('private server error', { status: 403 }))
 fireEvent.click(screen.getByRole('button', { name: '从原游标明确重连 job_turn_test:1' }))
 await screen.findByText(/事件显示已清除/)
 expect(screen.queryByLabelText('Codex 事件原文')).toBeNull(); expect(screen.queryByText(/private server error/)).toBeNull()
})

test('real parent control integration adds an idle read panel without changing command/detail traffic', async () => {
 const port = turnPort(), f = fixture()
 const local = () => { const store = new DraftStore({ name: `events-parent-${crypto.randomUUID()}`, factory: new IDBFactory() }); stores.push(store); return store }
 render(<CodexTurnPanel workspace={workspace} writeAdmitted port={port} eventPort={f.port} store={local()} formStore={local()} />)
 fireEvent.click(screen.getByRole('button', { name: '读取回合记录与权限' })); await screen.findByLabelText('回合原文')
 await screen.findByText(/已读取本机记录；当前 session/)
 fireEvent.change(screen.getByLabelText('已建立的 session ID'), { target: { value: 'codex_session_test' } })
 await waitFor(() => expect((screen.getByRole('button', { name: '读取安全回合分页' }) as HTMLButtonElement).disabled).toBe(false))
 fireEvent.click(screen.getByRole('button', { name: '读取安全回合分页' })); await screen.findByRole('button', { name: '读取回合控制 turn_test' })
 fireEvent.click(screen.getByRole('button', { name: '读取回合控制 turn_test' })); const section = await screen.findByRole('region', { name: 'Codex 回合事件 turn_test' })
 expect(f.fetcher).not.toHaveBeenCalled(); expect(f.port.session).not.toHaveBeenCalled()
 fireEvent.click(within(section).getByRole('button', { name: '明确连接回合事件 turn_test' })); await waitFor(() => expect(f.fetcher).toHaveBeenCalledOnce())
 expect(port.prepare).not.toHaveBeenCalled(); expect(port.cancel).not.toHaveBeenCalled(); expect(port.preparation).not.toHaveBeenCalled()
})
