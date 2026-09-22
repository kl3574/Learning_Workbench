import type { ApprovalDecision, AuthoringGroupDraftView, AuthoringGroupNumericCheckView, AuthoringGroupNumericPreviewWrite, AuthoringGroupPrepareWrite, AuthoringPrivateSolutionView, JobRef, NumericCheckDecisionAck } from '../../../../../packages/contracts/generated/api-types'
import { request } from '../../api/client'
import { checkedAuthoring } from './authoringCommands'

export type AuthoringGroupPort = {
  prepare(body: AuthoringGroupPrepareWrite, key: string): Promise<JobRef>
  draft(id: string): Promise<AuthoringGroupDraftView>
  solution(id: string, member: string): Promise<AuthoringPrivateSolutionView>
  preview(id: string, member: string, body: AuthoringGroupNumericPreviewWrite, key: string): Promise<AuthoringGroupNumericCheckView>
  numeric(id: string): Promise<AuthoringGroupNumericCheckView>
  decide(id: string, body: ApprovalDecision, key: string): Promise<NumericCheckDecisionAck>
}
export const authoringGroupClient: AuthoringGroupPort = {
  prepare: async (body, key) => checkedAuthoring('JobRef', await request('POST /api/v1/authoring/group-jobs', body, { 'Idempotency-Key': key })),
  draft: async id => checkedAuthoring('AuthoringGroupDraftView', await request('GET /api/v1/authoring/draft-groups/{id}', undefined, undefined, { path: { id } })),
  solution: async (id, member_key) => checkedAuthoring('AuthoringPrivateSolutionView', await request('GET /api/v1/authoring/draft-groups/{id}/solutions/{member_key}', undefined, undefined, { path: { id, member_key } })),
  preview: async (id, member_key, body, key) => checkedAuthoring('AuthoringGroupNumericCheckView', await request('POST /api/v1/authoring/draft-groups/{id}/members/{member_key}/numeric-checks', body, { 'Idempotency-Key': key }, { path: { id, member_key } })),
  numeric: async id => checkedAuthoring('AuthoringGroupNumericCheckView', await request('GET /api/v1/authoring/group-numeric-checks/{id}', undefined, undefined, { path: { id } })),
  decide: async (id, body, key) => checkedAuthoring('NumericCheckDecisionAck', await request('POST /api/v1/authoring/group-numeric-checks/{id}/decision', body, { 'Idempotency-Key': key }, { path: { id } })),
}
