import { createApiClient } from '../../../../packages/contracts/generated/api-client'
import type { WorkbenchSession } from '../../../../packages/contracts/generated/types'
let csrf = ''
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}
export const request = createApiClient(async (path, init, responseKind = 'json') => {
  const response = await fetch(path, {
    credentials: 'same-origin', ...init,
    headers: { ...(init.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }), ...(csrf ? { 'X-CSRF-Token': csrf } : {}), ...init.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, body?.error?.message ?? `服务请求失败 (${response.status})`)
  }
  return responseKind === 'text' ? response.text() : responseKind === 'blob' ? response.blob() : response.json()
})
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
