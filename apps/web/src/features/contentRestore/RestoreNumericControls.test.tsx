import 'fake-indexeddb/auto'
import { cleanup, render, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
const control = vi.hoisted(() => ({ controlReady: true, busy: false, commands: [] as { kind: 'cancel'; command_id: string; ack: null; rejection: null }[] }))
vi.mock('../authoring/useAuthoring', () => ({ useAuthoring: () => ({ ...control, jobs: [], cursor: null, error: '', refresh: vi.fn(), cancel: vi.fn() }) }))
import { RestoreNumericPanel } from './RestoreNumericPanel'
import { reviewSession } from '../draftReview/reviewFixtures'
import { numericSnapshot, numericPreview, numericDecisionReceipt } from './restoreNumericFixtures'
import type { RestoreNumericPort } from './restoreNumericClient'
import { restoreNumericCommandStore } from './restoreNumericStore'
afterEach(async () => { cleanup(); await restoreNumericCommandStore.close() })
test.each(['busy', 'unread', 'unknown_cancel', 'safe'] as const)('numeric safety controls preserve parent closure and unload protection: %s', async mode => {
  const workspace = `workspace_${crypto.randomUUID()}`, changed = vi.fn()
  control.busy = mode === 'busy'; control.controlReady = mode !== 'unread'; control.commands = mode === 'unknown_cancel' ? [{ kind: 'cancel', command_id: 'cancel_original', ack: null, rejection: null }] : []
  const port: RestoreNumericPort = { session: async () => reviewSession(workspace), draft: async () => numericSnapshot, current: async () => numericSnapshot.base_ref,
    preview: async () => numericPreview, check: async () => numericPreview, decide: async () => numericDecisionReceipt }
  render(<RestoreNumericPanel workspace={workspace} blockId={numericSnapshot.source_ref.id} draft={null} paused onState={changed} port={port} />)
  await waitFor(() => expect(changed.mock.lastCall?.[0]).toEqual({ dirty: mode === 'unknown_cancel', safe: !['busy', 'unread'].includes(mode), closeSafe: !['busy', 'unread'].includes(mode) }))
  const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event)
  expect(event.defaultPrevented).toBe(mode !== 'safe')
})
