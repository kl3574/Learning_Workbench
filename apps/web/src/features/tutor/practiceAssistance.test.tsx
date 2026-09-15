import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, it, vi } from 'vitest'
import type { PracticeSession } from '../../../../../packages/contracts/generated/api-types'
import type { SavedTab } from '../../../../../packages/contracts/generated/types'
import { PracticeView } from '../practice/PracticeView'
const state = vi.hoisted(() => ({ snapshot: null as PracticeSession | null, hint: vi.fn(), reveal: vi.fn() }))
vi.mock('../practice/usePracticeSession', () => ({ usePracticeSession: () => ({ snapshot: state.snapshot, responses: [], dirty: false, safe: true, localReady: true, busy: false, localConflicts: [], hints: {}, solutions: {}, commandReady: true, hint: state.hint, reveal: state.reveal }) }))
vi.mock('../practice/practiceClient', () => ({ readPracticeTarget: async () => ({ summary: { title: '合成习题' }, course: { title: '合成教材' }, lesson: { title: '合成小节' } }) }))
vi.mock('../practice/QuestionEditor', () => ({ QuestionEditor: () => <p>真实帮助事实显示的 UI seam；本例不重新测作答编辑器。</p> }))
vi.mock('../../shared/Markdown', () => ({ Markdown: ({ children }: { children: string }) => <span>{children}</span> }))
const practice = { entity: 'practice_set' as const, id: 'practice_display', revision: 1, sha256: 'a'.repeat(64) }, lesson = { ...practice, entity: 'lesson' as const, id: 'lesson_display' }, course = { ...practice, entity: 'course' as const, id: 'course_display' }
const target = { practice_ref: practice, lesson_ref: lesson, course_ref: course, session_id: 'practice_session_display' }
const tab: SavedTab = { id: 'tab_display', context: { view_kind: 'practice', active_ref: practice, attached_refs: [course, lesson], selection: null, attempt_id: target.session_id }, pinned: false, scroll_offset: 0 }
afterEach(() => { cleanup(); state.hint.mockClear(); state.reveal.mockClear() })
it('shows the actual per-question AI help fact without converting it into hint level 3 or released solution', async () => {
  const snapshot: PracticeSession = { id: target.session_id, revision: 1, practice_ref: practice, lesson_ref: lesson, questions: [{ id: 'question_display', revision: 1, kind: 'text_blank', stem_markdown: '原创问题', concept_ids: [], skill: 'recall', exposure_group: 'display', max_score: 1, input_instructions: '输入原创答案' }], responses: [], status: 'active', exposure_event_ids: [], assisted: false, results: null, assistance: [{ question_id: 'question_display', highest_hint_level: 0, solution_revealed: false, model_help_received: false }] }
  state.snapshot = snapshot
  const props = { workspace: 'workspace_display', target, tab, reader: vi.fn(), loaded: vi.fn(), onScroll: vi.fn(), onState: vi.fn() }
  const view = render(<PracticeView {...props} />)
  expect(screen.queryByText('已获 AI 帮助；此事实不等于获取规则提示或标准答案。')).toBeNull()
  state.snapshot = { ...snapshot, revision: 2, assisted: true, assistance: [{ ...snapshot.assistance[0], model_help_received: true }] }
  view.rerender(<PracticeView {...props} />)
  expect(screen.getByText('已获 AI 帮助；此事实不等于获取规则提示或标准答案。')).toBeTruthy()
  expect(screen.getByText('此题最高提示等级：0 · 参考解答未展开。明确请求会留下练习辅助记录。')).toBeTruthy()
  await waitFor(() => expect((screen.getByRole('button', { name: '获取 1 级规则提示' }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: '获取 1 级规则提示' }))
  expect(state.hint).toHaveBeenCalledWith('question_display', 1)
  expect(state.reveal).not.toHaveBeenCalled()
  expect(props.onState.mock.lastCall?.[0].assistance).toContain('已获 AI 帮助')
})
