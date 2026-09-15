import type { ConsentCreate, ConsentCreateAck, ConsentPage, ConsentPreviewWrite, ConsentProposalView, ConsentRevoke, MutationAck, ProviderCapabilitiesResponse, ProviderConfigAck, ProviderConfigView, ProviderConfigWrite, ProviderSecretAck, ProviderSecretWrite } from '../../../../../packages/contracts/generated/api-types'
import type { ProviderConsentQuery } from '../../../../../packages/contracts/generated/provider-ports-binding'
import { request } from '../../api/client'
import { checkedProvider } from './providerSchema'

export type ProviderPort = {
  capabilities(): Promise<ProviderCapabilitiesResponse>
  config(id: string): Promise<ProviderConfigView>
  saveConfig(id: string, body: ProviderConfigWrite, key: string): Promise<ProviderConfigAck>
  saveSecret(id: string, body: ProviderSecretWrite, key: string): Promise<ProviderSecretAck>
  deleteSecret(id: string, sha256: string, key: string): Promise<ProviderSecretAck>
  preview(body: ConsentPreviewWrite, key: string): Promise<ConsentProposalView>
  proposal(id: string): Promise<ConsentProposalView>
  grant(body: ConsentCreate, key: string): Promise<ConsentCreateAck>
  consents(query: ProviderConsentQuery): Promise<ConsentPage>
  revoke(id: string, body: ConsentRevoke, key: string): Promise<MutationAck>
}
export function configIfMatch(sha256: string): string {
  if (!/^[a-f0-9]{64}$/.test(sha256)) throw new Error('缺少实际读回的配置版本，未删除秘密引用。')
  return `"${sha256}"`
}
export const providerClient: ProviderPort = {
  capabilities: async () => checkedProvider('ProviderCapabilitiesResponse', await request('GET /api/v1/providers/capabilities', undefined)),
  config: async id => checkedProvider('ProviderConfigView', await request('GET /api/v1/providers/{id}/config', undefined, undefined, { path: { id } })),
  saveConfig: async (id, body, key) => checkedProvider('ProviderConfigAck', await request('PUT /api/v1/providers/{id}/config', body, { 'Idempotency-Key': key }, { path: { id } })),
  saveSecret: async (id, body, key) => checkedProvider('ProviderSecretAck', await request('POST /api/v1/providers/{id}/secret', body, { 'Idempotency-Key': key }, { path: { id } })),
  deleteSecret: async (id, sha256, key) => checkedProvider('ProviderSecretAck', await request('DELETE /api/v1/providers/{id}/secret', undefined, { 'Idempotency-Key': key, 'If-Match': configIfMatch(sha256) }, { path: { id } })),
  preview: async (body, key) => checkedProvider('ConsentProposalView', await request('POST /api/v1/consents/preview', body, { 'Idempotency-Key': key })),
  proposal: async id => checkedProvider('ConsentProposalView', await request('GET /api/v1/consents/preview/{id}', undefined, undefined, { path: { id } })),
  grant: async (body, key) => checkedProvider('ConsentCreateAck', await request('POST /api/v1/consents', body, { 'Idempotency-Key': key })),
  consents: async query => checkedProvider('ConsentPage', await request('GET /api/v1/consents', undefined, undefined, { query })),
  revoke: async (id, body, key) => checkedProvider('MutationAck', await request('POST /api/v1/consents/{id}/revoke', body, { 'Idempotency-Key': key }, { path: { id } })),
}
