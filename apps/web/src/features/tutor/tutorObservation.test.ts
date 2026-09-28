import { describe, expect, it } from 'vitest'
import { createTutorObservation } from './tutorObservation'

describe('optional Tutor metadata observation', () => {
  it('records bounded closed primitives and contains synchronous/rejected observers', async () => {
    for (const sink of [() => { throw new Error('SENTINEL') }, () => Promise.reject(new Error('SENTINEL'))]) {
      const observer = createTutorObservation('epoch', sink, () => 7, 2)
      const span = observer.begin('run_unit', 4, 2)
      expect(span).toBeDefined()
      observer.record(span, 'validated_event_yield', { seq: 3, event: 'completed' })
      observer.record(span, 'reload_trigger')
      observer.record(span, 'iterator_closed')
      await new Promise(resolve => setTimeout(resolve, 0))
      const snapshot = observer.snapshot()
      expect(snapshot.records).toHaveLength(2)
      expect(snapshot.omitted).toBe(1)
      expect(snapshot.records[0]).toMatchObject({ epoch: 'epoch', ordinal: 1, source_ms: 7, run: 'run_unit', operation: 4, after: 2, seq: 3 })
      expect(JSON.stringify(snapshot)).not.toContain('SENTINEL')
    }
  })
  it('rejects malformed metadata without retaining payload or creating arbitrary fields', () => {
    const observer = createTutorObservation('epoch', () => undefined, () => 1)
    expect(observer.begin('PRIVATE BODY', 0, 0)).toBeUndefined()
    const span = observer.begin('run_unit', 0, 0)
    observer.record(span, 'validated_event_yield', { seq: -1, event: 'completed' })
    observer.record(span, 'validated_event_yield', { seq: 1, event: 'completed', text: 'PRIVATE BODY' } as never)
    const value = observer.snapshot()
    expect(value.records).toHaveLength(0)
    expect(value.invalid).toBe(3)
    expect(JSON.stringify(value)).not.toContain('PRIVATE BODY')
  })
})

describe('observation of the unchanged strict SSE codec', () => {
  it('joins one actual fetch/cursor and only validated yields without collecting answer bytes', async () => {
    const { vi } = await import('vitest')
    vi.resetModules()
    const batches: unknown[] = []
    vi.stubGlobal('__tutorObservationEnabled', true)
    vi.stubGlobal('__tutorDiagnosticMechanism', (batch: unknown) => { batches.push(batch); throw new Error('OBSERVER_FAILURE') })
    const event = { run_id: 'run_unit', seq: 1, occurred_at: '2026-09-22T00:00:00Z', type: 'answer_delta', text: 'PRIVATE_ANSWER' }
    const frame = `id: run_unit:1\nevent: answer_delta\ndata: ${JSON.stringify(event)}\n\n`
    const fetcher = vi.fn(async () => new Response(frame + frame, { headers: { 'Content-Type': 'text/event-stream' } }))
    vi.stubGlobal('fetch', fetcher)
    try {
      const { tutorClient } = await import('./tutorClient'), { tutorTrace } = await import('./tutorObservation')
      const trace = tutorTrace('run_unit', 3, 0), signal = new AbortController().signal
      const received = []
      for await (const value of tutorClient.events('run_unit', 0, signal, trace)) received.push(value)
      expect(received).toEqual([event])
      expect(fetcher).toHaveBeenCalledTimes(1)
      const request = fetcher.mock.calls[0] as unknown as [string, RequestInit]
      expect(request[0]).toBe('/api/v1/runs/run_unit/events?after_seq=0')
      expect(request[1]).toMatchObject({ credentials: 'same-origin', cache: 'no-store', signal })
      expect(new Headers(request[1].headers).get('X-Tutor-Observation')).toBe(trace?.span)
      await new Promise(resolve => setTimeout(resolve, 0))
      const records = batches.flat() as { stage: string; span: string }[]
      expect(records.filter(value => value.stage === 'validated_event_yield')).toHaveLength(1)
      expect(records.every(value => value.span === trace?.span)).toBe(true)
      expect(JSON.stringify(batches)).not.toContain('PRIVATE_ANSWER')
      fetcher.mockImplementation(async () => new Response(frame.replace('"seq":1', '"seq":2'), { headers: { 'Content-Type': 'text/event-stream' } }))
      const broken = async () => { for await (const value of tutorClient.events('run_unit', 0, signal, trace)) void value }
      await expect(broken()).rejects.toThrow('Invalid Tutor SSE')
    } finally { vi.unstubAllGlobals() }
  })
})

