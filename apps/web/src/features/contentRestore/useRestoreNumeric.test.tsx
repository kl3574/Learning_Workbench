import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { ApiError } from '../../api/client'
import { reviewSession } from '../draftReview/reviewFixtures'
import { useRestoreNumeric } from './useRestoreNumeric'
import type { RestoreNumericPort } from './restoreNumericClient'
import { numericBoundSnapshot, numericDecision, numericDecisionReceipt, numericMaterial, numericPreview, numericSnapshot } from './restoreNumericFixtures'
import { numericFormFixture } from './restoreNumericFormFixtures'
import { restoreNumericCommandStore } from './restoreNumericStore'
import { discardRestoreNumericForms, ownRestoreNumericForm } from './restoreNumericFormMemory'
import { discardRestoreNumericMemory, recoverableRestoreNumericMemory } from './restoreNumericMemory'

const workspaces: string[] = []
afterEach(async () => { cleanup(); vi.restoreAllMocks(); for (const workspace of workspaces.splice(0)) { discardRestoreNumericForms(workspace, numericSnapshot.source_ref.id); discardRestoreNumericMemory(workspace) } await restoreNumericCommandStore.close() })
async function setup() {
  const workspace = `workspace_${crypto.randomUUID()}`; workspaces.push(workspace)
  const port: RestoreNumericPort = { session: vi.fn(async () => reviewSession(workspace)), current: vi.fn(async () => numericSnapshot.base_ref),
    draft: vi.fn(async () => structuredClone(numericSnapshot)), preview: vi.fn(async () => structuredClone(numericPreview)),
    check: vi.fn(async () => structuredClone(numericPreview)), decide: vi.fn(async () => structuredClone(numericDecisionReceipt)) }
  const view = renderHook(({ paused }) => useRestoreNumeric(workspace, numericSnapshot.source_ref.id, paused, port), { initialProps: { paused: false } })
  await waitFor(() => expect(view.result.current.ready).toBe(true))
  return { workspace, port, ...view }
}
test('opening does not read a draft, create a preview or run a numeric decision', async () => {
  const { port, result } = await setup()
  expect(result.current.snapshot).toBeNull(); expect(port.draft).not.toHaveBeenCalled(); expect(port.preview).not.toHaveBeenCalled(); expect(port.decide).not.toHaveBeenCalled()
})
test('explicit preview journals exact original material before HTTP and requires a separate current read before decision', async () => {
  const { port, result, workspace } = await setup()
  await act(() => result.current.select(numericSnapshot)); act(() => result.current.changeForm(numericFormFixture()))
  vi.mocked(port.preview).mockImplementation(async (_id, body, key) => {
    const saved = JSON.parse((await restoreNumericCommandStore.load(workspace))[key].text)
    expect(saved.body).toEqual(body); expect(saved.ack).toBeNull(); expect(body.material).toEqual(numericMaterial)
    return structuredClone(numericPreview)
  })
  await act(() => result.current.preview())
  expect(port.preview).toHaveBeenCalledTimes(1); expect(port.decide).not.toHaveBeenCalled(); expect(result.current.check).toBeNull()
  expect(result.current.commands[0].ack).toEqual(numericPreview)
  vi.mocked(port.draft).mockResolvedValue(numericBoundSnapshot)
  await act(() => result.current.readCheck(numericPreview.id))
  expect(result.current.snapshot?.numeric_material).toEqual(numericBoundSnapshot.numeric_material)
  expect(result.current.check?.id).toBe(numericPreview.id)
  await act(() => result.current.decide(numericDecision))
  expect(port.decide).toHaveBeenCalledTimes(1); expect(result.current.check).toBeNull()
})
test('lost preview response replays only original body and key, without a second execution decision', async () => {
  const { port, result } = await setup()
  await act(() => result.current.select(numericSnapshot)); act(() => result.current.changeForm(numericFormFixture()))
  vi.mocked(port.preview).mockRejectedValueOnce(new TypeError('synthetic lost response'))
  await act(() => result.current.preview()); const command = result.current.commands[0]
  expect(command.ack).toBeNull(); expect(command.rejection).toBeNull()
  await act(() => result.current.execute(command))
  expect(vi.mocked(port.preview).mock.calls[1]).toEqual(vi.mocked(port.preview).mock.calls[0]); expect(port.decide).not.toHaveBeenCalled()
})
test('unsubmitted material is hidden on Policy change then explicitly restored with fresh GETs and unchecked confirmation', async () => {
  const { port, result, rerender, workspace } = await setup()
  await act(() => result.current.select(numericSnapshot)); act(() => result.current.changeForm(numericFormFixture()))
  rerender({ paused: true }); expect(result.current.form).toBeNull(); expect(result.current.pendingForm).toBe(true)
  rerender({ paused: false }); await waitFor(() => expect(result.current.canRestoreForm).toBe(true))
  expect(result.current.form).toBeNull()
  const reads = vi.mocked(port.draft).mock.calls.length
  await act(() => result.current.restoreForm())
  expect(result.current.form).toEqual({ ...numericFormFixture(), confirmed: false }); expect(vi.mocked(port.draft).mock.calls.length).toBe(reads + 1)
  expect(ownRestoreNumericForm(workspace, numericSnapshot.source_ref.id, reviewSession(workspace).actor_session_id)?.snapshot).toEqual(numericSnapshot)
  expect(port.preview).not.toHaveBeenCalled(); expect(port.decide).not.toHaveBeenCalled()
})
test('new session cannot recover the previous session numeric form', async () => {
  const { port, result, rerender } = await setup()
  await act(() => result.current.select(numericSnapshot)); act(() => result.current.changeForm(numericFormFixture()))
  rerender({ paused: true }); vi.mocked(port.session).mockImplementation(async () => ({ ...await Promise.resolve(reviewSession('unused')), workspace_id: workspaces.at(-1)!, actor_session_id: 'other_actor' }))
  rerender({ paused: false }); await waitFor(() => expect(result.current.ready).toBe(true))
  expect(result.current.canRestoreForm).toBe(false); await act(() => result.current.restoreForm())
  expect(result.current.form).toBeNull(); expect(port.preview).not.toHaveBeenCalled()
})
test('advanced current preserves original material and disables preview instead of rebasing', async () => {
  const { port, result, rerender } = await setup()
  await act(() => result.current.select(numericSnapshot)); act(() => result.current.changeForm(numericFormFixture()))
  rerender({ paused: true }); vi.mocked(port.current).mockResolvedValue({ ...numericSnapshot.base_ref, revision: 4, sha256: '4'.repeat(64) })
  rerender({ paused: false }); await waitFor(() => expect(result.current.canRestoreForm).toBe(true)); await act(() => result.current.restoreForm())
  expect(result.current.form?.reason).toBe(numericMaterial.reason); expect(result.current.snapshot?.base_ref).toEqual(numericSnapshot.base_ref); expect(result.current.canPreview).toBe(false)
  await act(() => result.current.preview()); expect(port.preview).not.toHaveBeenCalled()
})
test('ACK persistence failure retains actual ACK, and explicit memory save does not send another POST', async () => {
  const { port, result, workspace } = await setup()
  await act(() => result.current.select(numericSnapshot)); act(() => result.current.changeForm(numericFormFixture()))
  const original = restoreNumericCommandStore.save.bind(restoreNumericCommandStore)
  vi.spyOn(restoreNumericCommandStore, 'save').mockImplementationOnce(original).mockRejectedValueOnce(new Error('synthetic IDB abort after server ACK'))
  await act(() => result.current.preview())
  expect(result.current.pendingMemory).toBe(true)
  expect(recoverableRestoreNumericMemory(workspace, reviewSession(workspace).csrf_token)[0].ack).toEqual(numericPreview)
  await act(() => result.current.saveMemory()); expect(result.current.pendingMemory).toBe(false); expect(port.preview).toHaveBeenCalledTimes(1)
  expect(result.current.commands[0].ack).toEqual(numericPreview)
})
test('actual 412 rejection keeps original body and neither rebases nor starts execution', async () => {
  const { port, result } = await setup()
  await act(() => result.current.select(numericSnapshot)); act(() => result.current.changeForm(numericFormFixture()))
  vi.mocked(port.preview).mockRejectedValue(new ApiError(412, 'conflict', 'RESTORE_BASE_CHANGED'))
  await act(() => result.current.preview())
  expect(result.current.commands[0].rejection?.status).toBe(412); expect(result.current.commands[0].body).toEqual({ candidate: numericSnapshot.candidate, material: numericMaterial }); expect(port.decide).not.toHaveBeenCalled()
})
test('a rejected approval permits a fresh current read and explicit decline with a new key', async () => {
  const { port, result } = await setup()
  vi.mocked(port.draft).mockResolvedValue(numericBoundSnapshot)
  await act(() => result.current.select(numericSnapshot)); await act(() => result.current.readCheck(numericPreview.id))
  vi.mocked(port.decide).mockRejectedValueOnce(new ApiError(412, 'synthetic changed base', 'RESTORE_BASE_CHANGED'))
  await act(() => result.current.decide(numericDecision))
  expect(result.current.commands[0].rejection?.status).toBe(412)
  await act(() => result.current.readCheck(numericPreview.id))
  const decline = { ...numericDecision, decision: 'decline' as const }
  vi.mocked(port.decide).mockResolvedValue({ ...numericDecisionReceipt, decision: 'decline', job: null })
  await act(() => result.current.decide(decline))
  const calls = vi.mocked(port.decide).mock.calls
  expect(calls).toHaveLength(2); expect(calls[0][1]).toEqual(numericDecision); expect(calls[1][1]).toEqual(decline); expect(calls[0][2]).not.toBe(calls[1][2])
  expect(result.current.commands).toHaveLength(2)
})
test('first local save failure keeps raw form and exact command; save-only consumes matching form before explicit replay', async () => {
  const { port, result, workspace } = await setup()
  await act(() => result.current.select(numericSnapshot)); act(() => result.current.changeForm(numericFormFixture()))
  vi.spyOn(restoreNumericCommandStore, 'save').mockRejectedValueOnce(new Error('synthetic first IDB commit abort'))
  await act(() => result.current.preview())
  const original = recoverableRestoreNumericMemory(workspace, reviewSession(workspace).csrf_token)[0]
  expect(result.current.pendingForm).toBe(true); expect(result.current.pendingMemory).toBe(true); expect(port.preview).not.toHaveBeenCalled()
  await act(() => result.current.saveMemory())
  expect(result.current.pendingForm).toBe(false); expect(result.current.pendingMemory).toBe(false); expect(port.preview).not.toHaveBeenCalled()
  expect(result.current.commands[0]).toEqual(original)
  await act(() => result.current.execute(result.current.commands[0]))
  expect(port.preview).toHaveBeenCalledWith(original.draft_id, original.body, original.command_id); expect(port.decide).not.toHaveBeenCalled()
})
