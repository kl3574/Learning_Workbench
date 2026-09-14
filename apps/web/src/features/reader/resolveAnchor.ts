import { request } from '../../api/client'
import type { ContentRef } from '../../../../../packages/contracts/generated/types'
import type { PageRevision } from '../../../../../packages/contracts/generated/api-types'
import { sameRef, type ReaderTarget } from './target'
export async function resolveAnchor(blockRef: ContentRef, courseRef: ContentRef): Promise<ReaderTarget> {
  const find = async (course: ContentRef) => {
    const outline = await request('GET /api/v1/courses/{id}/outline', undefined, undefined, { path: { id: course.id }, query: { revision: course.revision } })
    if (!sameRef(outline.course_ref, course)) throw new Error('课程目录哈希不符。')
    for (const section of outline.sections) for (const lesson of section.lessons) {
      const block = lesson.blocks.find(item => sameRef(item.ref, blockRef))
      if (block) return { course, lesson: lesson.ref, block: blockRef, view: block.kind === 'worked_example' ? 'worked_example' as const : 'lesson' as const }
    }
    return null
  }
  const selected = await find(courseRef)
  if (selected) return selected
  let cursor: string | null = null
  do {
    const revisions: PageRevision = await request('GET /api/v1/objects/{id}/revisions', undefined, undefined, { path: { id: courseRef.id }, query: { limit: 20, ...(cursor ? { cursor } : {}) } })
    for (const version of revisions.items) { if (sameRef(version.ref, courseRef)) continue; const target = await find(version.ref); if (target) return target }
    cursor = revisions.next_cursor
  } while (cursor)
  throw new Error('当前教材及其历史修订没有此笔记的准确块引用。请选择包含该内容的教材；笔记和锚点仍保留。')
}
