import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { GradingSummary } from './GradingSummary'
import { gradingResult } from './grading.testdata'
vi.mock('../../shared/Markdown', () => ({ Markdown: ({ children }: { children: string }) => <p>{children}</p> }))
afterEach(cleanup)
test('pending score is displayed as unknown rather than zero or a mastery claim', async () => { render(<GradingSummary result={gradingResult()} />); expect(screen.getByRole('region', { name: '当前评分结果' }).textContent).toContain('暂无分数，不将未知项计为零分'); expect(screen.getByText(/独立证据资格尚未评估/)).toBeTruthy(); expect(screen.queryByText(/总分/)).toBeNull(); await screen.findByText('合成参考未审，不能确定分数。') })
test('overflowing totals retain finite per-item scores and show an explicit aggregation limit', async () => { const value = gradingResult(); value.status = 'graded'; value.items = [0, 1].map(index => ({ question_ref: { ...value.items[0].question_ref, id: `question_synthetic_${index}` }, status: 'graded', score: 1e308, max_score: 1e308, feedback_markdown: '原创边界输入' })); render(<GradingSummary result={value} />); expect(screen.getByText(/汇总超出数值范围/)).toBeTruthy(); expect(screen.getAllByRole('heading', { level: 3 }).every(element => element.textContent?.includes('1e+308'))).toBe(true); expect(document.body.textContent).not.toContain('Infinity'); await screen.findAllByText('原创边界输入') })
