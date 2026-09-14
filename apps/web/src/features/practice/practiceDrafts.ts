import type { ContentRef, ResponseDraft } from '../../../../../packages/contracts/generated/types'
import responseSchema from '../../../../../packages/contracts/generated/schemas/ResponseDraft.schema.json'
import referenceSchema from '../../../../../packages/contracts/generated/schemas/ContentRef.schema.json'
import { DraftStore } from '../../workbench/DraftStore'
export type PracticeEnvelope = { version: 1; workspace_id: string; session_id: string; practice_ref: ContentRef; base_revision: number; base_responses: ResponseDraft[]; candidate_responses: ResponseDraft[] }
export const practiceDraftStore = new DraftStore({ name: 'learning-workbench.practice-drafts.v1' })
export const practiceKey = (sessionId: string) => `practice:${sessionId}`
const id = (value: unknown): value is string => typeof value === 'string' && new RegExp(referenceSchema.properties.id.pattern).test(value)
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('作答草稿结构无效，原记录保留。')
  return value as Record<string, unknown>
}
const text = (value: unknown, limit: number) => {
  if (typeof value !== 'string' || Array.from(value).length > limit || new TextDecoder().decode(new TextEncoder().encode(value)) !== value) throw new Error('作答文本超过契约限制或包含无效 Unicode，原记录保留。')
  return value
}
export function normalizeResponses(value: unknown): ResponseDraft[] {
  if (!Array.isArray(value)) throw new Error('作答列表无效，原记录保留。')
  const ids = new Set<string>()
  return value.map(item => {
    const source = record(item)
    if (Object.keys(source).some(key => !['question_id', 'answer', 'steps_markdown'].includes(key)) || !id(source.question_id) || ids.has(source.question_id) || !('answer' in source)) throw new Error('作答包含未知字段、重复题号或无效题号，原记录保留。')
    ids.add(source.question_id)
    return { question_id: source.question_id, answer: text(source.answer, responseSchema.properties.answer.maxLength), steps_markdown: text(source.steps_markdown ?? '', responseSchema.properties.steps_markdown.maxLength) }
  })
}
export const sameResponses = (a: ResponseDraft[], b: ResponseDraft[]) => JSON.stringify(normalizeResponses(a).sort((x, y) => x.question_id.localeCompare(y.question_id))) === JSON.stringify(normalizeResponses(b).sort((x, y) => x.question_id.localeCompare(y.question_id)))
export function decodePracticeEnvelope(raw: string, workspace: string): PracticeEnvelope {
  const source = record(JSON.parse(raw))
  const names = ['version', 'workspace_id', 'session_id', 'practice_ref', 'base_revision', 'base_responses', 'candidate_responses']
  if (Object.keys(source).some(key => !names.includes(key)) || names.some(key => !(key in source)) || source.version !== 1 || !id(source.workspace_id) || source.workspace_id !== workspace || !id(source.session_id) || !Number.isSafeInteger(source.base_revision) || Number(source.base_revision) < 1) throw new Error('作答草稿工作区、会话或基准不匹配，原记录保留。')
  const ref = record(source.practice_ref)
  if (Object.keys(ref).length !== 4 || Object.keys(ref).some(key => !['entity', 'id', 'revision', 'sha256'].includes(key)) || ref.entity !== 'practice_set' || !id(ref.id) || !Number.isSafeInteger(ref.revision) || Number(ref.revision) < 1 || typeof ref.sha256 !== 'string' || !new RegExp(referenceSchema.properties.sha256.pattern).test(ref.sha256)) throw new Error('作答草稿题集精确引用无效，原记录保留。')
  return { version: 1, workspace_id: workspace, session_id: source.session_id, practice_ref: { entity: 'practice_set', id: ref.id, revision: Number(ref.revision), sha256: ref.sha256 }, base_revision: Number(source.base_revision), base_responses: normalizeResponses(source.base_responses), candidate_responses: normalizeResponses(source.candidate_responses) }
}
export const practiceDirty = (value: PracticeEnvelope) => !sameResponses(value.base_responses, value.candidate_responses)
