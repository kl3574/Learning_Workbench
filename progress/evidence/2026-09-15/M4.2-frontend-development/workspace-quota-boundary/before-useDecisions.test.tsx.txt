import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { MutationAck } from '../../../../../packages/contracts/generated/api-types'
import { ApiError } from '../../api/client'
import { useDecisions } from './useDecisions'
import { decodeDecision, decisionStore, newDecision } from './decisionDrafts'
import { decisionFixture, testRecommendation } from './testFixtures'
afterEach(cleanup)
test('lost ACK retains the exact key, body and decision hash across reload and replays the original receipt after later correction', async () => {
  const workspace = 'workspace_recommendation_ack', state = decisionFixture(), actual = state.port.save
  state.port.save = vi.fn(async value => { const ack = await actual(value); throw new Error(`controlled ACK loss after revision ${ack.revision}`) })
  const first = renderHook(() => useDecisions(workspace, false, state.port))
  await waitFor(() => expect(first.result.current.safe).toBe(true))
  act(() => first.result.current.begin(state.current(), 'accepted'))
  act(() => first.result.current.edit({ decision: 'accepted', reason: '原始选择 🧠é' }))
  await waitFor(() => expect(first.result.current.safe).toBe(true))
  const original = first.result.current.editor!
  await act(() => first.result.current.save()); expect(state.current().decision_revision).toBe(2); expect(first.result.current.editor?.acknowledged).toBeNull()
  act(() => first.result.current.edit({ decision: 'dismissed', reason: '不能替换未确认命令' })); expect(first.result.current.editor?.fields).toEqual(original.fields)
  first.unmount()
  state.external({ ...state.current(), decision: 'dismissed', decision_reason: '后来明确更正', decision_revision: 3, decision_sha256: '3'.repeat(64), staleness: 'stale' })
  state.port.save = actual
  const second = renderHook(() => useDecisions(workspace, false, state.port))
  await waitFor(() => { expect(second.result.current.safe).toBe(true); expect(second.result.current.candidates).toHaveLength(1) })
  await act(() => second.result.current.restore(second.result.current.candidates[0]))
  expect(second.result.current.editor?.base.decision_revision).toBe(1); expect(second.result.current.remote?.decision_revision).toBe(3); expect(state.save).toHaveBeenCalledTimes(1)
  act(() => second.result.current.correct()); expect(second.result.current.editor?.command_id).toBe(original.command_id)
  await act(() => second.result.current.save()); await waitFor(() => expect(second.result.current.safe).toBe(true))
  expect(state.save.mock.calls.map(([value]) => ({ key: value.command_id, body: value.fields, hash: value.base.decision_sha256 }))).toEqual(Array(2).fill({ key: original.command_id, body: original.fields, hash: original.base.decision_sha256 }))
  expect(second.result.current.editor?.acknowledged).toEqual({ id: original.base.id, revision: 2, applied: true }); expect(second.result.current.remote?.decision_revision).toBe(3); expect(state.current().decision_revision).toBe(3)
  expect(decodeDecision((await decisionStore.load(workspace))[original.base.id].text, workspace).acknowledged?.revision).toBe(2)
})
test('an explicit 412 keeps all three values; correction changes the key and needs another save', async () => {
  const workspace = 'workspace_recommendation_cas', state = decisionFixture(), view = renderHook(() => useDecisions(workspace, false, state.port))
  await waitFor(() => expect(view.result.current.safe).toBe(true)); act(() => view.result.current.begin(state.current(), 'accepted')); act(() => view.result.current.edit({ decision: 'accepted', reason: '本页理由' })); await waitFor(() => expect(view.result.current.safe).toBe(true))
  const original = view.result.current.editor!
  state.external({ ...state.current(), decision: 'dismissed', decision_reason: '另一页面理由', decision_revision: 2, decision_sha256: '2'.repeat(64) })
  await act(() => view.result.current.save()); expect(view.result.current.rejected).toBe(true); expect(view.result.current.conflict).toBe(true); expect(view.result.current.editor?.base.decision).toBe('pending'); expect(view.result.current.editor?.fields.reason).toBe('本页理由'); expect(view.result.current.remote?.decision_reason).toBe('另一页面理由')
  await act(() => view.result.current.refresh()); expect(view.result.current.rejected).toBe(true); expect(view.result.current.editor?.command_id).toBe(original.command_id)
  act(() => view.result.current.correct()); expect(view.result.current.editor?.base.decision_revision).toBe(2); expect(view.result.current.editor?.command_id).not.toBe(original.command_id); expect(state.save).toHaveBeenCalledTimes(1)
  await waitFor(() => expect(view.result.current.safe).toBe(true)); await act(() => view.result.current.save()); expect(state.current().decision_revision).toBe(3); expect(state.current().decision_reason).toBe('本页理由')
})
test('offline recovery failure preserves durable candidates and never posts or fabricates a current baseline', async () => {
  const workspace = 'workspace_recommendation_offline', state = decisionFixture(), original = newDecision(state.current(), workspace, { decision: 'dismissed', reason: '离线候选' })
  await decisionStore.save(workspace, original.base.id, JSON.stringify(original), 0)
  state.read.mockRejectedValue(new Error('offline'))
  const view = renderHook(() => useDecisions(workspace, false, state.port)); await waitFor(() => { expect(view.result.current.safe).toBe(true); expect(view.result.current.candidates).toHaveLength(1) })
  await act(() => view.result.current.restore(view.result.current.candidates[0])); expect(view.result.current.remote).toBeNull(); expect(view.result.current.editor).toBeNull(); expect(state.save).not.toHaveBeenCalled(); expect(view.result.current.candidates[0].text).toBe(JSON.stringify(original))
})
test('current policy hides a late acknowledgement and keeps it bound to the same original command for later recovery', async () => {
  const workspace = 'workspace_recommendation_policy_ack', state = decisionFixture(), actual = state.port.save
  let resolve!: (value: MutationAck) => void, ack!: MutationAck
  state.port.save = vi.fn(async value => { ack = await actual(value); return new Promise<MutationAck>(done => { resolve = done }) })
  const view = renderHook(({ paused }) => useDecisions(workspace, paused, state.port), { initialProps: { paused: false } })
  await waitFor(() => expect(view.result.current.safe).toBe(true)); act(() => view.result.current.begin(state.current(), 'accepted')); await waitFor(() => expect(view.result.current.safe).toBe(true))
  let saving!: Promise<void>; act(() => { saving = view.result.current.save() }); await waitFor(() => expect(state.current().decision_revision).toBe(2))
  view.rerender({ paused: true }); await act(async () => { resolve(ack); await saving }); expect(view.result.current.editor).toBeNull(); expect(view.result.current.remote).toBeNull(); expect(view.result.current.candidates).toEqual([])
  view.rerender({ paused: false }); await waitFor(() => expect(view.result.current.remote?.decision_revision).toBe(2)); expect(view.result.current.editor?.acknowledged?.revision).toBe(2)
})
test('an old workspace acknowledgement cannot populate or overwrite a new workspace editor', async () => {
  const first = decisionFixture(), second = decisionFixture(testRecommendation('recommendation_second'))
  let resolve!: (value: MutationAck) => void
  first.port.save = vi.fn(async () => new Promise<MutationAck>(done => { resolve = done }))
  const view = renderHook(({ workspace, port }) => useDecisions(workspace, false, port), { initialProps: { workspace: 'workspace_recommendation_old', port: first.port } })
  await waitFor(() => expect(view.result.current.safe).toBe(true)); act(() => view.result.current.begin(first.current(), 'accepted')); await waitFor(() => expect(view.result.current.safe).toBe(true))
  const original = view.result.current.editor!
  let saving!: Promise<void>; act(() => { saving = view.result.current.save() }); await waitFor(() => expect(first.port.save).toHaveBeenCalledTimes(1))
  view.rerender({ workspace: 'workspace_recommendation_new', port: second.port }); await waitFor(() => expect(view.result.current.safe).toBe(true)); act(() => view.result.current.begin(second.current(), 'dismissed')); await waitFor(() => expect(view.result.current.safe).toBe(true)); const newer = JSON.stringify(view.result.current.editor)
  await act(async () => { resolve({ id: original.base.id, revision: 2, applied: true }); await saving }); expect(JSON.stringify(view.result.current.editor)).toBe(newer); expect((await decisionStore.load('workspace_recommendation_new'))[second.current().id].text).toBe(newer)
  expect((await decisionStore.load('workspace_recommendation_old'))[original.base.id].text).toBe(JSON.stringify(original))
})
test('stale 409 and policy 403 retain the original command without enabling silent correction', async () => {
  for (const status of [409, 403]) {
    const workspace = `workspace_recommendation_reject_${status}`, state = decisionFixture(), view = renderHook(() => useDecisions(workspace, false, state.port))
    state.port.save = vi.fn(async () => { throw new ApiError(status, 'controlled restriction') })
    await waitFor(() => expect(view.result.current.safe).toBe(true)); act(() => view.result.current.begin(state.current(), 'accepted')); await waitFor(() => expect(view.result.current.safe).toBe(true)); const original = JSON.stringify(view.result.current.editor)
    await act(() => view.result.current.save()); act(() => view.result.current.correct()); expect(JSON.stringify(view.result.current.editor)).toBe(original); expect(view.result.current.rejected).toBe(false); expect(view.result.current.sealed).toBe(true); view.unmount()
  }
})
test('foreign local branches require an explicit candidate selection and preserve both choices', async () => {
  const workspace = 'workspace_recommendation_branches', state = decisionFixture()
  const a = renderHook(() => useDecisions(workspace, false, state.port)), b = renderHook(() => useDecisions(workspace, false, state.port))
  await waitFor(() => { expect(a.result.current.safe).toBe(true); expect(b.result.current.safe).toBe(true) })
  act(() => { a.result.current.begin(state.current(), 'accepted'); b.result.current.begin(state.current(), 'dismissed') })
  await waitFor(() => { expect(a.result.current.safe).toBe(true); expect(b.result.current.safe).toBe(true); expect(a.result.current.competing).toHaveLength(1) })
  const originals = [JSON.stringify(a.result.current.editor), JSON.stringify(b.result.current.editor)]
  await act(() => a.result.current.save()); expect(state.save).not.toHaveBeenCalled()
  const disk = (await decisionStore.load(workspace))[state.current().id]; expect(new Set([disk.text, ...disk.conflicts.map(item => item.text)])).toEqual(new Set(originals))
  b.unmount(); await act(() => a.result.current.restore(a.result.current.candidates.find(candidate => candidate.value.fields.decision === 'accepted')!)); await waitFor(() => expect(a.result.current.competing).toHaveLength(0)); expect(state.save).not.toHaveBeenCalled()
})
test('malformed stored references and mismatched acknowledgements fail closed', () => {
  const workspace = 'workspace_recommendation_decode', value = newDecision(testRecommendation(), workspace, { decision: 'accepted', reason: null })
  expect(() => decodeDecision(JSON.stringify({ ...value, base: { ...value.base, target_ref: { ...value.base.target_ref, sha256: 'bad' } } }), workspace)).toThrow('哈希')
  expect(() => decodeDecision(JSON.stringify({ ...value, fields: { ...value.fields, expected_revision: 1 } }), workspace)).toThrow('决定')
  expect(() => decodeDecision(JSON.stringify({ ...value, acknowledged: { id: value.base.id, revision: 1, applied: false } }), workspace)).toThrow('回执')
  expect(() => decodeDecision(JSON.stringify(value), 'workspace_other')).toThrow('身份')
})
test('a local write failure prevents POST and protects the unsaved candidate until actual persistence succeeds', async () => {
  const workspace = 'workspace_recommendation_quota', state = decisionFixture(), view = renderHook(() => useDecisions(workspace, false, state.port))
  await waitFor(() => expect(view.result.current.safe).toBe(true))
  const write = vi.spyOn(decisionStore, 'save').mockRejectedValueOnce(new DOMException('injected unit storage failure', 'QuotaExceededError'))
  try {
    act(() => view.result.current.begin(state.current(), 'accepted')); await waitFor(() => expect(view.result.current.journal.error).toContain('本机作答草稿尚未保存'))
    expect(view.result.current.safe).toBe(false); const candidate = JSON.stringify(view.result.current.editor)
    await act(() => view.result.current.save()); expect(state.save).not.toHaveBeenCalled()
    const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event); expect(event.defaultPrevented).toBe(true)
    act(() => view.result.current.retain()); expect(JSON.stringify(view.result.current.editor)).toBe(candidate)
    act(() => view.result.current.retryLocal()); await waitFor(() => expect(view.result.current.safe).toBe(true)); expect((await decisionStore.load(workspace))[state.current().id].text).toBe(candidate)
  } finally { write.mockRestore(); act(() => view.result.current.retryLocal()); await waitFor(() => expect(view.result.current.safe).toBe(true)) }
})
test('an unchanged explicit choice accepts an applied=false receipt at its original revision', async () => {
  const workspace = 'workspace_recommendation_noop', state = decisionFixture({ ...testRecommendation(), decision: 'accepted', decision_revision: 2, decision_sha256: '2'.repeat(64) }), view = renderHook(() => useDecisions(workspace, false, state.port))
  await waitFor(() => expect(view.result.current.safe).toBe(true)); act(() => view.result.current.begin(state.current(), 'accepted')); await waitFor(() => expect(view.result.current.safe).toBe(true)); await act(() => view.result.current.save())
  expect(view.result.current.editor?.acknowledged).toEqual({ id: state.current().id, revision: 2, applied: false }); expect(state.current().decision_revision).toBe(2)
})
test('quota in another workspace does not lock current decisions while global close protection remains active', async () => {
  const a = 'workspace_recommendation_unsafe_a', b = 'workspace_recommendation_usable_b', state = decisionFixture(), actual = decisionStore.save.bind(decisionStore)
  const write = vi.spyOn(decisionStore, 'save').mockImplementation((workspace, ...args) => workspace === a ? Promise.reject(new Error('controlled workspace A write failure')) : actual(workspace, ...args))
  const view = renderHook(({ workspace }) => useDecisions(workspace, false, state.port), { initialProps: { workspace: a } })
  let original!: ReturnType<typeof newDecision>
  try {
    await waitFor(() => expect(view.result.current.journal.ready).toBe(true)); act(() => view.result.current.begin(state.current(), 'accepted')); await waitFor(() => expect(view.result.current.journal.error).toContain('workspace A write failure')); original = view.result.current.editor!
    view.rerender({ workspace: b }); await waitFor(() => expect(view.result.current.journal.ready).toBe(true))
    expect(view.result.current.safe).toBe(true); expect(view.result.current.closeSafe).toBe(false)
    act(() => view.result.current.begin(state.current(), 'dismissed')); await waitFor(() => expect(view.result.current.safe).toBe(true)); expect(view.result.current.editor?.workspace_id).toBe(b); expect((await decisionStore.load(b))[state.current().id]).toBeTruthy()
    const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event); expect(event.defaultPrevented).toBe(true)
  } finally {
    write.mockRestore(); view.rerender({ workspace: a }); act(() => view.result.current.journal.save(original)); await waitFor(() => expect(view.result.current.journal.unsafe).toBe(false))
  }
})
