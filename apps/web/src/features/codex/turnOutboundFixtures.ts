import type { ProviderConfigView } from '../../../../../packages/contracts/generated/api-types'
import type { CodexConsentCreateAck, CodexConsentProposalView, CodexConsentView, CodexCurrentSessionView, CodexOutboundPreviewWrite, CodexTurnControlView } from '../../../../../packages/contracts/generated/codex-turn-types'
import { actor, codexSession } from './bootstrapTestFixtures'
import { turnControl, turnPreparation } from './turnTestFixtures'
export const outboundPreparation = () => ({ ...turnPreparation(), validity: 'current' as const })
export const outboundProvider = (): ProviderConfigView => ({ id: 'codex_local', revision: 1, config_sha256: 'b'.repeat(64), adapter: 'official_responses', base_url: 'https://synthetic.example.test/v1', model: 'synthetic-model', embedding_model: null, endpoint_policy: 'public_https', pricing: null, configured: true, secret_present: true })
export const outboundCurrent = (): CodexCurrentSessionView => ({ ...codexSession(), revision: 3, active_turn_id: 'turn_test' })
export const previewBody = (): CodexOutboundPreviewWrite => ({ preparation_id: 'turn_preparation_test', preparation_sha256: 'a'.repeat(64), expected_job_revision: 1, expected_provider_revision: 1,
 budget: { max_input_tokens: 1000, max_output_tokens: 100, max_provider_calls: 1, max_search_calls: 0, max_cost_usd: null }, expires_at: '2026-10-04T00:10:00Z' })
export const outboundProposal = (): CodexConsentProposalView => ({ id: 'proposal_turn', proposal_sha256: 'c'.repeat(64), validity: 'current', consent_id: null, warnings: [], summary: {
 version: 'codex-outbound-summary-v1', preparation_id: 'turn_preparation_test', preparation_sha256: 'a'.repeat(64), session_id: 'codex_session_test', turn_id: 'turn_test', job_id: 'job_turn_test',
 source_job_revision: 1, source_input_sha256: 'a'.repeat(64), provider_id: 'codex_local', provider_revision: 1, config_sha256: 'b'.repeat(64), adapter: 'codex_app_server', adapter_version: 'synthetic-protocol-peer/v1',
 endpoint: 'https://synthetic.example.test/v1/responses', endpoint_policy: 'public_https', model: 'synthetic-model', context_snapshot_id: 'snapshot_test', context_snapshot_sha256: 'a'.repeat(64), input_sha256: 'a'.repeat(64), request_body_sha256: 'e'.repeat(64),
 messages: [{ role: 'system', character_count: 50, content_sha256: 'f'.repeat(64) }, { role: 'user', character_count: 50, content_sha256: 'a'.repeat(64) }], references: [], input_character_count: 100,
 input_token_assurance: { kind: 'local_exact', input_tokens: 50, checker_version: 'synthetic-counter/v1', proof_sha256: 'f'.repeat(64), request_body_sha256: 'e'.repeat(64) },
 budget: previewBody().budget, tools: outboundPreparation().summary.tools, runtime: outboundPreparation().summary.runtime, cost_estimate: { kind: 'unknown', currency: 'USD' }, created_at: '2026-10-04T00:00:00Z', expires_at: previewBody().expires_at,
} })
export const outboundGrant = (): CodexConsentCreateAck => ({ id: 'codexconsent_original', revision: 1, status: 'active', actor_session_id: actor, proposal_id: 'proposal_turn', proposal_sha256: 'c'.repeat(64), summary: outboundProposal().summary })
export const outboundConsent = (): CodexConsentView => ({ ...outboundGrant(), created_at: '2026-10-04T00:00:01Z', expires_at: previewBody().expires_at, revoked_at: null, dispatch: null })
export const outboundControl = (): CodexTurnControlView => ({ ...turnControl(), consent_control: { id: 'codexconsent_original', revision: 1, status: 'active' as const } })
