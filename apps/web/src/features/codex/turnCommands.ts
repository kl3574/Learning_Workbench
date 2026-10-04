import type { JobSnapshot } from '../../../../../packages/contracts/generated/api-types'
import type { CodexCurrentSessionView, CodexTurnControlView, CodexTurnPreparationView, CodexTurnPrepareWrite } from '../../../../../packages/contracts/generated/codex-turn-types'
import { assertDraftWriteAllowed, DraftStore, type DraftRecord, type DraftWriteGuard } from '../../workbench/DraftStore'
import { checkedProvider, exactObject, sameValue, validIdentity } from '../providers/providerSchema'
import { checkedBootstrap } from './bootstrapClient'
import { checkedTurn, checkedTurnJob } from './turnClient'

type Base = { version: 1; workspace_id: string; actor_session_id: string; command_id: string; session_id: string; error: { status: number; code: string | null } | null }
export type TurnCommand = Base & (
 { kind: 'prepare'; basis: CodexCurrentSessionView; body: CodexTurnPrepareWrite; ack: CodexTurnPreparationView | null }
 | { kind: 'cancel'; basis: CodexTurnControlView; body: { expected_revision: number }; ack: JobSnapshot | null })
export const turnStore = new DraftStore({ name: 'learning-workbench.codex-turn-commands.v1' })
const fail = (): never => { throw new Error('原回合命令或基准无法核验；本机记录保留。') }
export const turnIdentity = (value: unknown): value is string => validIdentity(value) && value.trim() === value
const immutable = (value: TurnCommand) => ({ ...value, ack: null, error: null })
export function decodeTurnCommand(raw: string, workspace: string): TurnCommand {
 const value = JSON.parse(raw) as TurnCommand
 if (!exactObject(value, ['version', 'workspace_id', 'actor_session_id', 'command_id', 'session_id', 'kind', 'basis', 'body', 'ack', 'error'])
  || value.version !== 1 || !turnIdentity(workspace) || value.workspace_id !== workspace
  || !turnIdentity(value.actor_session_id) || !turnIdentity(value.command_id) || !turnIdentity(value.session_id)) fail()
 if (value.error !== null && (!exactObject(value.error, ['status', 'code']) || !Number.isSafeInteger(value.error.status)
  || value.error.status < 400 || value.error.status > 599 || value.ack !== null
  || value.error.code !== null && (typeof value.error.code !== 'string' || !/^[A-Z][A-Z0-9_]{0,79}$/.test(value.error.code) || value.error.code.trim() !== value.error.code))) fail()
 if (value.kind === 'prepare') {
  const basis = checkedBootstrap<CodexCurrentSessionView>('CodexCurrentSessionView', value.basis)
  checkedTurn('CodexTurnPrepareWrite', value.body)
  if (basis.id !== value.session_id || basis.status !== 'ready' || basis.active_turn_id !== null || basis.revision !== value.body.expected_session_revision) fail()
  if (value.ack !== null) {
   const ack = checkedTurn('CodexTurnPreparationView', value.ack)
   if (ack.session_id !== value.session_id || ack.actor_session_id !== value.actor_session_id || !sameValue(ack.request, value.body)
    || ack.session_revision !== basis.revision + 1 || ack.job.status !== 'awaiting_approval' || ack.proposal_id !== null || ack.consent_id !== null) fail()
  }
 } else if (value.kind === 'cancel') {
  const basis = checkedTurn('CodexTurnControlView', value.basis)
  checkedProvider('JobCancelRequest', value.body)
  if (basis.session_id !== value.session_id || value.body.expected_revision !== basis.job_revision) fail()
  if (value.ack !== null) {
   const ack = checkedTurnJob(value.ack, basis.job.id, workspace)
   const observed = basis.execution === 'terminal' || basis.cancel_requested
   const status = observed ? basis.job.status : basis.job.status === 'running' ? 'running' : 'cancelled'
   if (ack.status !== status || ack.revision !== basis.job_revision + (observed ? 0 : 1)) fail()
  }
 } else fail()
 return value
}
export function turnPrepareCommand(workspace: string, actor: string, basis: CodexCurrentSessionView, body: CodexTurnPrepareWrite): TurnCommand {
 return decodeTurnCommand(JSON.stringify({ version: 1, workspace_id: workspace, actor_session_id: actor, command_id: `codexturn_${crypto.randomUUID()}`,
  session_id: basis.id, kind: 'prepare', basis, body, ack: null, error: null }), workspace)
}
export function turnCancelCommand(workspace: string, actor: string, basis: CodexTurnControlView): TurnCommand {
 return decodeTurnCommand(JSON.stringify({ version: 1, workspace_id: workspace, actor_session_id: actor, command_id: `codexturn_${crypto.randomUUID()}`,
  session_id: basis.session_id, kind: 'cancel', basis, body: { expected_revision: basis.job_revision }, ack: null, error: null }), workspace)
}
export function readTurnCommand(record: DraftRecord, workspace: string): TurnCommand {
 const values = [record.text, ...record.conflicts.map(v => v.text)].map(raw => decodeTurnCommand(raw, workspace)), first = values[0]
 if (record.objectId !== first.command_id || values.some(v => !sameValue(immutable(v), immutable(first)))) fail()
 const confirmed = values.filter(v => v.ack)
 if (confirmed.some(v => !sameValue(v.ack, confirmed[0].ack))) fail()
 return confirmed[0] ?? values.find(v => v.error) ?? first
}
export async function persistTurnCommand(command: TurnCommand, store = turnStore, guard?: DraftWriteGuard): Promise<TurnCommand> {
 let desired = decodeTurnCommand(JSON.stringify(command), command.workspace_id)
 for (let attempt = 0; attempt < 4; attempt++) {
  assertDraftWriteAllowed(guard)
  const old = (await store.load(command.workspace_id))[command.command_id]
  assertDraftWriteAllowed(guard)
  if (old) {
   const current = readTurnCommand(old, command.workspace_id)
   if (!sameValue(immutable(current), immutable(desired)) || current.ack && desired.ack && !sameValue(current.ack, desired.ack)) fail()
   if (current.ack || !desired.ack && !desired.error && current.error) desired = current
   if (!old.conflicts.length && sameValue(current, desired)) return current
  }
  const saved = await store.save(command.workspace_id, command.command_id, JSON.stringify(desired), old?.revision ?? 0, old?.conflicts.map(v => v.id) ?? [], guard)
  const actual = readTurnCommand(saved.record, command.workspace_id)
  if (!saved.record.conflicts.length && sameValue(actual, desired)) return actual
 }
 throw new Error('回合命令仍有并发保存；原 key 与完整内容保留。')
}
