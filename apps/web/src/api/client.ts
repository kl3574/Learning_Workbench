import { createApiClient } from '../../../../packages/contracts/generated/api-client'
import type { ApiArgs, ApiResponse, EndpointKey, ResponseKind } from '../../../../packages/contracts/generated/api-client'
import type { WorkbenchSession } from '../../../../packages/contracts/generated/types'
let csrf = ''
let sessionGeneration = 0
const roleChannel = typeof BroadcastChannel === 'undefined' ? null : new BroadcastChannel('learning-workbench.session-access.v1')
const accessListeners = new Set<() => void>()
const changed = (broadcast = true) => { sessionGeneration++; accessListeners.forEach(listener => listener()); if (broadcast) roleChannel?.postMessage('access-changed') }
if (roleChannel) roleChannel.onmessage = () => changed(false)
export const subscribeSessionAccess = (listener: () => void) => { accessListeners.add(listener); return () => { accessListeners.delete(listener) } }
export const getSessionGeneration = () => sessionGeneration
export class ApiError extends Error {
  status: number
  code?: string
  constructor(status: number, message: string, code?: string) { super(message); this.status = status; this.code = code }
}
async function transport(path: string, init: RequestInit, responseKind: ResponseKind = 'json', metadata?: (etag: string | null) => void) {
  const accessMutation = init.method === 'POST' && (['/api/v1/session/role', '/api/v1/session/logout', '/api/v1/session/bootstrap'].includes(path) || /^\/api\/v1\/(?:assessments\/[^/]+\/attempts|attempts\/[^/]+\/(?:submit|abandon))$/.test(path))
  if (accessMutation) changed()
  let response: Response
  try { response = await fetch(path, {
    credentials: 'same-origin', ...init,
    headers: { ...(init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...(csrf ? { 'X-CSRF-Token': csrf } : {}), ...init.headers },
  }) } finally { if (accessMutation) changed() }
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, body?.error?.message ?? `服务请求失败 (${response.status})`, body?.error?.code)
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
export const saveSession = (session: WorkbenchSession) => request('PUT /api/v1/workbench/session', { expected_revision: session.revision, session }, {})

export const readSessionWithMetadata = () => requestWithMetadata('GET /api/v1/workbench/session', undefined)
export const saveSessionWithMetadata = (session: WorkbenchSession, etag: string | null) => requestWithMetadata('PUT /api/v1/workbench/session', { expected_revision: session.revision, session }, etag ? { 'If-Match': etag } : {})