describe('normal GET transport remains authoritative', () => {
  it('keeps default/invalid headers and original errors while containing a throwing observer', async () => {
    const { vi } = await import('vitest')
    vi.resetModules()
    const { tutorRun } = await import('./tutorFixtures')
    const actual = tutorRun(), fetcher = vi.fn(async () => new Response(JSON.stringify(actual), { headers: { 'Content-Type': 'application/json' } }))
    vi.stubGlobal('fetch', fetcher)
    try {
      const { tutorClient } = await import('./tutorClient')
      const { tutorTrace } = await import('./tutorObservation')
      const { readTutorRunWithObservation } = await import('../../api/client')
      await expect(tutorClient.read(actual.run.id)).resolves.toEqual(actual)
      const ordinary = (fetcher.mock.calls[0] as unknown as [string, RequestInit])[1]
      vi.stubGlobal('__tutorObservationEnabled', true)
      vi.stubGlobal('__tutorDiagnosticMechanism', () => { throw new Error('OBSERVER_FAILURE') })
      await expect(readTutorRunWithObservation(actual.run.id, 'invalid\nlabel')).resolves.toEqual(actual)
      expect((fetcher.mock.calls[1] as unknown as [string, RequestInit])[1]).toEqual(ordinary)
      const trace = tutorTrace(actual.run.id, 1, 0)
      await expect(tutorClient.read(actual.run.id, trace)).resolves.toEqual(actual)
      const observed = (fetcher.mock.calls[2] as unknown as [string, RequestInit])[1]
      expect(observed).toEqual({ ...ordinary, headers: { ...ordinary.headers, 'X-Tutor-Observation': trace?.span } })
      vi.stubGlobal('__tutorObservationEnabled', false)
      await expect(tutorClient.read(actual.run.id, trace)).resolves.toEqual(actual)
      expect((fetcher.mock.calls[3] as unknown as [string, RequestInit])[1]).toEqual(ordinary)
      fetcher.mockImplementation(async () => new Response(JSON.stringify({ error: { code: 'POLICY_DENIED', message: 'Original policy error' } }), { status: 403 }))
      await expect(tutorClient.read(actual.run.id, trace)).rejects.toMatchObject({ status: 403, code: 'POLICY_DENIED', message: 'Original policy error' })
      expect(fetcher).toHaveBeenCalledTimes(5)
    } finally { vi.unstubAllGlobals() }
  })
})

it('a stalled metadata delivery remains bounded without holding the original stream open', async () => {
  const { vi } = await import('vitest')
  vi.resetModules()
  const deliveries = vi.fn(() => new Promise(() => undefined))
  vi.stubGlobal('__tutorObservationEnabled', true); vi.stubGlobal('__tutorDiagnosticMechanism', deliveries)
  const event = { run_id: 'run_stalled', seq: 1, occurred_at: '2026-09-22T00:00:00Z', type: 'completed' }
  vi.stubGlobal('fetch', vi.fn(async () => new Response(`id: run_stalled:1\nevent: completed\ndata: ${JSON.stringify(event)}\n\n`, { headers: { 'Content-Type': 'text/event-stream' } })))
  try {
    const { tutorClient } = await import('./tutorClient'), { tutorTrace } = await import('./tutorObservation')
    const items = []
    for await (const value of tutorClient.events('run_stalled', 0, new AbortController().signal, tutorTrace('run_stalled', 1, 0))) items.push(value)
    expect(items).toEqual([event]); expect(deliveries).toHaveBeenCalledTimes(1)
    const snapshot = (globalThis as unknown as { __tutorObservationSnapshot: () => { delivery_pending: number } }).__tutorObservationSnapshot()
    expect(snapshot.delivery_pending).toBe(3)
  } finally { vi.unstubAllGlobals() }
})
