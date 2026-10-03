import type { ContentRef, DraftPublishWrite } from '../../../../../packages/contracts/generated/api-types'
import { assertDraftWriteAllowed, DraftStore, type DraftRecord, type DraftWriteGuard } from '../../workbench/DraftStore'
import { exactObject, sameValue, validIdentity } from '../providers/providerSchema'
import { checkedPublication } from '../draftPublication/publicationSchema'
import { checkedSingleBasis, singleAcknowledgedCodes, singlePublishedRef, type SinglePublicationBasis } from './singlePublicationSchema'

export type SinglePublicationCommand = { version: 1; workspace_id: string; command_id: string; origin: { page_id: string; access_generation: number }; basis: SinglePublicationBasis;
  body: DraftPublishWrite; ack: ContentRef | null; rejection: { status: number; code: string | null } | null }
// This marker permits conservative same-page recovery; it is not actor identity.
export const singlePublicationPageId = `page_${crypto.randomUUID()}`
export const singlePublicationCommandStore = new DraftStore({ name: 'learning-workbench.single-publication-commands.v1' })
export function decodeSinglePublicationCommand(raw: string, workspace: string): SinglePublicationCommand {
  const value = JSON.parse(raw) as SinglePublicationCommand
  if (!exactObject(value, ['version', 'workspace_id', 'command_id', 'origin', 'basis', 'body', 'ack', 'rejection']) || value.version !== 1
      || value.workspace_id !== workspace || !validIdentity(value.command_id) || !exactObject(value.origin, ['page_id', 'access_generation'])
      || !validIdentity(value.origin.page_id) || !Number.isSafeInteger(value.origin.access_generation) || value.origin.access_generation < 0) throw new Error('原发布命令身份无效。')
  const basis = checkedSingleBasis(value.basis), body = checkedPublication<DraftPublishWrite>('DraftPublishWrite', value.body)
  const codes = singleAcknowledgedCodes(basis, basis.warnings.flatMap((warning, index) => warning.severity === 'warning' ? [index] : []))
  if (body.expected_revision !== basis.candidate.draft_revision || body.expected_content_sha256 !== basis.candidate.candidate_sha256
      || body.review_receipt_id !== basis.review.id || !sameValue(body.acknowledged_warning_codes, codes)) throw new Error('原发布命令没有绑定准确候选、审核和全部警告。')
  if (value.ack !== null) singlePublishedRef(value.ack)
  if (value.rejection !== null && (!exactObject(value.rejection, ['status', 'code']) || ![400, 409, 412, 422].includes(value.rejection.status)
      || value.rejection.code !== null && (typeof value.rejection.code !== 'string' || !/^[A-Z][A-Z0-9_]{0,79}$/.test(value.rejection.code)) || value.ack)) throw new Error('原发布拒绝记录无效。')
  return value
}
export function makeSinglePublicationCommand(workspace: string, access: number, basis: SinglePublicationBasis, selected: number[]): SinglePublicationCommand {
  const codes = singleAcknowledgedCodes(checkedSingleBasis(basis), selected)
  return decodeSinglePublicationCommand(JSON.stringify({ version: 1, workspace_id: workspace, command_id: `singlepublishcmd_${crypto.randomUUID()}`,
    origin: { page_id: singlePublicationPageId, access_generation: access }, basis,
    body: { expected_revision: basis.candidate.draft_revision, expected_content_sha256: basis.candidate.candidate_sha256, review_receipt_id: basis.review.id, acknowledged_warning_codes: codes }, ack: null, rejection: null }), workspace)
}
export const sameSinglePublicationActorPage = (value: SinglePublicationCommand, access: number) => value.origin.page_id === singlePublicationPageId && value.origin.access_generation === access
const immutable = (value: SinglePublicationCommand) => ({ ...value, ack: null, rejection: null })
export function readSinglePublicationCommand(record: DraftRecord, workspace: string): SinglePublicationCommand {
  const values = [record.text, ...record.conflicts.map(value => value.text)].map(raw => decodeSinglePublicationCommand(raw, workspace)), first = values[0]
  if (record.objectId !== first.command_id || values.some(value => !sameValue(immutable(value), immutable(first)))) throw new Error('原发布命令存在不同内容，全部本机候选保留。')
  const acknowledged = values.filter(value => value.ack)
  if (acknowledged.some(value => !sameValue(value.ack, acknowledged[0].ack))) throw new Error('原发布命令存在不同回执。')
  return acknowledged[0] ?? values.find(value => value.rejection) ?? first
}
export async function persistSinglePublicationCommand(value: SinglePublicationCommand, store = singlePublicationCommandStore, guard?: DraftWriteGuard): Promise<SinglePublicationCommand> {
  assertDraftWriteAllowed(guard)
  let desired = decodeSinglePublicationCommand(JSON.stringify(value), value.workspace_id)
  for (let attempt = 0; attempt < 4; attempt++) {
    assertDraftWriteAllowed(guard)
    const old = (await store.load(value.workspace_id))[value.command_id]
    assertDraftWriteAllowed(guard)
    if (old) {
      const current = readSinglePublicationCommand(old, value.workspace_id)
      if (!sameValue(immutable(current), immutable(desired)) || current.ack && desired.ack && !sameValue(current.ack, desired.ack)) throw new Error('不能替换原发布命令或原回执。')
      if (current.ack || !desired.ack && current.rejection) desired = current
      if (!old.conflicts.length && sameValue(current, desired)) return current
    }
    const saved = await store.save(value.workspace_id, value.command_id, JSON.stringify(desired), old?.revision ?? 0, old?.conflicts.map(item => item.id) ?? [], guard)
    const actual = readSinglePublicationCommand(saved.record, value.workspace_id)
    if (!saved.record.conflicts.length && sameValue(actual, desired)) return actual
  }
  throw new Error('本机发布命令仍有并发保存，原内容已保留。')
}
