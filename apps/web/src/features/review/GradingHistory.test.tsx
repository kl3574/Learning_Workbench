import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { GradingHistory } from './GradingHistory'
import { historyEntry } from './review.testdata'
afterEach(cleanup); beforeEach(() => localStorage.clear())
test('restores a selected actual old version across remount and does not silently switch when another grade arrives', async () => {
  const selected = vi.fn(), entries = [historyEntry(), historyEntry(2, 1)], props = { workspace: 'workspace_original', tabId: 'tab_review', history: entries, questionId: 'question_original', selected }
  const first = render(<GradingHistory {...props} />)
  fireEvent.change(screen.getByLabelText('选择评分版本'), { target: { value: '1' } }); expect(screen.getByText(/本题在版本 1/).textContent).toContain('分数为空'); first.unmount()
  const second = render(<GradingHistory {...props} />); expect((screen.getByLabelText('选择评分版本') as HTMLSelectElement).value).toBe('1')
  second.rerender(<GradingHistory {...props} history={[...entries, historyEntry(3, 2)]} />); expect((screen.getByLabelText('选择评分版本') as HTMLSelectElement).value).toBe('1')
  fireEvent.change(screen.getByLabelText('对照评分版本'), { target: { value: '3' } }); expect(screen.getByRole('table').textContent).toContain('2 / 2'); expect(screen.getByRole('table').textContent).toContain('分数为空')
  await waitFor(() => expect(selected.mock.lastCall?.[0].grading_revision).toBe(1)); expect(localStorage.getItem('learning-workbench.workspace_original.tab_review.review-grade.v1')).toBe('1')
})
test('a saved revision absent from the complete response is visible as unavailable until explicit selection', () => { localStorage.setItem('learning-workbench.workspace_original.tab_review.review-grade.v1', '9'); render(<GradingHistory workspace="workspace_original" tabId="tab_review" history={[historyEntry()]} questionId="question_original" selected={() => {}} />); expect(screen.getByRole('alert').textContent).toContain('未自动换成最新版本'); expect(screen.queryByText(/本题在版本/)).toBeNull(); fireEvent.change(screen.getByLabelText('选择评分版本'), { target: { value: '1' } }); expect(screen.queryByRole('alert')).toBeNull() })
test('evidence facts distinguish open-book mode, past exposure and unresolved scores without asserting actual assisted use', () => { const entry = historyEntry(); entry.items[0].independence = 'unknown'; entry.items[0].freshness = 'repeated'; entry.items[0].reason_codes = ['MODE_OPEN_BOOK', 'PREVIOUSLY_SEEN', 'GRADE_UNRESOLVED']; render(<GradingHistory workspace="workspace_original" tabId="tab_modes" history={[entry]} questionId="question_original" selected={() => {}} />); const facts = screen.getByRole('region', { name: '本题证据资格' }); expect(facts.textContent).toContain('开卷模式'); expect(facts.textContent).toContain('本次独立性未确认'); expect(facts.textContent).toContain('历史记录显示此前见过'); expect(facts.textContent).toContain('分数为空，不记作零分') })
