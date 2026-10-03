import type { AuthoringDraftView, AuthoringJobView, ContentRef, DraftPublishWrite, NumericCheckView, SessionResponse, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
import { request } from '../../api/client'
import { checkedAuthoring } from '../authoring/authoringCommands'
import { checkedPublication, publicationRef } from '../draftPublication/publicationSchema'
import { reviewReceipt } from '../draftReview/reviewSchema'
import { singlePublishedRef, singleSnapshot } from './singlePublicationSchema'

export type SinglePublicationPort = {
  session(): Promise<SessionResponse>; draft(id: string): Promise<AuthoringDraftView>; review(id: string): Promise<StoredReviewReceipt>
  generation(id: string): Promise<AuthoringJobView>
  numeric(id: string): Promise<NumericCheckView>; publish(id: string, body: DraftPublishWrite, key: string): Promise<ContentRef>
  current(id: string): Promise<ContentRef>
}
export const singlePublicationClient: SinglePublicationPort = {
  session: async () => checkedPublication('SessionResponse', await request('GET /api/v1/session', undefined)),
  draft: async id => { const draft = singleSnapshot(await request('GET /api/v1/authoring/drafts/{id}', undefined, undefined, { path: { id } })); if (draft.candidate.draft_id !== id) throw new Error('候选身份不一致。'); return draft },
  review: async id => reviewReceipt(await request('GET /api/v1/reviews/{id}', undefined, undefined, { path: { id } }), id),
  generation: async id => checkedAuthoring('AuthoringJobView', await request('GET /api/v1/authoring/jobs/{id}', undefined, undefined, { path: { id } })),
  numeric: async id => checkedAuthoring('NumericCheckView', await request('GET /api/v1/authoring/numeric-checks/{id}', undefined, undefined, { path: { id } })),
  publish: async (id, body, key) => singlePublishedRef(await request('POST /api/v1/drafts/{id}/publish', checkedPublication('DraftPublishWrite', body), { 'Idempotency-Key': key }, { path: { id } })),
  current: async id => publicationRef(await request('GET /api/v1/objects/{id}/current', undefined, undefined, { path: { id } })),
}
