import { vi } from 'vitest'
import type { ConsentPage, ConsentProposalView, ConsentView, ProviderConfigView, ProviderConfigWrite } from '../../../../../packages/contracts/generated/api-types'
import { ApiError } from '../../api/client'
import type { ProviderPort } from './providerClient'
import { checkedProvider } from './providerSchema'

export const configFixture = (revision = 1): ProviderConfigView => ({ id: 'provider_test', revision, config_sha256: revision.toString(16).padStart(64, '0'), adapter: 'official_responses', base_url: 'https://example.invalid/v1', model: `synthetic-model-${revision}`, embedding_model: null, endpoint_policy: 'public_https', pricing: null, configured: true, secret_present: false })
export const writeFixture = (base: ProviderConfigView): ProviderConfigWrite => ({ expected_revision: base.revision, adapter: base.adapter, base_url: base.base_url, model: 'my-model-candidate', embedding_model: base.embedding_model, endpoint_policy: base.endpoint_policy, pricing: base.pricing })
export function proposalFixture(): ConsentProposalView {
  return checkedProvider('ConsentProposalView', { id: 'proposal_test', proposal_sha256: 'a'.repeat(64), validity: 'current', consent_id: null, warnings: [{ code: 'price_unknown', message: '合成未知价格' }], summary: { job_id: 'job_test', source_job_revision: 1, source_input_sha256: 'b'.repeat(64), purpose: 'tutor', provider_id: 'provider_test', provider_revision: 1, config_sha256: configFixture().config_sha256, adapter: 'official_responses', adapter_version: 'synthetic-v1', base_url: 'https://example.invalid/v1', endpoint_policy: 'public_https', model: 'synthetic-model-1', context_snapshot_id: 'context_test', context_snapshot_sha256: 'c'.repeat(64), input_sha256: 'd'.repeat(64), messages: [{ role: 'user', character_count: 2, content_sha256: 'e'.repeat(64) }], references: [], input_character_count: 2, input_token_assurance: { kind: 'local_upper_bound', input_tokens_upper_bound: 8, checker_version: 'synthetic-v1', proof_sha256: 'f'.repeat(64), request_body_sha256: '1'.repeat(64) }, allow_web: false, budget: { max_input_tokens: 10, max_output_tokens: 20, max_provider_calls: 1, max_search_calls: 0, max_tool_calls: 0, timeout_seconds: 180, max_cost_usd: null }, cost_estimate: { kind: 'unknown', currency: 'USD' }, created_at: '2026-09-15T01:00:00Z', expires_at: '2099-09-15T02:00:00Z' } })
}
export function consentFixture(revision = 1): ConsentView { const proposal = proposalFixture(); return { id: 'consent_test', revision, status: revision === 1 ? 'active' : 'revoked', proposal_id: proposal.id, proposal_sha256: proposal.proposal_sha256, summary: proposal.summary, created_at: proposal.summary.created_at, expires_at: proposal.summary.expires_at, revoked_at: revision === 1 ? null : '2026-09-15T02:00:00Z', dispatch: null } }
export const pageFixture = (items: ConsentView[] = []): ConsentPage => ({ items, next_cursor: null })
export function providerFixture() {
  let config = configFixture(), consent = consentFixture(), proposal = proposalFixture()
  const configReceipts = new Map<string, { body: string; ack: { id: string; revision: number; config_sha256: string; configured: true; secret_present: boolean } }>()
  const port: ProviderPort = {
    capabilities: vi.fn(async () => ({ items: [{ provider_id: config.id, configured: true, chat: false, structured_output: false, web_search: false, streaming: false, tool_calls: false, version_evidence: 'INPUT_BOUND_UNAVAILABLE：仅合成单元配置，非生产证明' }] })),
    config: vi.fn(async id => { if (id !== config.id) throw new ApiError(404, 'not found'); return structuredClone(config) }),
    saveConfig: vi.fn(async (id, body, key) => {
      const old = configReceipts.get(key)
      if (old) { if (old.body !== JSON.stringify(body)) throw new ApiError(409, 'mismatch'); return old.ack }
      if (id !== config.id || body.expected_revision !== config.revision) throw new ApiError(412, 'stale')
      const { expected_revision, ...fields } = body
      config = { ...configFixture(expected_revision + 1), ...fields, secret_present: config.secret_present }
      const ack = { id, revision: config.revision, config_sha256: config.config_sha256, configured: true as const, secret_present: config.secret_present }
      configReceipts.set(key, { body: JSON.stringify(body), ack }); return ack
    }),
    saveSecret: vi.fn(async (id, body) => { if (body.expected_revision !== config.revision) throw new ApiError(412, 'stale'); config = { ...configFixture(config.revision + 1), secret_present: true }; return { id, revision: config.revision, config_sha256: config.config_sha256, secret_present: true } }),
    deleteSecret: vi.fn(async (id, sha) => { if (sha !== config.config_sha256) throw new ApiError(412, 'stale'); config = { ...configFixture(config.revision + (config.secret_present ? 1 : 0)), secret_present: false }; return { id, revision: config.revision, config_sha256: config.config_sha256, secret_present: false } }),
    preview: vi.fn(async () => structuredClone(proposal)), proposal: vi.fn(async () => structuredClone(proposal)),
    grant: vi.fn(async body => { proposal = { ...proposal, consent_id: consent.id }; return { id: consent.id, revision: 1, status: 'active', ...body, summary: structuredClone(proposal.summary) } }),
    consents: vi.fn(async () => pageFixture([structuredClone(consent)])),
    revoke: vi.fn(async (id, body) => { if (body.expected_revision !== consent.revision) throw new ApiError(412, 'stale'); const applied = consent.status !== 'revoked'; consent = consentFixture(consent.revision + (applied ? 1 : 0)); return { id, revision: consent.revision, applied } }),
  }
  return { port, current: () => config, currentConsent: () => consent, external: (value: ProviderConfigView) => { config = value } }
}
