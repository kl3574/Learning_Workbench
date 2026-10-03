import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'
import type { ContentRef, ContentImpactPage as Page, ContentImpactSummary as Summary, ContentImpactView as View, ImpactObjectDecisionReceipt as Receipt, ImpactObjectDecisionWrite as Write } from '../../../../../packages/contracts/generated/api-types'
import { checkedProvider, exactObject, sameValue, validIdentity } from '../providers/providerSchema'
export type Basis = { target_id: string; view: View; current_ref: ContentRef }
const entities = new Set(['course', 'lesson', 'block', 'concept', 'question', 'practice_set', 'assessment'])
const invalid = (): never => { throw new Error('内容影响记录与原事件、对象或决定依据不一致，已保留原记录。') }
export function checked<T>(name: string, raw: unknown): T { try { return checkedProvider<T>(name, raw) } catch { return invalid() } }
// These closed decision records contain only strings, safe integers and null;
// canonical learning-json-1 needs no floating-point normalization here.
function canonical(value: unknown): string {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']'
  if (value !== null && typeof value === 'object') return '{' + Object.entries(value).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([key, child]) => `${JSON.stringify(key)}:${canonical(child)}`).join(',') + '}'
  return JSON.stringify(value)
}
export const digest = (value: unknown) => bytesToHex(sha256(new TextEncoder().encode(canonical(value))))
const sorted = (values: string[]) => sameValue(values, [...new Set(values)].sort())
export const eventFacts = (v: Summary | View) => ({ event_id: v.event_id, old_ref: v.old_ref, new_ref: v.new_ref, reason: v.reason, evidence_version: v.evidence_version, event_snapshot_sha256: v.event_snapshot_sha256 })
export function summary(raw: unknown): Summary {
  const v = checked<Summary>('ContentImpactSummary', raw)
  if (!entities.has(v.old_ref.entity) || v.old_ref.entity !== v.new_ref.entity || v.old_ref.id !== v.new_ref.id || v.old_ref.revision >= v.new_ref.revision
      || (v.evidence_version === 'owner_frozen_v1') !== (v.event_snapshot_sha256 !== null) || !sorted(v.pending_target_ids) || !sorted(v.action_required_target_ids)
      || v.pending_target_ids.some(id => id === v.old_ref.id || v.action_required_target_ids.includes(id)) || v.action_required_target_ids.includes(v.old_ref.id)) invalid()
  return v
}
export function page(raw: unknown, filter: string | null, limit: number): Page {
  const v = checked<Page>('ContentImpactPage', raw)
  if (v.items.length > limit || new Set(v.items.map(x => x.event_id)).size !== v.items.length) invalid()
  v.items.forEach(item => { summary(item); if (filter !== null && item.old_ref.id !== filter) invalid() })
  return v
}
export const classification = (view: View, ref: ContentRef) => view.exact_dependency_refs.some(item => sameValue(item, ref)) ? 'exact_ref' : 'id_only_candidate'
function historical(raw: unknown, view: View): Receipt {
  const r = checked<Receipt>('ImpactObjectDecisionReceipt', raw), { receipt_sha256, ...content } = r
  if (r.event_id !== view.event_id || r.event_snapshot_sha256 !== view.event_snapshot_sha256 || r.target_id === view.old_ref.id || !view.affected_ids.includes(r.target_id)
      || r.observed_ref.id !== r.target_id || !entities.has(r.observed_ref.entity) || r.target_metadata_sha256 !== r.observed_ref.sha256
      || (r.observed_ref.entity === 'block') !== (r.target_body_sha256 !== null) || r.classification !== classification(view, r.observed_ref)
      || new Set(r.evidence_artifacts.map(x => x.id)).size !== r.evidence_artifacts.length || !r.reason.trim() || digest(content) !== receipt_sha256) invalid()
  return r
}
export function readView(raw: unknown, id: string, target: string | null = null): View {
  const v = checked<View>('ContentImpactView', raw)
  summary({ ...eventFacts(v), pending_target_ids: v.pending_target_ids, action_required_target_ids: v.action_required_target_ids })
  if (v.decisions.length > 100 || v.event_id !== id || !sorted(v.affected_ids) || !v.affected_ids.includes(v.old_ref.id) || !sorted(v.conservative_only_ids)
      || (target === null ? v.target_decision_head !== null : v.target_decision_head === null || target === v.old_ref.id || !v.affected_ids.includes(target))
      || [...v.pending_target_ids, ...v.action_required_target_ids, ...v.conservative_only_ids].some(x => !v.affected_ids.includes(x) || x === v.old_ref.id)
      || new Set(v.exact_dependency_refs.map(x => canonical(x))).size !== v.exact_dependency_refs.length
      || v.exact_dependency_refs.some(x => !v.affected_ids.includes(x.id) || x.id === v.old_ref.id || v.conservative_only_ids.includes(x.id))
      || v.evidence_version === 'legacy_unverified' && (v.exact_dependency_refs.length > 0 || v.decisions.length > 0 || (v.target_decision_head ?? 0) !== 0)) invalid()
  let previous: Receipt | null = null
  for (const item of v.decisions) {
    const r = historical(item, v)
    if (target !== null && (r.target_id !== target || r.decision_revision > v.target_decision_head!)
        || previous && (r.target_id < previous.target_id || r.target_id === previous.target_id && r.decision_revision <= previous.decision_revision)) invalid()
    previous = r
  }
  return v
}
export function currentRef(raw: unknown, id: string): ContentRef {
  const ref = checked<ContentRef>('ContentRef', raw)
  if (ref.id !== id || !entities.has(ref.entity)) invalid()
  return ref
}
export function basis(raw: Basis): Basis {
  if (!exactObject(raw, ['target_id', 'view', 'current_ref']) || !validIdentity(raw.target_id)) invalid()
  const view = readView(raw.view, raw.view.event_id, raw.target_id), ref = currentRef(raw.current_ref, raw.target_id)
  if (view.evidence_version !== 'owner_frozen_v1') invalid()
  return structuredClone({ target_id: raw.target_id, view, current_ref: ref })
}
export function write(raw: Write, frozen: Basis): Write {
  const b = basis(frozen), v = checked<Write>('ImpactObjectDecisionWrite', raw)
  if (v.target_id !== b.target_id || !sameValue(v.observed_ref, b.current_ref) || v.expected_event_snapshot_sha256 !== b.view.event_snapshot_sha256
      || v.expected_decision_revision !== b.view.target_decision_head || !v.reason.trim() || new Set(v.evidence_artifact_ids).size !== v.evidence_artifact_ids.length) invalid()
  return v
}
export function receipt(raw: unknown, frozen: Basis, body: Write): Receipt {
  write(body, frozen)
  const r = historical(raw, frozen.view)
  if (r.target_id !== body.target_id || !sameValue(r.observed_ref, body.observed_ref) || r.decision_revision !== body.expected_decision_revision + 1
      || r.decision !== body.decision || r.reason !== body.reason || r.request_sha256 !== digest(body) || !sameValue(r.evidence_artifacts.map(x => x.id), body.evidence_artifact_ids)) invalid()
  return r
}
export function artifacts(text: string): string[] {
  const ids = text.split(/\s+/u).filter(Boolean)
  if (ids.length > 32 || new Set(ids).size !== ids.length || ids.some(id => !validIdentity(id))) throw new Error('附件标识须为 0–32 个不重复的已授权证据 ID，每行一个；不接受网址。')
  return ids
}
