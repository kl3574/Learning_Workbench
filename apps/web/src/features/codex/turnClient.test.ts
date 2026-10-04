import { afterEach, expect, test, vi } from 'vitest'
import type { CodexTurnControlView, CodexTurnPreparationView, CodexTurnPrepareWrite } from '../../../../../packages/contracts/generated/codex-turn-types'
import { codexSession } from './bootstrapTestFixtures'
import { checkedTurn, turnClient } from './turnClient'

// Synthetic wire fixtures prove client admission/transport, never server history or runtime proof.
afterEach(() => vi.unstubAllGlobals())
const hash = 'a'.repeat(64), time = '2026-10-04T00:00:00Z'
const ref = (id: string) => ({ entity: 'block' as const, id, revision: 1, sha256: hash })
const material = (id: string) => ({ ref: ref(id), title: 'Synthetic source', locator: 'line 1', character_count: 20, excerpt_sha256: hash })
const body = (): CodexTurnPrepareWrite => ({ message: '  Original α\n中文😀  ', context_refs: [ref('block_one'), ref('block_two')],
 expected_session_revision: 2, provider_id: 'codex_local', tools: { max_tool_calls: 0, wall_seconds: 30 } })
const prepared = (): CodexTurnPreparationView => ({ id: 'preparation_test', preparation_sha256: hash, actor_session_id: 'actor_test',
 session_id: 'session_test', session_revision: 3, turn_id: 'turn_test', job: { id: 'job_test', status: 'awaiting_approval' }, request: body(),
 summary: { context_snapshot_id: 'snapshot_test', snapshot_sha256: hash, job_input_sha256: hash, prepared_input_sha256: hash,
  runtime: { profile_sha256: hash, cpu_seconds: 60, memory_bytes: 2147483648, file_bytes: 16777216, protocol_output_bytes: 16777216,
   file_descriptors: 128, processes: 16, core_bytes: 0, command_network: 'denied', writable_area: 'turn_outputs' },
  character_count: 100, materials: [material('block_two')], history_turn_ids: [], tools: body().tools, warnings: [] },
 created_at: time, proposal_id: null, consent_id: null, validity: 'unavailable' })
const control = (): CodexTurnControlView => ({ id: 'turn_test', session_id: 'session_test', actor_session_id: 'actor_test',
 job: { id: 'job_test', status: 'awaiting_approval' }, job_revision: 1, run_revision: 1, last_seq: 1, cancel_requested: false,
 execution: 'not_started', outcome: null, approval_ids: [], approval_controls: [], consent_control: null, manifest_id: null,
 created_at: time, started_at: null, finished_at: null, error_code: null })
function respond(value: unknown) {
 const fetch = vi.fn(async () => new Response(JSON.stringify(value), { status: 200 }))
 vi.stubGlobal('fetch', fetch); return fetch
}

test('new preparation preserves original Unicode and complete key/body with one explicit POST only', async () => {
 const original = body(), fetch = respond(prepared())
 expect(await turnClient.prepare('session_test', original, 'original_key')).toEqual(prepared())
 expect(fetch).toHaveBeenCalledTimes(1)
 const [path, init] = fetch.mock.calls[0] as unknown as [string, RequestInit]
 expect(path).toBe('/api/v1/codex/sessions/session_test/turn-preparations')
 expect(init.method).toBe('POST'); expect(JSON.parse(init.body as string)).toEqual(original)
 expect(new Headers(init.headers).get('Idempotency-Key')).toBe('original_key')
 expect(original.message).toBe('  Original α\n中文😀  ')
})

test('subject/current/control/page reads carry no replay key or body and retain exact cursor', async () => {
 for (const [value, read, path] of [
  [prepared(), () => turnClient.preparation('preparation_test'), '/api/v1/codex/turn-preparations/preparation_test'],
  [control(), () => turnClient.control('turn_test'), '/api/v1/codex/turns/turn_test'],
  [{ ...codexSession(), id: 'session_test', revision: 3, active_turn_id: 'turn_test' }, () => turnClient.current('session_test'), '/api/v1/codex/sessions/session_test'],
  [{ items: [control()], next_cursor: 'next_original' }, () => turnClient.turns('session_test', { cursor: 'same/α', limit: 20 }), '/api/v1/codex/sessions/session_test/turns?cursor=same%2F%CE%B1&limit=20'],
 ] as const) {
  const fetch = respond(value); expect(await read()).toEqual(value); expect(fetch).toHaveBeenCalledTimes(1)
  const [actual, init] = fetch.mock.calls[0] as unknown as [string, RequestInit]
  expect(actual).toBe(path); expect(init.method).toBe('GET'); expect(init.body).toBeUndefined()
  expect(new Headers(init.headers).get('Idempotency-Key')).toBeNull()
 }
})

