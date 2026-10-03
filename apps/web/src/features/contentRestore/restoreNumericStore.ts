import type { ApprovalDecision, NumericCheckDecisionAck } from '../../../../../packages/contracts/generated/api-types'
import type { RestoreNumericCheckPreviewWrite, RestoreNumericCheckView } from '../../../../../packages/contracts/generated/restore-numeric-types'
import { assertDraftWriteAllowed, DraftStore, type DraftRecord, type DraftWriteGuard } from '../../workbench/DraftStore'
import { checkedProvider, exactObject, sameValue, validIdentity } from '../providers/providerSchema'
import { checkedRestoreNumeric, restoreNumericDecisionAck, restoreNumericMaterial, restoreNumericPreviewAck } from './restoreNumericSchema'

type Identity = { version: 1; owner: 'authoring_restore'; workspace_id: string; command_id: string;
  origin: { page_id: string; actor_session_id: string; access_generation: number };
  rejection: { status: number; code: string | null } | null }
export type RestoreNumericCommand = Identity & (
  { kind: 'preview'; draft_id: string; body: RestoreNumericCheckPreviewWrite; ack: RestoreNumericCheckView | null }
  | { kind: 'decision'; draft_id: string; check_id: string; body: ApprovalDecision; ack: NumericCheckDecisionAck | null }
)
type Input<T> = T extends RestoreNumericCommand ? Omit<T, keyof Identity | 'ack'> : never
export type RestoreNumericCommandInput = Input<RestoreNumericCommand>
export const restoreNumericPageId = `page_${crypto.randomUUID()}`
export const restoreNumericCommandStore = new DraftStore({ name: 'learning-workbench.restore-numeric-commands.v1' })
const invalid = (): never => { throw new Error('恢复数值原命令、会话或回执冲突；全部原件保留。') }

export function decodeRestoreNumericCommand(raw: string, workspace: string): RestoreNumericCommand {
  const value = JSON.parse(raw) as RestoreNumericCommand
  const extra = value?.kind === 'decision' ? ['check_id'] : []
  if (!exactObject(value, ['version', 'owner', 'workspace_id', 'command_id', 'origin', 'rejection', 'kind', 'draft_id', 'body', 'ack', ...extra])
      || value.version !== 1 || value.owner !== 'authoring_restore' || value.workspace_id !== workspace || !validIdentity(workspace)
      || !validIdentity(value.command_id) || !validIdentity(value.draft_id)
      || !exactObject(value.origin, ['page_id', 'actor_session_id', 'access_generation'])
      || !validIdentity(value.origin.page_id) || !validIdentity(value.origin.actor_session_id)
      || !Number.isSafeInteger(value.origin.access_generation) || value.origin.access_generation < 0) invalid()
  if (value.rejection !== null && (!exactObject(value.rejection, ['status', 'code'])
      || ![400, 409, 412, 413, 422].includes(value.rejection.status)
      || value.rejection.code !== null && (typeof value.rejection.code !== 'string' || !/^[A-Z][A-Z0-9_]{0,79}$/.test(value.rejection.code))
      || value.ack !== null)) invalid()
  if (value.kind === 'preview') {
    checkedRestoreNumeric('RestoreNumericCheckPreviewWrite', value.body)
    restoreNumericMaterial(value.body.material)
    if (value.body.candidate.draft_id !== value.draft_id) invalid()
    if (value.ack !== null) restoreNumericPreviewAck(value.ack, value.body)
  } else if (value.kind === 'decision') {
    checkedProvider('ApprovalDecision', value.body)
    if (!validIdentity(value.check_id)) invalid()
    if (value.ack !== null) restoreNumericDecisionAck(value.ack, value.check_id, value.body)
  } else invalid()
  return value
}
export function makeRestoreNumericCommand(workspace: string, actorSessionId: string, access: number, input: RestoreNumericCommandInput): RestoreNumericCommand {
  return decodeRestoreNumericCommand(JSON.stringify({ ...input, version: 1, owner: 'authoring_restore', workspace_id: workspace,
    command_id: `restorenumeric_${crypto.randomUUID()}`, origin: { page_id: restoreNumericPageId, actor_session_id: actorSessionId, access_generation: access },
    ack: null, rejection: null }), workspace)
}
export const sameRestoreNumericActorPage = (value: RestoreNumericCommand, actorSessionId: string, access: number) =>
  value.origin.page_id === restoreNumericPageId && value.origin.actor_session_id === actorSessionId && value.origin.access_generation === access
const immutable = (value: RestoreNumericCommand) => ({ ...value, ack: null, rejection: null })
export function readRestoreNumericCommand(record: DraftRecord, workspace: string): RestoreNumericCommand {
  const values = [record.text, ...record.conflicts.map(value => value.text)].map(raw => decodeRestoreNumericCommand(raw, workspace)), first = values[0]
  if (record.objectId !== first.command_id || values.some(value => !sameValue(immutable(value), immutable(first)))) invalid()
  const acknowledged = values.filter(value => value.ack !== null), rejected = values.filter(value => value.rejection !== null)
  if (acknowledged.some(value => !sameValue(value.ack, acknowledged[0].ack))
      || rejected.some(value => !sameValue(value.rejection, rejected[0].rejection))) invalid()
  return acknowledged[0] ?? rejected[0] ?? first
}
export async function persistRestoreNumericCommand(value: RestoreNumericCommand, store = restoreNumericCommandStore, guard?: DraftWriteGuard): Promise<RestoreNumericCommand> {
  assertDraftWriteAllowed(guard)
  let desired = decodeRestoreNumericCommand(JSON.stringify(value), value.workspace_id)
  for (let attempt = 0; attempt < 4; attempt++) {
    assertDraftWriteAllowed(guard)
    const old = (await store.load(value.workspace_id))[value.command_id]
    assertDraftWriteAllowed(guard)
    if (old) {
      const current = readRestoreNumericCommand(old, value.workspace_id)
      if (!sameValue(immutable(current), immutable(desired)) || current.ack && desired.ack && !sameValue(current.ack, desired.ack)
          || current.rejection && desired.rejection && !sameValue(current.rejection, desired.rejection)) invalid()
      if (current.ack || !desired.ack && current.rejection) desired = current
      if (!old.conflicts.length && sameValue(current, desired)) return current
    }
    const saved = await store.save(value.workspace_id, value.command_id, JSON.stringify(desired), old?.revision ?? 0,
      old?.conflicts.map(item => item.id) ?? [], guard)
    const actual = readRestoreNumericCommand(saved.record, value.workspace_id)
    if (!saved.record.conflicts.length && sameValue(actual, desired)) return actual
  }
  throw new Error('其他页面仍在保存恢复数值命令，请保留当前页面并重试。')
}
