import type { ContentRef, GradingResult, ItemGrade, JobRef } from '../../../../../packages/contracts/generated/types'
import { DraftStore } from '../../workbench/DraftStore'
import { createResponseDraftJournal } from '../../shared/createResponseDraftJournal'
import { exactRef, validId } from '../assessment/target'
export type ReviewBaseline = Pick<GradingResult, 'attempt_id' | 'grading_revision' | 'status'> & { items: Pick<ItemGrade, 'question_ref' | 'score' | 'max_score' | 'status' | 'feedback_markdown'>[] }
export type ReviewField = { question_id: string; selected: boolean; score: string; feedback_markdown: string }
export type ReviewEnvelope = { version: 1; workspace_id: string; attempt_id: string; assessment_ref: ContentRef; base: ReviewBaseline; reason: string; items: ReviewField[]; command_id: string; submitted_job: JobRef | null }
const object = (value: unknown): Record<string, unknown> => { if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('复核草稿结构无效，原记录保留。'); return value as Record<string, unknown> }
function fields(value: Record<string, unknown>, keys: string[]) { if (Object.keys(value).length !== keys.length || keys.some(key => !(key in value))) throw new Error('复核草稿字段不匹配，原记录保留。') }
const string = (value: unknown): value is string => typeof value === 'string' && new TextDecoder().decode(new TextEncoder().encode(value)) === value
export function reviewBaseline(value: ReviewBaseline): ReviewBaseline { return { attempt_id: value.attempt_id, grading_revision: value.grading_revision, status: value.status, items: value.items.map(item => ({ question_ref: { ...item.question_ref }, score: item.score ?? null, max_score: item.max_score, status: item.status, feedback_markdown: item.feedback_markdown })) } }
export function decodeReview(raw: string, workspace: string): ReviewEnvelope {
  const value = object(JSON.parse(raw)); fields(value, ['version', 'workspace_id', 'attempt_id', 'assessment_ref', 'base', 'reason', 'items', 'command_id', 'submitted_job'])
  if (value.version !== 1 || value.workspace_id !== workspace || !validId(workspace) || !validId(value.attempt_id) || !exactRef(value.assessment_ref, 'assessment') || !validId(value.command_id) || !string(value.reason) || !Array.isArray(value.items)) throw new Error('复核草稿的工作区、实例或基准无效，原记录保留。')
  const base = object(value.base); fields(base, ['attempt_id', 'grading_revision', 'status', 'items'])
  if (base.attempt_id !== value.attempt_id || !Number.isSafeInteger(base.grading_revision) || Number(base.grading_revision) < 0 || !['graded', 'needs_review'].includes(String(base.status)) || !Array.isArray(base.items) || base.items.length !== value.items.length) throw new Error('复核草稿评分基准无效。')
  const ids = new Set<string>()
  for (const rawItem of base.items) {
    const item = object(rawItem); fields(item, ['question_ref', 'score', 'max_score', 'status', 'feedback_markdown'])
    if (!exactRef(item.question_ref, 'question') || ids.has(item.question_ref.id) || typeof item.max_score !== 'number' || !Number.isFinite(item.max_score) || item.max_score <= 0 || !string(item.feedback_markdown) || !['graded', 'needs_review'].includes(String(item.status)) || item.status === 'needs_review' && item.score !== null || item.status === 'graded' && (typeof item.score !== 'number' || !Number.isFinite(item.score) || item.score < 0 || item.score > item.max_score)) throw new Error('复核草稿包含无效引用或分数。')
    ids.add(item.question_ref.id)
  }
  for (const rawItem of value.items) { const item = object(rawItem); fields(item, ['question_id', 'selected', 'score', 'feedback_markdown']); if (!validId(item.question_id) || !ids.delete(item.question_id) || typeof item.selected !== 'boolean' || !string(item.score) || !string(item.feedback_markdown)) throw new Error('复核草稿题号或输入无效。') }
  if (ids.size) throw new Error('复核草稿未覆盖完整基准题目。')
  if ((base.items.some(rawItem => object(rawItem).status === 'needs_review') ? 'needs_review' : 'graded') !== base.status || base.grading_revision === 0 && base.items.some(rawItem => object(rawItem).score !== null)) throw new Error('复核草稿基准状态与逐题记录矛盾。')
  if (value.submitted_job !== null) { const job = object(value.submitted_job); fields(job, ['id', 'status']); if (!validId(job.id) || !['queued', 'running', 'awaiting_approval', 'completed', 'failed', 'cancelled'].includes(String(job.status))) throw new Error('复核任务回执无效。') }
  return value as unknown as ReviewEnvelope
}
export const reviewKey = (attempt: string, revision: number) => `review:${attempt}:${revision}`
export const reviewDirty = (value: ReviewEnvelope) => !value.submitted_job && (!!value.reason || value.items.some(item => item.selected || item.score || item.feedback_markdown))
export const reviewStore = new DraftStore({ name: 'learning-workbench.grading-review-drafts.v1' })
export const useReviewJournal = createResponseDraftJournal({ store: reviewStore, decode: decodeReview, dirty: reviewDirty, key: value => reviewKey(value.attempt_id, value.base.grading_revision) })
export function newReview(workspace: string, assessment: ContentRef, result: ReviewBaseline): ReviewEnvelope { return { version: 1, workspace_id: workspace, attempt_id: result.attempt_id, assessment_ref: assessment, base: reviewBaseline(result), reason: '', items: result.items.map(item => ({ question_id: item.question_ref.id, selected: false, score: '', feedback_markdown: '' })), command_id: `review_command_${crypto.randomUUID()}`, submitted_job: null } }
