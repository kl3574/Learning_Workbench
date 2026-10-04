import type { ApprovalDecision, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import type { CodexBootstrapDecisionAck, CodexBootstrapPreparationView, CodexBootstrapPreparationWrite, CodexBootstrapScope, CodexSessionCreateAck, CodexSessionCreateWrite, CodexSessionView } from '../../../../../packages/contracts/generated/codex-bootstrap-types'
import bootstrapSchemas from '../../../../../packages/contracts/generated/codex-bootstrap-schemas.json'
import type { CodexCurrentSessionView } from '../../../../../packages/contracts/generated/codex-turn-types'
import turnSchemas from '../../../../../packages/contracts/generated/codex-turn-schemas.json'
import { request } from '../../api/client'
import { checkedProvider } from '../providers/providerSchema'

export type BootstrapPort = {
  session(): Promise<SessionResponse>
  prepare(body: CodexBootstrapPreparationWrite, key: string): Promise<CodexBootstrapPreparationView>
  preparation(id: string): Promise<CodexBootstrapPreparationView>
  decide(id: string, body: ApprovalDecision, key: string): Promise<CodexBootstrapDecisionAck>
  create(body: CodexSessionCreateWrite, key: string): Promise<CodexSessionCreateAck>
  read(id: string): Promise<CodexCurrentSessionView>
}

const invalid = (): never => { throw new Error('Inconsistent bootstrap metadata') }
function utcMicros(value: string): bigint {
  const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?Z$/.exec(value)
  if (!match || value.startsWith('0000')) return invalid()
  const millis = Date.parse(match[1] + 'Z')
  if (!Number.isFinite(millis) || new Date(millis).toISOString().slice(0, 19) !== match[1]) return invalid()
  // Python's UTC validator retains the wire bytes but datetime uses microseconds.
  return BigInt(millis) * 1000n + BigInt((match[2] ?? '').slice(0, 6).padEnd(6, '0'))
}
function safeLabel(value: string) {
  if (!value.trim() || /^[\/\\]/.test(value) || value.includes('\\') || value.includes('://') || /[\u0000-\u001f\u007f]/.test(value)) invalid()
}
function scope(value: CodexBootstrapScope) { safeLabel(value.sandbox_label); safeLabel(value.adapter_version) }
export function checkedBootstrap<T>(name: string, raw: unknown): T {
  try {
    const schemas = name === 'CodexCurrentSessionView' ? turnSchemas.schemas
      : name in bootstrapSchemas.schemas ? bootstrapSchemas.schemas : undefined
    const checked = checkedProvider<T>(name, raw, schemas)
    if (name === 'CodexBootstrapPreparationView') {
      const value = checked as CodexBootstrapPreparationView
      scope(value.scope)
      const revision = { pending: 1, approved: 2, declined: 2, consumed: 3 }[value.status]
      if (value.revision !== revision || (value.consent_id !== null) !== ['approved', 'consumed'].includes(value.status)
        || (value.session_id !== null) !== (value.status === 'consumed')
        || (value.validity === 'closed') !== ['declined', 'consumed'].includes(value.status)
        || utcMicros(value.expires_at) - utcMicros(value.created_at) !== 600_000_000n) invalid()
    } else if (name === 'CodexBootstrapDecisionAck') {
      const value = checked as CodexBootstrapDecisionAck
      utcMicros(value.decided_at)
      if ((value.consent_id !== null) !== (value.decision === 'approve_once')) invalid()
    } else if (name === 'CodexCurrentSessionView') {
      const value = checked as CodexCurrentSessionView
      safeLabel(value.adapter_version)
      const empty = value.active_turn_id === null && !Object.values(value.capabilities).some(Boolean)
      if (value.status === 'ready') {
        if (value.revision < 2 || value.revision === 2 && !empty) invalid()
      } else if (value.revision !== (value.status === 'initializing' ? 1 : 2) || !empty) invalid()
    } else if (name === 'CodexSessionView' || name === 'CodexSessionCreateAck') {
      const value = checked as CodexSessionView | CodexSessionCreateAck
      safeLabel(value.adapter_version)
      if (value.revision !== (value.status === 'initializing' ? 1 : 2)) invalid()
    } else if (name === 'CodexBootstrapScope') scope(checked as CodexBootstrapScope)
    return checked
  }
  catch { throw new Error('本地会话记录不符合当前契约，原命令保留。') }
}

const keyHeader = (key: string) => ({ 'Idempotency-Key': key })
export const bootstrapClient: BootstrapPort = {
  session: async () => checkedBootstrap('SessionResponse', await request('GET /api/v1/session', undefined)),
  prepare: async (body, key) => checkedBootstrap('CodexBootstrapPreparationView', await request('POST /api/v1/codex/session-preparations', body, keyHeader(key))),
  preparation: async id => checkedBootstrap('CodexBootstrapPreparationView', await request('GET /api/v1/codex/session-preparations/{id}', undefined, undefined, { path: { id } })),
  decide: async (id, body, key) => checkedBootstrap('CodexBootstrapDecisionAck', await request('POST /api/v1/codex/session-preparations/{id}/decision', body, keyHeader(key), { path: { id } })),
  create: async (body, key) => checkedBootstrap('CodexSessionCreateAck', await request('POST /api/v1/codex/sessions', body, keyHeader(key))),
  read: async id => checkedBootstrap('CodexCurrentSessionView', await request('GET /api/v1/codex/sessions/{id}', undefined, undefined, { path: { id } })),
}
