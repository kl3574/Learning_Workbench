import type { ContentRef, GradingResult } from '../../../../../packages/contracts/generated/types'
import { sameRef } from '../reader/target'
export function validateGrading<T extends GradingResult>(result: T, attempt: string, questions: ContentRef[]): T {
  if (result.attempt_id !== attempt || !Number.isSafeInteger(result.grading_revision) || result.grading_revision < 1 || result.items.length !== questions.length) throw new Error('评分结果与当前测试或完整题目集合不一致，未显示混合结果。')
  const seen = new Set<string>()
  for (const item of result.items) {
    if (seen.has(item.question_ref.id) || !questions.some(ref => sameRef(ref, item.question_ref)) || !Number.isFinite(item.max_score) || item.max_score <= 0 || item.status === 'needs_review' && item.score != null || item.status === 'graded' && (item.score == null || !Number.isFinite(item.score) || item.score < 0 || item.score > item.max_score)) throw new Error('评分项引用或分数不符合冻结题目与待复核约束。')
    seen.add(item.question_ref.id)
  }
  if ((result.items.some(item => item.status === 'needs_review') ? 'needs_review' : 'graded') !== result.status) throw new Error('评分汇总与逐题状态不一致，未推测总分。')
  return result
}
export function gradingTotals(result: GradingResult) {
  const graded = result.items.filter(item => item.status === 'graded')
  const score = graded.reduce((sum, item) => sum + item.score!, 0), maximum = graded.reduce((sum, item) => sum + item.max_score, 0)
  const overflow = !Number.isFinite(score) || !Number.isFinite(maximum)
  return { graded: graded.length, pending: result.items.length - graded.length, score: overflow ? null : score, maximum: overflow ? null : maximum, overflow, complete: graded.length === result.items.length }
}
