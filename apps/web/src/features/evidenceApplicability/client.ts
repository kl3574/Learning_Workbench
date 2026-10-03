import type { SessionResponse, EvidenceApplicabilityDecisionView as View, EvidenceImpactDecisionReceipt as Receipt, EvidenceImpactDecisionWrite as Write } from '../../../../../packages/contracts/generated/api-types'
import { request } from '../../api/client'
import { checked, readView } from './schema'
export type ApplicabilityPort = { session(): Promise<SessionResponse>; read(id: string, event: string | null, cursor?: string): Promise<View>; decide(id: string, body: Write, key: string): Promise<Receipt> }
export const applicabilityClient: ApplicabilityPort = {
  session: async () => checked('SessionResponse', await request('GET /api/v1/session', undefined)),
  read: async (id, event, cursor) => readView(await request('GET /api/v1/learning/evidence/{id}/applicability', undefined, undefined, { path: { id }, query: { ...(event ? { event_id: event } : {}), ...(cursor ? { cursor } : {}) } }), id, event),
  decide: async (id, body, key) => checked('EvidenceImpactDecisionReceipt', await request('POST /api/v1/learning/evidence/{id}/applicability-decisions', checked('EvidenceImpactDecisionWrite', body), { 'Idempotency-Key': key }, { path: { id } })),
}
