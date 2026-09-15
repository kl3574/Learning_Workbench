import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { LearnerProfile } from '../../../../../packages/contracts/generated/types'
import { ApiError } from '../../api/client'
import { useProfile, type ProfilePort } from './useProfile'
import { editProfileDraft, newProfileDraft, profileDraftKey, profileStore, type ProfileEnvelope } from './profileDrafts'
afterEach(cleanup)
const base = (workspace: string): LearnerProfile => ({ workspace_id: workspace, revision: 1, goals: [], goal_concept_ids: [], weekly_minutes: 120, language: 'zh-CN', preferred_difficulty: 'beginner', self_assessments: [] })
function fixture(workspace: string) {
  let saved = base(workspace)
  const acknowledgements = new Map<string, LearnerProfile>()
  const read = vi.fn(async () => structuredClone(saved))
  const save = vi.fn(async (envelope: ProfileEnvelope) => {
    const prior = acknowledgements.get(envelope.command_id); if (prior) return structuredClone(prior)
    if (envelope.base.revision !== saved.revision) throw new ApiError(412, 'profile conflict')
    saved = { ...saved, ...envelope.fields, revision: saved.revision + 1, weekly_minutes: Number(envelope.fields.weekly_minutes), self_assessments: envelope.fields.self_assessments.map(item => ({ ...item, origin: 'self_report' as const, updated_at: '2026-09-15T00:00:00Z' })) }
    acknowledgements.set(envelope.command_id, saved); return structuredClone(saved)
  })
  const port: ProfilePort = { read, save }
  return { port, read, save, current: () => saved, external: (next: LearnerProfile) => { saved = next } }
}
test('lost acknowledgement retries the same durable command and creates only one server revision', async () => {
  const workspace = 'workspace_profile_ack', state = fixture(workspace), actual = state.port.save
  let lost = true
  state.port.save = vi.fn(async value => { const ack = await actual(value); if (lost) { lost = false; throw new Error('simulated lost acknowledgement') }; return ack })
  const view = renderHook(() => useProfile(workspace, false, state.port))
  await waitFor(() => expect(view.result.current.remote?.revision).toBe(1)); await waitFor(() => expect(view.result.current.safe).toBe(true))
  act(() => view.result.current.begin()); act(() => view.result.current.edit({ ...view.result.current.fields!, goals: ['恢复测试原创目标'] }))
  await waitFor(() => expect(view.result.current.safe).toBe(true))
  const command = view.result.current.editor!.command_id
  await act(() => view.result.current.save()); expect(state.current().revision).toBe(2); expect(view.result.current.editor!.acknowledged).toBeNull(); expect(view.result.current.error).toContain('尚未确认保存')
  const persisted = (await profileStore.load(workspace))[profileDraftKey]; expect(JSON.parse(persisted.text).command_id).toBe(command)
  await act(() => view.result.current.save()); await waitFor(() => expect(view.result.current.safe).toBe(true)); expect(view.result.current.editor?.acknowledged?.revision).toBe(2); expect(state.save.mock.calls.map(([value]) => value.command_id)).toEqual([command, command]); expect(state.current().revision).toBe(2)
})
test('server CAS shows the real three bases and a rebase only follows an explicit local choice', async () => {
  const workspace = 'workspace_profile_cas', state = fixture(workspace), view = renderHook(() => useProfile(workspace, false, state.port))
  await waitFor(() => expect(view.result.current.remote?.revision).toBe(1)); await waitFor(() => expect(view.result.current.safe).toBe(true))
  act(() => view.result.current.begin()); act(() => view.result.current.edit({ ...view.result.current.fields!, goals: ['本页原创目标'] })); await waitFor(() => expect(view.result.current.safe).toBe(true))
  const command = view.result.current.editor!.command_id
  state.external({ ...base(workspace), revision: 2, goals: ['另一页面目标'] })
  await act(() => view.result.current.save()); expect(view.result.current.conflict).toBe(true); expect(view.result.current.editor?.base.revision).toBe(1); expect(view.result.current.fields?.goals).toEqual(['本页原创目标']); expect(view.result.current.remote?.goals).toEqual(['另一页面目标'])
  act(() => view.result.current.rebase(true)); expect(view.result.current.editor?.base.revision).toBe(2); expect(view.result.current.editor?.command_id).not.toBe(command); expect(state.save).toHaveBeenCalledTimes(1)
  await waitFor(() => expect(view.result.current.safe).toBe(true)); await act(() => view.result.current.save()); expect(state.current().revision).toBe(3); expect(state.current().goals).toEqual(['本页原创目标'])
})
test('offline reload restores only after actual durable readback and cannot silently replace the original base', async () => {
  const workspace = 'workspace_profile_restore', state = fixture(workspace), original = newProfileDraft(base(workspace)), candidate = editProfileDraft(original, { ...original.fields, goals: ['离线保留 🧠é'] })
  await profileStore.save(workspace, profileDraftKey, JSON.stringify(candidate), 0)
  state.read.mockRejectedValueOnce(new Error('offline'))
  const view = renderHook(() => useProfile(workspace, false, state.port))
  await waitFor(() => expect(view.result.current.needsRecovery).toBe(true)); expect(view.result.current.editor).toBeNull(); expect(state.save).not.toHaveBeenCalled()
  state.external({ ...base(workspace), revision: 2, goals: ['真正远端'] })
  await act(() => view.result.current.restore(view.result.current.candidates[0])); expect(view.result.current.editor?.base.revision).toBe(1); expect(view.result.current.fields?.goals).toEqual(['离线保留 🧠é']); expect(view.result.current.conflict).toBe(true); expect(state.save).not.toHaveBeenCalled()
})
test('a late profile read cannot populate another workspace or reopen a paused projection', async () => {
  const first = fixture('workspace_profile_first'), second = fixture('workspace_profile_second')
  let resolve!: (value: LearnerProfile) => void
  first.read.mockImplementationOnce(() => new Promise(value => { resolve = value }))
  const view = renderHook(({ workspace, paused, port }) => useProfile(workspace, paused, port), { initialProps: { workspace: 'workspace_profile_first', paused: false, port: first.port } })
  view.rerender({ workspace: 'workspace_profile_second', paused: false, port: second.port }); await waitFor(() => expect(view.result.current.remote?.workspace_id).toBe('workspace_profile_second'))
  await act(async () => resolve(base('workspace_profile_first'))); expect(view.result.current.remote?.workspace_id).toBe('workspace_profile_second')
  view.rerender({ workspace: 'workspace_profile_second', paused: true, port: second.port }); expect(second.save).not.toHaveBeenCalled()
})

