import type { ApprovalDecision, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import type { CodexTurnControlView, GenericApprovalView, GenericApprovalDecisionAck } from '../../../../../packages/contracts/generated/codex-turn-types'
import schemas from '../../../../../packages/contracts/generated/codex-turn-schemas.json'
import { request } from '../../api/client'
import { checkedProvider } from '../providers/providerSchema'
import { turnClient } from './turnClient'
import { turnIdentity } from './turnCommands'
import { outboundTime } from './turnOutboundClient'

type Wire = { GenericApprovalView: GenericApprovalView; GenericApprovalDecisionAck: GenericApprovalDecisionAck }
const fail = (): never => { throw new Error('逐操作审批记录不符合完整合同；原命令保留。') }
const id = (value: string) => { if (!turnIdentity(value)) fail(); return value }
const path = (value: string) => { if (/[\\:\x00-\x1f\x7f]/.test(value) || value.split('/').some(p => ['', '.', '..'].includes(p))) fail() }
const unique = (values: string[]) => { if (new Set(values).size !== values.length) fail() }
/** Public relationships only. The operation SHA includes private owner facts and is never recomputed here. */
export function checkedApproval<N extends keyof Wire>(name: N, raw: unknown): Wire[N] {
 const v = checkedProvider<Wire[N]>(name, raw, schemas.schemas)
 if (v.run_id !== v.job.id) fail()
 if (name === 'GenericApprovalView') {
  const a = v as GenericApprovalView, op = a.operation
  if (outboundTime(a.expires_at) <= outboundTime(a.created_at)
   || (a.decision === 'pending') !== (a.decided_at === null) || a.decision !== 'pending' && a.revision < 2
   || a.execution === 'started' && a.revision < 3 || ['completed', 'failed', 'unknown'].includes(a.execution) && a.revision < 4
   || op.kind === 'unsupported' && a.decision === 'approve_once' || a.execution !== 'not_started' && a.decision !== 'approve_once'
   || (a.execution === 'not_started') !== (a.started_at === null)
   || ['completed', 'failed', 'unknown'].includes(a.execution) !== (a.finished_at !== null)
   || ['not_started', 'started'].includes(a.execution) && a.result_sha256 !== null
   || a.execution === 'completed' && (a.result_sha256 === null || a.error_code !== null)) fail()
  let previous = outboundTime(a.created_at)
  for (const value of [a.decided_at, a.started_at, a.finished_at]) if (value !== null) { const next = outboundTime(value); if (next < previous) fail(); previous = next }
  if (op.kind === 'command') { path(op.cwd); unique(op.read_files.map(f => f.path)); op.read_files.forEach(f => path(f.path)); if (!op.command_text.trim()) fail() }
  if (op.kind === 'file_change') {
   unique(op.files.map(f => f.path))
   for (const f of op.files) { path(f.path); if ((f.before_sha256 !== null) !== (f.action !== 'add') || (f.before_size !== null) !== (f.action !== 'add')
    || (f.after_sha256 !== null) !== (f.action !== 'delete') || (f.after_size !== null) !== (f.action !== 'delete')) fail() }
  }
 }
 return v
}
export type ApprovalPort = {
 session(): Promise<SessionResponse>
 control(turn: string): Promise<CodexTurnControlView>
 read(id: string): Promise<GenericApprovalView>
 decide(id: string, body: ApprovalDecision, key: string): Promise<GenericApprovalDecisionAck>
}
export const approvalClient: ApprovalPort = {
 session: turnClient.session, control: turnClient.control,
 read: async identifier => { const v = checkedApproval('GenericApprovalView', await request('GET /api/v1/approvals/{id}', undefined, undefined, { path: { id: id(identifier) } })); if (v.id !== identifier) fail(); return v },
 decide: async (identifier, body, key) => {
  const checked = checkedProvider<ApprovalDecision>('ApprovalDecision', body)
  const v = checkedApproval('GenericApprovalDecisionAck', await request('POST /api/v1/approvals/{id}/decision', checked, { 'Idempotency-Key': id(key) }, { path: { id: id(identifier) } }))
  if (v.id !== identifier || v.operation_sha256 !== checked.operation_sha256 || v.decision !== checked.decision) fail()
  return v
 },
}
