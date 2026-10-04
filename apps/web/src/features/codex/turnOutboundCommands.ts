import type { ConsentRevoke, MutationAck, ProviderConfigView } from '../../../../../packages/contracts/generated/api-types'
import type { CodexConsentCreateAck, CodexConsentCreateWrite, CodexConsentProposalView, CodexConsentView, CodexCurrentSessionView, CodexFrozenOutboundSummary, CodexOutboundPreviewWrite, CodexTurnControlView, CodexTurnPreparationView, CodexTurnStartAck, CodexTurnStartWrite } from '../../../../../packages/contracts/generated/codex-turn-types'
import { assertDraftWriteAllowed, DraftStore, type DraftRecord, type DraftWriteGuard } from '../../workbench/DraftStore'
import { checkedProvider, exactObject, sameValue } from '../providers/providerSchema'
import { checkedTurn } from './turnClient'
import { turnIdentity } from './turnCommands'
import { checkedOutbound, type TurnOutboundPort } from './turnOutboundClient'
import { checkedBootstrap } from './bootstrapClient'

type Base = { version: 1; workspace_id: string; actor_session_id: string; command_id: string; target_id: string; error: { status: number; code: string | null } | null }
export type OutboundCommand = Base & (
 { kind: 'preview'; route: 'POST /api/v1/codex/consent-previews'; basis: { preparation: CodexTurnPreparationView; control: CodexTurnControlView; provider: ProviderConfigView }; body: CodexOutboundPreviewWrite; ack: CodexConsentProposalView | null }
 | { kind: 'grant'; route: 'POST /api/v1/codex/consents'; basis: { preparation: CodexTurnPreparationView; proposal: CodexConsentProposalView }; body: CodexConsentCreateWrite; ack: CodexConsentCreateAck | null }
 | { kind: 'revoke'; route: 'POST /api/v1/codex/consents/{id}/revoke'; basis: CodexTurnControlView; body: ConsentRevoke; ack: MutationAck | null }
 | { kind: 'start'; route: 'POST /api/v1/codex/sessions/{id}/turns'; basis: { preparation: CodexTurnPreparationView; current: CodexCurrentSessionView; consent: CodexConsentView }; body: CodexTurnStartWrite; ack: CodexTurnStartAck | null })
