import type { ConceptStateResponse } from '../../../../../packages/contracts/generated/api-types'
import { refKey, sameRef } from '../reader/target'
import { exactRef } from '../assessment/target'
import type { ConceptChoice } from './ProfileFields'
export const skillLabels = { recall: '回忆', explain: '解释', compute: '计算', derive: '推导', transfer: '迁移' }
export const evidenceStateLabels = { none: '未诊断', preliminary: '初步记录', needs_support: '需要巩固', consistent: '多条一致记录' }
export function conceptChoices(value: ConceptStateResponse): ConceptChoice[] {
  const choices = new Map<string, ConceptChoice>()
  for (const concept of value.concepts) if (!choices.has(concept.ref.id)) choices.set(concept.ref.id, { id: concept.ref.id, title: concept.title })
  return [...choices.values()]
}
export function validateConceptStates(value: ConceptStateResponse): ConceptStateResponse {
  const concepts = new Set(value.concepts.map(item => refKey(item.ref))), rows = new Set<string>()
  if (value.course_refs.some(ref => !exactRef(ref, 'course')) || value.concepts.some(item => !exactRef(item.ref, 'concept')) || concepts.size !== value.concepts.length) throw new Error('概念范围包含无效或重复完整引用，未合并为当前概念。')
  for (const row of value.items) {
    const key = `${refKey(row.concept_ref)}:${row.skill}`
    if (rows.has(key) || !concepts.has(refKey(row.concept_ref)) || row.concept_id !== row.concept_ref.id) throw new Error('概念技能行不属于本次精确范围。')
    rows.add(key)
    if (row.sources.length !== row.evidence_ids.length || row.sources.some((source, index) => source.evidence.id !== row.evidence_ids[index] || !sameRef(source.concept_ref, row.concept_ref) || source.evidence.concept_id !== row.concept_id || source.evidence.skill !== row.skill)) throw new Error('证据来源与概念技能行不匹配。')
    if (row.state_input_evidence_ids.some(id => !row.sources.some(source => source.evidence.id === id && source.evidence.eligible && source.evidence.score != null && source.applicability.status === 'usable'))) throw new Error('状态使用了尚未获准或当前不可用的证据。')
    if (row.self_report && row.self_report.concept_id !== row.concept_id || row.practice_submission_count !== row.practice_submission_sources.length || row.hint_count !== row.hint_sources.length || row.solution_count !== row.solution_sources.length) throw new Error('自报或参与来源与当前行不一致。')
  }
  return value
}
