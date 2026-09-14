import type { ResponseDraft } from '../../../../packages/contracts/generated/types'
import responseSchema from '../../../../packages/contracts/generated/schemas/ResponseDraft.schema.json'
import referenceSchema from '../../../../packages/contracts/generated/schemas/ContentRef.schema.json'
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
