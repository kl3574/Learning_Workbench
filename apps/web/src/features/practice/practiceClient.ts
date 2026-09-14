import { request } from '../../api/client'
import type { ContentRef } from '../../../../../packages/contracts/generated/types'
import type { PagePracticeSet, PracticeSetSummary } from '../../../../../packages/contracts/generated/api-types'
import { readCourse, readLesson } from '../reader/contentClient'
import { sameRef } from '../reader/target'
import type { PracticeTarget } from './target'
export async function listPracticeSets(course: ContentRef, lesson?: ContentRef) {
  const items: PracticeSetSummary[] = []
  let cursor: string | null = null
  const seen = new Set<string>()
  do {
    const page: PagePracticeSet = await request('GET /api/v1/practice/sets', undefined, undefined, { query: { course_id: course.id, ...(lesson ? { lesson_id: lesson.id } : {}), ...(cursor ? { cursor } : {}), limit: 100 } })
    items.push(...page.items.filter(item => !lesson || sameRef(item.lesson_ref, lesson)))
    cursor = page.next_cursor
    if (cursor && seen.has(cursor)) throw new Error('习题目录分页游标重复；未猜测完整目录。')
    if (cursor) seen.add(cursor)
  } while (cursor)
  return items
}
export async function readPracticeTarget(target: PracticeTarget) {
  const [course, lesson, items] = await Promise.all([readCourse(target.course_ref), readLesson(target.lesson_ref), listPracticeSets(target.course_ref, target.lesson_ref)])
  if (!course.lesson_refs.some(ref => sameRef(ref, target.lesson_ref))) throw new Error('此小节不属于当前精确课程修订。')
  const summary = items.find(item => sameRef(item.ref, target.practice_ref) && sameRef(item.lesson_ref, target.lesson_ref))
  if (!summary) throw new Error('未找到同时匹配题集修订、哈希和所属小节的习题；原始标签和作答仍保留。')
  return { course, lesson, summary }
}
