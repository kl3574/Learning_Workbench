import 'fake-indexeddb/auto'
import { Profiler } from 'react'
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { DraftStore, type DraftSaveResult } from '../../workbench/DraftStore'
import { RouteEditor } from './RouteEditor'
import { decodeRouteDraft, routeStore } from './routeDrafts'

vi.mock('./routeChoices', () => ({ readRouteChoices: async () => [] }))
afterEach(cleanup)

function deferred() { let release!: () => void; const promise = new Promise<void>(done => { release = done }); return { promise, release } }

const cases = ['own_save_first', 'own_load_first', 'other_newer_primary', 'other_same_revision_conflict', 'other_newer_primary_without_new_edit'] as const
for (const scenario of cases) test(`real route input and conflict candidates survive ${scenario} delivery`, async () => {
  const concurrent = scenario.startsWith('other_'), saveFirst = scenario === 'own_save_first', noNewEdit = scenario === 'other_newer_primary_without_new_edit'
  const workspace = `workspace_route_input_${scenario}`
  const firstDelivery = deferred(), reloadDelivery = deferred(), reloadDelivered = deferred(), secondWrite = deferred(), secondStarted = deferred()
  const originalSave = routeStore.save.bind(routeStore), originalLoad = routeStore.load.bind(routeStore)
  let intercepted = false, released = false, calls = 0, initial: DraftSaveResult | null = null
  const save = vi.spyOn(routeStore, 'save').mockImplementation(async (...args) => {
    calls++
    if (calls === 1) { intercepted = true; initial = await originalSave(...args); await firstDelivery.promise; return initial }
    if (calls === 2) { secondStarted.release(); await secondWrite.promise }
    return originalSave(...args)
  })
  const load = vi.spyOn(routeStore, 'load').mockImplementation(async (...args) => {
    const actual = await originalLoad(...args)
    if (intercepted && !released) { await reloadDelivery.promise; reloadDelivered.release() }
    return actual
  })
  const other = new DraftStore({ name: 'learning-workbench.route-drafts.v1' })
  const onState = vi.fn(); let commits = 0
  render(<Profiler id="route-input" onRender={() => { commits++ }}><RouteEditor workspace={workspace} initial={null} paused={false} onState={onState} saved={() => {}} /></Profiler>)
  try {
    await waitFor(() => expect((screen.getByRole('button', { name: '填写新路线' }) as HTMLButtonElement).disabled).toBe(false))
    fireEvent.click(screen.getByRole('button', { name: '填写新路线' }))
    await waitFor(() => expect(initial).not.toBeNull())
    if (!noNewEdit) fireEvent.change(screen.getByLabelText('路线名称'), { target: { value: '同一本页的较新路线' } })
    const beforeDelivery = commits
    await act(async () => {
      released = true
      if (saveFirst) { firstDelivery.release(); await secondStarted.promise; reloadDelivery.release() }
      else { reloadDelivery.release(); await reloadDelivered.promise }
    })
    // The second store invocation proves the first save ACK was consumed;
    // for load-first, observe its committed render while the ACK is still held.
    if (saveFirst) expect(calls).toBe(2)
    else { expect(calls).toBe(1); expect(commits).toBeGreaterThan(beforeDelivery) }
    const goal = screen.getByLabelText('路线学习目标') as HTMLTextAreaElement
    if (concurrent) {
      const record = Object.values(await originalLoad(workspace))[0]
      const envelope = decodeRouteDraft(record.text, workspace)
      const remote = { ...envelope, command_id: 'route_command_other_page', candidate: { ...envelope.candidate, title: '另一个页面的真实候选', goal: '远端草稿目标' } }
      const result = await other.save(workspace, record.objectId, JSON.stringify(remote), scenario === 'other_same_revision_conflict' ? record.revision - 1 : record.revision)
      expect(result.kind).toBe(scenario === 'other_same_revision_conflict' ? 'conflict' : 'saved')
      act(() => window.dispatchEvent(new Event('focus')))
      await waitFor(() => expect(screen.getByText('远端草稿目标')).toBeTruthy())
      expect(goal.closest('fieldset')?.disabled).toBe(true)
      await act(async () => { firstDelivery.release(); if (!noNewEdit) await secondStarted.promise })
      if (noNewEdit) {
        expect(onState.mock.calls.at(-1)?.[0].safe).toBe(false)
        const closing = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(closing); expect(closing.defaultPrevented).toBe(true)
      }
      expect(screen.queryByText('远端草稿目标')).not.toBeNull()
      expect(goal.closest('fieldset')?.disabled).toBe(true)
      await act(async () => { secondWrite.release() })
      await waitFor(async () => {
        const disk = (await originalLoad(workspace))[record.objectId]
        const candidates = [disk.text, ...disk.conflicts.map(item => item.text)].map(text => decodeRouteDraft(text, workspace))
        expect(candidates.some(item => item.candidate.goal === '远端草稿目标')).toBe(true)
        expect(candidates.some(item => item.candidate.title === (noNewEdit ? '' : '同一本页的较新路线'))).toBe(true)
      })
      expect(goal.closest('fieldset')?.disabled).toBe(true)
      expect(screen.getByText('本机路线候选')).toBeTruthy()
    } else {
      expect(goal.closest('fieldset')?.disabled).toBe(false)
      fireEvent.change(goal, { target: { value: '下一输入必须保留' } })
      await act(async () => { firstDelivery.release(); secondWrite.release() })
      await waitFor(async () => {
        const disk = Object.values(await originalLoad(workspace))[0]
        expect(decodeRouteDraft(disk.text, workspace).candidate.goal).toBe('下一输入必须保留')
        expect(disk.conflicts).toEqual([])
      })
      expect(goal.value).toBe('下一输入必须保留')
    }
  } finally {
    await act(async () => { released = true; reloadDelivery.release(); firstDelivery.release(); secondWrite.release() })
    await waitFor(() => expect(screen.getByText('本机路线草稿存储可用')).toBeTruthy())
    save.mockRestore(); load.mockRestore(); await other.close()
  }
})
