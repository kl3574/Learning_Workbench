import type { ApprovalDecision, AuthoringGroupPrepareWrite, AuthoringGroupNumericPreviewWrite, AuthoringGroupNumericCheckView, AuthoringPrepareWrite, JobRef, JobSnapshot, NumericCheckDecisionAck, NumericCheckPreviewWrite, NumericCheckView } from '../../../../../packages/contracts/generated/api-types'
import { DraftStore, type DraftRecord } from '../../workbench/DraftStore'
import { checkedProvider, exactObject, sameValue, validIdentity } from '../providers/providerSchema'
type Identity = { version: 1; workspace_id: string; command_id: string; rejection: { status: number; code: string | null } | null }
export type AuthoringCommand = Identity & (
  { kind: 'prepare'; body: AuthoringPrepareWrite; ack: JobRef | null }
  | { kind: 'numeric_preview'; draft_id: string; body: NumericCheckPreviewWrite; ack: NumericCheckView | null }
  | { kind: 'numeric_decision'; check_id: string; body: ApprovalDecision; ack: NumericCheckDecisionAck | null }
  | { kind: 'group_prepare'; body: AuthoringGroupPrepareWrite; ack: JobRef | null }
  | { kind: 'group_numeric_preview'; draft_id: string; member_key: string; body: AuthoringGroupNumericPreviewWrite; ack: AuthoringGroupNumericCheckView | null }
  | { kind: 'group_numeric_decision'; check_id: string; body: ApprovalDecision; ack: NumericCheckDecisionAck | null }
  | { kind: 'cancel'; job_id: string; body: { expected_revision: number }; ack: JobSnapshot | null }
)
type Input<T> = T extends AuthoringCommand ? Omit<T, keyof Identity | 'ack'> : never
export type AuthoringCommandInput = Input<AuthoringCommand>
export const authoringCommandStore = new DraftStore({ name: 'learning-workbench.authoring-commands.v1' })
export const authoringControlStore = new DraftStore({ name: 'learning-workbench.authoring-controls.v1' })
export function checkedAuthoring<T>(name: string, value: unknown): T {
  try { return checkedProvider<T>(name, value) } catch { throw new Error('创作记录不符合当前生成契约；原命令保留。') }
}
export function decodeAuthoringCommand(raw: string, workspace: string): AuthoringCommand {
  const v = JSON.parse(raw) as AuthoringCommand
  const extra = v?.kind === 'cancel' ? ['job_id'] : v?.kind === 'group_numeric_preview' ? ['draft_id', 'member_key'] : v?.kind === 'numeric_preview' ? ['draft_id'] : (v?.kind === 'numeric_decision' || v?.kind === 'group_numeric_decision') ? ['check_id'] : []
  if (!exactObject(v, ['version', 'workspace_id', 'command_id', 'rejection', 'kind', 'body', 'ack', ...extra]) || v.version !== 1 || v.workspace_id !== workspace || !validIdentity(v.command_id)) throw new Error('创作命令身份不一致。')
  if (v.rejection !== null && (!exactObject(v.rejection, ['status', 'code']) || ![400, 409, 412, 422].includes(v.rejection.status) || v.rejection.code !== null && typeof v.rejection.code !== 'string') || v.rejection && v.ack) throw new Error('命令拒绝记录无效。')
  if (v.kind === 'cancel') {
    checkedAuthoring('JobCancelRequest', v.body)
    if (!validIdentity(v.job_id)) throw new Error('任务身份无效。')
    if (v.ack !== null) { const ack = checkedAuthoring<JobSnapshot>('JobSnapshot', v.ack); if (ack.id !== v.job_id || ack.workspace_id !== workspace || !['authoring', 'authoring_numeric_check'].includes(ack.kind)) throw new Error('取消回执与本工作区任务不一致。') }
  } else if (v.kind === 'prepare' || v.kind === 'group_prepare') {
    checkedAuthoring(v.kind === 'prepare' ? 'AuthoringPrepareWrite' : 'AuthoringGroupPrepareWrite', v.body)
    if (v.ack !== null && checkedAuthoring<JobRef>('JobRef', v.ack).status !== 'awaiting_approval') throw new Error('准备回执并非原授权前阶段。')
  } else if (v.kind === 'numeric_preview') {
    checkedAuthoring('NumericCheckPreviewWrite', v.body)
    if (!validIdentity(v.draft_id) || v.draft_id !== v.body.candidate.draft_id) throw new Error('数值预览候选身份不一致。')
    if (v.ack !== null) { const ack = checkedAuthoring<NumericCheckView>('NumericCheckView', v.ack); if (!sameValue(ack.candidate, v.body.candidate) || ack.revision !== 1 || ack.decision !== 'pending' || ack.job !== null || ack.result !== null) throw new Error('数值预览回执不匹配。') }
  } else if (v.kind === 'group_numeric_preview') {
    checkedAuthoring('AuthoringGroupNumericPreviewWrite', v.body)
    if (!validIdentity(v.draft_id) || v.draft_id !== v.body.candidate.draft_id || !validIdentity(v.member_key) || v.member_key !== v.body.target.member_key) throw new Error('组数值预览的候选或成员身份不一致。')
    if (v.ack !== null) { const ack = checkedAuthoring<AuthoringGroupNumericCheckView>('AuthoringGroupNumericCheckView', v.ack); if (!sameValue(ack.candidate, v.body.candidate) || !sameValue(ack.target, v.body.target) || ack.revision !== 1 || ack.decision !== 'pending' || ack.job !== null || ack.result !== null) throw new Error('组数值预览回执不匹配。') }
  } else if (v.kind === 'numeric_decision' || v.kind === 'group_numeric_decision') {
    checkedAuthoring('ApprovalDecision', v.body)
    if (!validIdentity(v.check_id)) throw new Error('数值批准身份无效。')
    if (v.ack !== null) { const ack = checkedAuthoring<NumericCheckDecisionAck>('NumericCheckDecisionAck', v.ack); if (ack.id !== v.check_id || ack.operation_sha256 !== v.body.operation_sha256 || ack.decision !== v.body.decision || ack.revision !== v.body.expected_revision + 1) throw new Error('数值决定回执不匹配原操作。') }
  } else throw new Error('未知创作命令。')
  return v
}
export function makeAuthoringCommand(workspace: string, input: AuthoringCommandInput): AuthoringCommand {
  return decodeAuthoringCommand(JSON.stringify({ ...input, version: 1, workspace_id: workspace, command_id: `authoring_${crypto.randomUUID()}`, rejection: null, ack: null }), workspace)
}
const immutable = (v: AuthoringCommand) => ({ ...v, rejection: null, ack: null })
export function readAuthoringCommand(record: DraftRecord, workspace: string): AuthoringCommand {
  const all = [record.text, ...record.conflicts.map(v => v.text)].map(raw => decodeAuthoringCommand(raw, workspace)), first = all[0]
  if (record.objectId !== first.command_id || all.some(v => !sameValue(immutable(v), immutable(first)))) throw new Error('原命令存在不同候选，未自动覆盖。')
  const acks = all.filter(v => v.ack)
  if (acks.some(v => !sameValue(v.ack, acks[0].ack))) throw new Error('原命令存在不同回执，保留全部事实。')
  return acks[0] ?? all.find(v => v.rejection) ?? first
}
export async function persistAuthoringCommand(value: AuthoringCommand, store = value.kind === 'cancel' ? authoringControlStore : authoringCommandStore): Promise<AuthoringCommand> {
  let desired = decodeAuthoringCommand(JSON.stringify(value), value.workspace_id)
  for (let i = 0; i < 4; i++) {
    const old = (await store.load(value.workspace_id))[value.command_id]
    if (old) {
      const current = readAuthoringCommand(old, value.workspace_id)
      if (!sameValue(immutable(current), immutable(desired)) || current.ack && desired.ack && !sameValue(current.ack, desired.ack)) throw new Error('不可替换原命令或回执。')
      if (current.ack || !desired.ack && current.rejection) desired = current
      if (!old.conflicts.length && sameValue(current, desired)) return current
    }
    const result = await store.save(value.workspace_id, value.command_id, JSON.stringify(desired), old?.revision ?? 0, old?.conflicts.map(v => v.id) ?? [])
    const resultValue = readAuthoringCommand(result.record, value.workspace_id)
    if (!result.record.conflicts.length && sameValue(resultValue, desired)) return resultValue
  }
  throw new Error('其他页面仍在保存原命令，请保留本页并重试。')
}
