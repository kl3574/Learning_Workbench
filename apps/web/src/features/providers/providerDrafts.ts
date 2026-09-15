import type { ConsentCreate, ConsentCreateAck, ConsentPreviewWrite, ConsentProposalView, ConsentRevoke, MutationAck, ProviderConfigAck, ProviderConfigView, ProviderConfigWrite } from '../../../../../packages/contracts/generated/api-types'
import { DraftStore } from '../../workbench/DraftStore'
import { createResponseDraftJournal } from '../../shared/createResponseDraftJournal'
import { checkedProvider, exactObject, sameValue, validIdentity } from './providerSchema'

type Identity = { version: 1; workspace_id: string; command_id: string }
export type ConfigCommand = Identity & { kind: 'config'; provider_id: string; base: ProviderConfigView | null; body: ProviderConfigWrite; ack: ProviderConfigAck | null }
export type PreviewCommand = Identity & { kind: 'preview'; body: ConsentPreviewWrite; ack: ConsentProposalView | null }
export type GrantCommand = Identity & { kind: 'grant'; proposal: ConsentProposalView; body: ConsentCreate; ack: ConsentCreateAck | null }
export type RevokeCommand = Identity & { kind: 'revoke'; consent_id: string; body: ConsentRevoke; ack: MutationAck | null }
export type ProviderCommand = ConfigCommand | PreviewCommand | GrantCommand | RevokeCommand
export type CommandInput = Omit<ConfigCommand, keyof Identity | 'ack'> | Omit<PreviewCommand, keyof Identity | 'ack'> | Omit<GrantCommand, keyof Identity | 'ack'> | Omit<RevokeCommand, keyof Identity | 'ack'>
export const commandKey = (value: ProviderCommand) => value.kind === 'config' ? `config:${value.provider_id}` : value.kind === 'preview' ? `preview:${value.body.job_id}` : value.kind === 'grant' ? `grant:${value.body.proposal_id}` : `revoke:${value.consent_id}`
export const commandSubject = (value: ProviderCommand) => value.kind === 'preview' || value.kind === 'grant'
export const commandDirty = (value: ProviderCommand) => value.ack === null
export const commandIdentity = (workspace: string): Identity => ({ version: 1, workspace_id: workspace, command_id: `provider_${crypto.randomUUID()}` })
export function newCommand(workspace: string, value: CommandInput): ProviderCommand { return decodeCommand(JSON.stringify({ ...value, ...commandIdentity(workspace), ack: null }), workspace) }
export function decodeCommand(raw: string, workspace: string): ProviderCommand {
  const parsed: unknown = JSON.parse(raw)
  const common = ['version', 'workspace_id', 'command_id', 'kind', 'body', 'ack']
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed) || !('kind' in parsed)) throw new Error('配置或授权候选无效；原记录保留。')
  const value = parsed as Record<string, unknown>
  const kind = value.kind, keys = kind === 'config' ? [...common, 'provider_id', 'base'] : kind === 'grant' ? [...common, 'proposal'] : kind === 'revoke' ? [...common, 'consent_id'] : kind === 'preview' ? common : []
  if (!exactObject(value, keys) || value.version !== 1 || value.workspace_id !== workspace || !validIdentity(value.command_id)) throw new Error('配置或授权候选身份不匹配；原记录保留。')
  const fail = () => { throw new Error('原命令、版本与回执不一致；未替换为当前状态。') }
  if (kind === 'config') {
    if (!validIdentity(value.provider_id)) fail()
    const body = checkedProvider<ProviderConfigWrite>('ProviderConfigWrite', value.body)
    const base = value.base === null ? null : checkedProvider<ProviderConfigView>('ProviderConfigView', value.base)
    if (body.expected_revision !== (base?.revision ?? 0) || base && base.id !== value.provider_id) fail()
    if (value.ack !== null) { const ack = checkedProvider<ProviderConfigAck>('ProviderConfigAck', value.ack); if (ack.id !== value.provider_id || ack.revision !== body.expected_revision + 1 || ack.secret_present !== (base?.secret_present ?? false)) fail() }
  } else if (kind === 'preview') {
    const body = checkedProvider<ConsentPreviewWrite>('ConsentPreviewWrite', value.body)
    if (value.ack !== null) {
      const ack = checkedProvider<ConsentProposalView>('ConsentProposalView', value.ack), summary = ack.summary
      if (summary.job_id !== body.job_id || summary.source_job_revision !== body.expected_job_revision || summary.provider_id !== body.provider_id || summary.provider_revision !== body.expected_provider_revision || !sameValue(summary.budget, { ...body.budget, timeout_seconds: body.budget.timeout_seconds ?? 180 }) || summary.expires_at !== body.expires_at) fail()
    }
  } else if (kind === 'grant') {
    const body = checkedProvider<ConsentCreate>('ConsentCreate', value.body), proposal = checkedProvider<ConsentProposalView>('ConsentProposalView', value.proposal)
    if (body.proposal_id !== proposal.id || body.proposal_sha256 !== proposal.proposal_sha256) fail()
    if (value.ack !== null) { const ack = checkedProvider<ConsentCreateAck>('ConsentCreateAck', value.ack); if (ack.proposal_id !== body.proposal_id || ack.proposal_sha256 !== body.proposal_sha256 || !sameValue(ack.summary, proposal.summary)) fail() }
  } else {
    if (!validIdentity(value.consent_id)) fail()
    const body = checkedProvider<ConsentRevoke>('ConsentRevoke', value.body)
    if (value.ack !== null) { const ack = checkedProvider<MutationAck>('MutationAck', value.ack); if (ack.id !== value.consent_id || ack.revision !== body.expected_revision + (ack.applied ? 1 : 0)) fail() }
  }
  return value as ProviderCommand
}
export const providerCommandStore = new DraftStore({ name: 'learning-workbench.provider-commands.v1' })
export const useProviderJournal = createResponseDraftJournal({ store: providerCommandStore, decode: decodeCommand, key: commandKey, dirty: commandDirty })
