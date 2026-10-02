import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { JobSnapshot, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, getSessionGeneration, request } from '../../api/client'
import { reviewSession } from '../draftReview/reviewFixtures'
import { authoringClient } from '../authoring/authoringClient'
import { authoringControlStore } from '../authoring/authoringCommands'
import { RestoreNumericPanel } from './RestoreNumericPanel'
import { useRestoreNumeric } from './useRestoreNumeric'
import type { RestoreNumericPort } from './restoreNumericClient'
import { numericBoundSnapshot, numericDecisionReceipt, numericMaterial, numericPreview, numericSnapshot } from './restoreNumericFixtures'
import { numericFormFixture } from './restoreNumericFormFixtures'
import { makeRestoreNumericCommand, persistRestoreNumericCommand, readRestoreNumericCommand, restoreNumericCommandStore } from './restoreNumericStore'
import { discardRestoreNumericForms, ownRestoreNumericForm } from './restoreNumericFormMemory'
import { discardRestoreNumericMemory, recoverableRestoreNumericMemory } from './restoreNumericMemory'

const workspaces: string[] = []
const deferred = <T,>() => { let resolve!: (value: T) => void; let reject!: (reason: unknown) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no }); return { promise, resolve, reject } }
afterEach(async () => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); for (const workspace of workspaces.splice(0)) { discardRestoreNumericForms(workspace, numericSnapshot.source_ref.id); discardRestoreNumericMemory(workspace) } await restoreNumericCommandStore.close(); await authoringControlStore.close() })
function fixture() {
  const workspace = `workspace_${crypto.randomUUID()}`; workspaces.push(workspace)
  const port: RestoreNumericPort = { session: vi.fn(async () => reviewSession(workspace)), current: vi.fn(async () => numericSnapshot.base_ref), draft: vi.fn(async () => structuredClone(numericSnapshot)), preview: vi.fn(async () => structuredClone(numericPreview)), check: vi.fn(async () => structuredClone(numericPreview)), decide: vi.fn(async () => structuredClone(numericDecisionReceipt)) }
  return { workspace, port }
}
async function mounted() {
  const f = fixture(), hook = renderHook(({ workspace, paused }) => useRestoreNumeric(workspace, numericSnapshot.source_ref.id, paused, f.port), { initialProps: { workspace: f.workspace, paused: false } })
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  return { ...f, ...hook }
}
test('independent: first IDB abort preserves lexical numeric strings, combining Unicode and CRLF raw reason across unmount and fresh recovery', async () => {
  const f = await mounted(), raw = numericFormFixture(); raw.variables[0].value = '2e0'; raw.assertions[0].expected = '3.0'; raw.assertions[0].atol = '-0'; raw.reason = 'e\u0301 🧮 原理由\r\n第二行\\frac{1}{2}'
  await act(() => f.result.current.select(numericSnapshot)); act(() => f.result.current.changeForm(raw))
  vi.spyOn(restoreNumericCommandStore, 'save').mockRejectedValueOnce(new Error('review first IDB abort'))
  await act(() => f.result.current.preview())
  expect(f.port.preview).not.toHaveBeenCalled(); expect(f.result.current.form).toEqual(raw)
  const held = ownRestoreNumericForm(f.workspace, numericSnapshot.source_ref.id, reviewSession(f.workspace).actor_session_id)
  expect(held?.value).toEqual(raw); expect(held?.snapshot).toEqual(numericSnapshot)
  f.unmount()
  const hook = renderHook(() => useRestoreNumeric(f.workspace, numericSnapshot.source_ref.id, false, f.port))
  await waitFor(() => expect(hook.result.current.canRestoreForm).toBe(true)); expect(hook.result.current.form).toBeNull()
  await act(() => hook.result.current.restoreForm()); expect(hook.result.current.form).toEqual({ ...raw, confirmed: false })
  expect(f.port.preview).not.toHaveBeenCalled(); expect(f.port.decide).not.toHaveBeenCalled()
})
test('independent: a late fresh permission read after Policy re-lock cannot expose the original form or read the candidate', async () => {
  const f = await mounted(); await act(() => f.result.current.select(numericSnapshot)); act(() => f.result.current.changeForm(numericFormFixture()))
  f.rerender({ workspace: f.workspace, paused: true }); f.rerender({ workspace: f.workspace, paused: false }); await waitFor(() => expect(f.result.current.canRestoreForm).toBe(true))
  const gate = deferred<SessionResponse>(), reads = vi.mocked(f.port.draft).mock.calls.length; vi.mocked(f.port.session).mockReturnValueOnce(gate.promise)
  let pending!: Promise<void>; act(() => { pending = f.result.current.restoreForm() }); f.rerender({ workspace: f.workspace, paused: true })
  await act(async () => { gate.resolve(reviewSession(f.workspace)); await pending })
  expect(f.result.current.form).toBeNull(); expect(f.result.current.snapshot).toBeNull(); expect(f.result.current.pendingForm).toBe(true); expect(f.port.draft).toHaveBeenCalledTimes(reads)
  expect(f.port.preview).not.toHaveBeenCalled(); expect(f.port.decide).not.toHaveBeenCalled()
})
test('independent: real access generation change hides a late ACK, keeps the durable original and refuses same-actor numeric replay', async () => {
  const f = await mounted(), gate = deferred<typeof numericPreview>(); await act(() => f.result.current.select(numericSnapshot)); act(() => f.result.current.changeForm(numericFormFixture())); vi.mocked(f.port.preview).mockReturnValueOnce(gate.promise)
  let pending!: Promise<void>; act(() => { pending = f.result.current.preview() }); await waitFor(() => expect(f.port.preview).toHaveBeenCalledTimes(1)); const original = f.result.current.commands[0]
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(reviewSession(f.workspace)))))
  await act(() => request('POST /api/v1/session/role', { role: 'author' }, { 'Idempotency-Key': 'independent_access_cycle' }))
  await act(async () => { gate.resolve(numericPreview); await pending }); await waitFor(() => expect(f.result.current.ready).toBe(true))
  expect(f.result.current.snapshot).toBeNull(); expect(f.result.current.check).toBeNull()
  const retained = readRestoreNumericCommand((await restoreNumericCommandStore.load(f.workspace))[original.command_id], f.workspace)
  expect(retained).toEqual(original); expect(retained.ack).toBeNull()
  await act(() => f.result.current.select(numericSnapshot)); expect(f.result.current.canReplay(retained)).toBe(false); await act(() => f.result.current.execute(retained)); await act(() => f.result.current.preview())
  expect(f.port.preview).toHaveBeenCalledTimes(1); expect(f.port.decide).not.toHaveBeenCalled()
})
test.each(['page', 'actor'] as const)('independent: previous %s journal cannot inherit replay or be replaced by a new preview key', async kind => {
  const f = fixture(), command = makeRestoreNumericCommand(f.workspace, reviewSession(f.workspace).actor_session_id, getSessionGeneration(), { kind: 'preview', draft_id: numericSnapshot.candidate.draft_id, body: { candidate: numericSnapshot.candidate, material: numericMaterial } })
  if (kind === 'page') command.origin.page_id = 'page_previous'; else command.origin.actor_session_id = 'actor_previous'
  await persistRestoreNumericCommand(command)
  const hook = renderHook(() => useRestoreNumeric(f.workspace, numericSnapshot.source_ref.id, false, f.port)); await waitFor(() => expect(hook.result.current.ready).toBe(true)); await act(() => hook.result.current.select(numericSnapshot))
  expect(hook.result.current.canReplay(command)).toBe(false); await act(() => hook.result.current.execute(command)); act(() => hook.result.current.changeForm(numericFormFixture())); await act(() => hook.result.current.preview())
  expect(f.port.preview).not.toHaveBeenCalled(); expect(f.port.decide).not.toHaveBeenCalled(); expect(Object.keys(await restoreNumericCommandStore.load(f.workspace))).toEqual([command.command_id])
})
test('independent: a different workspace or new actor gets only a recovery-exists signal, never old form or ACK memory', async () => {
  const f = await mounted(); await act(() => f.result.current.select(numericSnapshot)); act(() => f.result.current.changeForm(numericFormFixture()))
  vi.spyOn(restoreNumericCommandStore, 'save').mockRejectedValueOnce(new Error('review first IDB abort')); await act(() => f.result.current.preview())
  const other = fixture(); vi.mocked(f.port.session).mockResolvedValue(reviewSession(other.workspace)); f.rerender({ workspace: other.workspace, paused: false }); await waitFor(() => expect(f.result.current.ready).toBe(true))
  expect(f.result.current.pendingMemory).toBe(false); expect(f.result.current.pendingForm).toBe(false); expect(f.result.current.form).toBeNull()
  vi.mocked(f.port.session).mockResolvedValue({ ...reviewSession(f.workspace), actor_session_id: 'new_actor', csrf_token: '9'.repeat(64) }); f.rerender({ workspace: f.workspace, paused: false }); await waitFor(() => expect(f.result.current.ready).toBe(true))
  expect(f.result.current.pendingMemory).toBe(true); expect(f.result.current.pendingForm).toBe(true); expect(f.result.current.canSaveMemory).toBe(false); expect(f.result.current.canRestoreForm).toBe(false)
  await act(() => f.result.current.restoreForm()); await act(() => f.result.current.saveMemory()); expect(f.result.current.form).toBeNull(); expect(recoverableRestoreNumericMemory(f.workspace, reviewSession(f.workspace).csrf_token)).toHaveLength(1); expect(f.port.preview).not.toHaveBeenCalled()
})
test('independent: another preview binding won while form was isolated, original raw form remains and cannot silently switch plan', async () => {
  const f = await mounted(); await act(() => f.result.current.select(numericSnapshot)); act(() => f.result.current.changeForm(numericFormFixture()))
  f.rerender({ workspace: f.workspace, paused: true }); vi.mocked(f.port.draft).mockResolvedValue(numericBoundSnapshot); f.rerender({ workspace: f.workspace, paused: false }); await waitFor(() => expect(f.result.current.canRestoreForm).toBe(true)); await act(() => f.result.current.restoreForm())
  expect(f.result.current.form).toEqual({ ...numericFormFixture(), confirmed: false }); expect(f.result.current.canPreview).toBe(false); await act(() => f.result.current.preview()); expect(f.port.preview).not.toHaveBeenCalled(); expect(f.port.decide).not.toHaveBeenCalled()
})
function safeControls(workspace: string) {
  const job: JobSnapshot = { id: 'numeric_safe_review', workspace_id: workspace, kind: 'authoring_numeric_check', status: 'running', revision: 3, created_at: '2026-10-02T00:00:00Z', updated_at: '2026-10-02T00:00:01Z', progress: { completed: 0, total: null, label: 'safe' }, result_refs: [], warnings: [], error: null }
  vi.spyOn(authoringClient, 'session').mockResolvedValue({ ...reviewSession(workspace), role: 'learner' }); vi.spyOn(authoringClient, 'list').mockResolvedValue({ items: [job], next_cursor: null })
  return job
}
test('independent real useAuthoring: safe cancel busy prevents close; lost reply retains durable original and dirty/unload guard under Policy lock', async () => {
  const f = fixture(), job = safeControls(f.workspace), gate = deferred<JobSnapshot>(), changed = vi.fn(); vi.spyOn(authoringClient, 'cancel').mockReturnValue(gate.promise)
  render(<RestoreNumericPanel workspace={f.workspace} blockId={numericSnapshot.source_ref.id} draft={null} paused onState={changed} port={f.port} />)
  const cancel = await screen.findByRole('button', { name: `明确取消任务 ${job.id}` }); await waitFor(() => expect((cancel as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(cancel)
  await waitFor(() => expect(authoringClient.cancel).toHaveBeenCalledTimes(1)); await waitFor(() => expect(changed.mock.lastCall?.[0]).toEqual({ dirty: true, safe: false, closeSafe: false }))
  const call = vi.mocked(authoringClient.cancel).mock.calls[0]; expect(JSON.parse((await authoringControlStore.load(f.workspace))[call[2]].text).body).toEqual({ expected_revision: job.revision })
  await act(async () => { gate.reject(new TypeError('independent lost cancellation ACK')); await Promise.resolve() }); await waitFor(() => expect(changed.mock.lastCall?.[0]).toEqual({ dirty: true, safe: true, closeSafe: true }))
  const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event); expect(event.defaultPrevented).toBe(true)
  expect(f.port.draft).not.toHaveBeenCalled(); expect(f.port.preview).not.toHaveBeenCalled(); expect(f.port.decide).not.toHaveBeenCalled()
})
test('independent DOM: rejected approval exposes no stale approval panel; fresh read then decline uses a separate key and never automatically retries', async () => {
  const f = fixture(); safeControls(f.workspace); vi.mocked(f.port.draft).mockResolvedValue(numericBoundSnapshot); vi.mocked(f.port.decide).mockRejectedValueOnce(new ApiError(412, 'review base changed', 'RESTORE_BASE_CHANGED')).mockResolvedValueOnce({ ...numericDecisionReceipt, decision: 'decline', job: null })
  render(<RestoreNumericPanel workspace={f.workspace} blockId={numericSnapshot.source_ref.id} draft={numericBoundSnapshot} paused={false} port={f.port} />)
  const select = await screen.findByRole('button', { name: '重新读取这份恢复例题的数值材料' }); await waitFor(() => expect((select as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(select)
  fireEvent.click(await screen.findByRole('button', { name: `另行读取恢复数值检查 ${numericPreview.id}` })); await screen.findByRole('region', { name: '独立数值执行批准' })
  fireEvent.click(screen.getByLabelText('我已核对全部变量、表达式、容差、候选与本机隔离范围，单独批准这一次执行')); fireEvent.click(screen.getByRole('button', { name: '明确批准本次数值执行' }))
  await waitFor(() => expect(f.port.decide).toHaveBeenCalledTimes(1)); await screen.findByText('独立数值决定 · 服务端拒绝，原数值基准保留'); expect(screen.queryByRole('region', { name: '独立数值执行批准' })).toBeNull()
  fireEvent.click(screen.getByRole('button', { name: `另行读取恢复数值检查 ${numericPreview.id}` })); const decline = await screen.findByRole('button', { name: '明确拒绝本次数值执行' }); await waitFor(() => expect((decline as HTMLButtonElement).disabled).toBe(false)); fireEvent.click(decline)
  await waitFor(() => expect(f.port.decide).toHaveBeenCalledTimes(2)); const calls = vi.mocked(f.port.decide).mock.calls; expect(calls[0][1].decision).toBe('approve_once'); expect(calls[1][1].decision).toBe('decline'); expect(calls[1][2]).not.toBe(calls[0][2]); expect(f.port.preview).not.toHaveBeenCalled()
})
