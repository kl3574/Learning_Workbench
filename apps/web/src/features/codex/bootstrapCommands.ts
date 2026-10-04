import type { ApprovalDecision } from '../../../../../packages/contracts/generated/api-types'
import type { CodexBootstrapDecisionAck, CodexBootstrapPreparationView, CodexBootstrapPreparationWrite, CodexSessionCreateAck, CodexSessionCreateWrite } from '../../../../../packages/contracts/generated/codex-bootstrap-types'
import { assertDraftWriteAllowed, DraftStore, type DraftRecord, type DraftWriteGuard } from '../../workbench/DraftStore'
import { exactObject, sameValue, validIdentity } from '../providers/providerSchema'
import { checkedBootstrap } from './bootstrapClient'

type Base = { version: 1; workspace_id: string; actor_session_id: string; command_id: string; error: { status: number; code: string | null } | null }
export type BootstrapCommand = Base & (
  { kind: 'prepare'; preparation_id: null; basis: null; body: CodexBootstrapPreparationWrite; ack: CodexBootstrapPreparationView | null }
  | { kind: 'decision'; preparation_id: string; basis: CodexBootstrapPreparationView; body: ApprovalDecision; ack: CodexBootstrapDecisionAck | null }
  | { kind: 'create'; preparation_id: string; basis: CodexBootstrapPreparationView; body: CodexSessionCreateWrite; ack: CodexSessionCreateAck | null })
export const bootstrapStore = new DraftStore({ name: 'learning-workbench.codex-bootstrap-commands.v1' })
const fail = (): never => { throw new Error('原本地会话命令或绑定无法核验；全部本机记录保留。') }
const immutable = (value: BootstrapCommand) => ({ ...value, ack: null, error: null })

export function decodeBootstrapCommand(raw: string, workspace: string): BootstrapCommand {
  const value = JSON.parse(raw) as BootstrapCommand
  if (!exactObject(value, ['version', 'workspace_id', 'actor_session_id', 'command_id', 'kind', 'preparation_id', 'basis', 'body', 'ack', 'error'])
    || value.version !== 1 || !validIdentity(workspace) || value.workspace_id !== workspace || !validIdentity(value.actor_session_id) || !validIdentity(value.command_id)) fail()
  if (value.error !== null && (!exactObject(value.error, ['status', 'code']) || !Number.isSafeInteger(value.error.status)
    || value.error.status < 400 || value.error.status > 599 || value.error.code !== null && (typeof value.error.code !== 'string' || !/^[A-Z][A-Z0-9_]{0,79}$/.test(value.error.code)) || value.ack !== null)) fail()
  if (value.kind === 'prepare') {
    checkedBootstrap('CodexBootstrapPreparationWrite', value.body)
    if (value.preparation_id !== null || value.basis !== null) fail()
    if (value.ack !== null) {
      const ack = checkedBootstrap<CodexBootstrapPreparationView>('CodexBootstrapPreparationView', value.ack)
      if (ack.actor_session_id !== value.actor_session_id || ack.revision !== 1 || ack.status !== 'pending'
        || ack.scope.sandbox_root_id !== value.body.sandbox_root_id || !sameValue(ack.scope.allowed_actions, value.body.allowed_actions)
        || ack.consent_id !== null || ack.session_id !== null) fail()
    }
  } else if (value.kind === 'decision' || value.kind === 'create') {
    const basis = checkedBootstrap<CodexBootstrapPreparationView>('CodexBootstrapPreparationView', value.basis)
    if (!validIdentity(value.preparation_id) || value.preparation_id !== basis.id || basis.actor_session_id !== value.actor_session_id) fail()
    if (value.kind === 'decision') {
      checkedBootstrap('ApprovalDecision', value.body)
      if (basis.status !== 'pending' || basis.revision !== 1 || ['expired', 'closed'].includes(basis.validity) || value.body.decision === 'approve_once' && basis.validity !== 'current' || value.body.expected_revision !== basis.revision || value.body.operation_sha256 !== basis.operation_sha256) fail()
      if (value.ack !== null) {
        const ack = checkedBootstrap<CodexBootstrapDecisionAck>('CodexBootstrapDecisionAck', value.ack)
        if (ack.preparation_id !== basis.id || ack.actor_session_id !== value.actor_session_id || ack.revision !== 2
          || ack.decision !== value.body.decision || ack.operation_sha256 !== basis.operation_sha256
          || (ack.decision === 'decline') !== (ack.consent_id === null)) fail()
      }
    } else {
      checkedBootstrap('CodexSessionCreateWrite', value.body)
      if (basis.status !== 'approved' || basis.revision !== 2 || basis.validity !== 'current' || !basis.consent_id || value.body.consent_id !== basis.consent_id
        || value.body.sandbox_root_id !== basis.scope.sandbox_root_id || !sameValue(value.body.allowed_actions, basis.scope.allowed_actions)) fail()
      if (value.ack !== null) {
        const ack = checkedBootstrap<CodexSessionCreateAck>('CodexSessionCreateAck', value.ack)
        if (ack.adapter_version !== basis.scope.adapter_version) fail()
      }
    }
  } else fail()
  return value
}

