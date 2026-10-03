import type { SessionResponse, ContentRef, ContentImpactPage as Page, ContentImpactView as View, ImpactObjectDecisionReceipt as Receipt, ImpactObjectDecisionWrite as Write } from '../../../../../packages/contracts/generated/api-types'
import { request } from '../../api/client'
import { checked, page, readView, currentRef } from './schema'
export type ImpactPort = { session(): Promise<SessionResponse>; list(filter: string | null, limit: number, cursor?: string): Promise<Page>; read(id: string, target: string | null, cursor?: string): Promise<View>; current(id: string): Promise<ContentRef>; decide(id: string, body: Write, key: string): Promise<Receipt> }
export const impactClient: ImpactPort = {
  session: async () => checked('SessionResponse', await request('GET /api/v1/session', undefined)),
  list: async (filter, limit, cursor) => page(await request('GET /api/v1/content/impacts', undefined, undefined, { query: { limit, ...(filter ? { changed_object_id: filter } : {}), ...(cursor ? { cursor } : {}) } }), filter, limit),
  read: async (id, target, cursor) => readView(await request('GET /api/v1/content/impacts/{event_id}', undefined, undefined, { path: { event_id: id }, query: { limit: 100, ...(target ? { target_id: target } : {}), ...(cursor ? { cursor } : {}) } }), id, target),
  current: async id => currentRef(await request('GET /api/v1/objects/{id}/current', undefined, undefined, { path: { id } }), id),
  decide: async (id, body, key) => checked('ImpactObjectDecisionReceipt', await request('POST /api/v1/content/impacts/{event_id}/decisions', checked('ImpactObjectDecisionWrite', body), { 'Idempotency-Key': key }, { path: { event_id: id } })),
}