test('cancellation sends the explicitly read job revision, no implicit new preparation or retry', async () => {
 const fetch = respond({ id: 'job_test', status: 'cancelled' })
 expect(await turnClient.cancel('job_test', 7, 'cancel_original')).toEqual({ id: 'job_test', status: 'cancelled' })
 const [path, init] = fetch.mock.calls[0] as unknown as [string, RequestInit]
 expect(path).toBe('/api/v1/jobs/job_test/cancel'); expect(JSON.parse(init.body as string)).toEqual({ expected_revision: 7 })
 expect(new Headers(init.headers).get('Idempotency-Key')).toBe('cancel_original'); expect(fetch).toHaveBeenCalledTimes(1)
})

test.each([
 (v: CodexTurnPreparationView) => { v.session_revision = 2 },
 (v: CodexTurnPreparationView) => { v.summary.tools.max_tool_calls = 1 },
 (v: CodexTurnPreparationView) => { v.consent_id = 'consent_other' },
 (v: CodexTurnPreparationView) => { v.summary.history_turn_ids = [v.turn_id] },
 (v: CodexTurnPreparationView) => { v.summary.history_turn_ids = ['old', 'old'] },
 (v: CodexTurnPreparationView) => { v.summary.materials = [material('block_two'), material('block_one')] },
 (v: CodexTurnPreparationView) => { v.summary.materials = [material('block_missing')] },
 (v: CodexTurnPreparationView) => { v.summary.materials = [material('block_two'), material('block_two')] },
 (v: CodexTurnPreparationView) => { v.summary.materials[0].ref.entity = 'question' as 'block' },
 (v: CodexTurnPreparationView) => { v.summary.materials[0].ref.revision = 2 },
 (v: CodexTurnPreparationView) => { v.summary.character_count = 1 },
 (v: CodexTurnPreparationView) => { v.created_at = '2026-02-30T00:00:00Z' },
 (v: CodexTurnPreparationView) => { v.request.context_refs.push(ref('block_one')) },
 (v: CodexTurnPreparationView) => { Object.assign(v, { hidden_thread: 'unexpected' }) },
 (v: CodexTurnPreparationView) => { v.request.message = '\ud800' },
])('damaged preparation/source order cannot be admitted as an execution basis %#', corrupt => {
 const value = prepared(); corrupt(value); expect(() => checkedTurn('CodexTurnPreparationView', value)).toThrow()
})

test.each([
 (v: CodexTurnControlView) => { Object.assign(v, { message: 'academic payload' }) },
 (v: CodexTurnControlView) => { v.approval_ids = ['approval_missing'] },
 (v: CodexTurnControlView) => { v.approval_controls = [{ id: 'approval_missing', revision: 1, operation_sha256: hash, decision: 'pending', validity: 'current' }] },
 (v: CodexTurnControlView) => { v.execution = 'active' },
 (v: CodexTurnControlView) => { v.outcome = 'cancelled' },
 (v: CodexTurnControlView) => { v.finished_at = time },
 (v: CodexTurnControlView) => { v.started_at = time },
 (v: CodexTurnControlView) => { v.manifest_id = 'manifest_early' },
 (v: CodexTurnControlView) => { v.job.status = 'completed' },
 (v: CodexTurnControlView) => { v.consent_control = { id: 'consent', revision: 2, status: 'expired' } },
])('damaged safe controls cannot supply invented authority or terminal facts %#', corrupt => {
 const value = control(); corrupt(value); expect(() => checkedTurn('CodexTurnControlView', value)).toThrow()
})