export function prepareCommand(workspace: string, actor: string): BootstrapCommand {
  return decodeBootstrapCommand(JSON.stringify({ version: 1, workspace_id: workspace, actor_session_id: actor,
    command_id: `codexcmd_${crypto.randomUUID()}`, kind: 'prepare', preparation_id: null, basis: null,
    body: { sandbox_root_id: 'workspace_default', allowed_actions: [] }, ack: null, error: null }), workspace)
}
export function decidedCommand(workspace: string, actor: string, basis: CodexBootstrapPreparationView, decision: 'approve_once' | 'decline'): BootstrapCommand {
  return decodeBootstrapCommand(JSON.stringify({ version: 1, workspace_id: workspace, actor_session_id: actor,
    command_id: `codexcmd_${crypto.randomUUID()}`, kind: 'decision', preparation_id: basis.id, basis,
    body: { expected_revision: basis.revision, operation_sha256: basis.operation_sha256, decision }, ack: null, error: null }), workspace)
}
export function createCommand(workspace: string, actor: string, basis: CodexBootstrapPreparationView): BootstrapCommand {
  return decodeBootstrapCommand(JSON.stringify({ version: 1, workspace_id: workspace, actor_session_id: actor,
    command_id: `codexcmd_${crypto.randomUUID()}`, kind: 'create', preparation_id: basis.id, basis,
    body: { sandbox_root_id: basis.scope.sandbox_root_id, consent_id: basis.consent_id, allowed_actions: [] }, ack: null, error: null }), workspace)
}
export function readBootstrapCommand(record: DraftRecord, workspace: string): BootstrapCommand {
  const values = [record.text, ...record.conflicts.map(item => item.text)].map(raw => decodeBootstrapCommand(raw, workspace)), first = values[0]
  if (record.objectId !== first.command_id || values.some(item => !sameValue(immutable(item), immutable(first)))) fail()
  const acknowledged = values.filter(item => item.ack)
  if (acknowledged.some(item => !sameValue(item.ack, acknowledged[0].ack))) fail()
  return acknowledged[0] ?? values.find(item => item.error) ?? first
}
export async function persistBootstrapCommand(command: BootstrapCommand, store = bootstrapStore, guard?: DraftWriteGuard): Promise<BootstrapCommand> {
  assertDraftWriteAllowed(guard)
  let desired = decodeBootstrapCommand(JSON.stringify(command), command.workspace_id)
  for (let attempt = 0; attempt < 4; attempt++) {
    assertDraftWriteAllowed(guard)
    const old = (await store.load(command.workspace_id))[command.command_id]
    assertDraftWriteAllowed(guard)
    if (old) {
      const current = readBootstrapCommand(old, command.workspace_id)
      if (!sameValue(immutable(current), immutable(desired)) || current.ack && desired.ack && !sameValue(current.ack, desired.ack)) fail()
      if (current.ack || !desired.ack && current.error) desired = current
      if (!old.conflicts.length && sameValue(current, desired)) return current
    }
    const saved = await store.save(command.workspace_id, command.command_id, JSON.stringify(desired), old?.revision ?? 0, old?.conflicts.map(item => item.id) ?? [], guard)
    const actual = readBootstrapCommand(saved.record, command.workspace_id)
    if (!saved.record.conflicts.length && sameValue(actual, desired)) return actual
  }
  throw new Error('本机会话命令仍有并发保存，原 key 和内容保留。')
}
