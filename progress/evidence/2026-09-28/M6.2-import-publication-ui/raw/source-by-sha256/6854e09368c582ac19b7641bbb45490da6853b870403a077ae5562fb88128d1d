import type { ContentRef, DraftPublishWrite, ImportDraftSnapshot, SessionResponse, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
import { request } from '../../api/client'
import { reviewReceipt } from '../draftReview/reviewSchema'
import { checkedPublication, publicationRef } from './publicationSchema'

export type PublicationPort = {
  session(): Promise<SessionResponse>
  draft(id: string): Promise<ImportDraftSnapshot>
  review(id: string): Promise<StoredReviewReceipt>
  publish(id: string, body: DraftPublishWrite, key: string): Promise<ContentRef>
  current(id: string): Promise<ContentRef>
}
export const publicationClient: PublicationPort = {
  session: async () => checkedPublication('SessionResponse', await request('GET /api/v1/session', undefined)),
  draft: async id => checkedPublication('ImportDraftSnapshot', await request('GET /api/v1/drafts/{id}', undefined, undefined, { path: { id } })),
  review: async id => reviewReceipt(await request('GET /api/v1/reviews/{id}', undefined, undefined, { path: { id } }), id),
  publish: async (id, body, key) => publicationRef(await request('POST /api/v1/drafts/{id}/publish', checkedPublication('DraftPublishWrite', body), { 'Idempotency-Key': key }, { path: { id } })),
  current: async id => publicationRef(await request('GET /api/v1/objects/{id}/current', undefined, undefined, { path: { id } })),
}
