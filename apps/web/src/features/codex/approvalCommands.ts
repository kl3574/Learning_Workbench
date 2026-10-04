import type { ApprovalDecision } from '../../../../../packages/contracts/generated/api-types'
import type { CodexTurnControlView, GenericApprovalView, GenericApprovalDecisionAck } from '../../../../../packages/contracts/generated/codex-turn-types'
import { assertDraftWriteAllowed, DraftStore, type DraftRecord, type DraftWriteGuard } from '../../workbench/DraftStore'
import { checkedProvider, exactObject, sameValue } from '../providers/providerSchema'
import { turnIdentity } from './turnCommands'
import { checkedTurn } from './turnClient'
import { approvalClient, checkedApproval, type ApprovalPort } from './approvalClient'
export type ApprovalCommand = {
 version: 1; workspace_id: string; actor_session_id: string; command_id: string; target_id: string;
 route: 'POST /api/v1/approvals/{id}/decision';
 basis: { kind: 'approve'; view: GenericApprovalView } | { kind: 'decline'; control: CodexTurnControlView };
 body: ApprovalDecision; ack: GenericApprovalDecisionAck | null; error: { status: number; code: string | null } | null
}
export const approvalStore = new DraftStore({ name: 'learning-workbench.codex-operation-commands.v1' })
const fail = (): never => { throw new Error('原审批命令、只读基准或完整 ACK 无法核验；原记录保留。') }
export function decodeApprovalCommand(raw: string, workspace: string): ApprovalCommand {
 const c = JSON.parse(raw) as ApprovalCommand
 if (!exactObject(c, ['version', 'workspace_id', 'actor_session_id', 'command_id', 'target_id', 'route', 'basis', 'body', 'ack', 'error']) || c.version !== 1
  || c.workspace_id !== workspace || !turnIdentity(workspace) || !turnIdentity(c.actor_session_id) || !turnIdentity(c.command_id) || !turnIdentity(c.target_id)
  || c.route !== 'POST /api/v1/approvals/{id}/decision') fail()
 const b = checkedProvider<ApprovalDecision>('ApprovalDecision', c.body)
 let binding: { session_id: string; turn_id: string; job: { id: string } }
 if (c.basis?.kind === 'approve') {
  if (!exactObject(c.basis, ['kind', 'view'])) fail()
  const v = checkedApproval('GenericApprovalView', c.basis.view)
  if (b.decision !== 'approve_once' || v.actor_session_id !== c.actor_session_id || v.id !== c.target_id
   || v.operation_sha256 !== b.operation_sha256 || v.revision !== b.expected_revision || v.decision !== 'pending'
   || v.validity !== 'current' || v.execution !== 'not_started' || v.operation.kind === 'unsupported') fail()
  binding = v
 } else if (c.basis?.kind === 'decline') {
  if (!exactObject(c.basis, ['kind', 'control'])) fail()
  const control = checkedTurn('CodexTurnControlView', c.basis.control), v = control.approval_controls.find(a => a.id === c.target_id)
  if (!v || b.decision !== 'decline' || v.decision !== 'pending' || v.operation_sha256 !== b.operation_sha256 || v.revision !== b.expected_revision) fail()
  binding = { session_id: control.session_id, turn_id: control.id, job: control.job }
 } else return fail()
 if (c.ack !== null) {
  const a = checkedApproval('GenericApprovalDecisionAck', c.ack)
  if (a.id !== c.target_id || a.actor_session_id !== c.actor_session_id || a.operation_sha256 !== b.operation_sha256 || a.decision !== b.decision
   || a.session_id !== binding.session_id || a.turn_id !== binding.turn_id || a.run_id !== binding.job.id || a.job.id !== binding.job.id) fail()
 }
 if (c.error !== null && (!exactObject(c.error, ['status', 'code']) || !Number.isSafeInteger(c.error.status) || c.error.status < 400 || c.error.status > 599
  || c.ack !== null || c.error.code !== null && (typeof c.error.code !== 'string' || !/^[A-Z][A-Z0-9_]{0,79}$/.test(c.error.code) || c.error.code.trim() !== c.error.code))) fail()
 return c
}
export function makeApprovalCommand(workspace: string, actor: string, basis: ApprovalCommand['basis'], target: string): ApprovalCommand {
 const v = basis.kind === 'approve' ? basis.view : basis.control.approval_controls.find(a => a.id === target)
 if (!v) return fail()
 return decodeApprovalCommand(JSON.stringify({ version: 1, workspace_id: workspace, actor_session_id: actor,
  command_id: `codexapproval_${crypto.randomUUID()}`, target_id: target, route: 'POST /api/v1/approvals/{id}/decision', basis,
  body: { expected_revision: v.revision, operation_sha256: v.operation_sha256, decision: basis.kind === 'approve' ? 'approve_once' : 'decline' }, ack: null, error: null }), workspace)
}
const immutable = (value: ApprovalCommand) => ({ ...value, ack: null, error: null })
export function readApprovalCommand(record: DraftRecord, workspace: string): ApprovalCommand {
 const values = [record.text, ...record.conflicts.map(v => v.text)].map(raw => decodeApprovalCommand(raw, workspace)), first = values[0]
 if (first.command_id !== record.objectId || values.some(v => !sameValue(immutable(v), immutable(first)))) throw new Error('Conflicting original approval command')
 const confirmed = values.filter(v => v.ack)
 if (confirmed.some(v => !sameValue(v.ack, confirmed[0].ack))) throw new Error('Conflicting approval ACK')
 return confirmed[0] ?? values.find(v => v.error) ?? first
}
export async function persistApprovalCommand(command: ApprovalCommand, store = approvalStore, guard?: DraftWriteGuard): Promise<ApprovalCommand> {
 let desired = decodeApprovalCommand(JSON.stringify(command), command.workspace_id)
 for (let attempt = 0; attempt < 4; attempt++) {
  assertDraftWriteAllowed(guard)
  const old = (await store.load(command.workspace_id))[command.command_id]
  assertDraftWriteAllowed(guard)
  if (old) {
   const current = readApprovalCommand(old, command.workspace_id)
   if (!sameValue(immutable(current), immutable(desired)) || current.ack && desired.ack && !sameValue(current.ack, desired.ack)) throw new Error('Cannot replace original approval command or ACK')
   if (current.ack || !desired.ack && !desired.error && current.error) desired = current
   if (!old.conflicts.length && sameValue(current, desired)) return current
  }
  const saved = await store.save(command.workspace_id, command.command_id, JSON.stringify(desired), old?.revision ?? 0, old?.conflicts.map(v => v.id) ?? [], guard)
  const actual = readApprovalCommand(saved.record, command.workspace_id)
  if (!saved.record.conflicts.length && sameValue(actual, desired)) return actual
 }
 throw new Error('Concurrent approval command remains unresolved')
}
export async function dispatchApprovalCommand(command: ApprovalCommand, port: Pick<ApprovalPort, 'decide'> = approvalClient, store = approvalStore,
 options: { guard?: DraftWriteGuard; beforePost?: () => Promise<void>; onAck?: (ack: ApprovalCommand) => void; beforeDelivery?: () => Promise<void> } = {}): Promise<ApprovalCommand> {
 const original = await persistApprovalCommand(command, store, options.guard)
 if (original.ack) { await options.beforeDelivery?.(); return original }
 await options.beforePost?.(); assertDraftWriteAllowed(options.guard)
 const raw = await port.decide(original.target_id, original.body, original.command_id)
 const acknowledged = decodeApprovalCommand(JSON.stringify({ ...original, ack: raw, error: null }), original.workspace_id)
 options.onAck?.(acknowledged)
 await options.beforeDelivery?.()
 return persistApprovalCommand(acknowledged, store, options.guard)
}
