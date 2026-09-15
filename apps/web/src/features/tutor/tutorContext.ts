import type { PageRevision, TutorContextBinding, TutorViewContext } from '../../../../../packages/contracts/generated/api-types'
import type { ContentRef, ViewContext } from '../../../../../packages/contracts/generated/types'
import { request } from '../../api/client'
import { sameRef } from '../reader/target'
import type { PracticeTarget } from '../practice/target'
import type { AssessmentTarget } from '../assessment/target'

export type TutorLocation = { context: ViewContext; practice?: PracticeTarget; assessment?: AssessmentTarget; questionId?: string | null; gradingRevision?: number }
export type BoundTutorContext = { scope: TutorViewContext; binding: TutorContextBinding }
async function questionReference(id: string, revision: number): Promise<ContentRef> {
  let cursor: string | null = null
  const seen = new Set<string>()
  do {
    const page: PageRevision = await request('GET /api/v1/objects/{id}/revisions', undefined, undefined, { path: { id }, query: { limit: 100, ...(cursor ? { cursor } : {}) } })
    const match = page.items.find(value => value.ref.entity === 'question' && value.ref.id === id && value.ref.revision === revision)
    if (match) return match.ref
    cursor = page.next_cursor
    if (cursor && seen.has(cursor)) throw new Error('题目修订分页重复，未猜测题目哈希。')
    if (cursor) seen.add(cursor)
  } while (cursor)
  throw new Error('没有读到当前题目精确修订，不能建立问答绑定。')
}
export async function readTutorContext(workspace: string, location: TutorLocation): Promise<BoundTutorContext> {
  const scope = { ...location.context, attached_refs: location.context.attached_refs ?? [], selection: location.context.selection ?? null, attempt_id: location.context.attempt_id ?? null }
  const binding: TutorContextBinding = { practice: null, assessment: null }
  if (scope.view_kind === 'practice') {
    const target = location.practice
    if (!target?.session_id || !location.questionId) throw new Error('先打开真实练习会话并选择题目。')
    const session = await request('GET /api/v1/practice/sessions/{id}', undefined, undefined, { path: { id: target.session_id } })
    if (session.id !== target.session_id || !sameRef(session.practice_ref, scope.active_ref) || !sameRef(session.lesson_ref, target.lesson_ref)) throw new Error('练习会话与当前对象不一致。')
    const question = session.questions.find(value => value.id === location.questionId)
    if (!question) throw new Error('题目不属于当前练习会话。')
    const question_ref = await questionReference(question.id, question.revision)
    scope.attempt_id = null
    binding.practice = { session_id: session.id, session_revision: session.revision, question_ref }
  } else if (['assessment_help', 'assessment_review'].includes(scope.view_kind)) {
    if (!location.assessment?.attempt_id || !location.questionId || scope.attempt_id !== location.assessment.attempt_id) throw new Error('先选择真实测试实例及题目。')
    const attempt = await request('GET /api/v1/attempts/{id}', undefined, undefined, { path: { id: location.assessment.attempt_id } })
    if (attempt.id !== scope.attempt_id || attempt.workspace_id !== workspace || !sameRef(attempt.assessment_ref, scope.active_ref)) throw new Error('测试会话与当前对象不一致。')
    const question_ref = attempt.preflight.prior_seen.questions.find(value => value.question_ref.id === location.questionId)?.question_ref
    if (!question_ref) throw new Error('当前题目没有真实冻结引用。')
    if (scope.view_kind === 'assessment_help' && (attempt.status !== 'active' || attempt.policy.mode !== 'assisted')) throw new Error('此测试当前仅提供固定操作帮助。')
    if (scope.view_kind === 'assessment_review' && (!location.gradingRevision || ['active', 'abandoned'].includes(attempt.status))) throw new Error('尚无当前可用的真实评分复盘版本。')
    binding.assessment = { attempt_revision: attempt.revision, question_ref, grading_revision: scope.view_kind === 'assessment_review' ? location.gradingRevision! : null }
  } else if (!['route', 'lesson', 'worked_example'].includes(scope.view_kind)) throw new Error('此上下文尚不支持问答；没有创建模拟任务。')
  return { scope, binding }
}
