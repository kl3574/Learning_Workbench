import { afterEach, expect, test, vi } from 'vitest'
import { providerClient, configIfMatch } from './providerClient'
import { configFixture, pageFixture, proposalFixture, writeFixture } from './testFixtures'
afterEach(() => vi.unstubAllGlobals())
test('all ten operations use the actual generated local client and exact headers/body boundaries', async () => {
  const config = configFixture(), proposal = proposalFixture(), requests: { path: string; init: RequestInit }[] = []
  const responses: unknown[] = [{ items: [] }, config, { id: config.id, revision: 2, config_sha256: '2'.repeat(64), configured: true, secret_present: false }, { id: config.id, revision: 2, config_sha256: '2'.repeat(64), secret_present: true }, { id: config.id, revision: 3, config_sha256: '3'.repeat(64), secret_present: false }, proposal, proposal, { id: 'consent_test', revision: 1, status: 'active', proposal_id: proposal.id, proposal_sha256: proposal.proposal_sha256, summary: proposal.summary }, pageFixture(), { id: 'consent_test', revision: 2, applied: true }]
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => { requests.push({ path, init }); return new Response(JSON.stringify(responses.shift()), { status: 200, headers: { 'Content-Type': 'application/json' } }) }))
  await providerClient.capabilities(); await providerClient.config(config.id); await providerClient.saveConfig(config.id, writeFixture(config), 'config_original'); await providerClient.saveSecret(config.id, { expected_revision: 1, secret: 'synthetic-transient-only' }, 'secret_original'); await providerClient.deleteSecret(config.id, '2'.repeat(64), 'delete_original')
  await providerClient.preview({ job_id: 'job_test', expected_job_revision: 1, provider_id: config.id, expected_provider_revision: 1, budget: proposal.summary.budget, expires_at: proposal.summary.expires_at }, 'preview_original'); await providerClient.proposal(proposal.id); await providerClient.grant({ proposal_id: proposal.id, proposal_sha256: proposal.proposal_sha256 }, 'grant_original'); await providerClient.consents({ consent_id: 'consent_test' }); await providerClient.revoke('consent_test', { expected_revision: 1 }, 'revoke_original')
  expect(requests.map(value => [value.init.method, value.path])).toEqual([['GET', '/api/v1/providers/capabilities'], ['GET', '/api/v1/providers/provider_test/config'], ['PUT', '/api/v1/providers/provider_test/config'], ['POST', '/api/v1/providers/provider_test/secret'], ['DELETE', '/api/v1/providers/provider_test/secret'], ['POST', '/api/v1/consents/preview'], ['GET', '/api/v1/consents/preview/proposal_test'], ['POST', '/api/v1/consents'], ['GET', '/api/v1/consents?consent_id=consent_test'], ['POST', '/api/v1/consents/consent_test/revoke']])
  expect(new Headers(requests[4].init.headers).get('If-Match')).toBe(`"${'2'.repeat(64)}"`); expect(requests[4].init.body).toBeUndefined()
  expect(new Headers(requests[2].init.headers).get('Idempotency-Key')).toBe('config_original'); expect(JSON.parse(String(requests[2].init.body))).toEqual(writeFixture(config)); expect(JSON.parse(String(requests[7].init.body))).toEqual({ proposal_id: proposal.id, proposal_sha256: proposal.proposal_sha256 })
  expect(requests.filter(value => String(value.init.body).includes('synthetic-transient-only'))).toEqual([requests[3]])
})
test('response schemas reject extra private payload and malformed delete hashes without another transport', async () => {
  const transport = vi.fn(async () => new Response(JSON.stringify({ ...configFixture(), secret: 'unexpected-private-field' }), { status: 200, headers: { 'Content-Type': 'application/json' } })); vi.stubGlobal('fetch', transport)
  await expect(providerClient.config('provider_test')).rejects.toThrow('契约')
  for (const value of ['*', 'W/"abc"', 'a'.repeat(63), 'A'.repeat(64), '"' + 'a'.repeat(64) + '"']) expect(() => configIfMatch(value)).toThrow('版本')
  expect(transport).toHaveBeenCalledOnce()
})
