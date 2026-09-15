import { expect, test } from 'vitest'
import type { ContentRef, ViewContext } from '../../../../../packages/contracts/generated/types'
import { retrievalContext } from './retrievalContext'
const course: ContentRef = { entity: 'course', id: 'course_scope', revision: 1, sha256: 'a'.repeat(64) }
const lesson: ContentRef = { entity: 'lesson', id: 'lesson_scope', revision: 1, sha256: 'b'.repeat(64) }
const block: ContentRef = { entity: 'block', id: 'block_scope', revision: 1, sha256: 'c'.repeat(64) }
const context: ViewContext = { view_kind: 'lesson', active_ref: block, attached_refs: [course, lesson], selection: null, attempt_id: null }
test('only actual resolved Reader block or lesson supplies a default, never practice/assessment parents', () => {
  expect(retrievalContext(context, course, true)).toEqual({ course, lesson, block, view: 'lesson' })
  expect(retrievalContext(context, course, false)).toBeNull()
  expect(retrievalContext({ ...context, view_kind: 'practice', active_ref: { ...block, entity: 'practice_set' } }, course, true)).toBeNull()
  expect(retrievalContext({ ...context, view_kind: 'assessment_help', active_ref: { ...block, entity: 'assessment' } }, course, true)).toBeNull()
})
