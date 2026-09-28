import type { TutorMessagePage, TutorRunCancel, TutorRunControlView, TutorRunCreate, TutorRunView, TutorThreadCreate, TutorThreadPage, TutorThreadView } from '../../../../../packages/contracts/generated/api-types'
import type { TutorPageQuery } from '../../../../../packages/contracts/generated/tutor-ports-binding'
import { createTutorEventsClient, type TutorSSEEvent } from '../../../../../packages/contracts/generated/tutor-sse'
import { request, readTutorRunWithObservation } from '../../api/client'
import { activeTutorTrace, tutorMark, type TutorTrace } from './tutorObservation'
import { checkedTutor } from './tutorCommands'
export type TutorPort = {
  threads(query: TutorPageQuery): Promise<TutorThreadPage>
  create(body: TutorThreadCreate, key: string): Promise<TutorThreadView>
  messages(id: string, query: TutorPageQuery): Promise<TutorMessagePage>
  start(body: TutorRunCreate, key: string): Promise<TutorRunView>
  read(id: string, trace?: TutorTrace): Promise<TutorRunView>
  cancel(id: string, body: TutorRunCancel, key: string): Promise<TutorRunControlView>
  events(id: string, after: number, signal: AbortSignal, trace?: TutorTrace): AsyncIterable<TutorSSEEvent>
}
const events = createTutorEventsClient()
export const tutorClient: TutorPort = {
  threads: async query => checkedTutor('TutorThreadPage', await request('GET /api/v1/threads', undefined, undefined, { query })),
  create: async (body, key) => checkedTutor('TutorThreadView', await request('POST /api/v1/threads', body, { 'Idempotency-Key': key })),
  messages: async (id, query) => checkedTutor('TutorMessagePage', await request('GET /api/v1/threads/{id}/messages', undefined, undefined, { path: { id }, query })),
  start: async (body, key) => checkedTutor('TutorRunView', await request('POST /api/v1/tutor/runs', body, { 'Idempotency-Key': key })),
  read: async (id, trace) => {
    trace = activeTutorTrace(trace)
    tutorMark(trace, 'read_request')
    const value = checkedTutor<TutorRunView>('TutorRunView', await (trace
      ? readTutorRunWithObservation(id, trace.span)
      : request('GET /api/v1/runs/{id}', undefined, undefined, { path: { id } })))
    tutorMark(trace, 'read_checked', { seq: value.run.last_seq, revision: value.job_revision, status: value.run.status })
    return value
  },
  cancel: async (id, body, key) => checkedTutor('TutorRunControlView', await request('POST /api/v1/runs/{id}/cancel', body, { 'Idempotency-Key': key }, { path: { id } })),
  async *events(id, after, signal, trace) {
    trace = activeTutorTrace(trace)
    if (!trace) { yield* events(id, after, signal); return }
    const observed = createTutorEventsClient(async (input, init) => {
      tutorMark(trace, 'stream_request')
      const headers = new Headers(init?.headers); headers.set('X-Tutor-Observation', trace.span)
      const response = await fetch(input, { ...init, headers })
      tutorMark(trace, 'stream_response', { http_status: response.status })
      return response
    })
    for await (const event of observed(id, after, signal)) {
      tutorMark(trace, 'validated_event_yield', { seq: event.seq, event: event.type })
      yield event
    }
  },
}
