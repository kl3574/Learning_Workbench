import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { AuthoringPort } from './authoringClient'
import type { JobSnapshot } from '../../../../../packages/contracts/generated/api-types'
import { singlePublicationFixture } from '../singlePublication/singlePublicationFixtures'
import { authoringCommandStore, authoringControlStore } from './authoringCommands'
import { ApiError } from '../../api/client'
import { AuthoringPanel } from './AuthoringPanel'
import { providerFixture } from '../providers/testFixtures'
import { makeAuthoringCommand, persistAuthoringCommand } from './authoringCommands'
import { useAuthoring } from './useAuthoring'
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done }); return { promise, resolve } }
afterEach(async () => { cleanup(); vi.restoreAllMocks(); await Promise.all([authoringCommandStore.close(), authoringControlStore.close()]) })
function fixture() {
  const f = singlePublicationFixture()
  const job: JobSnapshot = { id: f.generation.summary.id, workspace_id: f.workspace, kind: 'authoring', status: 'running', revision: 3, created_at: f.generation.summary.created_at, updated_at: f.generation.summary.updated_at, progress: { completed: 0, total: 1, label: '合成运行中' }, result_refs: [], warnings: [], error: null }
  const port: AuthoringPort = { session: f.port.session, list: vi.fn(async () => ({ items: [job], next_cursor: null })), read: f.port.generation, draft: f.port.draft, numeric: f.port.numeric, preview: vi.fn(), prepare: vi.fn(), decide: vi.fn(), job: vi.fn(async () => job), cancel: vi.fn(async () => ({ ...job, status: 'cancelled' as const, revision: 4 })) }
  return { ...f, port, job }
}
test('early detail read cannot strand academic admission while its original journal read is pending', async () => {
  const f = fixture(), held = deferred<Awaited<ReturnType<typeof authoringCommandStore.load>>>()
  vi.spyOn(authoringCommandStore, 'load').mockReturnValueOnce(held.promise)
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await waitFor(() => expect(hook.result.current.academic && hook.result.current.controlReady).toBe(true)); expect(hook.result.current.ready).toBe(false)
  await act(() => hook.result.current.read(f.job.id))
  await act(async () => held.resolve({}))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  expect(f.port.read).not.toHaveBeenCalled()
  await act(() => hook.result.current.read(f.job.id)); expect(hook.result.current.detail?.summary.id).toBe(f.job.id)
})
test('safe cancellation remains available during academic recovery and its ACK survives admission completion', async () => {
  const f = fixture(), held = deferred<Awaited<ReturnType<typeof authoringCommandStore.load>>>()
  vi.spyOn(authoringCommandStore, 'load').mockReturnValueOnce(held.promise)
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await waitFor(() => expect(hook.result.current.academic && hook.result.current.controlReady).toBe(true))
  await act(() => hook.result.current.cancel(f.job)); expect(f.port.cancel).toHaveBeenCalledTimes(1)
  const command = hook.result.current.commands[0]; expect(command.kind === 'cancel' && command.ack?.revision).toBe(4)
  await act(async () => held.resolve({})); await waitFor(() => expect(hook.result.current.ready).toBe(true))
  expect(hook.result.current.commands).toEqual([command]); await act(() => hook.result.current.read(f.job.id)); expect(hook.result.current.detail?.summary.id).toBe(f.job.id)
})

