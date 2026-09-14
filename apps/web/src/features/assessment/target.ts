import type { ContentRef, ViewContext } from '../../../../../packages/contracts/generated/types'
import type { Session } from '../../workbench/model'
import { openTab, tabIdentity } from '../../workbench/model'
import { sameFrozenReferences } from '../reader/navigation'
export type AssessmentTarget = { assessment_ref: ContentRef; course_ref?: ContentRef; attempt_id?: string; view?: 'review' }
export const validId = (value: unknown): value is string => typeof value === 'string' && /^[A-Za-z][A-Za-z0-9_-]{0,79}$/.test(value)
export function exactRef(value: unknown, entity: ContentRef['entity']): value is ContentRef {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  const item = value as Record<string, unknown>
  return Object.keys(item).length === 4 && Object.keys(item).every(key => ['entity', 'id', 'revision', 'sha256'].includes(key)) && item.entity === entity && validId(item.id) && Number.isSafeInteger(item.revision) && Number(item.revision) >= 1 && typeof item.sha256 === 'string' && /^[a-f0-9]{64}$/.test(item.sha256)
}
export function assessmentContext(target: AssessmentTarget): ViewContext {
  return { view_kind: target.view === 'review' ? 'assessment_review' : 'assessment_help', active_ref: target.assessment_ref, attached_refs: target.course_ref ? [target.course_ref] : [], attempt_id: target.attempt_id ?? null, selection: null }
}
export function assessmentTarget(context: ViewContext): AssessmentTarget | null {
  if (!['assessment_help', 'assessment_review'].includes(context.view_kind) || !exactRef(context.active_ref, 'assessment') || context.view_kind === 'assessment_review' && !context.attempt_id) return null
  const course = context.attached_refs?.find(item => item.entity === 'course')
  return { assessment_ref: context.active_ref, ...(course ? { course_ref: course } : {}), ...(context.attempt_id ? { attempt_id: context.attempt_id } : {}), ...(context.view_kind === 'assessment_review' ? { view: 'review' } : {}) }
}
export const assessmentHref = (target: AssessmentTarget) => `/?assessment=${encodeURIComponent(JSON.stringify(target))}`
export function readAssessmentTarget(search = location.search): AssessmentTarget | null {
  const raw = new URLSearchParams(search).get('assessment')
  if (!raw) return null
  try {
    const item: unknown = JSON.parse(raw)
    if (!item || typeof item !== 'object' || Array.isArray(item)) throw new Error()
    const value = item as Record<string, unknown>
    if (Object.keys(value).some(key => !['assessment_ref', 'course_ref', 'attempt_id', 'view'].includes(key)) || !exactRef(value.assessment_ref, 'assessment') || value.course_ref !== undefined && !exactRef(value.course_ref, 'course') || value.attempt_id !== undefined && !validId(value.attempt_id) || value.view !== undefined && value.view !== 'review' || value.view === 'review' && !validId(value.attempt_id)) throw new Error()
    return { assessment_ref: value.assessment_ref, ...(value.course_ref ? { course_ref: value.course_ref as ContentRef } : {}), ...(typeof value.attempt_id === 'string' ? { attempt_id: value.attempt_id } : {}), ...(value.view === 'review' ? { view: 'review' } : {}) }
  } catch { throw new Error('测试链接的精确引用、所属课程或作答实例无效；原标签仍保留。') }
}
export function openAssessment(session: Session, target: AssessmentTarget, pinned: boolean, hasDraft: (id: string) => boolean): { kind: 'opened' | 'conflict'; session: Session } {
  const context = assessmentContext(target)
  const existing = session.tabs.find(tab => tab.id === tabIdentity(context))
  if (existing && !sameFrozenReferences(existing.context, context)) return { kind: 'conflict', session }
  return { kind: 'opened', session: openTab({ ...session, ...(target.course_ref ? { course_ref: target.course_ref } : {}), navigation: 'assessment' }, context, pinned, hasDraft) }
}
