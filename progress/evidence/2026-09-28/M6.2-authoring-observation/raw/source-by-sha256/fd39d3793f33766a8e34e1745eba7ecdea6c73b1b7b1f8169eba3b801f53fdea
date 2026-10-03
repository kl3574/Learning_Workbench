import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { AuthoringGroupPrepareWrite, AuthoringJobPage, JobSnapshot, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import type { AuthoringPort } from './authoringClient'
import { useAuthoring } from './useAuthoring'

type Observation = { stage: string; basis_list_sequence?: number; busy?: boolean; working: boolean; job_count?: number }
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(done => { resolve = done })
  return { promise, resolve }
}

function fixture() {
  const workspace = `workspace_${crypto.randomUUID()}`, records: Observation[] = []
  vi.stubGlobal('__authoringObservationEnabled', true)
  vi.stubGlobal('__authoringDiagnosticMechanism', (batch: Observation[]) => { records.push(...batch) })
  const job: JobSnapshot = { id: 'authoring_observed', workspace_id: workspace, kind: 'authoring', status: 'awaiting_approval', revision: 1, created_at: '2026-09-28T00:00:00Z', updated_at: '2026-09-28T00:00:00Z', progress: { completed: 0, total: null, label: '等待明确授权' }, result_refs: [], warnings: [], error: null }
  const session: SessionResponse = { workspace_id: workspace, role: 'author', csrf_token: 'SYNTHETIC_PRIVATE_CSRF_NOT_OBSERVED', active_independent_attempt_id: null, active_open_book_attempt_id: null }
  const body: AuthoringGroupPrepareWrite = { output_kind: 'practice_set', topic: 'SYNTHETIC_PRIVATE_TOPIC_NOT_OBSERVED', prerequisites: [], objectives: ['合成观察'], proof_policy: 'full', provider_id: 'provider_synthetic', source_refs: [], target_concept_refs: [{ entity: 'concept', id: 'concept_synthetic', revision: 1, sha256: 'a'.repeat(64) }], lesson_ref: { entity: 'lesson', id: 'lesson_synthetic', revision: 1, sha256: 'b'.repeat(64) } }
  const unavailable = vi.fn(async (): Promise<never> => { throw new Error('Unexpected operation') })
  const prepare = vi.fn<NonNullable<AuthoringPort['groups']>['prepare']>().mockRejectedValueOnce(new Error('SYNTHETIC_PRIVATE_LOST_ACK')).mockResolvedValue({ id: job.id, status: job.status })
  const port: AuthoringPort = { session: vi.fn(async () => session), list: vi.fn(async () => ({ items: [job], next_cursor: null })), job: vi.fn(async () => job),
    prepare: unavailable, read: unavailable, draft: unavailable, preview: unavailable, numeric: unavailable, decide: unavailable, cancel: unavailable,
    groups: { prepare, draft: unavailable, solution: unavailable, preview: unavailable, numeric: unavailable, decide: unavailable } }
  return { workspace, records, job, port, prepare, input: { kind: 'group_prepare' as const, body } }
}

test('observes a held list after the real original ACK persistence without inventing current controls or extra calls', async () => {
  const f = fixture(), pending = deferred<AuthoringJobPage>()
  f.port.list = vi.fn<AuthoringPort['list']>().mockResolvedValueOnce({ items: [], next_cursor: null }).mockReturnValueOnce(pending.promise)
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await waitFor(() => expect(hook.result.current.ready && hook.result.current.academic).toBe(true))
  await act(() => hook.result.current.create(f.input))
  const original = hook.result.current.commands[0]
  let replay!: Promise<void>
  act(() => { replay = hook.result.current.execute(original) })
  try {
    await waitFor(() => expect(hook.result.current.commands[0].ack).toEqual({ id: f.job.id, status: f.job.status }))
    expect(hook.result.current.jobs).toEqual([]); expect(hook.result.current.busy).toBe(true)
    await waitFor(() => expect(f.records.some(r => r.stage === 'list_requested' && r.basis_list_sequence === 2)).toBe(true))
    expect(f.records.some(r => r.stage === 'ack_persisted')).toBe(true)
    expect(f.records.some(r => r.stage === 'list_accepted' && r.basis_list_sequence === 2)).toBe(false)
  } finally { await act(async () => { pending.resolve({ items: [f.job], next_cursor: null }); await replay }) }
  expect(hook.result.current.jobs).toEqual([f.job]); expect(hook.result.current.busy).toBe(false)
  await waitFor(() => expect(f.records.some(r => r.stage === 'rendered' && r.busy === false && r.job_count === 1)).toBe(true))
  expect(f.records.some(r => r.stage === 'operation_finally')).toBe(true)
  expect(f.records.some(r => r.stage === 'operation_error')).toBe(true)
  expect(f.records.some(r => r.stage === 'ack_received')).toBe(true)
  expect(f.prepare).toHaveBeenCalledTimes(2); expect(f.port.list).toHaveBeenCalledTimes(2)
  expect(f.prepare).toHaveBeenNthCalledWith(2, original.body, original.command_id)
  expect(JSON.stringify(f.records)).not.toContain('SYNTHETIC_PRIVATE_')
  expect(JSON.stringify(f.records)).not.toContain(original.command_id)
})

