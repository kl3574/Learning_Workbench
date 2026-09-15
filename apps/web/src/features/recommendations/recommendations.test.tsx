import 'fake-indexeddb/auto'
import { act, cleanup, fireEvent, render, renderHook, screen, waitFor, within } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { RecommendationPage } from '../../../../../packages/contracts/generated/api-types'
import { useRecommendations, type RecommendationQuery } from './useRecommendations'
import { navigationHref, validateNavigation } from './recommendationModel'
import { RecommendationsPanel } from './RecommendationsPanel'
import { decisionFixture, testPage, testRecommendation } from './testFixtures'
afterEach(cleanup)
test('a delayed list cannot leak subject sources after a policy pause or replace a different course scope', async () => {
  let resolve!: (value: RecommendationPage) => void
  const list = vi.fn(async (_query: RecommendationQuery) => new Promise<RecommendationPage>(done => { resolve = done })), port = { list }
  const view = renderHook(({ paused, course }) => useRecommendations('workspace_list_policy', paused, course, port), { initialProps: { paused: false, course: undefined as string | undefined } })
  await waitFor(() => expect(list).toHaveBeenCalledTimes(1)); view.rerender({ paused: true, course: undefined }); await act(async () => resolve(testPage())); expect(view.result.current.value).toBeNull()
  list.mockResolvedValue(testPage([testRecommendation('recommendation_second')]))
  view.rerender({ paused: false, course: 'course_b' }); await waitFor(() => expect(view.result.current.value?.items[0].id).toBe('recommendation_second'))
  expect(list.mock.calls.at(-1)?.[0]).toEqual({ course_id: 'course_b' })
})
test('pagination refuses to mix frozen batches and exposes a refreshable error', async () => {
  const first = { ...testPage(), next_cursor: 'server_cursor_first' }, second = { ...testPage([testRecommendation('recommendation_next')]), snapshot_id: 'snapshot_other' }
  const port = { list: vi.fn().mockResolvedValueOnce(first).mockResolvedValueOnce(second) }
  const view = renderHook(() => useRecommendations('workspace_list_pages', false, undefined, port))
  await waitFor(() => expect(view.result.current.value?.next_cursor).toBe('server_cursor_first'))
  await act(() => view.result.current.more()); expect(view.result.current.value).toBeNull(); expect(view.result.current.error).toContain('同一冻结批次'); expect(port.list.mock.calls[1][0]).toEqual({ cursor: 'server_cursor_first' })
})
test('opening either real parent chain is explicit, preserves all full refs and does not accept the recommendation', async () => {
  const item = testRecommendation(), state = decisionFixture(item), port = { ...state.port, list: vi.fn(async () => testPage([item])) }, open = vi.fn()
  render(<RecommendationsPanel workspace="workspace_panel_navigation" paused={false} course={null} port={port} open={open} onState={() => {}} />)
  await screen.findByRole('article', { name: `学习建议：${item.target_title}` }); await screen.findByText('本机推荐候选存储可用')
  expect(screen.getByText('此目标有多个真实教材父链，请明确选择从哪条路径打开。')).toBeTruthy()
  const button = screen.getByRole('button', { name: '从教材 course_b · r2 / 小节 lesson_original · r1 打开材料' })
  expect(screen.queryByRole('link')).toBeNull(); expect(button.getAttribute('href')).toBeNull(); expect(new URL(navigationHref(item.navigation_options[1]), 'http://localhost').searchParams.get('reader')).toBe(JSON.stringify({ course: item.navigation_options[1].course_ref, lesson: item.target_ref }))
  fireEvent.click(button); await waitFor(() => expect(open).toHaveBeenCalledExactlyOnceWith(item.navigation_options[1])); expect(state.inspect).toHaveBeenCalledExactlyOnceWith(item.id); expect(state.save).not.toHaveBeenCalled(); expect(state.current().decision).toBe('pending')
  expect(screen.getByText(/预计用时：未知/)).toBeTruthy(); expect(screen.getByText(/复习提醒间隔 3 天 · 未校准/)).toBeTruthy(); expect(screen.getByText(/尚未审核/)).toBeTruthy()
})
test('acceptance saves only after the explicit command action and never opens content; policy hides the whole source projection', async () => {
  const state = decisionFixture(), port = { ...state.port, list: vi.fn(async () => testPage([state.current()])) }, open = vi.fn(), props = { workspace: 'workspace_panel_accept', course: null, port, open, onState: vi.fn() }
  const view = render(<RecommendationsPanel {...props} paused={false} />)
  await screen.findByRole('button', { name: '接受此建议' }); await screen.findByText('本机推荐候选存储可用')
  fireEvent.click(screen.getByRole('button', { name: '接受此建议' })); expect(state.save).not.toHaveBeenCalled(); expect(open).not.toHaveBeenCalled()
  const editor = screen.getByRole('region', { name: '推荐决定编辑' })
  fireEvent.change(within(editor).getByRole('textbox'), { target: { value: '我选择先读' } }); await waitFor(() => expect(within(editor).getByRole('button', { name: '保存推荐决定' }).hasAttribute('disabled')).toBe(false)); fireEvent.click(within(editor).getByRole('button', { name: '保存推荐决定' }))
  await waitFor(() => expect(state.current().decision).toBe('accepted')); expect(open).not.toHaveBeenCalled()
  view.rerender(<RecommendationsPanel {...props} paused />); expect(screen.queryByText('合成建议目标 · 记录选择')).toBeNull(); expect(screen.queryByText('合成单测目标')).toBeNull(); expect(screen.queryByRole('article')).toBeNull()
})
test('an actual empty projection warning remains visible without fabricated local targets or a personalized score', async () => {
  const state = decisionFixture(), empty: RecommendationPage = { ...testPage([]), warnings: [{ code: 'NO_LOCAL_MATERIAL', severity: 'warning', message: '缺少对应教材：已记录目标概念没有匹配的本地内容。', locator: 'concept_original' }] }
  render(<RecommendationsPanel workspace="workspace_panel_missing" paused={false} course={null} port={{ ...state.port, list: vi.fn(async () => empty) }} open={vi.fn()} onState={() => {}} />)
  await screen.findByText(/缺少对应教材/); expect(screen.queryByRole('article')).toBeNull(); expect(screen.queryByRole('link')).toBeNull(); expect(screen.queryByText(/掌握.*%/)).toBeNull()
})
test('an exact target mismatch or invalid full parent ref fails before constructing navigation', () => {
  const item = testRecommendation()
  expect(() => validateNavigation({ ...item, target_ref: { ...item.target_ref, revision: 2 } })).toThrow('原精确目标')
  expect(() => validateNavigation({ ...item, navigation_options: [{ kind: 'reader', course_ref: { ...item.navigation_options[0].course_ref!, sha256: 'bad' }, lesson_ref: item.target_ref, block_ref: null }] })).toThrow('精确引用')
})
test('authoritatively stale navigation disables the old batch while keeping its source metadata readable', async () => {
  const item = testRecommendation(), state = decisionFixture(item), open = vi.fn()
  const port = { ...state.port, list: vi.fn(async () => testPage([item])), inspect: vi.fn(async () => ({ ...testPage([{ ...item, staleness: 'stale' }]), projection_state: 'stale' as const })) }
  render(<RecommendationsPanel workspace="workspace_panel_stale_open" paused={false} course={null} port={port} open={open} onState={() => {}} />)
  await screen.findByText('本机推荐候选存储可用'); const button = await screen.findByRole('button', { name: '从教材 course_b · r2 / 小节 lesson_original · r1 打开材料' })
  fireEvent.click(button); await screen.findByText(/尚未打开推荐内容。推荐依据已过期/)
  expect(button.hasAttribute('disabled')).toBe(true); expect(screen.getByRole('button', { name: '接受此建议' }).hasAttribute('disabled')).toBe(true); expect(screen.getByText(/历史推荐依据已过期/)).toBeTruthy(); expect(screen.getByText('核对推荐原因与真实来源')).toBeTruthy(); expect(open).not.toHaveBeenCalled(); expect(screen.queryByRole('link')).toBeNull()
})
