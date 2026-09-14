import { createApiClient } from '../../../../packages/contracts/generated/api-client'
import type { ApiArgs, ApiResponse, EndpointKey, ResponseKind } from '../../../../packages/contracts/generated/api-client'
import type { WorkbenchSession } from '../../../../packages/contracts/generated/types'
let csrf = ''
let sessionGeneration = 0
const roleChannel = typeof BroadcastChannel === 'undefined' ? null : new BroadcastChannel('learning-workbench.session-access.v1')
if (roleChannel) roleChannel.onmessage = () => { sessionGeneration++ }
export const getSessionGeneration = () => sessionGeneration
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}
async function transport(path: string, init: RequestInit, responseKind: ResponseKind = 'json', metadata?: (etag: string | null) => void) {
  if (init.method === 'POST' && ['/api/v1/session/role', '/api/v1/session/logout', '/api/v1/session/bootstrap'].includes(path)) { sessionGeneration++; roleChannel?.postMessage('access-changed') }
  const response = await fetch(path, {
    credentials: 'same-origin', ...init,
    headers: { ...(init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...(csrf ? { 'X-CSRF-Token': csrf } : {}), ...init.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, body?.error?.message ?? `服务请求失败 (${response.status})`)
  }
  metadata?.(response.headers.get('ETag'))
  return responseKind === 'text' ? response.text() : responseKind === 'blob' ? response.blob() : response.json()
}
export const request = createApiClient(transport)
export async function requestWithMetadata<K extends EndpointKey>(operation: K, ...args: ApiArgs<K>): Promise<{ data: ApiResponse<K>; etag: string | null }> {
  let etag: string | null = null
  const client = createApiClient((path, init, kind) => transport(path, init, kind, value => { etag = value }))
  return { data: await client(operation, ...args), etag }
}
export async function connectSession(): Promise<string> {
  const oneTimeCode = new URLSearchParams(location.hash.slice(1)).get('bootstrap')
  if (oneTimeCode) {
    history.replaceState(null, '', `${location.pathname}${location.search}`)
    const result = await request('POST /api/v1/session/bootstrap', { one_time_code: oneTimeCode })
    csrf = result.csrf_token
    return result.workspace_id
  }
  const result = await request('GET /api/v1/session', undefined)
  csrf = result.csrf_token
  return result.workspace_id
}
export const readSession = () => request('GET /api/v1/workbench/session', undefined)
export const saveSession = (session: WorkbenchSession) => request('PUT /api/v1/workbench/session', { expected_revision: session.revision, session })
