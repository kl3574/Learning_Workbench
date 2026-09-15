import type { ContentRef, Route } from '../../../../../packages/contracts/generated/types'
import { DraftStore } from '../../workbench/DraftStore'
import { createResponseDraftJournal } from '../../shared/createResponseDraftJournal'
import { exactRef, validId } from '../assessment/target'
export type RouteEnvelope = { version: 1; workspace_id: string; base_ref: ContentRef | null; base: Route | null; candidate: Route; command_id: string; acknowledged: ContentRef | null }
const object = (value: unknown): Record<string, unknown> => { if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('路线草稿结构无效，原记录保留。'); return value as Record<string, unknown> }
function keys(value: Record<string, unknown>, allowed: string[], required = allowed) { if (Object.keys(value).some(key => !allowed.includes(key)) || required.some(key => !(key in value))) throw new Error('路线草稿字段不匹配。') }
export function validateRoute(value: unknown, draft = false): Route {
  const row = object(value); keys(row, ['schema_version', 'entity', 'id', 'revision', 'title', 'goal', 'steps'], ['id', 'revision', 'title', 'goal', 'steps'])
  if (!validId(row.id) || !Number.isSafeInteger(row.revision) || Number(row.revision) < 1 || row.entity !== undefined && row.entity !== 'route' || row.schema_version !== undefined && row.schema_version !== '3.0.0' || typeof row.title !== 'string' || typeof row.goal !== 'string' || !Array.isArray(row.steps) || !draft && !row.steps.length) throw new Error('路线内容或修订无效。')
  const seen = new Set<string>()
  for (const value of row.steps) {
    const step = object(value); keys(step, ['id', 'title', 'target', 'requires_steps', 'completion_rule'], ['id', 'title', 'target', 'completion_rule'])
    const ref = object(step.target)
    if (!validId(step.id) || seen.has(step.id) || typeof step.title !== 'string' || !['lesson', 'block', 'practice_set', 'assessment'].includes(String(ref.entity)) || !exactRef(ref, ref.entity as ContentRef['entity']) || !['manual', 'read', 'practice_submitted', 'assessment_submitted'].includes(String(step.completion_rule))) throw new Error('路线步骤身份或目标引用无效。')
    if (step.requires_steps !== undefined && (!Array.isArray(step.requires_steps) || !step.requires_steps.every(validId) || new Set(step.requires_steps).size !== step.requires_steps.length)) throw new Error('先修步骤列表无效。')
    seen.add(step.id)
  }
  return value as Route
}
export function routeValidation(value: Route): string | null {
  if (!value.title.trim() || !value.goal.trim() || !value.steps.length || value.steps.some(step => !step.title.trim())) return '请填写路线名称、目标，并添加至少一个有标题的任务。'
  const steps = new Map(value.steps.map(step => [step.id, step])), visiting = new Set<string>(), done = new Set<string>()
  const walk = (id: string): boolean => { if (visiting.has(id) || !steps.has(id)) return false; if (done.has(id)) return true; visiting.add(id); for (const parent of steps.get(id)!.requires_steps ?? []) if (!walk(parent)) return false; visiting.delete(id); done.add(id); return true }
  if (value.steps.some(step => !walk(step.id))) return '先修任务包含循环或已删除的步骤；请修改提醒关系后保存。'
  if (value.steps.some(step => step.completion_rule === 'read' && !['lesson', 'block'].includes(step.target.entity) || step.completion_rule === 'practice_submitted' && step.target.entity !== 'practice_set' || step.completion_rule === 'assessment_submitted' && step.target.entity !== 'assessment')) return '完成规则必须与真实任务类型一致。'
  return null
}
export function decodeRouteDraft(raw: string, workspace: string): RouteEnvelope {
  const row = object(JSON.parse(raw)); keys(row, ['version', 'workspace_id', 'base_ref', 'base', 'candidate', 'command_id', 'acknowledged'])
  if (row.version !== 1 || !validId(workspace) || row.workspace_id !== workspace || !validId(row.command_id)) throw new Error('路线草稿的归属或命令身份无效。')
  const candidate = validateRoute(row.candidate, true)
  if (row.base_ref !== null) { if (!exactRef(row.base_ref, 'route')) throw new Error('原路线引用无效。'); const base = validateRoute(row.base); if (base.id !== row.base_ref.id || base.revision !== row.base_ref.revision || candidate.id !== base.id || candidate.revision !== base.revision + 1) throw new Error('路线候选不对应原修订。') }
  else if (row.base !== null || candidate.revision !== 1) throw new Error('新路线应从修订 1 创建。')
  if (row.acknowledged !== null && (!exactRef(row.acknowledged, 'route') || row.acknowledged.id !== candidate.id || row.acknowledged.revision !== candidate.revision)) throw new Error('路线保存回执不对应当前候选。')
  return row as unknown as RouteEnvelope
}
export const routeDirty = (value: RouteEnvelope) => !value.acknowledged
export const routeDraftKey = (value: RouteEnvelope) => `route:${value.candidate.id}`
export const routeStore = new DraftStore({ name: 'learning-workbench.route-drafts.v1' })
export const useRouteJournal = createResponseDraftJournal({ store: routeStore, decode: decodeRouteDraft, dirty: routeDirty, key: routeDraftKey })
export function newRouteDraft(workspace: string, base: Route | null = null, ref: ContentRef | null = null): RouteEnvelope { return { version: 1, workspace_id: workspace, base_ref: ref ? { ...ref } : null, base: base ? structuredClone(base) : null, candidate: base ? { ...structuredClone(base), revision: base.revision + 1 } : { schema_version: '3.0.0', entity: 'route', id: `route_${crypto.randomUUID()}`, revision: 1, title: '', goal: '', steps: [] }, command_id: `route_command_${crypto.randomUUID()}`, acknowledged: null } }
