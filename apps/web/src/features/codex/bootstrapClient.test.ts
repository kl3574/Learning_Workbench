import { afterEach, expect, test, vi } from 'vitest'
import type { CodexBootstrapPreparationWrite } from '../../../../../packages/contracts/generated/codex-bootstrap-types'
import { bootstrapClient, checkedBootstrap } from './bootstrapClient'
import { codexSession, preparation } from './bootstrapTestFixtures'
afterEach(() => vi.unstubAllGlobals())

test.each(['pending', 'approved', 'declined', 'consumed'] as const)('strict schema accepts coherent %s metadata', status => {
 const value = preparation(status)
 expect(checkedBootstrap('CodexBootstrapPreparationView', value)).toEqual(value)
})
test.each([
 { revision: 2 }, { consent_id: 'consent_wrong' }, { session_id: 'session_wrong' }, { validity: 'closed' },
 { expires_at: '2026-10-03T12:10:00.000002Z' }, { expires_at: '2026-10-03T12:11:00.000001Z' },
 { created_at: '2026-02-30T12:00:00Z', expires_at: '2026-02-30T12:10:00Z' },
])('rejects semantically inconsistent preparation %j', patch => {
 expect(() => checkedBootstrap('CodexBootstrapPreparationView', { ...preparation(), ...patch })).toThrow()
})
test.each(['/private/path', 'file://private', 'back\\slash', 'bad\nlabel', '\u0000', '\ud800', '   '])('rejects unsafe label %j', label => {
 expect(() => checkedBootstrap('CodexBootstrapPreparationView', { ...preparation(), scope: { ...preparation().scope, sandbox_label: label } })).toThrow()
})
test('closed consumed retains its true session and false features never accept numbers', () => {
 expect(() => checkedBootstrap('CodexBootstrapPreparationView', { ...preparation('consumed'), session_id: null })).toThrow()
 expect(() => checkedBootstrap('CodexSessionView', { ...codexSession(), capabilities: { approvals: 0, interrupt: false, artifacts: false } })).toThrow()
 expect(() => checkedBootstrap('CodexSessionView', { ...codexSession(), revision: 1 })).toThrow()
 expect(() => checkedBootstrap('CodexSessionView', { ...codexSession('initializing'), revision: 2 })).toThrow()
})
test('empty actions and closed keys are mandatory', () => {
 expect(() => checkedBootstrap('CodexBootstrapPreparationWrite', { sandbox_root_id: 'workspace_default', allowed_actions: ['read'] })).toThrow()
 expect(() => checkedBootstrap('CodexSessionView', { ...codexSession(), thread_id: 'external_not_allowed' })).toThrow()
 expect(() => checkedBootstrap('CodexSessionView', { ...codexSession(), active_turn_id: 'turn_not_allowed' })).toThrow()
})

test('registered generated transport preserves five exact routes, original keys/bodies and bodyless GETs', async () => {
 const calls: { path: string; init: RequestInit }[] = []
 vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => {
  calls.push({ path, init })
  const value = path.endsWith('/decision') ? { preparation_id: 'preparation_test', revision: 2, actor_session_id: 'session_bootstrap_test', decision: 'approve_once', operation_sha256: 'b'.repeat(64), consent_id: 'consent_bootstrap_test', decided_at: '2026-10-03T12:01:00Z' }
   : path.endsWith('/codex/sessions') ? { id: 'codex_session_test', revision: 2, status: 'ready', capabilities: { approvals: false, interrupt: false, artifacts: false }, adapter_version: 'codex-cli/0.160.0' }
   : path.includes('/codex/sessions/') ? codexSession() : preparation()
  return new Response(JSON.stringify(value), { status: init.method === 'POST' && !path.endsWith('/decision') ? 201 : 200 })
 }))
 const body: CodexBootstrapPreparationWrite = { sandbox_root_id: 'workspace_default', allowed_actions: [] }
 await bootstrapClient.prepare(body, 'original_prepare_key')
 await bootstrapClient.preparation('preparation_test')
 const decision = { decision: 'approve_once' as const, expected_revision: 1, operation_sha256: 'b'.repeat(64) }
 await bootstrapClient.decide('preparation_test', decision, 'original_decision_key')
 const create = { ...body, consent_id: 'consent_bootstrap_test' }
 await bootstrapClient.create(create, 'original_create_key')
 await bootstrapClient.read('codex_session_test')
 expect(calls.map(v => `${v.init.method} ${v.path}`)).toEqual([
  'POST /api/v1/codex/session-preparations', 'GET /api/v1/codex/session-preparations/preparation_test',
  'POST /api/v1/codex/session-preparations/preparation_test/decision', 'POST /api/v1/codex/sessions', 'GET /api/v1/codex/sessions/codex_session_test',
 ])
 expect(calls.filter(v => v.init.method === 'POST').map(v => new Headers(v.init.headers).get('Idempotency-Key'))).toEqual(['original_prepare_key', 'original_decision_key', 'original_create_key'])
 expect(calls.filter(v => v.init.method === 'POST').map(v => JSON.parse(v.init.body as string))).toEqual([body, decision, create])
 expect(calls.filter(v => v.init.method === 'GET').every(v => v.init.body === undefined && new Headers(v.init.headers).get('Idempotency-Key') === null)).toBe(true)
})
