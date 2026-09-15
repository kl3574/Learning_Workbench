import type { MutationAck, RecommendationDecisionWrite, RecommendationView } from '../../../../../packages/contracts/generated/api-types'
import { DraftStore } from '../../workbench/DraftStore'
import { createResponseDraftJournal } from '../../shared/createResponseDraftJournal'
import { exactRef, validId } from '../assessment/target'

export type DecisionBase = Pick<RecommendationView, 'id' | 'target_ref' | 'target_title' | 'decision' | 'decision_revision' | 'decision_sha256' | 'decision_reason'>
export type DecisionEnvelope = { version: 1; workspace_id: string; base: DecisionBase; command_id: string; fields: RecommendationDecisionWrite; acknowledged: MutationAck | null }
const object = (value: unknown, keys: string[]): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value) && Object.keys(value).length === keys.length && Object.keys(value).every(key => keys.includes(key))
const text = (value: unknown): value is string => typeof value === 'string' && !/[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/u.test(value)
const revision = (value: unknown): value is number => Number.isSafeInteger(value) && Number(value) >= 1
const reason = (value: unknown): value is string | null => value === null || text(value)
export function decisionBase(value: RecommendationView): DecisionBase {
  return { id: value.id, target_ref: structuredClone(value.target_ref), target_title: value.target_title, decision: value.decision, decision_revision: value.decision_revision, decision_sha256: value.decision_sha256, decision_reason: value.decision_reason }
}
export function decisionDirty(value: DecisionEnvelope): boolean { return value.acknowledged === null }
export function newDecision(value: RecommendationView, workspace: string, fields: RecommendationDecisionWrite): DecisionEnvelope {
  return decodeDecision(JSON.stringify({ version: 1, workspace_id: workspace, base: decisionBase(value), fields, command_id: `recommendation_${crypto.randomUUID()}`, acknowledged: null }), workspace)
}
export function decodeDecision(raw: string, workspace: string): DecisionEnvelope {
  const value: unknown = JSON.parse(raw)
  if (!object(value, ['version', 'workspace_id', 'base', 'command_id', 'fields', 'acknowledged']) || value.version !== 1 || value.workspace_id !== workspace || !validId(value.command_id)) throw new Error('推荐候选身份无效，原记录保留。')
  const base = value.base, fields = value.fields
  if (!object(base, ['id', 'target_ref', 'target_title', 'decision', 'decision_revision', 'decision_sha256', 'decision_reason']) || !validId(base.id) || !text(base.target_title) || !base.target_title.trim() || !['pending', 'accepted', 'dismissed'].includes(String(base.decision)) || !revision(base.decision_revision) || typeof base.decision_sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(base.decision_sha256) || !reason(base.decision_reason)) throw new Error('推荐候选原基准无效，未改用当前版本。')
  if (base.decision === 'pending' ? base.decision_revision !== 1 || base.decision_reason !== null : base.decision_revision < 2) throw new Error('推荐候选决定状态与原修订不一致。')
  const target = base.target_ref
  if (!target || typeof target !== 'object' || !('entity' in target) || !['lesson', 'block', 'practice_set', 'assessment'].includes(String(target.entity))) throw new Error('推荐候选精确目标无效。')
  if (!exactRef(target, target.entity as 'lesson' | 'block' | 'practice_set' | 'assessment')) throw new Error('推荐候选精确目标修订或哈希无效。')
  if (!object(fields, ['decision', 'reason']) || !['accepted', 'dismissed'].includes(String(fields.decision)) || !reason(fields.reason)) throw new Error('推荐决定必须是接受或拒绝，理由须为有效文本或空值。')
  if (value.acknowledged !== null) {
    const ack = value.acknowledged
    if (!object(ack, ['id', 'revision', 'applied']) || ack.id !== base.id || !revision(ack.revision) || typeof ack.applied !== 'boolean' || ack.revision !== Number(base.decision_revision) + (ack.applied ? 1 : 0) || !ack.applied && (fields.decision !== base.decision || fields.reason !== base.decision_reason)) throw new Error('推荐回执与原命令不一致；候选仍待确认。')
  }
  return value as DecisionEnvelope
}
export const decisionStore = new DraftStore({ name: 'learning-workbench.recommendation-decisions.v1' })
export const useDecisionJournal = createResponseDraftJournal({ store: decisionStore, decode: decodeDecision, key: value => value.base.id, dirty: decisionDirty })
