import type { EvidenceApplicabilityDecisionView as View, EvidenceImpactDecisionReceipt as Receipt, EvidenceImpactDecisionWrite as Write } from '../../../../../packages/contracts/generated/api-types'
import { checkedProvider, exactObject, sameValue, validIdentity } from '../providers/providerSchema'
export type Basis = { event_id: string; view: View }
const invalid = (): never => { throw new Error('证据适用性记录不符合严格合同或原证据、事件与决定基准。') }
export function checked<T>(name: string, value: unknown): T { try { return checkedProvider<T>(name, value) } catch { return invalid() } }
const pins = (value: View | Receipt) => ({ evidence_id: value.evidence_id, question_ref: value.question_ref, concept_ref: value.concept_ref, attempt_id: value.attempt_id, grading_revision: value.grading_revision, original_evidence_sha256: value.original_evidence_sha256 })
export function readView(raw: unknown, id: string, event: string | null = null): View {
  const value = checked<View>('EvidenceApplicabilityDecisionView', raw)
  if (value.evidence_id !== id || value.original_evidence.id !== id || value.original_evidence.concept_id !== value.concept_ref.id
      || value.question_ref.entity !== 'question' || value.concept_ref.entity !== 'concept'
      || new Set(value.relevant_event_ids).size !== value.relevant_event_ids.length
      || (event === null ? value.event_decision_head !== null : value.event_decision_head === null || !value.relevant_event_ids.includes(event))) invalid()
  const seen = new Set<string>()
  for (const receipt of value.decisions) {
    const key = `${receipt.event_id}:${receipt.decision_revision}`
    if (!sameValue(pins(receipt), pins(value)) || event !== null && receipt.event_id !== event || seen.has(key) || event !== null && receipt.decision_revision > value.event_decision_head!
        || new Set(receipt.evidence_artifacts.map(item => item.id)).size !== receipt.evidence_artifacts.length) invalid()
    seen.add(key)
  }
  return value
}
export function basis(raw: Basis): Basis {
  if (!exactObject(raw, ['event_id', 'view']) || !validIdentity(raw.event_id)) invalid()
  return { event_id: raw.event_id, view: readView(raw.view, raw.view.evidence_id, raw.event_id) }
}
export function write(value: Write, frozen: Basis): Write {
  const b = basis(frozen), body = checked<Write>('EvidenceImpactDecisionWrite', value)
  if (body.event_id !== b.event_id || body.expected_current_basis_sha256 !== b.view.current_basis_sha256 || body.expected_decision_revision !== b.view.event_decision_head
      || !body.reason.trim() || new Set(body.evidence_artifact_ids).size !== body.evidence_artifact_ids.length) invalid()
  return body
}
export function receipt(raw: unknown, frozen: Basis, body: Write): Receipt {
  const value = checked<Receipt>('EvidenceImpactDecisionReceipt', raw)
  write(body, frozen)
  if (!sameValue(pins(value), pins(frozen.view)) || value.event_id !== body.event_id || value.current_basis_sha256 !== body.expected_current_basis_sha256
      || value.decision_revision !== body.expected_decision_revision + 1 || value.decision !== body.decision || value.reason !== body.reason
      || !sameValue(value.evidence_artifacts.map(item => item.id), body.evidence_artifact_ids)) invalid()
  return value
}
export function artifacts(text: string): string[] {
  const ids = text.split(/\s+/u).filter(Boolean)
  if (ids.length > 32 || new Set(ids).size !== ids.length || ids.some(id => !validIdentity(id))) throw new Error('证据附件须为 0–32 个不重复的实际授权 artifact ID，每行一个；不接受 URL。')
  return ids
}
