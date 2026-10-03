import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { request } from '../../api/client'
import { useApplicability } from './useApplicability'
import { commandStore } from './commands'
import { ack, evidenceId, eventId, portFor, session } from './fixtures'
import { discard, recoverable } from './memory'
const spaces: string[] = []
const deferred = <T,>() => { let resolve!: (value: T) => void; const promise = new Promise<T>(yes => { resolve = yes }); return { promise, resolve } }
afterEach(async () => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); for (const space of spaces.splice(0)) discard(space); await commandStore.close() })
test('mounted and newly opened applicability owners remain hidden during a real client role mutation and retain original ACK memory', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`; spaces.push(workspace)
  const port = portFor(workspace), gate = deferred<Response>(); let role: 'author' | 'learner' = 'author'
  vi.stubGlobal('fetch', vi.fn(async (path: string) => path.endsWith('/role') ? gate.promise : new Response(JSON.stringify({ ...session(workspace), role }))))
  port.session = () => request('GET /api/v1/session', undefined); port.decide = vi.fn(port.decide)
  const first = renderHook(() => useApplicability(workspace, false, port)); await waitFor(() => expect(first.result.current.ready).toBe(true))
  await act(() => first.result.current.read(evidenceId)); await act(() => first.result.current.read(evidenceId, eventId)); act(() => first.result.current.adopt())
  const save = commandStore.save.bind(commandStore)
  const failing = vi.spyOn(commandStore, 'save').mockImplementation(async (...args) => { if (JSON.parse(args[2]).ack) throw new Error('Synthetic received ACK storage failure'); return save(...args) })
  await act(() => first.result.current.submit('usable', 'Original immutable synthetic reason', []))
  const original = recoverable(workspace, session(workspace).csrf_token)[0]; expect(original.ack).toEqual(ack(original.body)); expect(first.result.current.pendingMemory).toBe(true)
  let switching!: Promise<unknown>
  await act(async () => { switching = request('POST /api/v1/session/role', { role: 'learner' }, { 'Idempotency-Key': 'synthetic-role-pending' }); await new Promise(resolve => setTimeout(resolve, 0)) })
  const next = renderHook(() => useApplicability(workspace, false, port))
  try {
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 0)) })
    expect(first.result.current.ready).toBe(false); expect(next.result.current.ready).toBe(false)
    expect(first.result.current.commands).toEqual([]); expect(next.result.current.commands).toEqual([])
    expect(next.result.current.canSaveMemory).toBe(false); expect(recoverable(workspace, session(workspace).csrf_token)).toEqual([original])
  } finally { role = 'learner'; await act(async () => { gate.resolve(new Response(JSON.stringify({ ...session(workspace), role }))); await switching }) }
  await waitFor(() => expect(next.result.current.busy).toBe(false)); expect(next.result.current.ready).toBe(false)
  expect(recoverable(workspace, session(workspace).csrf_token)).toEqual([original]); expect(port.decide).toHaveBeenCalledTimes(1)
  failing.mockRestore(); role = 'author'; await act(() => next.result.current.refresh()); await act(() => next.result.current.saveMemory())
  expect(next.result.current.commands[0]).toEqual(original); expect(port.decide).toHaveBeenCalledTimes(1)
})
test('an old already-dispatched author session response cannot readmit its owner after learner completion', async () => {
  const workspace = `workspace_${crypto.randomUUID()}`; spaces.push(workspace)
  const old = deferred<Response>(), gate = deferred<Response>(); let reads = 0
  vi.stubGlobal('fetch', vi.fn(async (path: string) => path.endsWith('/role') ? gate.promise : ++reads === 1 ? old.promise : new Response(JSON.stringify({ ...session(workspace), role: 'learner' }))))
  const port = portFor(workspace); port.session = () => request('GET /api/v1/session', undefined)
  const hook = renderHook(() => useApplicability(workspace, false, port)); await waitFor(() => expect(reads).toBe(1))
  let switching!: Promise<unknown>; act(() => { switching = request('POST /api/v1/session/role', { role: 'learner' }, { 'Idempotency-Key': 'synthetic-late-session' }) })
  await act(async () => { gate.resolve(new Response(JSON.stringify({ ...session(workspace), role: 'learner' }))); await switching })
  await waitFor(() => expect(hook.result.current.busy).toBe(false)); expect(hook.result.current.ready).toBe(false)
  await act(async () => old.resolve(new Response(JSON.stringify(session(workspace)))))
  expect(hook.result.current.ready).toBe(false); expect(hook.result.current.commands).toEqual([])
})
