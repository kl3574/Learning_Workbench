import { gradingResult, gradingSnapshot } from '../grading/grading.testdata'
import type { AssessmentGradingResult, GradeHistoryEntry } from '../../../../../packages/contracts/generated/api-types'
import type { ContentRef } from '../../../../../packages/contracts/generated/types'
export const concept: ContentRef = { entity: 'concept', id: 'concept_original', revision: 1, sha256: 'c'.repeat(64) }
export const course: ContentRef = { entity: 'course', id: 'course_original', revision: 1, sha256: 'd'.repeat(64) }
export const lesson: ContentRef = { entity: 'lesson', id: 'lesson_original', revision: 1, sha256: 'e'.repeat(64) }
export const block: ContentRef = { entity: 'block', id: 'block_original', revision: 1, sha256: 'f'.repeat(64) }
export function reviewSnapshot() { const value = gradingSnapshot(); value.preflight.target_concept_refs = [concept]; value.preflight.course_refs = [course]; return value }
export function historyEntry(revision = 1, score: number | null = null): GradeHistoryEntry {
  const value = gradingResult().history[0]; value.grading_revision = revision; value.status = score === null ? 'needs_review' : 'graded'
  value.items[0] = { ...value.items[0], score, status: value.status, concept_refs: [concept], evidence_ids: [`evidence_original_${revision}`], reason_codes: score === null ? ['ANSWER_UNREVIEWED', 'GRADE_UNRESOLVED'] : ['ANSWER_UNREVIEWED'] }
  return value
}
export function reviewResult(): AssessmentGradingResult {
  const value = gradingResult(); value.grading_revision = 2; value.status = 'graded'; value.items[0] = { ...value.items[0], score: 1, status: 'graded' }; value.history = [historyEntry(), historyEntry(2, 1)]; value.eligibility_status = 'evaluated'
  value.review_materials[0].materials = [{ course_ref: course, lesson_ref: lesson, block_ref: block, concept_refs: [concept], title: '原创合成的精确教材块' }]
  value.current_review_policy = { tutor_scope: 'academic', allow_materials: true, allow_web: false }; return value
}
