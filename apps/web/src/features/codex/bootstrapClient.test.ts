import { expect, test } from 'vitest'
import { checkedBootstrap } from './bootstrapClient'
import { codexSession, preparation } from './bootstrapTestFixtures'

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
