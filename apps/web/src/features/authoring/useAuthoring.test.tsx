import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { JobSnapshot, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import type { AuthoringPort } from './authoringClient'
import { useAuthoring } from './useAuthoring'
afterEach(cleanup)
const job = (workspace: string): JobSnapshot => ({ id: 'job_safe_authoring', workspace_id: workspace, kind: 'authoring_numeric_check', status: 'running', revision: 4, created_at: '2026-09-16T00:00:00Z', updated_at: '2026-09-16T00:00:01Z', progress: { completed: 0, total: null, label: '本机任务执行中' }, result_refs: [], warnings: [], error: null })
function fixture() {
  const workspace = `workspace_${crypto.randomUUID()}`, value = job(workspace)
  const session: SessionResponse = { workspace_id: workspace, role: 'learner', csrf_token: 'synthetic-no-network-token', active_independent_attempt_id: null, active_open_book_attempt_id: null }
  const unavailable = vi.fn(async (): Promise<never> => { throw new Error('Unexpected academic request') })
  const port: AuthoringPort = { session: vi.fn(async () => session), list: vi.fn(async () => ({ items: [value], next_cursor: null })), job: vi.fn(async () => value), cancel: vi.fn(async (): Promise<JobSnapshot> => ({ ...value, status: 'cancelled', revision: 5 })), prepare: unavailable, read: unavailable, draft: unavailable, preview: unavailable, numeric: unavailable, decide: unavailable }
  return { workspace, value, session, port }
}
test('learner with unknown Policy can discover and cancel real controls without academic reads', async () => {
  const f = fixture(), hook = renderHook(() => useAuthoring(f.workspace, true, f.port))
  await waitFor(() => expect(hook.result.current.jobs).toHaveLength(1))
  expect(hook.result.current.academic).toBe(false)
  await act(() => hook.result.current.cancel(hook.result.current.jobs[0]))
  expect(f.port.cancel).toHaveBeenCalledWith(f.value.id, { expected_revision: 4 }, expect.any(String))
  expect(f.port.read).not.toHaveBeenCalled(); expect(f.port.numeric).not.toHaveBeenCalled()
})
test('lost cancel ACK remains available immediately and replays its original key and revision after refresh', async () => {
  const f = fixture(); f.port.cancel = vi.fn().mockRejectedValueOnce(new Error('lost accepted ACK')).mockResolvedValue({ ...f.value, status: 'cancelled', revision: 5 })
  const hook = renderHook(() => useAuthoring(f.workspace, true, f.port))
  await waitFor(() => expect(hook.result.current.jobs).toHaveLength(1)); await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.cancel(f.value))
  expect(hook.result.current.commands).toHaveLength(1)
  const original = hook.result.current.commands[0]
  f.value.revision = 9
  await act(() => hook.result.current.refresh())
  await act(() => hook.result.current.execute(original))
  expect(f.port.cancel).toHaveBeenNthCalledWith(2, f.value.id, { expected_revision: 4 }, original.command_id)
  const acknowledged = hook.result.current.commands[0]; expect(acknowledged.kind === 'cancel' && acknowledged.ack?.revision).toBe(5)
  expect(hook.result.current.jobs[0].revision).toBe(9)
})
test('a late control page from the old workspace cannot enter the replacement workspace', async () => {
  const f = fixture(), next = fixture(); let release!: (value: Awaited<ReturnType<AuthoringPort['list']>>) => void
  f.port.list = vi.fn(() => new Promise<Awaited<ReturnType<AuthoringPort['list']>>>(done => { release = done }))
  const hook = renderHook(({ workspace, port }) => useAuthoring(workspace, true, port), { initialProps: { workspace: f.workspace, port: f.port } })
  await waitFor(() => expect(f.port.list).toHaveBeenCalledTimes(1)); hook.rerender({ workspace: next.workspace, port: next.port })
  await waitFor(() => expect(hook.result.current.jobs[0]?.workspace_id).toBe(next.workspace))
  await act(async () => release({ items: [f.value], next_cursor: null }))
  expect(hook.result.current.jobs[0].workspace_id).toBe(next.workspace)
})
function detail(id: string): Awaited<ReturnType<AuthoringPort['read']>> {
  return { summary: { id, kind: 'authoring', job_revision: 2, status: 'awaiting_approval', title: '受保护的原主题', candidate: null, created_at: '2026-09-16T00:00:00Z', updated_at: '2026-09-16T00:00:01Z' }, request: { topic: '受保护的题设', prerequisites: [], objectives: ['合成目标'], proof_policy: 'full', output_kind: 'worked_example', provider_id: 'provider_synthetic', source_refs: [] }, preparation: { context_snapshot_id: 'context_synthetic', snapshot_sha256: 'a'.repeat(64), job_input_sha256: 'b'.repeat(64), prepared_input_sha256: 'c'.repeat(64), character_count: 50, materials: [], warnings: [] }, proposal_id: null, consent_id: null, provider_receipt_id: null, provider_outcome: null, usage: { input_tokens: null, output_tokens: null }, raw_answer: null, raw_refusal: null, validation: { schema: 'NOT_RUN', references: 'NOT_RUN', symbol_declarations: 'NOT_RUN', issues: [], mathematical: 'NOT_RUN', sources: 'NOT_RUN', independent_pedagogy: 'NOT_RUN' }, error_code: null }
}
test('Policy change clears academic projection immediately and late read never restores it; safe discovery remains', async () => {
  const f = fixture(); f.session.role = 'author'; f.value.kind = 'authoring'; f.port.read = vi.fn<AuthoringPort['read']>(async () => detail(f.value.id))
  const hook = renderHook(({ paused }) => useAuthoring(f.workspace, paused, f.port), { initialProps: { paused: false } })
  await waitFor(() => expect(hook.result.current.academic).toBe(true)); await act(() => hook.result.current.read(f.value.id)); expect(hook.result.current.detail?.summary.title).toBe('受保护的原主题')
  let release!: (value: Awaited<ReturnType<AuthoringPort['read']>>) => void
  f.port.read = vi.fn<AuthoringPort['read']>(() => new Promise<Awaited<ReturnType<AuthoringPort['read']>>>(done => { release = done }))
  let pending!: Promise<void>; act(() => { pending = hook.result.current.read(f.value.id) })
  hook.rerender({ paused: true }); expect(hook.result.current.detail).toBeNull(); expect(hook.result.current.draft).toBeNull(); expect(hook.result.current.numeric).toBeNull()
  await act(async () => { release(detail(f.value.id)); await pending })
  expect(hook.result.current.detail).toBeNull()
  await waitFor(() => expect(hook.result.current.jobs).toHaveLength(1))
  hook.rerender({ paused: false }); await waitFor(() => expect(hook.result.current.academic).toBe(true))
  expect(hook.result.current.detail).toBeNull() // restoration requires explicit protected read
})
test('unreadable academic journal blocks new academic commands and closing but keeps safe cancellation available', async () => {
  const { authoringCommandStore } = await import('./authoringCommands')
  const f = fixture(); f.session.role = 'author'
  const failed = vi.spyOn(authoringCommandStore, 'load').mockRejectedValue(new Error('controlled academic IDB read failure'))
  try {
    const hook = renderHook(() => useAuthoring(f.workspace, false, f.port))
    await waitFor(() => expect(hook.result.current.academic).toBe(true)); await waitFor(() => expect(hook.result.current.error).not.toBe(''))
    expect(hook.result.current.ready).toBe(false)
    await act(() => hook.result.current.cancel(f.value)); expect(f.port.cancel).toHaveBeenCalledTimes(1)
  } finally { failed.mockRestore() }
})
test('a candidate whose raw Markdown no longer matches its declared byte hash is never displayed', async () => {
  const f = fixture(); f.session.role = 'author'; f.value.kind = 'authoring'
  const candidate = { draft_id: 'draft_bound_example', draft_revision: 1, entity: 'block' as const, candidate_sha256: 'a'.repeat(64) }
  f.port.read = vi.fn<AuthoringPort['read']>(async () => ({ ...detail(f.value.id), summary: { ...detail(f.value.id).summary, candidate, status: 'completed' } }))
  f.port.draft = vi.fn<AuthoringPort['draft']>(async () => ({ owner: 'authoring', candidate, source_job_id: f.value.id, state: 'draft', base_ref: null, body_sha256: '0'.repeat(64), payload: { version: 'worked-example-candidate-v1', kind: 'worked_example', title: '合成候选', body_markdown: '正文 bytes 与所报 hash 不相同', symbols: [{ name: 'x', tex: 'x', domain: 'real', dimension: '1' }], declared_source_refs: [], numeric_plan: { version: 'finite-arithmetic-v1', seed: null, variables: [{ name: 'x', value: 1, unit: '1' }], assertions: [{ id: 'assertion_x', expression: 'x+1', expected: 2, atol: 0, rtol: 0, unit: '1' }] } }, validation: { ...detail(f.value.id).validation, schema: 'PASS', references: 'PASS', symbol_declarations: 'PASS' }, numeric_check_ids: [], warnings: [] }))
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await waitFor(() => expect(hook.result.current.academic).toBe(true)); await act(() => hook.result.current.read(f.value.id)); await act(() => hook.result.current.readDraft())
  expect(hook.result.current.draft).toBeNull()
  expect(hook.result.current.error).not.toBe('')
})
test('a current protected 409 Policy rejection clears the old subject and never displays server private text', async () => {
  const { ApiError } = await import('../../api/client'), f = fixture(); f.session.role = 'author'; f.port.read = vi.fn<AuthoringPort['read']>(async () => detail(f.value.id))
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await waitFor(() => expect(hook.result.current.academic).toBe(true)); await act(() => hook.result.current.read(f.value.id))
  f.port.read = vi.fn<AuthoringPort['read']>(async () => { throw new ApiError(409, 'SECRET ORIGINAL PROTECTED TITLE', 'POLICY_DENIED') })
  await act(() => hook.result.current.read(f.value.id))
  expect(hook.result.current.academic).toBe(false); expect(hook.result.current.detail).toBeNull(); expect(hook.result.current.commands.every(v => v.kind === 'cancel')).toBe(true)
  expect(hook.result.current.error).not.toContain('SECRET ORIGINAL PROTECTED TITLE')
  await act(() => hook.result.current.cancel(f.value)); expect(f.port.cancel).toHaveBeenCalledTimes(1)
})
test('a capability admission failure is reported as its actual safe code, not a successful model call', async () => {
  const { ApiError } = await import('../../api/client'), f = fixture(); f.session.role = 'author'
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port)); await waitFor(() => expect(hook.result.current.academic).toBe(true))
  act(() => hook.result.current.reportAccessError(new ApiError(409, 'do not display arbitrary backend message', 'CAPABILITY_UNSUPPORTED')))
  expect(hook.result.current.error).toContain('CAPABILITY_UNSUPPORTED')
  expect(hook.result.current.error).not.toContain('arbitrary backend')
  expect(hook.result.current.detail).toBeNull()
})
test('same-workspace session access change discards the old pending subject response', async () => {
  const { request } = await import('../../api/client'), f = fixture(); f.session.role = 'author'
  let release!: (value: Awaited<ReturnType<AuthoringPort['read']>>) => void
  f.port.read = vi.fn<AuthoringPort['read']>(() => new Promise(done => { release = done }))
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await waitFor(() => expect(hook.result.current.academic).toBe(true))
  let pending!: Promise<void>; act(() => { pending = hook.result.current.read(f.value.id) })
  f.session.role = 'learner'
  const original = globalThis.fetch; globalThis.fetch = vi.fn(async () => new Response(JSON.stringify(f.session), { status: 200, headers: { 'Content-Type': 'application/json' } }))
  try { await act(async () => { await request('POST /api/v1/session/role', { role: 'learner' }, { 'Idempotency-Key': 'synthetic-role-change' }) }) } finally { globalThis.fetch = original }
  await act(async () => { release(detail(f.value.id)); await pending })
  expect(hook.result.current.academic).toBe(false); expect(hook.result.current.detail).toBeNull()
  await waitFor(() => expect(hook.result.current.jobs).toHaveLength(1))
})
