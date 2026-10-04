import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'
import { IDBFactory } from 'fake-indexeddb'
import { afterEach, expect, test, vi } from 'vitest'
import type { CodexTurnResultView } from '../../../../../packages/contracts/generated/codex-turn-types'
import { DraftStore } from '../../workbench/DraftStore'
import { actor, workspace } from './bootstrapTestFixtures'
import { turnControl } from './turnTestFixtures'
import { checkedOutbound, outboundTime, turnOutboundClient } from './turnOutboundClient'
import { decodeOutboundCommand, dispatchOutboundCommand, makeOutboundCommand, persistOutboundCommand, readOutboundCommand } from './turnOutboundCommands'
import { outboundConsent, outboundControl, outboundCurrent, outboundGrant, outboundPreparation, outboundProposal, outboundProvider, previewBody } from './turnOutboundFixtures'
afterEach(() => vi.unstubAllGlobals())
const proposal = () => { const p = outboundProposal(); p.summary.input_sha256 = outboundPreparation().summary.prepared_input_sha256; return p }
const preview = () => makeOutboundCommand(workspace, actor, { kind: 'preview', basis: { preparation: outboundPreparation(), control: turnControl(), provider: outboundProvider() }, body: previewBody() })
const result = (answer: string, outcome: 'completed' | 'failed' = 'completed'): CodexTurnResultView => ({
 control: { ...turnControl(), job: { id: 'job_turn_test', status: outcome }, execution: 'terminal', outcome, started_at: '2026-10-04T00:00:02Z', finished_at: '2026-10-04T00:00:03Z', error_code: outcome === 'completed' ? null : 'CODEX_NEW_OUTBOUND_CONSENT_REQUIRED' },
 preparation_id: 'turn_preparation_test', answer_markdown: answer, output_sha256: answer ? bytesToHex(sha256(new TextEncoder().encode(answer))) : null,
 output_state: answer ? outcome === 'completed' ? 'complete' : 'partial' : 'none', usage: { input_tokens: 50, output_tokens: 3 }, mathematical: 'NOT_RUN', sources: 'NOT_RUN', independent_pedagogy: 'NOT_RUN',
})

