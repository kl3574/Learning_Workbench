import type { ContentRestoreDraftCreateAck, ContentRestoreDraftCreateWrite } from '../../../../../packages/contracts/generated/api-types'
import { assertDraftWriteAllowed, DraftStore, type DraftRecord, type DraftWriteGuard } from '../../workbench/DraftStore'
import { exactObject, sameValue, validIdentity } from '../providers/providerSchema'
import { restoreAck, restoreRequest } from './restoreSchema'

export type RestoreCreateCommand = { version: 1; workspace_id: string; command_id: string; origin: { page_id: string; access_generation: number };
  body: ContentRestoreDraftCreateWrite; ack: ContentRestoreDraftCreateAck | null; rejection: { status: number; code: string | null } | null }
export const restoreCreatePageId = `page_${crypto.randomUUID()}`
export const restoreCreateCommandStore = new DraftStore({ name: 'learning-workbench.restore-create-commands.v1' })
export function decodeRestoreCreateCommand(raw: string, workspace: string): RestoreCreateCommand {
  const value = JSON.parse(raw) as RestoreCreateCommand
  if (!exactObject(value, ['version', 'workspace_id', 'command_id', 'origin', 'body', 'ack', 'rejection']) || value.version !== 1
      || value.workspace_id !== workspace || !validIdentity(value.command_id) || !exactObject(value.origin, ['page_id', 'access_generation'])
      || !validIdentity(value.origin.page_id) || !Number.isSafeInteger(value.origin.access_generation) || value.origin.access_generation < 0) throw new Error('原恢复命令身份无效。')
  restoreRequest(value.body)
  if (value.ack !== null) restoreAck(value.ack, value.body)
  if (value.rejection !== null && (!exactObject(value.rejection, ['status', 'code']) || ![400, 409, 412, 422].includes(value.rejection.status)
      || value.rejection.code !== null && (typeof value.rejection.code !== 'string' || !/^[A-Z][A-Z0-9_]{0,79}$/.test(value.rejection.code)) || value.ack)) throw new Error('原恢复拒绝记录无效。')
  return value
}
export function makeRestoreCreateCommand(workspace: string, access: number, body: ContentRestoreDraftCreateWrite): RestoreCreateCommand {
  return decodeRestoreCreateCommand(JSON.stringify({ version: 1, workspace_id: workspace, command_id: `restorecmd_${crypto.randomUUID()}`,
    origin: { page_id: restoreCreatePageId, access_generation: access }, body, ack: null, rejection: null }), workspace)
}
export const sameRestoreCreateActorPage = (value: RestoreCreateCommand, access: number) => value.origin.page_id === restoreCreatePageId && value.origin.access_generation === access
const immutable = (value: RestoreCreateCommand) => ({ ...value, ack: null, rejection: null })
export function readRestoreCreateCommand(record: DraftRecord, workspace: string): RestoreCreateCommand {
  const values = [record.text, ...record.conflicts.map(value => value.text)].map(raw => decodeRestoreCreateCommand(raw, workspace)), first = values[0]
  if (record.objectId !== first.command_id || values.some(value => !sameValue(immutable(value), immutable(first)))) throw new Error('恢复原命令冲突，全部原件保留。')
  const acknowledged = values.filter(value => value.ack)
  if (acknowledged.some(value => !sameValue(value.ack, acknowledged[0].ack))) throw new Error('恢复原命令回执冲突。')
  return acknowledged[0] ?? values.find(value => value.rejection) ?? first
}
export async function persistRestoreCreateCommand(value: RestoreCreateCommand, store = restoreCreateCommandStore, guard?: DraftWriteGuard): Promise<RestoreCreateCommand> {
  assertDraftWriteAllowed(guard)
  let desired = decodeRestoreCreateCommand(JSON.stringify(value), value.workspace_id)
  for (let attempt = 0; attempt < 4; attempt++) {
    assertDraftWriteAllowed(guard)
    const old = (await store.load(value.workspace_id))[value.command_id]
    assertDraftWriteAllowed(guard)
    if (old) {
      const current = readRestoreCreateCommand(old, value.workspace_id)
      if (!sameValue(immutable(current), immutable(desired)) || current.ack && desired.ack && !sameValue(current.ack, desired.ack)) throw new Error('不能改写原恢复命令或 ACK。')
      if (current.ack || !desired.ack && current.rejection) desired = current
      if (!old.conflicts.length && sameValue(current, desired)) return current
    }
    const saved = await store.save(value.workspace_id, value.command_id, JSON.stringify(desired), old?.revision ?? 0, old?.conflicts.map(item => item.id) ?? [], guard)
    const actual = readRestoreCreateCommand(saved.record, value.workspace_id)
    if (!saved.record.conflicts.length && sameValue(actual, desired)) return actual
  }
  throw new Error('本机恢复命令并发记录尚未解决，原件已保留。')
}
