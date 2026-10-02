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
function identity(id: string, key?: string): void {
  if (!validIdentity(id) || key !== undefined && !/^[A-Za-z0-9_-]{1,128}$/.test(key)) throw new Error('恢复数值对象或原命令键无效。')
}
export const restoreNumericClient: RestoreNumericPort = {
  session: async () => checkedProvider('SessionResponse', await request('GET /api/v1/session', undefined)),
  draft: async id => restoreNumericSnapshot(await request('GET /api/v1/content/restore-drafts/{id}', undefined, undefined, { path: { id } }), id),
  current: publicationClient.current,
  preview: async (id, raw, key) => {
    identity(id, key)
    const body = checkedRestoreNumeric<RestoreNumericCheckPreviewWrite>('RestoreNumericCheckPreviewWrite', raw)
    restoreNumericMaterial(body.material)
    if (body.candidate.draft_id !== id) throw new Error('恢复数值预览必须属于当前原候选。')
    return restoreNumericPreviewAck(await request('POST /api/v1/content/restore-drafts/{id}/numeric-checks', body, { 'Idempotency-Key': key }, { path: { id } }), body)
  },
  check: async id => { identity(id); return restoreNumericCheck(await request('GET /api/v1/content/restore-numeric-checks/{id}', undefined, undefined, { path: { id } }), id) },
  decide: async (id, raw, key) => {
    identity(id, key)
    const body = checkedProvider<ApprovalDecision>('ApprovalDecision', raw)
    return restoreNumericDecisionAck(await request('POST /api/v1/content/restore-numeric-checks/{id}/decision', body, { 'Idempotency-Key': key }, { path: { id } }), id, body)
  },
}
