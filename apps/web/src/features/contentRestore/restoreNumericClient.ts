import { API_ENDPOINTS, type EndpointKey } from '../../../../../packages/contracts/generated/api-client'
import type { ApprovalDecision, ContentRef, ContentRestoreDraftSnapshot, NumericCheckDecisionAck, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import type { RestoreNumericCheckPreviewWrite, RestoreNumericCheckView } from '../../../../../packages/contracts/generated/restore-numeric-types'
import { request } from '../../api/client'
import { publicationClient } from '../draftPublication/publicationClient'
import { checkedProvider, validIdentity } from '../providers/providerSchema'
import { checkedRestoreNumeric, restoreNumericCheck, restoreNumericDecisionAck, restoreNumericMaterial, restoreNumericPreviewAck, restoreNumericSnapshot } from './restoreNumericSchema'

export type RestoreNumericPort = {
  session(): Promise<SessionResponse>
  draft(id: string): Promise<ContentRestoreDraftSnapshot>
  current(id: string): Promise<ContentRef>
  preview(id: string, body: RestoreNumericCheckPreviewWrite, key: string): Promise<RestoreNumericCheckView>
  check(id: string): Promise<RestoreNumericCheckView>
  decide(id: string, body: ApprovalDecision, key: string): Promise<NumericCheckDecisionAck>
}
type Operation = 'POST /api/v1/content/restore-drafts/{id}/numeric-checks' | 'GET /api/v1/content/restore-numeric-checks/{id}' | 'POST /api/v1/content/restore-numeric-checks/{id}/decision'
type NumericRequest = (operation: EndpointKey, body: unknown, headers: Record<string, string> | undefined, parameters: { path: { id: string } }) => Promise<unknown>
function numericRequest(operation: Operation, id: string, body?: unknown, key?: string): Promise<unknown> {
  if (!validIdentity(id) || key !== undefined && !/^[A-Za-z0-9_-]{1,128}$/.test(key)) throw new Error('恢复数值对象或原命令键无效。')
  // Until the real owner is registered and contracts regenerated, fail closed.
  // Never invent an endpoint or bypass the shared session/CSRF transport.
  if (!Object.hasOwn(API_ENDPOINTS, operation)) throw new Error('恢复数值实际接口尚未生成，未发送请求。')
  return (request as NumericRequest)(operation as EndpointKey, body, key === undefined ? undefined : { 'Idempotency-Key': key }, { path: { id } })
}
export const restoreNumericClient: RestoreNumericPort = {
  session: async () => checkedProvider('SessionResponse', await request('GET /api/v1/session', undefined)),
  draft: async id => restoreNumericSnapshot(await request('GET /api/v1/content/restore-drafts/{id}', undefined, undefined, { path: { id } }), id),
  current: publicationClient.current,
  preview: async (id, raw, key) => {
    const body = checkedRestoreNumeric<RestoreNumericCheckPreviewWrite>('RestoreNumericCheckPreviewWrite', raw)
    restoreNumericMaterial(body.material)
    if (body.candidate.draft_id !== id) throw new Error('恢复数值预览必须属于当前原候选。')
    return restoreNumericPreviewAck(await numericRequest('POST /api/v1/content/restore-drafts/{id}/numeric-checks', id, body, key), body)
  },
  check: async id => restoreNumericCheck(await numericRequest('GET /api/v1/content/restore-numeric-checks/{id}', id), id),
  decide: async (id, raw, key) => {
    const body = checkedProvider<ApprovalDecision>('ApprovalDecision', raw)
    return restoreNumericDecisionAck(await numericRequest('POST /api/v1/content/restore-numeric-checks/{id}/decision', id, body, key), id, body)
  },
}