test.each(['source_input_sha256', 'input_sha256', 'references'] as const)('journal rejects a preview ACK whose %s differs from its frozen preparation', field => {
 const ack = proposal()
 if (field === 'references') ack.summary.references = [{ ref: { entity: 'block', id: 'block_other', revision: 1, sha256: 'a'.repeat(64) }, title: '公开合成材料', locator: 'block:1', character_count: 1, excerpt_sha256: 'f'.repeat(64) }]
 else ack.summary[field] = '0'.repeat(64)
 expect(() => decodeOutboundCommand(JSON.stringify({ ...preview(), ack }), workspace)).toThrow()
})
test('closed decoder accepts actual completed-but-empty receipt as no output, never promotes empty text to complete', () => {
 expect(checkedOutbound('CodexTurnResultView', result(''))).toEqual(result(''))
})
test('loopback summary still rejects a non-HTTP protocol', () => {
 const p = proposal(); p.summary.endpoint_policy = 'explicit_loopback'; p.summary.endpoint = 'ftp://localhost/responses'
 expect(() => checkedOutbound('CodexConsentProposalView', p)).toThrow()
})
test.each(['2026-10-04T00:00:00Z\n', '2026-02-30T00:00:00Z', '2026-10-04T00:00:00+00:00', '0000-10-04T00:00:00Z'])('rejects non-canonical UTC %j', time => {
 expect(() => outboundTime(time)).toThrow()
})
test('closed summary preserves a valid positive microsecond lifetime without rounding it to zero', () => {
 const p = proposal(); p.summary.created_at = '2026-10-04T00:00:00.000001Z'; p.summary.expires_at = '2026-10-04T00:00:00.000002Z'
 expect(checkedOutbound('CodexConsentProposalView', p)).toEqual(p)
})
test.each(['  原文 α\n中文😀  ', '', 'e\u0301 ≠ é'])('UTF-8 result wire preserves %j exactly', async answer => {
 const value = result(answer, answer ? 'failed' : 'completed'), fetch = vi.fn(async (_path: string) => new Response(JSON.stringify(value)))
 vi.stubGlobal('fetch', fetch)
 expect(await turnOutboundClient.result('turn_test')).toEqual(value)
 expect(fetch.mock.calls[0][0]).toBe('/api/v1/codex/turns/turn_test/result')
})
test.each(['digest', 'normalized', 'empty', 'wrong_turn', 'extra'])('actual result GET rejects %s wire before delivery', async mode => {
 const value = result('  α\n中文😀  ', 'failed')
 const raw = mode === 'digest' ? { ...value, output_sha256: '0'.repeat(64) }
  : mode === 'normalized' ? { ...value, answer_markdown: value.answer_markdown.trim() }
  : mode === 'empty' ? { ...value, answer_markdown: '', output_sha256: null }
  : mode === 'wrong_turn' ? { ...value, control: { ...value.control, id: 'other_turn' } } : { ...value, private_body: 'synthetic-only' }
 vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(raw))))
 await expect(turnOutboundClient.result('turn_test')).rejects.toThrow()
})
test.each(['proof_body', 'tokens', 'cost', 'expiry', 'credential', 'duplicate_warning'])('closed summary rejects %s', mode => {
 const p = proposal()
 if (mode === 'proof_body') p.summary.input_token_assurance.request_body_sha256 = '0'.repeat(64)
 if (mode === 'tokens') p.summary.budget.max_input_tokens = 1
 if (mode === 'cost') { p.summary.budget.max_cost_usd = 1; p.summary.cost_estimate = { kind: 'estimated', currency: 'USD', maximum_estimated_cost: 2, pricing_sha256: 'a'.repeat(64) } }
 if (mode === 'expiry') p.summary.expires_at = '2026-10-04T00:10:01Z'
 if (mode === 'credential') p.summary.endpoint = 'https://user:synthetic@example.test/v1/responses'
 if (mode === 'duplicate_warning') p.warnings = [{ code: 'price_unknown', message: 'synthetic' }, { code: 'price_unknown', message: 'synthetic' }]
 expect(() => checkedOutbound('CodexConsentProposalView', p)).toThrow()
})
test('grant ACK permanently retains original summary when the independent current consent becomes revoked', async () => {
 const store = new DraftStore({ name: `outbound-facts-${crypto.randomUUID()}`, factory: new IDBFactory() })
 const p = proposal(), original = makeOutboundCommand(workspace, actor, { kind: 'grant', basis: { preparation: outboundPreparation(), proposal: p }, body: { proposal_id: p.id, proposal_sha256: p.proposal_sha256 } })
 const ack = { ...outboundGrant(), summary: p.summary }
 try {
  await persistOutboundCommand({ ...original, ack } as typeof original, store)
  const stale = await persistOutboundCommand(original, store)
  expect(stale.ack).toEqual(ack)
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ ...outboundConsent(), summary: p.summary, revision: 2, status: 'revoked', revoked_at: '2026-10-04T00:00:03Z' }))))
  expect((await turnOutboundClient.consent(ack.id)).status).toBe('revoked')
  expect(readOutboundCommand((await store.load(workspace))[original.command_id], workspace).ack).toEqual(ack)
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch)
  expect((await dispatchOutboundCommand(original, turnOutboundClient, store)).ack).toEqual(ack); expect(fetch).not.toHaveBeenCalled()
 } finally { await store.close() }
})
test.each(['actor', 'job', 'session_revision'])('start journal rejects ACK/basis changed %s', field => {
 const consent = outboundConsent(); consent.summary = proposal().summary
 const c = makeOutboundCommand(workspace, actor, { kind: 'start', basis: { preparation: outboundPreparation(), current: outboundCurrent(), consent }, body: { preparation_id: 'turn_preparation_test', preparation_sha256: 'a'.repeat(64), consent_id: consent.id, expected_session_revision: 3 } })
 const raw = { ...c, ack: { turn_id: 'turn_test', session_revision: field === 'session_revision' ? 3 : 4, job: { id: field === 'job' ? 'job_other' : 'job_turn_test', status: 'queued' } } }
 if (field === 'actor') raw.actor_session_id = 'actor_other'
 expect(() => decodeOutboundCommand(JSON.stringify(raw), workspace)).toThrow()
})
test('safe revoke no-op retains actual revoked revision without fabricating another mutation', () => {
 const basis = outboundControl(); basis.consent_control = { id: 'codexconsent_original', revision: 2, status: 'revoked' }
 const c = makeOutboundCommand(workspace, 'learner_new', { kind: 'revoke', basis, body: { expected_revision: 2 } })
 expect(decodeOutboundCommand(JSON.stringify({ ...c, ack: { id: 'codexconsent_original', revision: 2, applied: false } }), workspace).ack).toEqual({ id: 'codexconsent_original', revision: 2, applied: false })
 expect(() => decodeOutboundCommand(JSON.stringify({ ...c, ack: { id: 'codexconsent_original', revision: 3, applied: true } }), workspace)).toThrow()
})

test.each(['failed', 'cancelled'] as const)('actual result GET preserves completed response output after turn becomes %s', async outcome => {
 // The worker can retain a completed response then fail/stop the turn after
 // an access/cancellation change; the result owner keeps both original facts.
 const value = result('Synthetic exact answer α\n')
 value.control = { ...value.control, job: { id: 'job_turn_test', status: outcome }, outcome, error_code: outcome === 'failed' ? 'POLICY_DENIED' : 'CODEX_CANCELLED', cancel_requested: outcome === 'cancelled' }
 vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(value))))
 expect(await turnOutboundClient.result('turn_test')).toEqual(value)
})
test.each(['http:/localhost/model', 'http:///localhost/model', 'http://127.1/model'])('rejects non-owner endpoint spelling %s despite browser URL normalization', endpoint => {
 const p = proposal(); p.summary.endpoint = endpoint; p.summary.endpoint_policy = 'explicit_loopback'
 expect(() => checkedOutbound('CodexConsentProposalView', p)).toThrow()
})