test('two pages entering an unchanged profile cannot leave a permanent unselectable conflict', async () => {
  const workspace = 'workspace_clean_branches', profile = base(workspace)
  const port = { read: vi.fn(async () => structuredClone(profile)), save: vi.fn() }
  const a = renderHook(() => useProfile(workspace, false, port))
  const b = renderHook(() => useProfile(workspace, false, port))
  await waitFor(() => { expect(a.result.current.safe).toBe(true); expect(b.result.current.safe).toBe(true); expect(a.result.current.remote).not.toBeNull(); expect(b.result.current.remote).not.toBeNull() })
  act(() => { a.result.current.begin(); b.result.current.begin() })
  await waitFor(() => { expect(a.result.current.safe).toBe(true); expect(b.result.current.safe).toBe(true) })
  const disk = (await profileStore.load(workspace))[profileDraftKey]
  expect(disk).toBeDefined()
  // A clean baseline may be ignored or offered as an explicit recoverable choice;
  // it must not disable edit with no selectable candidate and no dirty user data.
  expect(a.result.current.conflicts.length === 0 || a.result.current.candidates.length > 0).toBe(true)
  act(() => a.result.current.edit({ ...a.result.current.fields!, goals: ['Original branch input'] }))
  expect(a.result.current.fields?.goals).toEqual(['Original branch input'])
})

