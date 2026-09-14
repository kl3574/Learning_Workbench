import { expect, test } from 'vitest'
import { validateHistory, validateReviewResult, scoreText } from './reviewModel'
import { reviewResult, reviewSnapshot } from './review.testdata'
test('accepts complete real version summaries and preserves unresolved null independently from a later human grade', () => { const result = reviewResult(); expect(validateReviewResult(result, reviewSnapshot())).toBe(result); expect(scoreText(result.history[0].items[0])).toBe('待复核 · 分数为空'); expect(result.history.every(entry => !entry.items[0].eligible)).toBe(true); expect(result.history[1].items[0].reason_codes).toContain('ANSWER_UNREVIEWED') })
test('rejects reordered assignments, nonfinite or divergent latest scores, and an eligible claim from unreviewed content', () => {
  for (const mutate of [
    (value: ReturnType<typeof reviewResult>) => { value.history[0].items[0].question_ref.sha256 = '1'.repeat(64) },
    (value: ReturnType<typeof reviewResult>) => { value.history[1].items[0].score = Number.POSITIVE_INFINITY },
    (value: ReturnType<typeof reviewResult>) => { value.history[1].items[0].score = 0 },
    (value: ReturnType<typeof reviewResult>) => { value.history[1].items[0].eligible = true },
  ]) { const value = reviewResult(); mutate(value); expect(() => validateReviewResult(value, reviewSnapshot())).toThrow() }
})
test('rejects a matching ID with a different concept revision/hash or different frozen material parent', () => {
  const concept = reviewResult(); concept.history[0].items[0].concept_refs = [{ ...concept.history[0].items[0].concept_refs[0], revision: 2 }]; expect(() => validateReviewResult(concept, reviewSnapshot())).toThrow()
  const material = reviewResult(); material.review_materials[0].materials[0].course_ref = { ...material.review_materials[0].materials[0].course_ref, sha256: '9'.repeat(64) }; expect(() => validateReviewResult(material, reviewSnapshot())).toThrow()
})
test('legacy qualification remains explicitly unknown to the old submission, and cannot be upgraded by later scores', () => { const value = reviewResult(); for (const entry of value.history) { entry.qualification_basis = 'history_not_frozen'; entry.items[0].reason_codes.push('HISTORY_PREREQUISITES_NOT_FROZEN') }; expect(validateHistory(value.history, reviewSnapshot())).toHaveLength(2); value.history[1].items[0].reason_codes = ['ANSWER_UNREVIEWED']; expect(() => validateHistory(value.history, reviewSnapshot())).toThrow() })
