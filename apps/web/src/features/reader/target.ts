import type { ContentRef, ViewContext } from '../../../../../packages/contracts/generated/types'
export type ReaderTarget = { course: ContentRef; lesson: ContentRef; block?: ContentRef; view?: 'lesson' | 'worked_example' }
export const sameRef = (a: ContentRef | null | undefined, b: ContentRef | null | undefined) => !!a && !!b && a.entity === b.entity && a.id === b.id && a.revision === b.revision && a.sha256 === b.sha256
export const refKey = (ref: ContentRef) => `${ref.entity}:${ref.id}:${ref.revision}:${ref.sha256}`
export function readerContext(target: ReaderTarget): ViewContext {
  return { view_kind: target.view === 'worked_example' ? 'worked_example' : 'lesson', active_ref: target.block ?? target.lesson, attached_refs: target.block ? [target.course, target.lesson] : [target.course], selection: null, attempt_id: null }
}
export function contextTarget(context: ViewContext, fallback: ContentRef | null): ReaderTarget | null {
  const course = context.attached_refs?.find(ref => ref.entity === 'course') ?? fallback
  const lesson = context.active_ref.entity === 'lesson' ? context.active_ref : context.attached_refs?.find(ref => ref.entity === 'lesson')
  if (!course || course.entity !== 'course' || !lesson) return null
  return { course, lesson, view: context.view_kind === 'worked_example' ? 'worked_example' : 'lesson', ...(context.active_ref.entity === 'block' ? { block: context.active_ref } : {}) }
}
export function readerHref(target: ReaderTarget): string {
  return `/?reader=${encodeURIComponent(JSON.stringify(target))}${target.block ? `#block-${target.block.id}-r${target.block.revision}` : ''}`
}
export function readTarget(search = location.search): ReaderTarget | null {
  const raw = new URLSearchParams(search).get('reader')
  if (!raw) return null
  const valid = (value: unknown, entity: string): value is ContentRef => {
    if (!value || typeof value !== 'object') return false
    const ref = value as Record<string, unknown>
    return Object.keys(ref).every(key => ['entity', 'id', 'revision', 'sha256'].includes(key)) && ref.entity === entity && typeof ref.id === 'string' && /^[A-Za-z][A-Za-z0-9_-]{0,79}$/.test(ref.id) && Number.isInteger(ref.revision) && Number(ref.revision) >= 1 && typeof ref.sha256 === 'string' && /^[a-f0-9]{64}$/.test(ref.sha256)
  }
  try {
    const value = JSON.parse(raw)
    if (!value || Object.keys(value).some(key => !['course', 'lesson', 'block', 'view'].includes(key)) || !valid(value.course, 'course') || !valid(value.lesson, 'lesson') || (value.block && !valid(value.block, 'block')) || (value.view && !['lesson', 'worked_example'].includes(value.view))) throw new Error()
    return value
  } catch { throw new Error('阅读链接的精确引用无效；未改为当前版本。') }
}