type Input<T> = T extends OutboundCommand ? Omit<T, keyof Base | 'route' | 'ack'> : never
export type OutboundCommandInput = Input<OutboundCommand>
const routes = { preview: 'POST /api/v1/codex/consent-previews', grant: 'POST /api/v1/codex/consents', revoke: 'POST /api/v1/codex/consents/{id}/revoke', start: 'POST /api/v1/codex/sessions/{id}/turns' } as const
const fail = (): never => { throw new Error('外发原命令、只读基准或完整回执无法核验；本机记录保留。') }
function boundSummary(s: CodexFrozenOutboundSummary, p: CodexTurnPreparationView) {
 if (s.preparation_id !== p.id || s.preparation_sha256 !== p.preparation_sha256 || s.session_id !== p.session_id || s.turn_id !== p.turn_id || s.job_id !== p.job.id
  || s.provider_id !== p.request.provider_id || s.context_snapshot_id !== p.summary.context_snapshot_id || s.context_snapshot_sha256 !== p.summary.snapshot_sha256
  || s.source_input_sha256 !== p.summary.job_input_sha256 || s.input_sha256 !== p.summary.prepared_input_sha256 || !sameValue(s.references, p.summary.materials)
  || !sameValue(s.tools, p.summary.tools) || !sameValue(s.runtime, p.summary.runtime)) fail()
}
export const outboundStore = new DraftStore({ name: 'learning-workbench.codex-outbound-commands.v1' })
export function decodeOutboundCommand(raw: string, workspace: string): OutboundCommand {
 const c = JSON.parse(raw) as OutboundCommand
 if (!exactObject(c, ['version', 'kind', 'route', 'workspace_id', 'actor_session_id', 'command_id', 'target_id', 'basis', 'body', 'ack', 'error']) || c.version !== 1 || c.workspace_id !== workspace || !turnIdentity(workspace)
  || !turnIdentity(c.actor_session_id) || !turnIdentity(c.command_id) || !turnIdentity(c.target_id) || !Object.hasOwn(routes, c.kind) || c.route !== routes[c.kind]) fail()
 if (c.error !== null && (!exactObject(c.error, ['status', 'code']) || !Number.isSafeInteger(c.error.status) || c.error.status < 400 || c.error.status > 599
  || c.ack !== null || c.error.code !== null && (typeof c.error.code !== 'string' || !/^[A-Z][A-Z0-9_]{0,79}$/.test(c.error.code) || c.error.code.trim() !== c.error.code))) throw new Error('Invalid outbound error')
 if (c.kind === 'revoke') {
  const basis = checkedTurn('CodexTurnControlView', c.basis); checkedProvider('ConsentRevoke', c.body)
  if (!basis.consent_control || c.target_id !== basis.consent_control.id || c.body.expected_revision !== basis.consent_control.revision) fail()
  if (c.ack !== null) { checkedProvider('MutationAck', c.ack); if (c.ack.id !== c.target_id || c.ack.revision !== 2 || c.ack.applied !== (basis.consent_control!.status !== 'revoked')) fail() }
 } else {
  const keys = c.kind === 'preview' ? ['preparation', 'control', 'provider'] : c.kind === 'grant' ? ['preparation', 'proposal'] : ['preparation', 'current', 'consent']
  if (!exactObject(c.basis, keys)) fail()
  const p = checkedTurn('CodexTurnPreparationView', c.basis.preparation)
  if (p.actor_session_id !== c.actor_session_id) fail()
  if (c.kind === 'preview') {
   const control = checkedTurn('CodexTurnControlView', c.basis.control), config = checkedProvider<ProviderConfigView>('ProviderConfigView', c.basis.provider), body = checkedOutbound('CodexOutboundPreviewWrite', c.body)
   if (c.target_id !== p.id || p.validity !== 'current' || p.proposal_id !== null || p.consent_id !== null || control.id !== p.turn_id || control.session_id !== p.session_id
    || control.actor_session_id !== c.actor_session_id || control.job.id !== p.job.id || control.job.status !== 'awaiting_approval' || control.execution !== 'not_started' || control.cancel_requested
    || config.id !== p.request.provider_id || body.preparation_id !== p.id || body.preparation_sha256 !== p.preparation_sha256
    || body.expected_job_revision !== control.job_revision || body.expected_provider_revision !== config.revision) fail()
   if (c.ack !== null) {
    const ack = checkedOutbound('CodexConsentProposalView', c.ack), s = ack.summary; boundSummary(s, p)
    if (ack.consent_id !== null || s.source_job_revision !== control.job_revision || s.provider_revision !== config.revision || s.config_sha256 !== config.config_sha256
     || s.model !== config.model || s.endpoint_policy !== config.endpoint_policy || !sameValue(s.budget, body.budget) || s.expires_at !== body.expires_at) fail()
   }
  } else if (c.kind === 'grant') {
   const proposal = checkedOutbound('CodexConsentProposalView', c.basis.proposal), body = checkedOutbound('CodexConsentCreateWrite', c.body)
   boundSummary(proposal.summary, p)
   if (c.target_id !== proposal.id || proposal.validity !== 'current' || proposal.consent_id !== null || body.proposal_id !== proposal.id || body.proposal_sha256 !== proposal.proposal_sha256) fail()
   if (c.ack !== null) {
    const ack = checkedOutbound('CodexConsentCreateAck', c.ack)
    if (ack.actor_session_id !== c.actor_session_id || ack.proposal_id !== proposal.id || ack.proposal_sha256 !== proposal.proposal_sha256 || !sameValue(ack.summary, proposal.summary)) fail()
   }
  } else {
   const current = checkedBootstrap<CodexCurrentSessionView>('CodexCurrentSessionView', c.basis.current), consent = checkedOutbound('CodexConsentView', c.basis.consent), body = checkedOutbound('CodexTurnStartWrite', c.body)
   boundSummary(consent.summary, p)
   if (c.target_id !== p.session_id || current.id !== p.session_id || current.active_turn_id !== p.turn_id || current.status !== 'ready'
    || consent.actor_session_id !== c.actor_session_id || consent.status !== 'active' || consent.dispatch !== null || body.consent_id !== consent.id
    || body.preparation_id !== p.id || body.preparation_sha256 !== p.preparation_sha256 || body.expected_session_revision !== current.revision) fail()
   if (c.ack !== null) {
    const ack = checkedOutbound('CodexTurnStartAck', c.ack)
    if (ack.turn_id !== p.turn_id || ack.job.id !== p.job.id || ack.session_revision !== current.revision + 1) fail()
   }
  }
 }
 return c
}
export function outboundRevokeCommand(workspace: string, actor: string, basis: CodexTurnControlView): OutboundCommand {
 return decodeOutboundCommand(JSON.stringify({ version: 1, kind: 'revoke', route: 'POST /api/v1/codex/consents/{id}/revoke', workspace_id: workspace, actor_session_id: actor,
  command_id: `codexout_${crypto.randomUUID()}`, target_id: basis.consent_control?.id, basis, body: { expected_revision: basis.consent_control?.revision }, ack: null, error: null }), workspace)
}
function commandFromInput(workspace: string, actor: string, input: OutboundCommandInput, key: string): OutboundCommand {
 const target = input.kind === 'revoke' ? input.basis.consent_control?.id : input.kind === 'preview' ? input.basis.preparation.id : input.kind === 'grant' ? input.basis.proposal.id : input.basis.current.id
 return decodeOutboundCommand(JSON.stringify({ ...input, version: 1, workspace_id: workspace, actor_session_id: actor, command_id: key, target_id: target, route: routes[input.kind], ack: null, error: null }), workspace)
}
export function validateOutboundInput(workspace: string, actor: string, input: OutboundCommandInput): void { commandFromInput(workspace, actor, input, 'codexout_validation') }
export function makeOutboundCommand(workspace: string, actor: string, input: OutboundCommandInput): OutboundCommand { return commandFromInput(workspace, actor, input, `codexout_${crypto.randomUUID()}`) }
const immutable = (value: OutboundCommand) => ({ ...value, ack: null, error: null })
export function readOutboundCommand(record: DraftRecord, workspace: string): OutboundCommand {
 const values = [record.text, ...record.conflicts.map(v => v.text)].map(raw => decodeOutboundCommand(raw, workspace)), first = values[0]
 if (first.command_id !== record.objectId || values.some(v => !sameValue(immutable(v), immutable(first)))) throw new Error('Conflicting original outbound command')
 const confirmed = values.filter(v => v.ack)
 if (confirmed.some(v => !sameValue(v.ack, confirmed[0].ack))) throw new Error('Conflicting outbound ACK')
 return confirmed[0] ?? values.find(v => v.error) ?? first
}
export async function persistOutboundCommand(command: OutboundCommand, store = outboundStore, guard?: DraftWriteGuard): Promise<OutboundCommand> {
 let desired = decodeOutboundCommand(JSON.stringify(command), command.workspace_id)
 for (let attempt = 0; attempt < 4; attempt++) {
  assertDraftWriteAllowed(guard)
  const old = (await store.load(command.workspace_id))[command.command_id]
  assertDraftWriteAllowed(guard)
  if (old) {
   const current = readOutboundCommand(old, command.workspace_id)
   if (!sameValue(immutable(current), immutable(desired)) || current.ack && desired.ack && !sameValue(current.ack, desired.ack)) throw new Error('Cannot replace original outbound command or ACK')
   if (current.ack || !desired.ack && !desired.error && current.error) desired = current
   if (!old.conflicts.length && sameValue(current, desired)) return current
  }
  const saved = await store.save(command.workspace_id, command.command_id, JSON.stringify(desired), old?.revision ?? 0, old?.conflicts.map(v => v.id) ?? [], guard)
  const actual = readOutboundCommand(saved.record, command.workspace_id)
  if (!saved.record.conflicts.length && sameValue(actual, desired)) return actual
 }
 throw new Error('Concurrent outbound command remains unresolved')
}
export async function dispatchOutboundCommand(command: OutboundCommand, port: TurnOutboundPort, store = outboundStore,
 options: { guard?: DraftWriteGuard; beforePost?: () => Promise<void>; onAck?: (ack: OutboundCommand) => void; beforeDelivery?: () => Promise<void> } = {}): Promise<OutboundCommand> {
 const original = await persistOutboundCommand(command, store, options.guard)
 if (original.ack) { await options.beforeDelivery?.(); return original }
 await options.beforePost?.(); assertDraftWriteAllowed(options.guard)
 const raw = original.kind === 'preview' ? await port.preview(original.body, original.command_id)
  : original.kind === 'grant' ? await port.grant(original.body, original.command_id)
   : original.kind === 'start' ? await port.start(original.target_id, original.body, original.command_id)
    : await port.revoke(original.target_id, original.body, original.command_id)
 const acknowledged = decodeOutboundCommand(JSON.stringify({ ...original, ack: raw, error: null }), original.workspace_id)
 options.onAck?.(acknowledged)
 await options.beforeDelivery?.()
 return persistOutboundCommand(acknowledged, store, options.guard)
}