test('observes the existing late-list discard while keeping the current result authoritative', async () => {
  const f = fixture(), initial = deferred<AuthoringJobPage>()
  f.port.list = vi.fn<AuthoringPort['list']>().mockReturnValueOnce(initial.promise).mockResolvedValue({ items: [f.job], next_cursor: null })
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await waitFor(() => expect(hook.result.current.ready && hook.result.current.academic).toBe(true))
  await act(() => hook.result.current.refresh())
  await act(async () => { initial.resolve({ items: [], next_cursor: null }); await initial.promise })
  expect(hook.result.current.jobs).toEqual([f.job]); expect(hook.result.current.busy).toBe(false)
  await waitFor(() => expect(f.records.some(r => r.stage === 'list_discarded' && r.basis_list_sequence === 1)).toBe(true))
  expect(f.port.list).toHaveBeenCalledTimes(2); expect(f.prepare).not.toHaveBeenCalled()
})

test('observes list failure and finally without retaining its arbitrary exception or changing busy recovery', async () => {
  const f = fixture()
  f.port.list = vi.fn<AuthoringPort['list']>().mockResolvedValueOnce({ items: [f.job], next_cursor: null }).mockRejectedValue(new Error('SYNTHETIC_PRIVATE_EXCEPTION'))
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await waitFor(() => expect(hook.result.current.ready && hook.result.current.academic).toBe(true))
  await act(() => hook.result.current.refresh())
  expect(hook.result.current.jobs).toEqual([f.job]); expect(hook.result.current.busy).toBe(false)
  await waitFor(() => expect(f.records.some(r => r.stage === 'list_error')).toBe(true))
  expect(f.records.some(r => r.stage === 'list_finally')).toBe(true)
  expect(JSON.stringify(f.records)).not.toContain('SYNTHETIC_PRIVATE_')
  expect(f.port.list).toHaveBeenCalledTimes(2)
})

test.each(['off', 'blocked', 'throwing'] as const)('the %s observer preserves original replay, request counts and actual busy recovery', async mode => {
  const f = fixture()
  if (mode === 'off') vi.stubGlobal('__authoringObservationEnabled', false)
  else vi.stubGlobal('__authoringDiagnosticMechanism', () => { if (mode === 'throwing') throw new Error('PRIVATE_SINK'); return new Promise(() => undefined) })
  f.port.list = vi.fn<AuthoringPort['list']>().mockResolvedValueOnce({ items: [], next_cursor: null }).mockResolvedValue({ items: [f.job], next_cursor: null })
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await waitFor(() => expect(hook.result.current.ready && hook.result.current.academic).toBe(true))
  await act(() => hook.result.current.create(f.input))
  const original = hook.result.current.commands[0]
  expect(original.ack).toBeNull(); expect(hook.result.current.busy).toBe(false)
  await act(() => hook.result.current.execute(original))
  expect(hook.result.current.commands[0].ack).toEqual({ id: f.job.id, status: f.job.status })
  expect(hook.result.current.commands[0].command_id).toBe(original.command_id)
  expect(hook.result.current.jobs).toEqual([f.job]); expect(hook.result.current.busy).toBe(false)
  expect(f.prepare).toHaveBeenCalledTimes(2); expect(f.port.list).toHaveBeenCalledTimes(2); expect(f.port.session).toHaveBeenCalledTimes(1)
  expect(f.prepare).toHaveBeenNthCalledWith(1, original.body, original.command_id)
  expect(f.prepare).toHaveBeenNthCalledWith(2, original.body, original.command_id)
  expect(f.records).toEqual([])
})
