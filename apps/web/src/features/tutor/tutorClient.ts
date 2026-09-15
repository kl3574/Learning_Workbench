import type { TutorMessagePage, TutorRunCancel, TutorRunControlView, TutorRunCreate, TutorRunView, TutorThreadCreate, TutorThreadPage, TutorThreadView } from '../../../../../packages/contracts/generated/api-types'
import type { TutorPageQuery } from '../../../../../packages/contracts/generated/tutor-ports-binding'
import { createTutorEventsClient, type TutorSSEEvent } from '../../../../../packages/contracts/generated/tutor-sse'
import { request } from '../../api/client'
import { checkedTutor } from './tutorCommands'
export type TutorPort = {
  threads(query: TutorPageQuery): Promise<TutorThreadPage>
  create(body: TutorThreadCreate, key: string): Promise<TutorThreadView>
  messages(id: string, query: TutorPageQuery): Promise<TutorMessagePage>
  start(body: TutorRunCreate, key: string): Promise<TutorRunView>
  read(id: string): Promise<TutorRunView>
  cancel(id: string, body: TutorRunCancel, key: string): Promise<TutorRunControlView>
  events(id: string, after: number, signal: AbortSignal): AsyncIterable<TutorSSEEvent>
}
const events = createTutorEventsClient()
export const tutorClient: TutorPort = {
  threads: async query => checkedTutor('TutorThreadPage', await request('GET /api/v1/threads', undefined, undefined, { query })),
  create: async (body, key) => checkedTutor('TutorThreadView', await request('POST /api/v1/threads', body, { 'Idempotency-Key': key })),
  messages: async (id, query) => checkedTutor('TutorMessagePage', await request('GET /api/v1/threads/{id}/messages', undefined, undefined, { path: { id }, query })),
  start: async (body, key) => checkedTutor('TutorRunView', await request('POST /api/v1/tutor/runs', body, { 'Idempotency-Key': key })),
  read: async id => checkedTutor('TutorRunView', await request('GET /api/v1/runs/{id}', undefined, undefined, { path: { id } })),
  cancel: async (id, body, key) => checkedTutor('TutorRunControlView', await request('POST /api/v1/runs/{id}/cancel', body, { 'Idempotency-Key': key }, { path: { id } })),
  events,
}
