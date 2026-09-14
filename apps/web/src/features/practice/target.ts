import type { ContentRef, ViewContext } from '../../../../../packages/contracts/generated/types'
import type { Session } from '../../workbench/model'
import { openTab, tabIdentity } from '../../workbench/model'
import { sameFrozenReferences } from '../reader/navigation'
export type PracticeTarget = { practice_ref: ContentRef; course_ref: ContentRef; lesson_ref: ContentRef; session_id?: string }
const idPattern = /^[A-Za-z][A-Za-z0-9_-]{0,79}$/
function ref(value: unknown, entity: ContentRef['entity']): value is ContentRef {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  const item = value as Record<string, unknown>
  return Object.keys(item).length === 4 && Object.keys(item).every(key => ['entity', 'id', 'revision', 'sha256'].includes(key)) && item.entity === entity && typeof item.id === 'string' && idPattern.test(item.id) && Number.isSafeInteger(item.revision) && Number(item.revision) >= 1 && typeof item.sha256 === 'string' && /^[a-f0-9]{64}$/.test(item.sha256)
}
export function practiceContext(target: PracticeTarget): ViewContext {
  return { view_kind: 'practice', active_ref: target.practice_ref, attached_refs: [target.course_ref, target.lesson_ref], attempt_id: target.session_id ?? null, selection: null }
}
export function practiceTarget(context: ViewContext): PracticeTarget | null {
  if (context.view_kind !== 'practice' || context.active_ref.entity !== 'practice_set') return null
  const course = context.attached_refs?.find(item => item.entity === 'course')
  const lesson = context.attached_refs?.find(item => item.entity === 'lesson')
  return course && lesson ? { practice_ref: context.active_ref, course_ref: course, lesson_ref: lesson, ...(context.attempt_id ? { session_id: context.attempt_id } : {}) } : null
}
export const practiceHref = (target: PracticeTarget) => `/?practice=${encodeURIComponent(JSON.stringify(target))}`
export function readPracticeTarget(search = location.search): PracticeTarget | null {
  const text = new URLSearchParams(search).get('practice')
  if (!text) return null
  try {
    const value: unknown = JSON.parse(text)
    if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error()
    const item = value as Record<string, unknown>
    if (Object.keys(item).some(key => !['practice_ref', 'course_ref', 'lesson_ref', 'session_id'].includes(key)) || !ref(item.practice_ref, 'practice_set') || !ref(item.course_ref, 'course') || !ref(item.lesson_ref, 'lesson') || item.session_id !== undefined && (typeof item.session_id !== 'string' || !idPattern.test(item.session_id))) throw new Error()
    return { practice_ref: item.practice_ref, course_ref: item.course_ref, lesson_ref: item.lesson_ref, ...(typeof item.session_id === 'string' ? { session_id: item.session_id } : {}) }
  } catch { throw new Error('练习链接的精确题集、教材或会话引用无效，未替换为其他练习。') }
}
export function openPractice(session: Session, target: PracticeTarget, pinned: boolean, hasDraft: (id: string) => boolean): { kind: 'opened' | 'conflict'; session: Session } {
  const context = practiceContext(target)
  const existing = session.tabs.find(tab => tab.id === tabIdentity(context))
  if (existing && !sameFrozenReferences(existing.context, context)) return { kind: 'conflict', session }
  return { kind: 'opened', session: openTab({ ...session, course_ref: target.course_ref, navigation: 'practice' }, context, pinned, hasDraft) }
}
