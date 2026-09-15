import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { ContentRef, JobRef, JobSnapshot, RetrievalIndexOverview, RetrievalIndexScopeStatus, RetrievalQueryView } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, request } from '../../api/client'
import { scopeHash } from './retrievalModel'
import { useRetrieval } from './useRetrieval'
import { readCommands, retrievalCommandStore } from './retrievalCommands'
import type { RetrievalPort } from './retrievalClient'
afterEach(() => { cleanup(); vi.restoreAllMocks() })
const ref: ContentRef = { entity: 'block', id: 'block_hook', revision: 1, sha256: 'a'.repeat(64) }
function fixture() {
  const workspace = `workspace_${crypto.randomUUID()}`
  let corpus = 'b'.repeat(64)
  const status = (owner = workspace): RetrievalIndexScopeStatus => ({ kind: 'scope', scope_refs: [ref], scope_sha256: scopeHash(owner, [ref]), corpus_sha256: corpus, state: 'missing', index_version: null, indexed_corpus_sha256: null, last_built_at: null, latest_job: null })
  const job: JobSnapshot = { id: 'job_hook', workspace_id: workspace, kind: 'retrieval_index', status: 'completed', revision: 3, created_at: '2026-09-15T00:00:00Z', updated_at: '2026-09-15T00:00:01Z', progress: { completed: 1, total: 1, label: '已完成' }, result_refs: [ref], warnings: [], error: null }
  const port: RetrievalPort = {
    status: vi.fn(async owner => status(owner)),
    query: vi.fn(async (): Promise<RetrievalQueryView> => ({ scope_refs: [ref], scope_sha256: scopeHash(workspace, [ref]), corpus_sha256: corpus, index_state: 'missing', index_version: null, indexed_corpus_sha256: null, result_state: 'not_ready', matched_count: null, hits: [], omissions: { result_limit: 0, text_byte_budget: 0, json_byte_budget: 0 }, warnings: [{ code: 'INDEX_MISSING', message: '未构建', locator: null, severity: 'warning' }] })),
    rebuild: vi.fn(async (): Promise<JobRef> => ({ id: job.id, status: 'queued' })), job: vi.fn(async () => job),
    cancel: vi.fn(async (): Promise<JobSnapshot> => ({ ...job, status: 'cancelled' })), block: vi.fn(async () => { throw new Error('not requested') }), overview: vi.fn(async (): Promise<RetrievalIndexOverview> => ({ kind: 'overview', items: [], next_cursor: null })),
  }
  return { workspace, status, job, port, change: () => { corpus = 'c'.repeat(64) } }
}
test('cold scope/read never rebuild; explicit original command is durable before POST and ACK stays separate from job', async () => {
  const f = fixture(), original = f.port.rebuild
  f.port.rebuild = vi.fn(async (body, key) => { expect((await readCommands(f.workspace)).find(value => value.command_id === key)?.body).toEqual(body); return original(body, key) })
  const hook = renderHook(() => useRetrieval(f.workspace, [ref], false, f.port))
  await waitFor(() => expect(hook.result.current.status?.state).toBe('missing'))
  await act(() => hook.result.current.query('概率'))
  expect(f.port.rebuild).not.toHaveBeenCalled()
  await act(() => hook.result.current.begin('rebuild'))
  expect(hook.result.current.commands[0].ack?.status).toBe('queued')
  expect(hook.result.current.job?.status).toBe('completed')
  expect(hook.result.current.status?.state).toBe('missing')
  expect(f.port.status).toHaveBeenCalledWith(f.workspace, [ref])
})
test('lost ACK survives unmount and retries exactly the stored key/body after current corpus changes', async () => {
  const f = fixture(); f.port.rebuild = vi.fn().mockRejectedValueOnce(new Error('controlled lost ACK')).mockResolvedValue({ id: f.job.id, status: 'queued' })
  const first = renderHook(() => useRetrieval(f.workspace, [ref], false, f.port))
  await waitFor(() => expect(first.result.current.status).not.toBeNull()); await act(() => first.result.current.begin('rebuild'))
  const original = (await readCommands(f.workspace))[0]; expect(original.ack).toBeNull(); first.unmount(); f.change()
  const next = renderHook(() => useRetrieval(f.workspace, [ref], false, f.port))
  await waitFor(() => expect(next.result.current.commands).toHaveLength(1)); await waitFor(() => expect(next.result.current.status?.corpus_sha256).toBe('c'.repeat(64)))
  await act(() => next.result.current.begin('rebuild')); expect(f.port.rebuild).toHaveBeenCalledTimes(1)
  await act(() => next.result.current.retry(original))
  expect(f.port.rebuild).toHaveBeenNthCalledWith(2, original.body, original.command_id)
  expect((await readCommands(f.workspace))[0].ack?.status).toBe('queued')
})
test('412 preserves old base; only explicit later begin uses new corpus/key', async () => {
  const f = fixture(); f.port.rebuild = vi.fn().mockRejectedValueOnce(new ApiError(412, 'changed', 'INDEX_CORPUS_CONFLICT')).mockResolvedValue({ id: f.job.id, status: 'queued' })
  const hook = renderHook(() => useRetrieval(f.workspace, [ref], false, f.port))
  await waitFor(() => expect(hook.result.current.status).not.toBeNull()); await act(() => hook.result.current.begin('rebuild'))
  const original = (await readCommands(f.workspace))[0]; expect(original.rejected).toBe(true); f.change()
  await act(() => hook.result.current.refresh()); expect(f.port.rebuild).toHaveBeenCalledTimes(1)
  await act(() => hook.result.current.begin('rebuild'))
  const current = (await readCommands(f.workspace)).find(value => value.command_id !== original.command_id)!
  expect(current.kind === 'rebuild' && current.body.expected_corpus_sha256).toBe('c'.repeat(64))
  expect(original.kind === 'rebuild' && original.body.expected_corpus_sha256).toBe('b'.repeat(64))
})
test('late old workspace and paused reads never populate a different owner', async () => {
  const f = fixture(); let release!: (value: RetrievalIndexScopeStatus) => void
  f.port.status = vi.fn().mockImplementationOnce(() => new Promise(done => { release = done })).mockImplementation(async owner => f.status(owner))
  const nextWorkspace = `workspace_${crypto.randomUUID()}`
  const hook = renderHook(({ workspace, paused }) => useRetrieval(workspace, [ref], paused, f.port), { initialProps: { workspace: f.workspace, paused: false } })
  await waitFor(() => expect(f.port.status).toHaveBeenCalledTimes(1)); hook.rerender({ workspace: nextWorkspace, paused: false })
  await waitFor(() => expect(hook.result.current.status?.scope_sha256).toBe(scopeHash(nextWorkspace, [ref])))
  await act(async () => { release(f.status()) }); expect(hook.result.current.status?.scope_sha256).toBe(scopeHash(nextWorkspace, [ref]))
  hook.rerender({ workspace: nextWorkspace, paused: true }); expect(hook.result.current.status).toBeNull(); expect(hook.result.current.commands).toEqual([])
  await act(() => hook.result.current.begin('rebuild')); expect(f.port.rebuild).not.toHaveBeenCalled()
})
test('actual IDB write failure prevents POST rather than silently losing the original command', async () => {
  const f = fixture(), hook = renderHook(() => useRetrieval(f.workspace, [ref], false, f.port))
  await waitFor(() => expect(hook.result.current.status).not.toBeNull())
  vi.spyOn(retrievalCommandStore, 'save').mockRejectedValueOnce(new Error('controlled quota'))
  await act(() => hook.result.current.begin('rebuild'))
  expect(f.port.rebuild).not.toHaveBeenCalled(); expect(hook.result.current.error).toContain('controlled quota')
})
test('lost cancel ACK keeps its exact original job revision/key while current GET changes', async () => {
  const f = fixture(); f.job.status = 'running'; f.job.revision = 2
  const hook = renderHook(() => useRetrieval(f.workspace, [ref], false, f.port))
  await waitFor(() => expect(hook.result.current.status).not.toBeNull()); await act(() => hook.result.current.begin('rebuild'))
  expect(hook.result.current.job?.revision).toBe(2)
  const cancelled: JobSnapshot = { ...f.job, status: 'cancelled', revision: 3 }
  f.port.cancel = vi.fn().mockRejectedValueOnce(new Error('controlled lost cancel ACK')).mockResolvedValue(cancelled)
  await act(() => hook.result.current.begin('cancel'))
  const original = (await readCommands(f.workspace)).find(value => value.kind === 'cancel')!
  expect(original.ack).toBeNull(); expect(original.body).toEqual({ expected_revision: 2 })
  f.port.job = vi.fn(async () => cancelled)
  await act(() => hook.result.current.retry(original))
  expect(f.port.cancel).toHaveBeenNthCalledWith(2, f.workspace, f.job.id, 2, original.command_id)
  expect(hook.result.current.job?.status).toBe('cancelled')
})
test('actual session-access invalidation suppresses a pending former-generation response', async () => {
  const f = fixture(); let release!: (value: RetrievalIndexScopeStatus) => void
  f.port.status = vi.fn().mockImplementationOnce(() => new Promise(done => { release = done })).mockImplementation(async owner => ({ ...f.status(owner), corpus_sha256: 'c'.repeat(64) }))
  const hook = renderHook(() => useRetrieval(f.workspace, [ref], false, f.port))
  await waitFor(() => expect(f.port.status).toHaveBeenCalledTimes(1))
  vi.spyOn(globalThis, 'fetch').mockResolvedValue(new Response('{}', { status: 200, headers: { 'Content-Type': 'application/json' } }))
  await act(() => request('POST /api/v1/session/role', { role: 'learner' }, { 'Idempotency-Key': 'synthetic-access-change' }))
  await waitFor(() => expect(hook.result.current.status?.corpus_sha256).toBe('c'.repeat(64)))
  await act(async () => { release(f.status()) })
  expect(hook.result.current.status?.corpus_sha256).toBe('c'.repeat(64))
})
