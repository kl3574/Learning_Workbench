import type { ApprovalDecision, AuthoringDraftView, AuthoringJobPage, AuthoringJobView, AuthoringPrepareWrite, JobRef, JobSnapshot, NumericCheckDecisionAck, NumericCheckPreviewWrite, NumericCheckView, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import { request } from '../../api/client'
import { checkedAuthoring } from './authoringCommands'
export type AuthoringPort = {
  session(): Promise<SessionResponse>
  list(cursor?: string): Promise<AuthoringJobPage>
  prepare(body: AuthoringPrepareWrite, key: string): Promise<JobRef>
  read(id: string): Promise<AuthoringJobView>
  draft(id: string): Promise<AuthoringDraftView>
  preview(id: string, body: NumericCheckPreviewWrite, key: string): Promise<NumericCheckView>
  numeric(id: string): Promise<NumericCheckView>
  decide(id: string, body: ApprovalDecision, key: string): Promise<NumericCheckDecisionAck>
  job(id: string): Promise<JobSnapshot>
  cancel(id: string, body: { expected_revision: number }, key: string): Promise<JobSnapshot>
}
export const authoringClient: AuthoringPort = {
  session: () => request('GET /api/v1/session', undefined),
  list: async cursor => checkedAuthoring('AuthoringJobPage', await request('GET /api/v1/authoring/jobs', undefined, undefined, { query: { limit: 20, ...(cursor ? { cursor } : {}) } })),
  prepare: async (body, key) => checkedAuthoring('JobRef', await request('POST /api/v1/authoring/jobs', body, { 'Idempotency-Key': key })),
  read: async id => checkedAuthoring('AuthoringJobView', await request('GET /api/v1/authoring/jobs/{id}', undefined, undefined, { path: { id } })),
  draft: async id => checkedAuthoring('AuthoringDraftView', await request('GET /api/v1/authoring/drafts/{id}', undefined, undefined, { path: { id } })),
  preview: async (id, body, key) => checkedAuthoring('NumericCheckView', await request('POST /api/v1/authoring/drafts/{id}/numeric-checks', body, { 'Idempotency-Key': key }, { path: { id } })),
  numeric: async id => checkedAuthoring('NumericCheckView', await request('GET /api/v1/authoring/numeric-checks/{id}', undefined, undefined, { path: { id } })),
  decide: async (id, body, key) => checkedAuthoring('NumericCheckDecisionAck', await request('POST /api/v1/authoring/numeric-checks/{id}/decision', body, { 'Idempotency-Key': key }, { path: { id } })),
  job: async id => checkedAuthoring('JobSnapshot', await request('GET /api/v1/jobs/{id}', undefined, undefined, { path: { id } })),
  cancel: async (id, body, key) => checkedAuthoring('JobSnapshot', await request('POST /api/v1/jobs/{id}/cancel', body, { 'Idempotency-Key': key }, { path: { id } })),
}
