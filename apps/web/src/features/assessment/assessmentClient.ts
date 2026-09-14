import { request } from '../../api/client'
import type { ContentRef } from '../../../../../packages/contracts/generated/types'
import type { AssessmentSummary, AttemptSnapshot, PageAssessment } from '../../../../../packages/contracts/generated/api-types'
import { sameRef } from '../reader/target'
import { normalizeResponses } from '../../shared/responses'
import type { AssessmentTarget } from './target'
export async function listAssessments(course?: ContentRef) {
  const items: AssessmentSummary[] = [], seen = new Set<string>()
  let cursor: string | null = null
  do {
    const page: PageAssessment = await request('GET /api/v1/assessments', undefined, undefined, { query: { ...(course ? { course_id: course.id } : {}), ...(cursor ? { cursor } : {}), limit: 100 } })
    items.push(...page.items.filter(item => !course || item.preflight.course_refs.some(ref => sameRef(ref, course))))
    cursor = page.next_cursor
    if (cursor && seen.has(cursor)) throw new Error('测试目录游标重复，未猜测完整目录。')
    if (cursor) seen.add(cursor)
  } while (cursor)
  return items
}
export async function readAssessment(target: AssessmentTarget) {
  const items = await listAssessments(target.course_ref)
  const summary = items.find(item => sameRef(item.ref, target.assessment_ref))
  if (!summary) throw new Error('未找到匹配测试修订、哈希及课程关系的测试；原引用仍保留。')
  return summary
}
export function validateAttempt(value: AttemptSnapshot, target: AssessmentTarget, workspace: string) {
  if (value.workspace_id !== workspace || target.attempt_id && value.id !== target.attempt_id || !sameRef(value.assessment_ref, target.assessment_ref) || target.course_ref && !value.preflight.course_refs.some(ref => sameRef(ref, target.course_ref))) throw new Error('测试实例或冻结父链与当前精确引用不一致，未替换为其他内容。')
  return value
}
export async function readAttempt(workspace: string, target: AssessmentTarget & { attempt_id: string }) {
  for (let index = 0; index < 4; index++) {
    const snapshot = validateAttempt(await request('GET /api/v1/attempts/{id}', undefined, undefined, { path: { id: target.attempt_id } }), target, workspace)
    const responses = await request('GET /api/v1/attempts/{id}/responses', undefined, undefined, { path: { id: target.attempt_id } })
    if (snapshot.revision !== responses.revision) continue
    const values = normalizeResponses(responses.responses)
    if (values.some(item => !snapshot.questions.some(question => question.id === item.question_id))) throw new Error('服务端作答包含未分配的题号；未显示混合快照。')
    return { snapshot, responses: values, saved_at: responses.saved_at }
  }
  throw new Error('测试状态持续变化，题目与作答尚未读到同一版本；请重新读取。')
}
export type AttemptRead = Awaited<ReturnType<typeof readAttempt>>
