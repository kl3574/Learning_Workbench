import { IDBFactory } from 'fake-indexeddb'
import { afterEach, expect, test, vi } from 'vitest'
import { DraftStore } from '../../workbench/DraftStore'
import { actor, workspace } from './bootstrapTestFixtures'
import { turnControl } from './turnTestFixtures'
import { turnOutboundClient } from './turnOutboundClient'
import { dispatchOutboundCommand, outboundRevokeCommand, type OutboundCommand } from './turnOutboundCommands'
import { outboundConsent, outboundCurrent, outboundGrant, outboundPreparation, outboundProposal, outboundProvider, previewBody } from './turnOutboundFixtures'
afterEach(() => vi.unstubAllGlobals())
test('actual Codex revoke wire first persists the original safe reader, key, full body and control before any POST', async () => {
 const store = new DraftStore({ name: `outbound-wire-${crypto.randomUUID()}`, factory: new IDBFactory() })
 const basis = { ...turnControl(), consent_control: { id: 'codexconsent_original', revision: 1, status: 'active' as const } }
 const original = outboundRevokeCommand(workspace, actor, basis)
 try {
  const fetch = vi.fn(async (path: string, init: RequestInit) => {
   expect(path).toBe('/api/v1/codex/consents/codexconsent_original/revoke')
   expect(new Headers(init.headers).get('Idempotency-Key')).toBe(original.command_id)
   expect(JSON.parse(init.body as string)).toEqual({ expected_revision: 1 })
   const durable = (await store.load(workspace))[original.command_id]
   expect(durable, 'original command must exist before the real transport boundary').toBeDefined()
   expect(JSON.parse(durable.text)).toEqual(original)
   return new Response(JSON.stringify({ id: 'codexconsent_original', revision: 2, applied: true }), { status: 200 })
  })
  vi.stubGlobal('fetch', fetch)
  const actual = await dispatchOutboundCommand(original, turnOutboundClient, store)
  expect(actual.ack).toEqual({ id: 'codexconsent_original', revision: 2, applied: true })
  expect(fetch).toHaveBeenCalledOnce()
  expect(JSON.parse((await store.load(workspace))[original.command_id].text)).toEqual(actual)
 } finally { await store.close() }
})
test.each(['preview', 'grant', 'start'] as const)('actual %s route retains original full wire ACK after durable request admission', async kind => {
 const store = new DraftStore({ name: `outbound-${kind}-${crypto.randomUUID()}`, factory: new IDBFactory() })
 const preparation = outboundPreparation(), proposal = outboundProposal(), consent = outboundConsent()
 const part = kind === 'preview' ? { route: 'POST /api/v1/codex/consent-previews', target_id: preparation.id, basis: { preparation, control: turnControl(), provider: outboundProvider() }, body: previewBody(), response: proposal, path: '/api/v1/codex/consent-previews' }
  : kind === 'grant' ? { route: 'POST /api/v1/codex/consents', target_id: proposal.id, basis: { preparation, proposal }, body: { proposal_id: proposal.id, proposal_sha256: proposal.proposal_sha256 }, response: outboundGrant(), path: '/api/v1/codex/consents' }
   : { route: 'POST /api/v1/codex/sessions/{id}/turns', target_id: preparation.session_id, basis: { preparation, current: outboundCurrent(), consent }, body: { preparation_id: preparation.id, preparation_sha256: preparation.preparation_sha256, consent_id: consent.id, expected_session_revision: 3 }, response: { turn_id: preparation.turn_id, session_revision: 4, job: { id: preparation.job.id, status: 'queued' } }, path: '/api/v1/codex/sessions/codex_session_test/turns' }
 const { response, path, ...fields } = part
 const original = { version: 1, kind, workspace_id: workspace, actor_session_id: actor, command_id: `codexout_${crypto.randomUUID()}`, ...fields, ack: null, error: null } as unknown as OutboundCommand
 try {
  const fetch = vi.fn(async (actualPath: string, init: RequestInit) => {
   expect(actualPath).toBe(path); expect(JSON.parse(init.body as string)).toEqual(fields.body)
   expect(new Headers(init.headers).get('Idempotency-Key')).toBe(original.command_id)
   expect(JSON.parse((await store.load(workspace))[original.command_id].text)).toEqual(original)
   return new Response(JSON.stringify(response), { status: kind === 'start' ? 202 : 201 })
  })
  vi.stubGlobal('fetch', fetch)
  const actual = await dispatchOutboundCommand(original, turnOutboundClient, store)
  expect(actual.ack).toEqual(response); expect(fetch).toHaveBeenCalledOnce()
  expect(JSON.parse((await store.load(workspace))[original.command_id].text)).toEqual(actual)
 } finally { await store.close() }
})
