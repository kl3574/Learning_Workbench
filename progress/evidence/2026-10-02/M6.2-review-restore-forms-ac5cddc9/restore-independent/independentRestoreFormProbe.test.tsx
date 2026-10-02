import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { reviewSession } from '../draftReview/reviewFixtures'
import { useRestoreDrafts } from './useRestoreDrafts'
import type { RestorePort } from './restoreClient'
import { base, current, createAck, publicationDraft, publicationReceipt, publicationRef } from './restoreFixtures'
import { discardRestoreForms, ownRestoreForm } from './restoreFormMemory'
import { discardRestoreCreateMemory } from './restoreCreateMemory'
import { readRestoreCreateCommand, restoreCreateCommandStore } from './restoreCreateCommands'
const workspaces: string[] = []
afterEach(async () => { cleanup(); vi.restoreAllMocks(); for (const workspace of workspaces.splice(0)) { discardRestoreForms(workspace, base.metadata.id); discardRestoreCreateMemory(workspace) }; await restoreCreateCommandStore.close() })
async function held() {
  const workspace = `workspace_${crypto.randomUUID()}`; workspaces.push(workspace)
  const port: RestorePort = { session: vi.fn(async () => reviewSession(workspace)), current: vi.fn(async () => publicationDraft.base_ref),
    source: vi.fn(async ref => structuredClone(ref.revision === 1 ? base : current)), create: vi.fn(async () => structuredClone(createAck)),
    draft: vi.fn(async () => structuredClone(publicationDraft)), review: vi.fn(async () => publicationReceipt), publish: vi.fn(async () => publicationRef) }
  const hook = renderHook(({ paused, scope }) => useRestoreDrafts(scope, paused, base.metadata.id, port), { initialProps: { paused: false, scope: workspace } })
  await waitFor(() => expect(hook.result.current.ready).toBe(true)); await act(() => hook.result.current.prepare(publicationDraft.source_ref))
  const reason = '独立反例原理由 🧠\n'
  act(() => hook.result.current.changeForm({ reason, confirmed: true }))
  return { workspace, port, hook, reason }
}
async function hideAndReturn(ctx: Awaited<ReturnType<typeof held>>) {
  ctx.hook.rerender({ paused: true, scope: ctx.workspace }); expect(ctx.hook.result.current.form).toBeNull()
  ctx.hook.rerender({ paused: false, scope: ctx.workspace }); await waitFor(() => expect(ctx.hook.result.current.ready).toBe(true))
}
test.each(['body', 'metadata', 'current_id'] as const)('recovery rejects corrupt protected originals without erasing the held reason: %s', async fault => {
  const c = await held(); await hideAndReturn(c)
  if (fault === 'body') vi.mocked(c.port.source).mockResolvedValueOnce({ ...base, body_markdown: 'corrupt bytes' })
  if (fault === 'metadata') vi.mocked(c.port.source).mockResolvedValueOnce({ ...base, metadata: { ...base.metadata, title: 'corrupt metadata' } })
  if (fault === 'current_id') vi.mocked(c.port.current).mockResolvedValueOnce({ ...publicationDraft.base_ref, id: 'block_foreign' })
  await act(() => c.hook.result.current.restoreForm())
  expect(c.hook.result.current.form).toBeNull(); expect(c.hook.result.current.basis).toBeNull()
  expect(ownRestoreForm(c.workspace, base.metadata.id, reviewSession(c.workspace).csrf_token)?.value.reason).toBe(c.reason)
  expect(c.port.create).not.toHaveBeenCalled(); expect(Object.keys(await restoreCreateCommandStore.load(c.workspace))).toHaveLength(0)
})
test.each(['foreign_workspace', 'learner'] as const)('fresh permission check closes protected recovery before source reads: %s', async fault => {
  const c = await held(); await hideAndReturn(c)
  vi.mocked(c.port.session).mockResolvedValueOnce({ ...reviewSession(c.workspace), ...(fault === 'foreign_workspace' ? { workspace_id: 'workspace_foreign' } : { role: 'learner' as const }) })
  const reads = vi.mocked(c.port.source).mock.calls.length
  await act(() => c.hook.result.current.restoreForm())
  expect(c.hook.result.current.form).toBeNull(); expect(c.hook.result.current.ready).toBe(false)
  expect(vi.mocked(c.port.source).mock.calls).toHaveLength(reads); expect(c.port.create).not.toHaveBeenCalled()
  expect(ownRestoreForm(c.workspace, base.metadata.id, reviewSession(c.workspace).csrf_token)?.value.reason).toBe(c.reason)
})
test('late original bytes cannot reopen payload after Policy revocation; another explicit recovery succeeds', async () => {
  const c = await held(); await hideAndReturn(c)
  let done!: (value: typeof base) => void
  vi.mocked(c.port.source).mockImplementationOnce(() => new Promise(resolve => { done = resolve }))
  let recovering!: Promise<void>
  act(() => { recovering = c.hook.result.current.restoreForm() })
  await waitFor(() => expect(vi.mocked(c.port.source).mock.calls.length).toBe(4))
  c.hook.rerender({ paused: true, scope: c.workspace }); await act(async () => { done(base); await recovering })
  expect(c.hook.result.current.form).toBeNull(); expect(c.hook.result.current.basis).toBeNull(); expect(c.port.create).not.toHaveBeenCalled()
  c.hook.rerender({ paused: false, scope: c.workspace }); await waitFor(() => expect(c.hook.result.current.ready).toBe(true))
  await act(() => c.hook.result.current.restoreForm()); expect(c.hook.result.current.form).toEqual({ reason: c.reason, confirmed: false })
})
test('failed initial journal write preserves both original form and command; memory save records original body without HTTP', async () => {
  const c = await held(), save = vi.spyOn(restoreCreateCommandStore, 'save').mockRejectedValueOnce(new Error('independent abort'))
  await act(() => c.hook.result.current.create(c.reason))
  expect(c.port.create).not.toHaveBeenCalled(); expect(c.hook.result.current.pendingMemory).toBe(true)
  expect(ownRestoreForm(c.workspace, base.metadata.id, reviewSession(c.workspace).csrf_token)?.value.reason).toBe(c.reason)
  save.mockRestore(); await hideAndReturn(c)
  await act(() => c.hook.result.current.saveMemory())
  expect(c.port.create).not.toHaveBeenCalled(); expect(c.hook.result.current.pendingMemory).toBe(false)
  const records = Object.values(await restoreCreateCommandStore.load(c.workspace)); expect(records).toHaveLength(1)
  expect(readRestoreCreateCommand(records[0], c.workspace).body).toEqual({ source_ref: publicationDraft.source_ref, expected_current_ref: publicationDraft.base_ref, reason: c.reason })
  expect(c.hook.result.current.pendingForm).toBe(false)
})
test('same-page different workspace cannot adopt the original form even if test session token is reused', async () => {
  const c = await held(), other = `workspace_${crypto.randomUUID()}`; workspaces.push(other)
  vi.mocked(c.port.session).mockResolvedValue(reviewSession(other))
  c.hook.rerender({ paused: false, scope: other }); await waitFor(() => expect(c.hook.result.current.ready).toBe(true))
  expect(c.hook.result.current.pendingForm).toBe(false); expect(c.hook.result.current.canRestoreForm).toBe(false)
  await act(() => c.hook.result.current.restoreForm()); expect(c.hook.result.current.form).toBeNull()
  expect(ownRestoreForm(c.workspace, base.metadata.id, reviewSession(c.workspace).csrf_token)?.value.reason).toBe(c.reason)
  expect(c.port.create).not.toHaveBeenCalled()
})
