import type { WorkbenchSession } from '../../../../packages/contracts/generated/types'
let csrf = ''
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    credentials: 'same-origin', ...init,
    headers: { 'Content-Type': 'application/json', ...(csrf ? { 'X-CSRF-Token': csrf } : {}), ...init.headers },
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, body?.error?.message ?? `服务请求失败 (${response.status})`)
  }
  return response.json() as Promise<T>
}
export async function connectSession(): Promise<string> {
  const fragment = new URLSearchParams(location.hash.slice(1))
  const oneTimeCode = fragment.get('bootstrap')
  if (oneTimeCode) {
    history.replaceState(null, '', `${location.pathname}${location.search}`)
    const result = await api<{ csrf_token: string; workspace_id: string }>('/session/bootstrap', { method: 'POST', body: JSON.stringify({ one_time_code: oneTimeCode }) })
    csrf = result.csrf_token
    return result.workspace_id
  } else {
    const result = await api<{ csrf_token: string; workspace_id: string }>('/session')
    csrf = result.csrf_token
    return result.workspace_id
  }
}
export const readSession = () => api<WorkbenchSession>('/workbench/session')
export const saveSession = (session: WorkbenchSession) => api<WorkbenchSession>('/workbench/session', {
  method: 'PUT', body: JSON.stringify({ expected_revision: session.revision, session }),
})
