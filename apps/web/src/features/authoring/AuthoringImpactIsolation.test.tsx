import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
const controls = vi.hoisted(() => ({ ready: true, busy: false, reviewSafe: true }))
vi.mock('./useAuthoring', () => ({ useAuthoring: () => ({ academic: false, ready: controls.ready, busy: controls.busy, jobs: [], commands: [], cursor: null, controlReady: true, refresh: vi.fn() }) }))
vi.mock('../contentImpacts/ContentImpactsPanel', async () => {
  const { useEffect } = await import('react')
  return { ContentImpactsPanel: ({ onState }: { onState(value: { dirty: boolean; safe: boolean; isolated: boolean }): void }) => {
    useEffect(() => { onState({ dirty: true, safe: false, isolated: true }) }, [onState]); return null
  } }
})
vi.mock('../draftReview/ReviewPanel', async () => {
  const { useEffect } = await import('react')
  return { ReviewPanel: ({ onState }: { onState(value: { dirty: boolean; safe: boolean }): void }) => {
    useEffect(() => { onState({ dirty: !controls.reviewSafe, safe: controls.reviewSafe }) }, [onState]); return null
  } }
})
import { AuthoringPanel } from './AuthoringPanel'
afterEach(cleanup)
test.each(['busy', 'unread', 'review_undurable', 'others_safe'] as const)('Content isolated memory does not bypass other Authoring protection: %s', async mode => {
  controls.ready = mode !== 'unread'; controls.busy = mode === 'busy'; controls.reviewSafe = mode !== 'review_undurable'
  const changed = vi.fn(); render(<AuthoringPanel workspace="workspace_isolation" paused={false} currentBlock={null} onState={changed} />)
  fireEvent.click(screen.getByRole('button', { name: '打开候选审核与恢复' })); fireEvent.click(screen.getByRole('button', { name: '打开内容变更影响复核' }))
  await waitFor(() => expect(changed.mock.lastCall?.[0]).toEqual({ dirty: true, safe: false, isolated: mode === 'others_safe' }))
})
