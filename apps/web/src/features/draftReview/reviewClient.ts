import type { DraftReviewWrite, JobCancelRequest, JobSnapshot, ReviewDecisionWrite, ReviewJobAck, SessionResponse, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
import { request, requestWithMetadata } from '../../api/client'
import { checkedReview, reviewReceipt } from './reviewSchema'

export type ReviewPort = {
  session(): Promise<SessionResponse>
  create(id: string, body: DraftReviewWrite, key: string): Promise<ReviewJobAck>
  read(id: string): Promise<StoredReviewReceipt>
  decide(id: string, body: ReviewDecisionWrite, key: string): Promise<StoredReviewReceipt>
  job(id: string): Promise<JobSnapshot>
  cancel(id: string, body: JobCancelRequest, key: string): Promise<JobSnapshot>
  artifact(id: string): Promise<{ data: Blob; etag: string | null }>
}
export const reviewClient: ReviewPort = {
  session: async () => checkedReview('SessionResponse', await request('GET /api/v1/session', undefined)),
  create: async (id, body, key) => checkedReview('ReviewJobAck', await request('POST /api/v1/drafts/{id}/review', checkedReview('DraftReviewWrite', body), { 'Idempotency-Key': key }, { path: { id } })),
  read: async id => reviewReceipt(await request('GET /api/v1/reviews/{id}', undefined, undefined, { path: { id } }), id),
  decide: async (id, body, key) => reviewReceipt(await request('POST /api/v1/reviews/{id}/decision', checkedReview('ReviewDecisionWrite', body), { 'Idempotency-Key': key }, { path: { id } }), id),
  job: async id => checkedReview('JobSnapshot', await request('GET /api/v1/jobs/{id}', undefined, undefined, { path: { id } })),
  cancel: async (id, body, key) => checkedReview('JobSnapshot', await request('POST /api/v1/jobs/{id}/cancel', checkedReview('JobCancelRequest', body), { 'Idempotency-Key': key }, { path: { id } })),
  artifact: id => requestWithMetadata('GET /api/v1/artifacts/{id}/download', undefined, undefined, { path: { id } }),
}
