import type { AttemptPublic, ContentRef, PolicySnapshot, ResponseDraft } from '../../../../../packages/contracts/generated/types'
import { DraftStore } from '../../workbench/DraftStore'
import { createResponseDraftJournal } from '../../shared/createResponseDraftJournal'
import { normalizeResponses, sameResponses } from '../../shared/responses'
import { exactRef, validId } from './target'
export type AssessmentEnvelope = {
  version: 1; workspace_id: string; attempt_id: string; assessment_ref: ContentRef; course_ref: ContentRef | null
  policy: PolicySnapshot; base_revision: number; base_status: AttemptPublic['status']
  base_responses: ResponseDraft[]; candidate_responses: ResponseDraft[]
}
export const assessmentDraftStore = new DraftStore({ name: 'learning-workbench.assessment-drafts.v1' })
export const assessmentKey = (id: string) => `assessment:${id}`
export const assessmentDirty = (value: AssessmentEnvelope) => !sameResponses(value.base_responses, value.candidate_responses)
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('测试草稿结构无效，原记录保留。')
  return value as Record<string, unknown>
}
export function decodeAssessmentEnvelope(raw: string, workspace: string): AssessmentEnvelope {
  const value = record(JSON.parse(raw))
  const fields = ['version', 'workspace_id', 'attempt_id', 'assessment_ref', 'course_ref', 'policy', 'base_revision', 'base_status', 'base_responses', 'candidate_responses']
  if (Object.keys(value).some(key => !fields.includes(key)) || fields.some(key => !(key in value)) || value.version !== 1 || !validId(value.workspace_id) || value.workspace_id !== workspace || !validId(value.attempt_id) || !exactRef(value.assessment_ref, 'assessment') || value.course_ref !== null && !exactRef(value.course_ref, 'course') || !Number.isSafeInteger(value.base_revision) || Number(value.base_revision) < 1 || !['active', 'submitted', 'grading', 'graded', 'needs_review', 'abandoned'].includes(String(value.base_status))) throw new Error('测试草稿工作区、实例或精确基准无效，原记录保留。')
  const policy = record(value.policy)
  if (Object.keys(policy).some(key => !['policy_version', 'mode', 'tutor_scope', 'allow_web', 'allow_materials', 'solution_release'].includes(key)) || (policy.policy_version ?? '1.0.0') !== '1.0.0' || !['independent', 'open_book', 'assisted'].includes(String(policy.mode)) || !['operation_help_only', 'academic'].includes(String(policy.tutor_scope)) || typeof policy.allow_web !== 'boolean' || typeof policy.allow_materials !== 'boolean' || policy.solution_release !== 'after_submit' || policy.mode === 'independent' && (policy.tutor_scope !== 'operation_help_only' || policy.allow_web || policy.allow_materials) || policy.mode === 'open_book' && (policy.tutor_scope !== 'operation_help_only' || policy.allow_web || !policy.allow_materials) || policy.mode === 'assisted' && (policy.tutor_scope !== 'academic' || !policy.allow_materials)) throw new Error('测试草稿冻结策略无效，不能据本机缓存提升权限。')
  return { version: 1, workspace_id: workspace, attempt_id: value.attempt_id, assessment_ref: value.assessment_ref, course_ref: value.course_ref as ContentRef | null, policy: { policy_version: '1.0.0', mode: policy.mode as PolicySnapshot['mode'], tutor_scope: policy.tutor_scope as PolicySnapshot['tutor_scope'], allow_web: policy.allow_web, allow_materials: policy.allow_materials, solution_release: 'after_submit' }, base_revision: Number(value.base_revision), base_status: value.base_status as AssessmentEnvelope['base_status'], base_responses: normalizeResponses(value.base_responses), candidate_responses: normalizeResponses(value.candidate_responses) }
}
export const useAssessmentDrafts = createResponseDraftJournal({ store: assessmentDraftStore, decode: decodeAssessmentEnvelope, dirty: assessmentDirty, key: value => assessmentKey(value.attempt_id) })
