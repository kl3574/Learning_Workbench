import type { ImpactObjectDecisionReceipt as Receipt, ImpactObjectDecisionWrite as Write } from '../../../../../packages/contracts/generated/api-types'
import { DraftStore, assertDraftWriteAllowed, type DraftRecord, type DraftWriteGuard } from '../../workbench/DraftStore'
import { exactObject, sameValue, validIdentity } from '../providers/providerSchema'
import { basis, receipt, write, type Basis } from './schema'
export type Command = { version: 1; workspace_id: string; command_id: string; origin: { page_id: string; access_generation: number }; basis: Basis; body: Write; ack: Receipt | null; rejection: { status: number; code: string | null } | null }
export const pageId = `page_${crypto.randomUUID()}`
export const commandStore = new DraftStore({ name: 'learning-workbench.content-impact-commands.v1' })
export function decode(raw: string, workspace: string): Command {
  const c = JSON.parse(raw) as Command
  if (!exactObject(c, ['version', 'workspace_id', 'command_id', 'origin', 'basis', 'body', 'ack', 'rejection']) || c.version !== 1 || c.workspace_id !== workspace || !validIdentity(c.command_id)
      || !exactObject(c.origin, ['page_id', 'access_generation']) || !validIdentity(c.origin.page_id) || !Number.isSafeInteger(c.origin.access_generation) || c.origin.access_generation < 0) throw new Error('原内容影响命令身份无效。')
  basis(c.basis); write(c.body, c.basis)
  if (c.ack !== null) receipt(c.ack, c.basis, c.body)
  if (c.rejection !== null && (!exactObject(c.rejection, ['status', 'code']) || ![400, 409, 412, 422].includes(c.rejection.status) || c.rejection.code !== null && !/^[A-Z][A-Z0-9_]{0,79}$/.test(c.rejection.code)) || c.rejection && c.ack) throw new Error('原决定拒绝记录无效。')
  return c
}
export const makeCommand = (workspace: string, access: number, frozen: Basis, body: Write) => decode(JSON.stringify({ version: 1, workspace_id: workspace, command_id: `impactcmd_${crypto.randomUUID()}`, origin: { page_id: pageId, access_generation: access }, basis: frozen, body, ack: null, rejection: null }), workspace)
export const samePage = (c: Command, access: number) => c.origin.page_id === pageId && c.origin.access_generation === access
const immutable = (c: Command) => ({ ...c, ack: null, rejection: null })
export function readCommand(row: DraftRecord, workspace: string): Command {
  const values = [row.text, ...row.conflicts.map(c => c.text)].map(raw => decode(raw, workspace)), first = values[0], acknowledged = values.filter(c => c.ack)
  if (row.objectId !== first.command_id || values.some(c => !sameValue(immutable(c), immutable(first))) || acknowledged.some(c => !sameValue(c.ack, acknowledged[0].ack))) throw new Error('原决定命令或回执冲突，已保留全部本机版本。')
  return acknowledged[0] ?? values.find(c => c.rejection) ?? first
}
export async function persist(c: Command, guard?: DraftWriteGuard, store = commandStore): Promise<Command> {
  let desired = decode(JSON.stringify(c), c.workspace_id)
  for (let attempt = 0; attempt < 4; attempt++) {
    assertDraftWriteAllowed(guard)
    const old = (await store.load(c.workspace_id))[c.command_id]
    assertDraftWriteAllowed(guard)
    if (old) {
      const current = readCommand(old, c.workspace_id)
      if (!sameValue(immutable(current), immutable(desired)) || current.ack && desired.ack && !sameValue(current.ack, desired.ack)) throw new Error('不能替换原决定、基准或回执。')
      if (current.ack || !desired.ack && current.rejection) desired = current
      if (!old.conflicts.length && sameValue(current, desired)) return current
    }
    const saved = await store.save(c.workspace_id, c.command_id, JSON.stringify(desired), old?.revision ?? 0, old?.conflicts.map(x => x.id) ?? [], guard)
    const actual = readCommand(saved.record, c.workspace_id)
    if (!saved.record.conflicts.length && sameValue(actual, desired)) return actual
  }
  throw new Error('其他页面仍在保存原决定，未覆盖。')
}
