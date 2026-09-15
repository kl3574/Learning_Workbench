import { request } from '../../api/client'
import type { PageCourse } from '../../../../../packages/contracts/generated/api-types'
import { listPracticeSets } from '../practice/practiceClient'
import { listAssessments } from '../assessment/assessmentClient'
import { refKey } from '../reader/target'
import type { RouteChoice } from './RouteEditorFields'
export async function readRouteChoices(): Promise<RouteChoice[]> {
  const result = new Map<string, RouteChoice>(), cursors = new Set<string>(); let cursor: string | null = null
  do {
    const page: PageCourse = await request('GET /api/v1/courses', undefined, undefined, { query: { limit: 100, ...(cursor ? { cursor } : {}) } })
    for (const course of page.items) {
      const outline = await request('GET /api/v1/courses/{id}/outline', undefined, undefined, { path: { id: course.ref.id }, query: { revision: course.ref.revision } })
      for (const section of outline.sections) for (const lesson of section.lessons) {
        result.set(refKey(lesson.ref), { ref: lesson.ref, title: lesson.title, label: `教材 · ${course.title} r${course.ref.revision} / ${lesson.title} r${lesson.ref.revision}` })
        for (const block of lesson.blocks) result.set(refKey(block.ref), { ref: block.ref, title: block.title, label: `内容块 · ${lesson.title} / ${block.title} r${block.ref.revision}` })
        for (const practice of await listPracticeSets(course.ref, lesson.ref)) result.set(refKey(practice.ref), { ref: practice.ref, title: practice.title, label: `习题 · ${practice.title} r${practice.ref.revision}` })
      }
    }
    cursor = page.next_cursor
    if (cursor && cursors.has(cursor)) throw new Error('课程目录分页重复，未猜测可添加目标。')
    if (cursor) cursors.add(cursor)
  } while (cursor)
  for (const assessment of await listAssessments()) result.set(refKey(assessment.ref), { ref: assessment.ref, title: assessment.title, label: `测试 · ${assessment.title} r${assessment.ref.revision}` })
  return [...result.values()]
}
