import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'
import type { ConsentRevoke, MutationAck, ProviderConfigView } from '../../../../../packages/contracts/generated/api-types'
import type { CodexConsentCreateAck, CodexConsentCreateWrite, CodexConsentProposalView, CodexConsentView, CodexFrozenOutboundSummary, CodexOutboundPreviewWrite, CodexTurnResultView, CodexTurnStartAck, CodexTurnStartWrite } from '../../../../../packages/contracts/generated/codex-turn-types'
import schemas from '../../../../../packages/contracts/generated/codex-turn-schemas.json'
import { request } from '../../api/client'
import { checkedProvider, sameValue } from '../providers/providerSchema'
import { providerClient } from '../providers/providerClient'
import { checkedTurn, turnClient, type TurnPort } from './turnClient'
import { turnIdentity } from './turnCommands'

type Wire = { CodexOutboundPreviewWrite: CodexOutboundPreviewWrite; CodexConsentProposalView: CodexConsentProposalView; CodexConsentCreateWrite: CodexConsentCreateWrite; CodexConsentCreateAck: CodexConsentCreateAck; CodexConsentView: CodexConsentView; CodexTurnStartWrite: CodexTurnStartWrite; CodexTurnStartAck: CodexTurnStartAck; CodexTurnResultView: CodexTurnResultView }
const fail = (): never => { throw new Error('Codex 外发记录不符合闭合契约或原对象；本机原命令保留。') }
const id = (value: string) => { if (!turnIdentity(value)) fail(); return value }
function instant(value: string): bigint {
 const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?Z$/.exec(value), result = Date.parse(match?.[1] + 'Z')
 if (!match || value.trim() !== value || value.startsWith('0000') || !Number.isFinite(result) || new Date(result).toISOString().slice(0, 19) !== match[1]) fail()
 return BigInt(result) * 1000n + BigInt((match![2] ?? '').slice(0, 6).padEnd(6, '0'))
}
export function outboundTime(value: string): number { return Number(instant(value)) / 1000 }
function summary(value: CodexFrozenOutboundSummary) {
 const duration = instant(value.expires_at) - instant(value.created_at), proof = value.input_token_assurance
 const tokens = proof.kind === 'local_exact' ? proof.input_tokens : proof.input_tokens_upper_bound
 if (duration <= 0n || duration > 600000000n || proof.request_body_sha256 !== value.request_body_sha256 || tokens > value.budget.max_input_tokens
  || value.cost_estimate.kind === 'estimated' && value.budget.max_cost_usd !== null && value.cost_estimate.maximum_estimated_cost > value.budget.max_cost_usd) fail()
 const endpoint = new URL(value.endpoint)
 if (!['http:', 'https:'].includes(endpoint.protocol) || !endpoint.hostname || endpoint.username || endpoint.password || endpoint.hash || endpoint.search
  || /[\x00-\x20\x7f\\]/.test(value.endpoint) || value.endpoint.split('/')[2]?.includes('@') || endpoint.port === '0'
  || value.endpoint_policy === 'public_https' && endpoint.protocol !== 'https:'
  || value.endpoint_policy === 'explicit_loopback' && !['127.0.0.1', 'localhost', '[::1]'].includes(endpoint.hostname)) fail()
 const refs = value.references.map(v => [v.ref.entity, v.ref.id, v.ref.revision])
 if (value.references.some(v => v.ref.entity !== 'block') || new Set(refs.map(v => JSON.stringify(v))).size !== refs.length) fail()
}
export function checkedOutbound<N extends keyof Wire>(name: N, raw: unknown): Wire[N] {
 const value = checkedProvider<Wire[N]>(name, raw, schemas.schemas)
 if (name === 'CodexOutboundPreviewWrite') outboundTime((value as CodexOutboundPreviewWrite).expires_at)
 if ('summary' in value) summary(value.summary)
 if (name === 'CodexConsentProposalView') {
  const p = value as CodexConsentProposalView
  if (new Set(p.warnings.map(v => v.code)).size !== p.warnings.length) fail()
 }
 if (name === 'CodexConsentView') {
  const c = value as CodexConsentView, created = instant(c.created_at)
  if (c.expires_at !== c.summary.expires_at || created < instant(c.summary.created_at) || created >= instant(c.expires_at)
   || (c.status === 'revoked') !== (c.revoked_at !== null) || c.revoked_at && instant(c.revoked_at) < created
   || c.revision !== (c.status === 'revoked' ? 2 : 1) || c.dispatch && c.dispatch.job.id !== c.summary.job_id) fail()
  if (c.dispatch) {
   const d = c.dispatch
   if ((d.finished_at === null) !== (d.outcome === null) || d.outcome === 'completed' && d.error_code !== null) fail()
   if (d.started_at) instant(d.started_at)
   if (d.finished_at && (instant(d.finished_at) < created || d.started_at && instant(d.finished_at) < instant(d.started_at))) fail()
  }
 }
 if (name === 'CodexTurnStartAck' && (value as CodexTurnStartAck).job.status !== 'queued') fail()
 if (name === 'CodexTurnResultView') {
  const r = value as CodexTurnResultView; checkedTurn('CodexTurnControlView', r.control)
  const digest = r.answer_markdown === '' ? null : bytesToHex(sha256(new TextEncoder().encode(r.answer_markdown)))
  if (r.output_sha256 !== digest || (r.output_state === 'none') !== (digest === null)
   || r.output_state === 'complete' && r.control.outcome !== 'completed' || digest !== null && r.control.outcome === 'completed' && r.output_state !== 'complete') fail()
 }
 return value
}
export type TurnOutboundPort = Pick<TurnPort, 'session' | 'current' | 'preparation' | 'control'> & {
 config(id: string): Promise<ProviderConfigView>
 preview(body: CodexOutboundPreviewWrite, key: string): Promise<CodexConsentProposalView>
 proposal(id: string): Promise<CodexConsentProposalView>
 grant(body: CodexConsentCreateWrite, key: string): Promise<CodexConsentCreateAck>
 consent(id: string): Promise<CodexConsentView>
 revoke(id: string, body: ConsentRevoke, key: string): Promise<MutationAck>
 start(id: string, body: CodexTurnStartWrite, key: string): Promise<CodexTurnStartAck>
 result(id: string): Promise<CodexTurnResultView>
}
export const turnOutboundClient: TurnOutboundPort = {
 session: turnClient.session, current: turnClient.current, preparation: turnClient.preparation, control: turnClient.control,
 config: async target => { const v = await providerClient.config(id(target)); if (v.id !== target) fail(); return v },
 preview: async (body, key) => {
  const b = checkedOutbound('CodexOutboundPreviewWrite', body), v = checkedOutbound('CodexConsentProposalView', await request('POST /api/v1/codex/consent-previews', b, { 'Idempotency-Key': key }))
  if (v.summary.preparation_id !== b.preparation_id || v.summary.preparation_sha256 !== b.preparation_sha256 || v.summary.source_job_revision !== b.expected_job_revision
   || v.summary.provider_revision !== b.expected_provider_revision || !sameValue(v.summary.budget, b.budget) || v.summary.expires_at !== b.expires_at) fail()
  return v
 },
 proposal: async target => { const v = checkedOutbound('CodexConsentProposalView', await request('GET /api/v1/codex/consent-proposals/{id}', undefined, undefined, { path: { id: id(target) } })); if (v.id !== target) fail(); return v },
 grant: async (body, key) => {
  const b = checkedOutbound('CodexConsentCreateWrite', body), v = checkedOutbound('CodexConsentCreateAck', await request('POST /api/v1/codex/consents', b, { 'Idempotency-Key': key }))
  if (v.proposal_id !== b.proposal_id || v.proposal_sha256 !== b.proposal_sha256) fail(); return v
 },
 consent: async target => { const v = checkedOutbound('CodexConsentView', await request('GET /api/v1/codex/consents/{id}', undefined, undefined, { path: { id: id(target) } })); if (v.id !== target) fail(); return v },
 revoke: async (target, body, key) => {
  const b = checkedProvider<ConsentRevoke>('ConsentRevoke', body), v = checkedProvider<MutationAck>('MutationAck', await request('POST /api/v1/codex/consents/{id}/revoke', b, { 'Idempotency-Key': key }, { path: { id: id(target) } }))
  if (v.id !== target) fail(); return v
 },
 start: async (target, body, key) => {
  const b = checkedOutbound('CodexTurnStartWrite', body), v = checkedOutbound('CodexTurnStartAck', await request('POST /api/v1/codex/sessions/{id}/turns', b, { 'Idempotency-Key': key }, { path: { id: id(target) } }))
  if (v.session_revision !== b.expected_session_revision + 1) fail(); return v
 },
 result: async target => { const v = checkedOutbound('CodexTurnResultView', await request('GET /api/v1/codex/turns/{id}/result', undefined, undefined, { path: { id: id(target) } })); if (v.control.id !== target) fail(); return v },
}
