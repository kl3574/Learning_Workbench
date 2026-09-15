import { act, cleanup, renderHook } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { RecommendationPage } from '../../../../../packages/contracts/generated/api-types'
import { useRecommendationNavigation } from './useRecommendationNavigation'
import { navigationLabel, validateNavigation } from './recommendationModel'
import { testPage, testRecommendation, testRef } from './testFixtures'
afterEach(cleanup)
test('a current-looking old row cannot open after the authoritative historical GET marks its basis stale', async () => {
  const item = testRecommendation(), open = vi.fn(), port = { inspect: vi.fn(async () => ({ ...testPage([{ ...item, staleness: 'stale' }]), projection_state: 'stale' as const })) }
  const view = renderHook(() => useRecommendationNavigation('workspace_navigation_stale', false, true, 'batch_a', port, open))
  await act(() => view.result.current.navigate(item, item.navigation_options[0])); expect(port.inspect).toHaveBeenCalledExactlyOnceWith(item.id); expect(open).not.toHaveBeenCalled(); expect(view.result.current.error).toContain('推荐依据已过期，请查看最新推荐'); expect(view.result.current.error).not.toContain('归档'); expect(view.result.current.staleIds).toEqual([item.id])
})
test('the selected full parent chain must still exist; no fallback to another course or lesson', async () => {
  const item = testRecommendation(), open = vi.fn(), port = { inspect: vi.fn(async () => testPage([{ ...item, navigation_options: [item.navigation_options[0]] }])) }
  const view = renderHook(() => useRecommendationNavigation('workspace_navigation_chain', false, true, 'batch_a', port, open))
  await act(() => view.result.current.navigate(item, item.navigation_options[1])); expect(open).not.toHaveBeenCalled(); expect(view.result.current.error).toContain('所选教材父链已变化')
})
test.each(['workspace', 'policy', 'unsafe', 'batch', 'unmount'])('a delayed navigation GET cannot open after %s changes even if the guard later clears', async kind => {
  const item = testRecommendation(), open = vi.fn(); let resolve!: (page: RecommendationPage) => void
  const port = { inspect: vi.fn(async () => new Promise<RecommendationPage>(done => { resolve = done })) }
  const initial = { workspace: 'workspace_navigation_owner', paused: false, safe: true, context: 'batch_a' }
  const view = renderHook(({ workspace, paused, safe, context }) => useRecommendationNavigation(workspace, paused, safe, context, port, open), { initialProps: initial })
  let pending!: Promise<void>; act(() => { pending = view.result.current.navigate(item, item.navigation_options[0]) }); expect(view.result.current.busy).toBe(true); expect(open).not.toHaveBeenCalled()
  if (kind === 'unmount') view.unmount()
  else { view.rerender({ ...initial, ...(kind === 'workspace' ? { workspace: 'workspace_navigation_other' } : kind === 'policy' ? { paused: true } : kind === 'unsafe' ? { safe: false } : { context: 'batch_b' }) }); view.rerender(initial) }
  await act(async () => { resolve(testPage([item])); await pending }); expect(open).not.toHaveBeenCalled()
})
test('four valid parent chains expose four distinct choices including different lessons in the same course', () => {
  const item = testRecommendation(), block = testRef('block', 'block_shared'), courseA = testRef('course', 'course_a'), courseB = testRef('course', 'course_b'), lessonA = testRef('lesson', 'lesson_a'), lessonB = testRef('lesson', 'lesson_b')
  const options = [courseA, courseB].flatMap(course => [lessonA, lessonB].map(lesson => ({ kind: 'reader' as const, course_ref: course, lesson_ref: lesson, block_ref: block })))
  expect(validateNavigation({ ...item, target_ref: block, navigation_options: options }).navigation_options).toHaveLength(4); expect(new Set(options.map(navigationLabel)).size).toBe(4)
})
