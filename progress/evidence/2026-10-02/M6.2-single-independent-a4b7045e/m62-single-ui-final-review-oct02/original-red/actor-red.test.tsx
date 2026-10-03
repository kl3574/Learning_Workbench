import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { getSessionGeneration } from '../../api/client'
import { singlePublicationFixture } from './singlePublicationFixtures'
import { singlePublicationCommandStore } from './singlePublicationCommands'
import { discardSinglePublicationForms, discardSinglePublicationMemory } from './singlePublicationMemory'
import { useSinglePublication } from './useSinglePublication'

let workspace = ''
afterEach(async () => { cleanup(); discardSinglePublicationForms(workspace); discardSinglePublicationMemory(workspace); await singlePublicationCommandStore.close() })
test('independent: newly observed different actor cannot replay same-page original command', async () => {
  const f = singlePublicationFixture(); workspace = f.workspace
  vi.mocked(f.port.publish).mockRejectedValueOnce(new Error('synthetic response unavailable'))
  const hook = renderHook(() => useSinglePublication(f.workspace, false, 'selected', f.port, f.draft.candidate.draft_id))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.prepare(f.draft, f.receipt))
  await act(() => hook.result.current.publish([0, 1]))
  const original = hook.result.current.commands[0], oldGeneration = getSessionGeneration()
  expect(original.ack).toBeNull()
  // Fresh /session truth changed, independently of this page's event counter.
  f.session.actor_session_id = 'session_independently_observed_new_actor'
  await act(() => hook.result.current.refresh())
  expect(hook.result.current.ready).toBe(true)
  expect(getSessionGeneration()).toBe(oldGeneration)
  expect(hook.result.current.canReplay(original)).toBe(false)
  await act(() => hook.result.current.execute(original))
  expect(f.port.publish).toHaveBeenCalledTimes(1)
})