test('complete safe decided membership and consumed/expired consent remain readable after cancellation', () => {
 const value: CodexTurnControlView = { ...control(), execution: 'terminal', outcome: 'cancelled', finished_at: time,
  job: { id: 'job_test', status: 'cancelled' }, consent_control: { id: 'consent', revision: 1, status: 'expired' },
  approval_ids: ['approved', 'declined'], approval_controls: [
   { id: 'approved', revision: 4, operation_sha256: hash, decision: 'approve_once', validity: 'closed' },
   { id: 'declined', revision: 2, operation_sha256: hash, decision: 'decline', validity: 'closed' },
  ] }
 expect(checkedTurn('CodexTurnControlView', value)).toEqual(value)
 const reordered = structuredClone(value); reordered.approval_controls.reverse()
 expect(() => checkedTurn('CodexTurnControlView', reordered)).toThrow()
 const completed = { ...value, outcome: 'completed', job: { id: 'job_test', status: 'completed' } }
 expect(() => checkedTurn('CodexTurnControlView', completed)).toThrow()
})

test('server response for another object/command/session is rejected instead of changing the current UI target', async () => {
 for (const read of [
  () => turnClient.prepare('session_test', { ...body(), message: 'different' }, 'original_key'),
  () => turnClient.preparation('different_id'),
 ]) { respond(prepared()); await expect(read()).rejects.toThrow() }
 respond(control()); await expect(turnClient.control('different_turn')).rejects.toThrow()
 respond({ ...codexSession(), id: 'wrong_session' }); await expect(turnClient.current('session_test')).rejects.toThrow()
 respond({ items: [{ ...control(), session_id: 'wrong_session' }], next_cursor: null })
 await expect(turnClient.turns('session_test')).rejects.toThrow()
 respond({ id: 'wrong_job', status: 'cancelled' }); await expect(turnClient.cancel('job_test', 1, 'cancel_original')).rejects.toThrow()
})

test('duplicate/mixed-session pages and invalid local controls issue zero requests', async () => {
 expect(() => checkedTurn('CodexTurnPage', { items: [control(), control()], next_cursor: null })).toThrow()
 expect(() => checkedTurn('CodexTurnPage', { items: [control(), { ...control(), id: 'turn_other', session_id: 'different' }], next_cursor: null })).toThrow()
 const fetch = respond(control())
 for (const query of [{ limit: 0 }, { limit: 101 }, { limit: true as unknown as number }, { cursor: ' ' }, { extra: 'unknown' }]) {
  await expect(turnClient.turns('session_test', query)).rejects.toThrow()
 }
 await expect(turnClient.current('../escape')).rejects.toThrow()
 await expect(turnClient.cancel('job_test', true as unknown as number, 'cancel_original')).rejects.toThrow()
 await expect(turnClient.prepare('session_test', { ...body(), context_refs: [ref('block_one'), ref('block_one')] }, 'original_key')).rejects.toThrow()
 expect(fetch).not.toHaveBeenCalled()
})

test.each([
 (v: CodexTurnPreparationView) => { v.created_at += '\n' },
 (v: CodexTurnPreparationView) => { v.actor_session_id += '\n' },
 (v: CodexTurnPreparationView) => { v.job.id += '\n' },
 (v: CodexTurnPreparationView) => { v.preparation_sha256 += '\n' },
 (v: CodexTurnPreparationView) => { v.summary.snapshot_sha256 += '\n' },
 (v: CodexTurnPreparationView) => { v.summary.runtime.profile_sha256 += '\n' },
 (v: CodexTurnPreparationView) => { v.request.context_refs[0].id += '\n' },
 (v: CodexTurnPreparationView) => { v.request.context_refs[0].sha256 += '\n' },
 (v: CodexTurnPreparationView) => { v.summary.materials[0].excerpt_sha256 += '\n' },
])('anchored IDs/SHA/time must consume the entire original scalar %#', corrupt => {
 const value = prepared(); corrupt(value)
 expect(() => checkedTurn('CodexTurnPreparationView', value)).toThrow()
})

test('invalid path identity ending in newline cannot issue even one GET', async () => {
 const fetch = respond(control())
 await expect(turnClient.control('turn_test\n')).rejects.toThrow()
 expect(fetch).not.toHaveBeenCalled()
})
