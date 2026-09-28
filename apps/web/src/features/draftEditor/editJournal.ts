import type { ContentRef, DraftCreated, DraftCreateWrite, DraftPatched, DraftPatchWrite, EditDraftSnapshot } from '../../../../../packages/contracts/generated/api-types'
import { DraftStore, assertDraftWriteAllowed, type DraftRecord, type DraftWriteGuard } from '../../workbench/DraftStore'
import { exactObject, sameValue, validIdentity } from '../providers/providerSchema'
import { checkedEdit, editSnapshot, editText, type EditText } from './editSchema'

export type EditCommand = { version: 1; workspace: string; key: string; page: string; access: number; base_ref: ContentRef;
  operation: { kind: 'create'; body: DraftCreateWrite } | { kind: 'patch'; baseline: EditDraftSnapshot; local: EditText; body: DraftPatchWrite };
  ack: DraftCreated | DraftPatched | null; rejection: number | null }
export type EditBuffer = { version: 1; workspace: string; id: string; base_ref: ContentRef; baseline: EditDraftSnapshot; local: EditText }
export const editPage = `page_${crypto.randomUUID()}`
export const editCommands = new DraftStore({ name: 'learning-workbench.edit-commands.v1' })
export const editBuffers = new DraftStore({ name: 'learning-workbench.edit-buffers.v1' })
const bad = (): never => { throw new Error('本机编辑记录无法核验，原记录保留。') }
export function decodeBuffer(raw: string, workspace: string): EditBuffer {
  const b = JSON.parse(raw) as EditBuffer
  if (!exactObject(b, ['version', 'workspace', 'id', 'base_ref', 'baseline', 'local']) || b.version !== 1 || b.workspace !== workspace || !validIdentity(b.id)) bad()
  checkedEdit('ContentRef', b.base_ref); editSnapshot(b.baseline, b.base_ref); editText(b.local, false)
  return b
}
export function patchBody(baseline: EditDraftSnapshot, local: EditText): DraftPatchWrite {
  editText(local)
  return { expected_revision: baseline.candidate.draft_revision, patches: [{ field: 'title', value: local.title }, { field: 'body_markdown', value: local.body_markdown }] }
}
export function decodeCommand(raw: string, workspace: string): EditCommand {
  const c = JSON.parse(raw) as EditCommand
  if (!exactObject(c, ['version', 'workspace', 'key', 'page', 'access', 'base_ref', 'operation', 'ack', 'rejection']) || c.version !== 1 || c.workspace !== workspace
      || !validIdentity(c.key) || !validIdentity(c.page) || !Number.isSafeInteger(c.access) || c.access < 0) bad()
  checkedEdit('ContentRef', c.base_ref)
  if (c.operation.kind === 'create') {
    if (!exactObject(c.operation, ['kind', 'body'])) bad()
    const body = checkedEdit<DraftCreateWrite>('DraftCreateWrite', c.operation.body)
    if (body.kind !== 'block' || !sameValue(body.base_ref, c.base_ref)) bad()
    if (c.ack) { const a = checkedEdit<DraftCreated>('DraftCreated', c.ack); if (a.revision !== 1 || a.state !== 'draft' || !sameValue(a.base_ref, c.base_ref)) bad() }
  } else if (c.operation.kind === 'patch') {
    if (!exactObject(c.operation, ['kind', 'baseline', 'local', 'body'])) bad()
    const o = c.operation; editSnapshot(o.baseline, c.base_ref); editText(o.local)
    if (o.baseline.state !== 'draft' || !sameValue(patchBody(o.baseline, o.local), checkedEdit('DraftPatchWrite', o.body))) bad()
    if (c.ack) { const a = checkedEdit<DraftPatched>('DraftPatched', c.ack); if (a.draft_id !== o.baseline.candidate.draft_id || a.revision !== o.body.expected_revision + 1) bad() }
  } else bad()
  if (c.rejection !== null && (c.ack || ![400, 409, 412, 422].includes(c.rejection))) bad()
  return c
}
const immutable = (c: EditCommand) => ({ ...c, ack: null, rejection: null })
export function readCommand(record: DraftRecord, workspace: string): EditCommand {
  const all = [record.text, ...record.conflicts.map(x => x.text)].map(x => decodeCommand(x, workspace)), first = all[0]
  if (record.objectId !== first.key || all.some(x => !sameValue(immutable(x), immutable(first)))) bad()
  const acks = all.filter(x => x.ack)
  if (acks.some(x => !sameValue(x.ack, acks[0].ack))) bad()
  return acks[0] ?? all.find(x => x.rejection !== null) ?? first
}
export async function persistCommand(command: EditCommand, guard?: DraftWriteGuard): Promise<EditCommand> {
  let desired = decodeCommand(JSON.stringify(command), command.workspace)
  for (let i = 0; i < 4; i++) {
    assertDraftWriteAllowed(guard)
    const old = (await editCommands.load(command.workspace))[command.key]
    if (old) {
      const current = readCommand(old, command.workspace)
      if (!sameValue(immutable(current), immutable(desired)) || current.ack && desired.ack && !sameValue(current.ack, desired.ack)) bad()
      if (current.ack || !desired.ack && current.rejection !== null) desired = current
      if (!old.conflicts.length && sameValue(current, desired)) return current
    }
    const next = await editCommands.save(command.workspace, command.key, JSON.stringify(desired), old?.revision ?? 0, old?.conflicts.map(x => x.id) ?? [], guard)
    const value = readCommand(next.record, command.workspace)
    if (!next.record.conflicts.length && sameValue(value, desired)) return value
  }
  return bad()
}
