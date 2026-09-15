import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import type { SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import { useWorkspacePolicy } from './useWorkspacePolicy'

const api = vi.hoisted(() => ({ request: vi.fn(), listeners: new Set<() => void>() }))
vi.mock('../../api/client', () => ({
  request: api.request,
  subscribeSessionAccess: (listener: () => void) => { api.listeners.add(listener); return () => { api.listeners.delete(listener) } },
}))
const session = (workspace = 'workspace_policy', independentId: string | null = null): SessionResponse => ({ workspace_id: workspace, role: 'learner', csrf_token: 'synthetic-policy-test', active_independent_attempt_id: independentId })
let replies: { resolve: (value: SessionResponse) => void; reject: (reason: Error) => void }[]
beforeEach(() => {
  vi.useFakeTimers(); replies = []; api.request.mockReset()
  api.request.mockImplementation(() => new Promise<SessionResponse>((resolve, reject) => { replies.push({ resolve, reject }) }))
})
afterEach(() => { cleanup(); api.listeners.clear(); vi.useRealTimers() })

test('a slow policy response can establish access even after multiple background poll ticks', async () => {
  const view = renderHook(() => useWorkspacePolicy('workspace_policy'))
  expect(view.result.current.known).toBe(false)
  await act(() => vi.advanceTimersByTimeAsync(4000))
  await act(async () => { replies[0].resolve(session()) })
  expect(view.result.current.known).toBe(true)
  expect(view.result.current.independentId).toBeNull()
  await act(() => vi.advanceTimersByTimeAsync(2000))
  await act(async () => { replies.at(-1)!.resolve(session('workspace_policy', 'attempt_other_profile')) })
  expect(view.result.current.independentId).toBe('attempt_other_profile')
})

test.each(['access', 'focus', 'refresh'])('%s invalidation supersedes a pending read and cannot be undone by its late response', async kind => {
  const view = renderHook(() => useWorkspacePolicy('workspace_policy'))
  act(() => {
    if (kind === 'access') api.listeners.forEach(listener => listener())
    else if (kind === 'focus') window.dispatchEvent(new Event('focus'))
    else view.result.current.refresh()
  })
  expect(replies).toHaveLength(2)
  await act(async () => { replies[0].resolve(session()) })
  expect(view.result.current.known).toBe(false)
  await act(() => vi.advanceTimersByTimeAsync(4000))
  await act(async () => { replies[1].resolve(session('workspace_policy', 'attempt_active')) })
  expect(view.result.current.known).toBe(true)
  expect(view.result.current.independentId).toBe('attempt_active')
})

test('a failed poll removes known access and a later successful poll restores the actual policy', async () => {
  const view = renderHook(() => useWorkspacePolicy('workspace_policy'))
  await act(async () => { replies[0].resolve(session()) })
  expect(view.result.current.known).toBe(true)
  await act(() => vi.advanceTimersByTimeAsync(2000))
  await act(async () => { replies[1].reject(new Error('Synthetic connection interrupted')) })
  expect(view.result.current.known).toBe(false)
  expect(view.result.current.error).toBe('Synthetic connection interrupted')
  await act(() => vi.advanceTimersByTimeAsync(2000))
  await act(async () => { replies[2].resolve(session('workspace_policy', 'attempt_recovered')) })
  expect(view.result.current.known).toBe(true)
  expect(view.result.current.independentId).toBe('attempt_recovered')
  expect(view.result.current.error).toBe('')
})

test('a hung older read does not prevent a subsequent poll from observing restricted access', async () => {
  const view = renderHook(() => useWorkspacePolicy('workspace_policy'))
  await act(() => vi.advanceTimersByTimeAsync(2000))
  expect(replies).toHaveLength(2)
  await act(async () => { replies[1].resolve(session('workspace_policy', 'attempt_newer')) })
  expect(view.result.current.known).toBe(true)
  expect(view.result.current.independentId).toBe('attempt_newer')
  await act(async () => { replies[0].resolve(session()) })
  expect(view.result.current.independentId).toBe('attempt_newer')
})

test('an older successful read cannot undo a newer policy read failure', async () => {
  const view = renderHook(() => useWorkspacePolicy('workspace_policy'))
  await act(() => vi.advanceTimersByTimeAsync(2000))
  expect(replies).toHaveLength(2)
  await act(async () => { replies[1].reject(new Error('Synthetic session revoked')) })
  await act(async () => { replies[0].resolve(session()) })
  expect(view.result.current.known).toBe(false)
  expect(view.result.current.error).toBe('Synthetic session revoked')
})

test('late responses cannot cross workspace or survive unmount and all observers are released', async () => {
  const view = renderHook(({ workspace }) => useWorkspacePolicy(workspace), { initialProps: { workspace: 'workspace_policy' } })
  view.rerender({ workspace: 'workspace_other' })
  await act(async () => { replies[0].resolve(session()) })
  expect(view.result.current.known).toBe(false)
  await act(async () => { replies[1].resolve(session('workspace_other', 'attempt_other')) })
  expect(view.result.current.independentId).toBe('attempt_other')
  await act(() => vi.advanceTimersByTimeAsync(2000))
  view.unmount()
  await act(async () => { replies[2].resolve(session('workspace_other')) })
  const requestsBefore = replies.length
  await act(() => vi.advanceTimersByTimeAsync(6000))
  expect(replies).toHaveLength(requestsBefore)
  expect(api.listeners.size).toBe(0)
})
