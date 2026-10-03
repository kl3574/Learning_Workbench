import { afterEach, expect, test, vi } from 'vitest'
import { authoringMark, authoringObservationHandle, createAuthoringObservation, safeAuthoringObservation } from './authoringObservation'

const facts = { operation: 1, list_sequence: 2, working: true }
const settle = async () => { for (let index = 0; index < 8; index++) await Promise.resolve() }
afterEach(() => { vi.unstubAllGlobals(); authoringObservationHandle(); delete (globalThis as { __authoringObservationSnapshot?: unknown }).__authoringObservationSnapshot })

test('default off requires both explicit synthetic switch and sink; disabling keeps an earlier snapshot safe', () => {
  const sink = vi.fn(), clock = vi.spyOn(performance, 'now')
  expect(authoringObservationHandle()).toBeUndefined()
  vi.stubGlobal('__authoringDiagnosticMechanism', sink)
  expect(authoringObservationHandle()).toBeUndefined()
  expect(clock).not.toHaveBeenCalled()
  vi.stubGlobal('__authoringObservationEnabled', true)
  const handle = authoringObservationHandle()
  authoringMark(handle, 'list_requested', facts)
  const snapshot = (globalThis as { __authoringObservationSnapshot?: () => unknown }).__authoringObservationSnapshot!
  const before = snapshot()
  vi.stubGlobal('__authoringObservationEnabled', false)
  authoringMark(handle, 'list_returned', facts)
  expect(authoringObservationHandle()).toBeUndefined()
  expect(snapshot()).toEqual(before)
  expect(sink).not.toHaveBeenCalled()
  clock.mockRestore()
})

test('closed metadata rejects arbitrary text, headers, values, foreign handles and invalid clocks', () => {
  const sink = vi.fn(), ring = createAuthoringObservation('synthetic', sink, () => 4), handle = ring.begin()
  ring.record(handle, 'list_requested', facts)
  const value = ring.snapshot().records[0]
  for (const extra of [{ text: 'PRIVATE_BODY' }, { headers: 'PRIVATE_HEADER' }, { error: 'PRIVATE_ERROR' }, { job_count: -1 }, { working: 'PRIVATE_VALUE' }, { stage: 'PRIVATE_STAGE' }]) expect(safeAuthoringObservation({ ...value, ...extra })).toBe(false)
  ring.record({ epoch: 'synthetic', hook: 1 }, 'list_requested', facts)
  ring.record(handle, 'list_requested', { ...facts, text: 'PRIVATE_BODY' } as typeof facts)
  const brokenClock = createAuthoringObservation('clock', sink, () => { throw new Error('PRIVATE_CLOCK') })
  brokenClock.record(brokenClock.begin(), 'list_requested', facts)
  expect(ring.snapshot().invalid).toBe(2); expect(brokenClock.snapshot().invalid).toBe(1)
  expect(JSON.stringify(ring.snapshot())).not.toContain('PRIVATE_')
  const copied = ring.snapshot(); copied.records[0].working = false; copied.records.pop()
  expect(ring.snapshot().records).toEqual([value]); expect(value.working).toBe(true)
  ring.dispose(); brokenClock.dispose()
})

test('bounded stalled delivery cannot block or grow beyond the explicit ring capacity', async () => {
  const sink = vi.fn(() => new Promise(() => undefined)), ring = createAuthoringObservation('bounded', sink, () => 1, 2), handle = ring.begin()
  for (let count = 0; count < 1000; count++) ring.record(handle, 'list_requested', facts)
  await settle()
  expect(sink).toHaveBeenCalledTimes(1)
  expect(ring.snapshot()).toMatchObject({ omitted: 998, invalid: 0, delivery_pending: 2, delivery_failures: 0 })
  expect(ring.snapshot().records).toHaveLength(2)
  ring.dispose()
})

test.each(['throw', 'reject'] as const)('a %s sink never escapes and records its own failure without exception text', async mode => {
  const ring = createAuthoringObservation('failure', () => { if (mode === 'throw') throw new Error('PRIVATE_SINK'); return Promise.reject(new Error('PRIVATE_SINK')) }, () => 1)
  expect(() => ring.record(ring.begin(), 'list_requested', facts)).not.toThrow()
  await settle()
  expect(ring.snapshot()).toMatchObject({ delivery_failures: 1, delivery_pending: 0 })
  expect(JSON.stringify(ring.snapshot())).not.toContain('PRIVATE_')
  ring.dispose()
})
