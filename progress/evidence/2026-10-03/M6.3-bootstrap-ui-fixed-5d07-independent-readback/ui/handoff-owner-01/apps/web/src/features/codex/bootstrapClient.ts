import type { ApprovalDecision, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import type { CodexBootstrapDecisionAck, CodexBootstrapPreparationView, CodexBootstrapPreparationWrite, CodexSessionCreateAck, CodexSessionCreateWrite, CodexSessionView } from '../../../../../packages/contracts/generated/codex-bootstrap-types'
import bootstrapSchemas from '../../../../../packages/contracts/generated/codex-bootstrap-schemas.json'
import { request } from '../../api/client'
import { checkedProvider } from '../providers/providerSchema'

export type BootstrapPort = {
  session(): Promise<SessionResponse>
  prepare(body: CodexBootstrapPreparationWrite, key: string): Promise<CodexBootstrapPreparationView>
  preparation(id: string): Promise<CodexBootstrapPreparationView>
  decide(id: string, body: ApprovalDecision, key: string): Promise<CodexBootstrapDecisionAck>
  create(body: CodexSessionCreateWrite, key: string): Promise<CodexSessionCreateAck>
  read(id: string): Promise<CodexSessionView>
}

export function checkedBootstrap<T>(name: string, raw: unknown): T {
  try { return checkedProvider<T>(name, raw, name in bootstrapSchemas.schemas ? bootstrapSchemas.schemas : undefined) }
  catch { throw new Error('本地会话记录不符合当前契约，原命令保留。') }
}

const keyHeader = (key: string) => ({ 'Idempotency-Key': key })
export const bootstrapClient: BootstrapPort = {
  session: async () => checkedBootstrap('SessionResponse', await request('GET /api/v1/session', undefined)),
  prepare: async (body, key) => checkedBootstrap('CodexBootstrapPreparationView', await request('POST /api/v1/codex/session-preparations', body, keyHeader(key))),
  preparation: async id => checkedBootstrap('CodexBootstrapPreparationView', await request('GET /api/v1/codex/session-preparations/{id}', undefined, undefined, { path: { id } })),
  decide: async (id, body, key) => checkedBootstrap('CodexBootstrapDecisionAck', await request('POST /api/v1/codex/session-preparations/{id}/decision', body, keyHeader(key), { path: { id } })),
  create: async (body, key) => checkedBootstrap('CodexSessionCreateAck', await request('POST /api/v1/codex/sessions', body, keyHeader(key))),
  read: async id => checkedBootstrap('CodexSessionView', await request('GET /api/v1/codex/sessions/{id}', undefined, undefined, { path: { id } })),
}