test.each(['explicit_refresh', 'policy_denial'])('late academic admission cannot undo %s', async boundary => {
  const f = fixture(), held = deferred<Awaited<ReturnType<typeof authoringCommandStore.load>>>()
  vi.spyOn(authoringCommandStore, 'load').mockReturnValueOnce(held.promise)
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await waitFor(() => expect(hook.result.current.academic && hook.result.current.controlReady).toBe(true))
  if (boundary === 'explicit_refresh') { f.session.role = 'learner'; await act(() => hook.result.current.refresh()) }
  else act(() => hook.result.current.reportAccessError(new ApiError(403, 'synthetic policy rejection', 'POLICY_DENIED')))
  await act(async () => held.resolve({}))
  expect(hook.result.current.academic).toBe(false); expect(hook.result.current.detail).toBeNull(); expect(hook.result.current.commands.every(command => command.kind === 'cancel')).toBe(true)
  await act(() => hook.result.current.read(f.job.id)); expect(f.port.read).not.toHaveBeenCalled()
  await act(() => hook.result.current.cancel(f.job)); expect(f.port.cancel).toHaveBeenCalledTimes(1)
})
test('a late initial control journal does not erase already recovered academic commands', async () => {
  const f = fixture(), held = deferred<Awaited<ReturnType<typeof authoringControlStore.load>>>()
  const original = makeAuthoringCommand(f.workspace, { kind: 'prepare', body: f.generation.request }); await persistAuthoringCommand(original)
  vi.spyOn(authoringControlStore, 'load').mockReturnValueOnce(held.promise)
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port))
  await waitFor(() => expect(hook.result.current.commands).toEqual([original])); expect(hook.result.current.controlReady).toBe(false)
  await act(async () => held.resolve({})); await waitFor(() => expect(hook.result.current.ready).toBe(true)); expect(hook.result.current.commands).toEqual([original])
})
test('late old-workspace journal cannot enter a replacement workspace', async () => {
  const f = fixture(), next = fixture(), held = deferred<Awaited<ReturnType<typeof authoringCommandStore.load>>>()
  vi.spyOn(authoringCommandStore, 'load').mockReturnValueOnce(held.promise)
  const hook = renderHook(({ workspace, port }) => useAuthoring(workspace, false, port), { initialProps: { workspace: f.workspace, port: f.port } })
  await waitFor(() => expect(hook.result.current.academic && hook.result.current.controlReady).toBe(true)); hook.rerender({ workspace: next.workspace, port: next.port })
  await waitFor(() => expect(hook.result.current.ready).toBe(true)); await act(async () => held.resolve({}))
  expect(hook.result.current.jobs[0].workspace_id).toBe(next.workspace); expect(hook.result.current.commands).toEqual([])
})
test('visible safe cancel stays usable while only academic detail controls wait for journal admission', async () => {
  const f = fixture(), held = deferred<Awaited<ReturnType<typeof authoringCommandStore.load>>>()
  vi.spyOn(authoringCommandStore, 'load').mockReturnValueOnce(held.promise)
  render(<AuthoringPanel workspace={f.workspace} paused={false} currentBlock={null} port={f.port} provider={providerFixture().port} onState={vi.fn()} />)
  const read = await screen.findByRole('button', { name: `读取创作详情 ${f.job.id}` }) as HTMLButtonElement
  const cancel = screen.getByRole('button', { name: `明确取消任务 ${f.job.id}` }) as HTMLButtonElement
  await waitFor(() => expect(cancel.disabled).toBe(false)); expect(read.disabled).toBe(true); fireEvent.click(read); expect(f.port.read).not.toHaveBeenCalled()
  fireEvent.click(cancel); await waitFor(() => expect(f.port.cancel).toHaveBeenCalledTimes(1))
  await act(async () => held.resolve({})); await waitFor(() => expect(read.disabled).toBe(false)); fireEvent.click(read)
  await screen.findByRole('region', { name: '受保护创作详情' })
})
test('academic recovery completed during a pending safe cancel remains visible after its original ACK arrives', async () => {
  const f = fixture(), heldJournal = deferred<Awaited<ReturnType<typeof authoringCommandStore.load>>>(), heldCancel = deferred<JobSnapshot>()
  const original = makeAuthoringCommand(f.workspace, { kind: 'prepare', body: f.generation.request }); await persistAuthoringCommand(original)
  const records = await authoringCommandStore.load(f.workspace)
  vi.spyOn(authoringCommandStore, 'load').mockReturnValueOnce(heldJournal.promise); vi.mocked(f.port.cancel).mockReturnValueOnce(heldCancel.promise)
  const hook = renderHook(() => useAuthoring(f.workspace, false, f.port)); await waitFor(() => expect(hook.result.current.academic && hook.result.current.controlReady).toBe(true))
  let cancelling!: Promise<void>; act(() => { cancelling = hook.result.current.cancel(f.job) }); await waitFor(() => expect(f.port.cancel).toHaveBeenCalledTimes(1))
  await act(async () => heldJournal.resolve(records)); await waitFor(() => expect(hook.result.current.ready).toBe(true)); expect(hook.result.current.commands).toContainEqual(original)
  await act(async () => { heldCancel.resolve({ ...f.job, status: 'cancelled', revision: 4 }); await cancelling })
  expect(hook.result.current.commands).toContainEqual(original)
  const cancelled = hook.result.current.commands.find(command => command.kind === 'cancel'); expect(cancelled?.kind === 'cancel' && cancelled.ack?.revision).toBe(4)
})
