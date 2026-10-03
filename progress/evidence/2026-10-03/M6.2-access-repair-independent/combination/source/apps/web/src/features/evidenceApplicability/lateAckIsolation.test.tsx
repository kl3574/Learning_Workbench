import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { request } from '../../api/client'
import { commandStore, readCommand } from './commands'
import { discard, recoverable } from './memory'
import { ack, evidenceId, eventId, portFor, session } from './fixtures'
import { useApplicability } from './useApplicability'

const spaces: string[] = []
afterEach(async () => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); for (const workspace of spaces.splice(0)) discard(workspace); await commandStore.close() })
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(r => { resolve = r }); return { promise, resolve } }
async function sending() {
  const workspace = `workspace_${crypto.randomUUID()}`; spaces.push(workspace)
  const port = portFor(workspace), response = deferred<ReturnType<typeof ack>>()
  port.session = vi.fn(port.session); port.decide = vi.fn(() => response.promise)
  const h = renderHook(() => useApplicability(workspace, false, port))
  await waitFor(() => expect(h.result.current.ready).toBe(true))
  await act(() => h.result.current.read(evidenceId, null)); await act(() => h.result.current.read(evidenceId, eventId)); act(() => h.result.current.adopt())
  let operation!: Promise<void>; act(() => { operation = h.result.current.submit('usable', 'Synthetic original actor receipt', []) })
  await waitFor(() => expect(port.decide).toHaveBeenCalledTimes(1))
  const original = h.result.current.commands[0], result = { ...ack(original.body), actor_session_id: session(workspace).actor_session_id }
  const change = async (next: ReturnType<typeof session>) => {
    vi.mocked(port.session).mockResolvedValue(next)
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(next))))
    await act(() => request('POST /api/v1/session/role', { role: 'author' }, { 'Idempotency-Key': 'synthetic-access-change' }))
    await waitFor(() => expect(h.result.current.ready && !h.result.current.busy).toBe(true))
  }
  const deliver = async (value = result) => { await act(async () => { response.resolve(value); await operation }) }
  return { workspace, port, h, original, result, change, deliver }
}

test('late ACK remains isolated from a different current session and survives an original-session save abort without another POST', async () => {
  const f = await sending(), other = { ...session(f.workspace), actor_session_id: 'session_other', csrf_token: 'synthetic-other-page-binding' }
  await f.change(other); await f.deliver()
  expect(f.h.result.current.ready).toBe(true); expect(f.h.result.current.pendingMemory).toBe(true); expect(f.h.result.current.canSaveMemory).toBe(false)
  expect(recoverable(f.workspace, other.csrf_token)).toEqual([])
  expect(recoverable(f.workspace, session(f.workspace).csrf_token)).toEqual([{ ...f.original, ack: f.result, rejection: null }])
  await act(() => f.h.result.current.saveMemory())
  expect(readCommand((await commandStore.load(f.workspace))[f.original.command_id], f.workspace)).toEqual(f.original)
  expect(f.h.result.current.commands.every(command => command.ack === null)).toBe(true)
  await f.change(session(f.workspace)); expect(f.h.result.current.canSaveMemory).toBe(true)
  const failOnce = vi.spyOn(commandStore, 'save').mockRejectedValueOnce(new Error('Synthetic IDB abort after permission recovery'))
  await act(() => f.h.result.current.saveMemory()); expect(failOnce).toHaveBeenCalledTimes(1)
  expect(f.h.result.current.pendingMemory).toBe(true)
  expect(readCommand((await commandStore.load(f.workspace))[f.original.command_id], f.workspace)).toEqual(f.original)
  await act(() => f.h.result.current.saveMemory())
  expect(f.h.result.current.pendingMemory).toBe(false)
  expect(readCommand((await commandStore.load(f.workspace))[f.original.command_id], f.workspace)).toEqual({ ...f.original, ack: f.result, rejection: null })
  expect(f.h.result.current.canReplay(f.original)).toBe(false)
  await act(() => f.h.result.current.execute(f.original)); expect(f.port.decide).toHaveBeenCalledTimes(1)
})

test('a late response with substituted original-command binding cannot become an isolated ACK', async () => {
  const f = await sending(); await f.change(session(f.workspace))
  await f.deliver({ ...f.result, current_basis_sha256: '0'.repeat(64) })
  expect(f.h.result.current.pendingMemory).toBe(false)
  expect(recoverable(f.workspace, session(f.workspace).csrf_token)).toEqual([])
  expect(readCommand((await commandStore.load(f.workspace))[f.original.command_id], f.workspace)).toEqual(f.original)
  expect(f.port.decide).toHaveBeenCalledTimes(1)
})
