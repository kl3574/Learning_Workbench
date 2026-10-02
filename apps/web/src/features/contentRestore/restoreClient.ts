import type { ContentRef, ContentRestoreDraftCreateAck, ContentRestoreDraftCreateWrite, ContentRestoreDraftSnapshot, DraftPublishWrite, SessionResponse, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
import { request } from '../../api/client'
import { publicationClient } from '../draftPublication/publicationClient'
import { compareClient } from '../reader/versionCompare/compareClient'
import { checkedRestore, restoreAck, restoreRequest, restoreSnapshot, type RestoreMaterial } from './restoreSchema'

export type RestorePort = {
  session(): Promise<SessionResponse>
  source(ref: ContentRef): Promise<RestoreMaterial>
  current(id: string): Promise<ContentRef>
  create(body: ContentRestoreDraftCreateWrite, key: string): Promise<ContentRestoreDraftCreateAck>
  draft(id: string): Promise<ContentRestoreDraftSnapshot>
  review(id: string): Promise<StoredReviewReceipt>
  publish(id: string, body: DraftPublishWrite, key: string): Promise<ContentRef>
}
export const restoreClient: RestorePort = {
  session: async () => checkedRestore('SessionResponse', await request('GET /api/v1/session', undefined)),
  source: async ref => { const value = await compareClient.block(ref); return { metadata: value.block, body_markdown: value.body } },
  current: publicationClient.current,
  create: async (raw, key) => { const body = restoreRequest(raw); return restoreAck(await request('POST /api/v1/content/restore-drafts', body, { 'Idempotency-Key': key }), body) },
  draft: async id => restoreSnapshot(await request('GET /api/v1/content/restore-drafts/{id}', undefined, undefined, { path: { id } }), id),
  review: publicationClient.review, publish: publicationClient.publish,
}
