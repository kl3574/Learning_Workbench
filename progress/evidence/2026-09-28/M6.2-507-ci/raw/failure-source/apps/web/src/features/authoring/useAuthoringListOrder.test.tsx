import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { AuthoringGroupPrepareWrite, AuthoringJobPage, JobSnapshot, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import type { AuthoringPort } from './authoringClient'
import { useAuthoring } from './useAuthoring'

afterEach(cleanup)

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(done => { resolve = done })
  return { promise, resolve }
}

function fixture() {
  const workspace = `workspace_${crypto.randomUUID()}`
  const value: JobSnapshot = { id: 'authoring_list_order', workspace_id: workspace, kind: 'authoring', status: 'awaiting_approval', revision: 1, created_at: '2026-09-22T00:00:00Z', updated_at: '2026-09-22T00:00:00Z', progress: { completed: 0, total: null, label: '等待明确授权' }, result_refs: [], warnings: [], error: null }
  const session: SessionResponse = { workspace_id: workspace, role: 'author', csrf_token: 'synthetic-list-test-only', active_independent_attempt_id: null, active_open_book_attempt_id: null }
  const body: AuthoringGroupPrepareWrite = { output_kind: 'practice_set', topic: '合成列表顺序检查', prerequisites: [], objectives: ['保留准确原命令与当前列表'], proof_policy: 'full', provider_id: 'provider_synthetic', source_refs: [], target_concept_refs: [{ entity: 'concept', id: 'concept_synthetic', revision: 1, sha256: 'a'.repeat(64) }], lesson_ref: { entity: 'lesson', id: 'lesson_synthetic', revision: 1, sha256: 'b'.repeat(64) } }
  const unavailable = vi.fn(async (): Promise<never> => { throw new Error('Unexpected subject operation') })
  const prepare = vi.fn<NonNullable<AuthoringPort['groups']>['prepare']>().mockRejectedValueOnce(new Error('Controlled lost original ACK')).mockResolvedValue({ id: value.id, status: value.status })
  const port: AuthoringPort = {
    session: vi.fn(async () => session), list: vi.fn(async () => ({ items: [value], next_cursor: null })), job: vi.fn(async () => value),
    prepare: unavailable, read: unavailable, draft: unavailable, preview: unavailable, numeric: unavailable, decide: unavailable, cancel: unavailable,
    groups: { prepare, draft: unavailable, solution: unavailable, preview: unavailable, numeric: unavailable, decide: unavailable },
  }
  return { workspace, value, port, prepare, input: { kind: 'group_prepare' as const, body } }
}

test('a held post-replay list leaves the durable original ACK separate from current controls until that list resolves', async () => {
  const f = fixture(), pending = deferred<AuthoringJobPage>()
  f.port.list = vi.fn<AuthoringPort['list']>().mockResolvedValueOnce({ items: [], next_cursor: null }).mockReturnValueOnce(pending.promise)
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await waitFor(() => expect(hook.result.current.ready && hook.result.current.academic).toBe(true))
  await act(() => hook.result.current.create(f.input))
  const original = hook.result.current.commands[0]
  expect(original.ack).toBeNull()
  let replay!: Promise<void>
  act(() => { replay = hook.result.current.execute(original) })
  await waitFor(() => expect(hook.result.current.commands[0].ack).toEqual({ id: f.value.id, status: f.value.status }))
  expect(hook.result.current.jobs).toEqual([])
  expect(hook.result.current.busy).toBe(true)
  await act(async () => { pending.resolve({ items: [f.value], next_cursor: null }); await replay })
  expect(hook.result.current.jobs).toEqual([f.value])
  expect(hook.result.current.busy).toBe(false)
  expect(f.prepare).toHaveBeenNthCalledWith(2, original.body, original.command_id)
  expect(f.prepare).toHaveBeenCalledTimes(2)
})

test('an earlier empty list cannot erase current controls after the same original group command is replayed', async () => {
  const f = fixture(), initial = deferred<AuthoringJobPage>()
  f.port.list = vi.fn<AuthoringPort['list']>().mockReturnValueOnce(initial.promise).mockResolvedValue({ items: [f.value], next_cursor: null })
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await waitFor(() => expect(hook.result.current.ready && hook.result.current.academic).toBe(true))
  await act(() => hook.result.current.create(f.input))
  const original = hook.result.current.commands[0]
  await act(() => hook.result.current.execute(original))
  expect(hook.result.current.jobs).toEqual([f.value])
  expect(hook.result.current.busy).toBe(false)
  await act(async () => { initial.resolve({ items: [], next_cursor: null }); await initial.promise })
  expect(hook.result.current.jobs).toEqual([f.value])
  expect(f.prepare).toHaveBeenNthCalledWith(2, original.body, original.command_id)
  expect(f.prepare).toHaveBeenCalledTimes(2)
})

test('a previous Policy lifecycle list cannot replace a later current same-workspace control revision', async () => {
  const f = fixture(), initial = deferred<AuthoringJobPage>(), next = { ...f.value, revision: 2, status: 'cancelled' as const }
  f.port.list = vi.fn<AuthoringPort['list']>().mockReturnValueOnce(initial.promise).mockResolvedValue({ items: [next], next_cursor: null })
  const hook = renderHook(({ paused }) => useAuthoring(f.workspace, paused, f.port), { initialProps: { paused: false } })
  await waitFor(() => expect(hook.result.current.ready && hook.result.current.academic).toBe(true))
  hook.rerender({ paused: true })
  await waitFor(() => expect(hook.result.current.jobs).toEqual([next]))
  await act(async () => { initial.resolve({ items: [f.value], next_cursor: null }); await initial.promise })
  expect(hook.result.current.jobs).toEqual([next])
  expect(hook.result.current.academic).toBe(false)
  expect(f.prepare).not.toHaveBeenCalled()
})

test('a late initial cursor cannot alter the cursor used to read the next current control page', async () => {
  const f = fixture(), initial = deferred<AuthoringJobPage>(), next = { ...f.value, id: 'authoring_next_page' }
  f.port.list = vi.fn<AuthoringPort['list']>()
    .mockReturnValueOnce(initial.promise)
    .mockResolvedValueOnce({ items: [f.value], next_cursor: 'current_cursor' })
    .mockResolvedValueOnce({ items: [next], next_cursor: null })
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await waitFor(() => expect(hook.result.current.ready && hook.result.current.academic).toBe(true))
  await act(() => hook.result.current.refresh())
  await act(async () => { initial.resolve({ items: [], next_cursor: 'old_cursor' }); await initial.promise })
  expect(hook.result.current.cursor).toBe('current_cursor')
  await act(() => hook.result.current.refresh(true))
  expect(f.port.list).toHaveBeenNthCalledWith(3, 'current_cursor')
  expect(hook.result.current.jobs).toEqual([f.value, next])
  expect(hook.result.current.cursor).toBeNull()
})

test('the newest successful empty page is still authoritative and clears the earlier controls', async () => {
  const f = fixture()
  f.port.list = vi.fn<AuthoringPort['list']>().mockResolvedValueOnce({ items: [f.value], next_cursor: 'current_cursor' }).mockResolvedValueOnce({ items: [], next_cursor: null })
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await waitFor(() => expect(hook.result.current.jobs).toEqual([f.value]))
  await act(() => hook.result.current.refresh())
  expect(hook.result.current.jobs).toEqual([])
  expect(hook.result.current.cursor).toBeNull()
  expect(hook.result.current.busy).toBe(false)
  expect(f.prepare).not.toHaveBeenCalled()
})
