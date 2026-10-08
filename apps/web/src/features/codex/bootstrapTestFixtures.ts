import type { SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import type { CodexBootstrapPreparationView, CodexSessionView } from '../../../../../packages/contracts/generated/codex-bootstrap-types'
import { vi } from 'vitest'
import type { BootstrapPort } from './bootstrapClient'
export const workspace = 'workspace_bootstrap_test'
export const actor = 'session_bootstrap_test'
export const session = (): SessionResponse => ({ workspace_id: workspace, actor_session_id: actor, role: 'author', csrf_token: 'synthetic-only-not-persisted', active_independent_attempt_id: null, active_open_book_attempt_id: null })
export const preparation = (status: CodexBootstrapPreparationView['status'] = 'pending'): CodexBootstrapPreparationView => ({
 id: 'preparation_test', revision: status === 'pending' ? 1 : status === 'consumed' ? 3 : 2, actor_session_id: actor, status,
 scope: { version: 'codex-local-session-bootstrap-v1', sandbox_root_id: 'workspace_default', sandbox_label: '此工作区的隔离 Broker', allowed_actions: [], adapter_version: 'codex-cli/0.160.0', bootstrap_profile_sha256: 'a'.repeat(64) },
 operation_sha256: 'b'.repeat(64), created_at: '2026-10-03T12:00:00.000001Z', expires_at: '2026-10-03T12:10:00.000001Z',
 consent_id: ['approved', 'consumed'].includes(status) ? 'consent_bootstrap_test' : null, session_id: status === 'consumed' ? 'codex_session_test' : null, validity: ['declined', 'consumed'].includes(status) ? 'closed' : 'current',
})
export const codexSession = (status: CodexSessionView['status'] = 'ready'): CodexSessionView => ({ id: 'codex_session_test', revision: status === 'initializing' ? 1 : 2, status, active_turn_id: null, adapter_version: 'codex-cli/0.160.0', capabilities: { approvals: false, interrupt: false, artifacts: false } })
export const bootstrapPort = (): BootstrapPort => ({
 session: vi.fn(async () => session()), prepare: vi.fn(async () => preparation()), preparation: vi.fn(async () => preparation()),
 decide: vi.fn<BootstrapPort['decide']>(async (id, body) => ({ preparation_id: id, revision: 2, actor_session_id: actor, decision: body.decision, operation_sha256: body.operation_sha256, consent_id: body.decision === 'approve_once' ? 'consent_bootstrap_test' : null, decided_at: '2026-10-03T12:01:00Z' })),
 create: vi.fn<BootstrapPort['create']>(async () => ({ id: 'codex_session_test', revision: 2, status: 'ready', capabilities: { approvals: false, interrupt: false, artifacts: false }, adapter_version: 'codex-cli/0.160.0' })), read: vi.fn(async () => codexSession()),
})
export function deferred<T>() { let resolve!: (value: T) => void; let reject!: (reason: unknown) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no }); return { promise, resolve, reject } }