test('a late acknowledged old command cannot erase a newer durable profile candidate after policy resume', async () => {
  const workspace = 'workspace_profile_late_ack'
  let server: LearnerProfile = { workspace_id: workspace, revision: 1, goals: [], goal_concept_ids: [], weekly_minutes: 120, language: 'zh-CN', preferred_difficulty: 'beginner', self_assessments: [] }
  let acknowledge!: (value: LearnerProfile) => void
  const port = { read: vi.fn(async () => structuredClone(server)), save: vi.fn(async (value: ProfileEnvelope) => {
    server = { ...server, ...value.fields, revision: 2, weekly_minutes: Number(value.fields.weekly_minutes), self_assessments: [] }
    return new Promise<LearnerProfile>(resolve => { acknowledge = resolve })
  }) }
  const view = renderHook(({ paused }) => useProfile(workspace, paused, port), { initialProps: { paused: false } })
  await waitFor(() => { expect(view.result.current.safe).toBe(true); expect(view.result.current.remote?.revision).toBe(1) })
  act(() => view.result.current.begin())
  act(() => view.result.current.edit({ ...view.result.current.fields!, goals: ['Original command A'] }))
  await waitFor(() => expect(view.result.current.safe).toBe(true))
  let saving!: Promise<void>
  act(() => { saving = view.result.current.save() })
  await waitFor(() => expect(port.save).toHaveBeenCalledTimes(1))
  view.rerender({ paused: true }); view.rerender({ paused: false })
  await waitFor(() => { expect(view.result.current.busy).toBe(false); expect(view.result.current.remote?.revision).toBe(2) })
  act(() => view.result.current.edit({ ...view.result.current.fields!, goals: ['Newer durable candidate B'] }))
  await waitFor(() => expect(view.result.current.safe).toBe(true))
  act(() => view.result.current.rebase(true))
  await waitFor(() => expect(view.result.current.safe).toBe(true))
  const candidate = JSON.stringify(view.result.current.editor)
  expect((await profileStore.load(workspace))[profileDraftKey].text).toBe(candidate)
  await act(async () => { acknowledge(structuredClone(server)); await saving })
  await waitFor(() => expect(view.result.current.safe).toBe(true))
  expect(view.result.current.fields?.goals).toEqual(['Newer durable candidate B'])
  const disk = (await profileStore.load(workspace))[profileDraftKey]
  expect([disk.text, ...disk.conflicts.map(item => item.text)]).toContain(candidate)
})

test('an already entered clean page must explicitly recover another page durable edit before replacing it', async () => {
  const workspace = 'workspace_profile_claimed_peer', state = fixture(workspace)
  const a = renderHook(() => useProfile(workspace, false, state.port)), b = renderHook(() => useProfile(workspace, false, state.port))
  await waitFor(() => { expect(a.result.current.safe).toBe(true); expect(b.result.current.safe).toBe(true); expect(a.result.current.remote).not.toBeNull(); expect(b.result.current.remote).not.toBeNull() })
  act(() => { a.result.current.begin(); b.result.current.begin() })
  await waitFor(() => { expect(a.result.current.safe).toBe(true); expect(b.result.current.safe).toBe(true) })
  act(() => a.result.current.edit({ ...a.result.current.fields!, goals: ['Another page actual edit'] }))
  await waitFor(() => { expect(a.result.current.safe).toBe(true); expect(b.result.current.needsRecovery).toBe(true) })
  const original = JSON.stringify(a.result.current.editor)
  act(() => b.result.current.edit({ ...b.result.current.fields!, goals: ['Must not silently replace'] }))
  expect(b.result.current.fields?.goals).toEqual([])
  expect(b.result.current.candidates.some(candidate => candidate.text === original)).toBe(true)
  a.unmount()
  await act(() => b.result.current.restore(b.result.current.candidates.find(candidate => candidate.text === original)!))
  expect(b.result.current.fields?.goals).toEqual(['Another page actual edit'])
  act(() => b.result.current.edit({ ...b.result.current.fields!, goals: ['Explicitly recovered and edited'] }))
  await waitFor(() => expect(b.result.current.safe).toBe(true))
  const durable = (await profileStore.load(workspace))[profileDraftKey]
  expect(durable.text).toBe(JSON.stringify(b.result.current.editor))
  expect(state.save).not.toHaveBeenCalled()
})

test('a delayed acknowledgement of the still-current profile command remains usable after policy resumes', async () => {
  const workspace = 'workspace_profile_current_ack', state = fixture(workspace), actual = state.port.save
  let release!: () => void
  state.port.save = async value => { const response = await actual(value); await new Promise<void>(resolve => { release = resolve }); return response }
  const view = renderHook(({ paused }) => useProfile(workspace, paused, state.port), { initialProps: { paused: false } })
  await waitFor(() => { expect(view.result.current.remote?.revision).toBe(1); expect(view.result.current.safe).toBe(true) })
  act(() => view.result.current.begin()); act(() => view.result.current.edit({ ...view.result.current.fields!, goals: ['Same command before policy pause'] }))
  await waitFor(() => expect(view.result.current.safe).toBe(true))
  let saving!: Promise<void>; act(() => { saving = view.result.current.save() })
  await waitFor(() => expect(state.current().revision).toBe(2))
  view.rerender({ paused: true }); view.rerender({ paused: false })
  await waitFor(() => expect(view.result.current.remote?.revision).toBe(2))
  await act(async () => { release(); await saving })
  await waitFor(() => expect(view.result.current.safe).toBe(true))
  expect(view.result.current.editor?.acknowledged?.revision).toBe(2)
  expect(view.result.current.changed).toBe(false)
  expect((await profileStore.load(workspace))[profileDraftKey].text).toBe(JSON.stringify(view.result.current.editor))
})
