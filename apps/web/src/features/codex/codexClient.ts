import type { CodexCapabilities, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import { request } from '../../api/client'
import { checkedProvider } from '../providers/providerSchema'

export type CodexCapabilityPort = {
  session(): Promise<SessionResponse>
  capabilities(): Promise<CodexCapabilities>
}

/** Validate the generated wire contract before any connection status is shown. */
export function checkedCodex<T>(name: 'CodexCapabilities' | 'SessionResponse', value: unknown): T {
  try {
    const checked = checkedProvider<T>(name, value)
    if (name === 'CodexCapabilities') {
      const view = checked as CodexCapabilities
      if (!view.available && (view.authorized || view.sandbox_roots.length > 0 || Object.values(view.capabilities).some(Boolean))
        || view.available && !view.adapter_version?.trim()
        || new Set(view.sandbox_roots.map(root => root.id)).size !== view.sandbox_roots.length) throw new Error('Inconsistent capability observation')
    }
    return checked
  }
  catch { throw new Error('Codex 连接状态不符合当前契约，请重新检查。') }
}

export const codexCapabilityClient: CodexCapabilityPort = {
  session: async () => checkedCodex('SessionResponse', await request('GET /api/v1/session', undefined)),
  capabilities: async () => checkedCodex('CodexCapabilities', await request('GET /api/v1/codex/capabilities', undefined)),
}
