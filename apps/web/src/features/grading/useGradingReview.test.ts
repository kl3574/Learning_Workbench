import { expect, test } from 'vitest'
import { newReview } from './reviewDrafts'
import { reviewRequest } from './useGradingReview'
import { gradingResult, gradingSnapshot } from './grading.testdata'
function draft() { const value = newReview('workspace_original', gradingSnapshot().assessment_ref, gradingResult()); value.reason = '原创复核界面测试'; value.items[0] = { question_id: 'question_original', selected: true, score: '1.5', feedback_markdown: '明确逐项依据' }; return value }
test('converts explicit finite score and only selected questions using the frozen grading baseline', () => { expect(reviewRequest(draft())).toEqual({ expected_grading_revision: 1, reason: '原创复核界面测试', item_reviews: [{ question_id: 'question_original', score: 1.5, feedback_markdown: '明确逐项依据' }] }) })
test.each(['', ' ', 'NaN', 'Infinity', '-1', '3', '0x1', '1/2', '1e999'])('does not coerce invalid author input %s into an accepted score', score => { const value = draft(); value.items[0].score = score; expect(() => reviewRequest(value)).toThrow() })
test('requires a selected item and a nonblank signed reason and item feedback', () => { const value = draft(); value.items[0].selected = false; expect(() => reviewRequest(value)).toThrow(); value.items[0].selected = true; value.reason = ' '; expect(() => reviewRequest(value)).toThrow(); value.reason = '原因'; value.items[0].feedback_markdown = ' '; expect(() => reviewRequest(value)).toThrow() })
