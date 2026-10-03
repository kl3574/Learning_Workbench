import type { TutorRunView } from '../../../../../packages/contracts/generated/api-types'

const stages = ['validated_event_yield', 'stream_request', 'stream_response', 'iterator_closed', 'event_applied', 'scope_discarded', 'reload_trigger', 'read_request', 'read_checked', 'snapshot_accepted'] as const
const eventTypes = ['queued', 'context_ready', 'approval_required', 'answer_delta', 'citation', 'retrieval_completed', 'usage', 'completed', 'failed', 'cancelled']
const statuses = ['queued', 'running', 'awaiting_approval', 'completed', 'failed', 'cancelled']
type Stage = typeof stages[number]
export type TutorTrace = Readonly<{ run: string; operation: number; after: number; span: string; cause?: string }>
type Facts = { seq?: number; revision?: number; event?: string; status?: string; http_status?: number }
export type TutorObservationRecord = TutorTrace & Facts & { epoch: string; ordinal: number; source_ms: number; stage: Stage }
export type TutorObservationSnapshot = { epoch: string; records: TutorObservationRecord[]; omitted: number; invalid: number; delivery_failures: number; delivery_pending: number }
const integer = (value: unknown) => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0
const label = (value: unknown) => typeof value === 'string' && /^[A-Za-z0-9_-]{1,96}$/.test(value)
const spanId = (value: unknown): value is string => typeof value === 'string' && /^[A-Za-z0-9_-]{1,96}:\d{1,16}$/.test(value)
export function safeTutorObservation(value: unknown): value is TutorObservationRecord {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  const item = value as Record<string, unknown>
  if (Object.keys(item).some(key => !['epoch', 'ordinal', 'source_ms', 'stage', 'run', 'operation', 'after', 'span', 'cause', 'seq', 'revision', 'event', 'status', 'http_status'].includes(key))) return false
  return label(item.epoch) && integer(item.ordinal) && (item.ordinal as number) > 0 && Number.isFinite(item.source_ms) && typeof item.source_ms === 'number' && item.source_ms >= 0
    && stages.includes(item.stage as Stage) && typeof item.run === 'string' && /^run_[A-Za-z0-9_-]{1,90}$/.test(item.run)
    && integer(item.operation) && integer(item.after) && spanId(item.span) && item.span.startsWith(`${item.epoch}:`)
    && (item.cause === undefined || spanId(item.cause))
    && ['seq', 'revision', 'http_status'].every(key => item[key] === undefined || integer(item[key]))
    && (item.event === undefined || typeof item.event === 'string' && eventTypes.includes(item.event))
    && (item.status === undefined || typeof item.status === 'string' && statuses.includes(item.status))
}

/** An opt-in metadata ring. No caller DTO, payload, exception or sink result is retained.
 * Delivery runs in a separate microtask; one unresolved sink cannot grow a queue. */
export function createTutorObservation(epoch: string, sink: (records: TutorObservationRecord[]) => unknown,
  clock: () => number = () => performance.now(), capacity = 1024) {
  const records: TutorObservationRecord[] = []
  const handles = new WeakSet<TutorTrace>()
  let serial = 0, omitted = 0, invalid = 0, failures = 0, pending = false, delivered = 0, inFlight = 0
  const limit = Number.isSafeInteger(capacity) ? Math.max(1, Math.min(capacity, 1024)) : 1024
  const flush = () => {
    if (pending || delivered === records.length) return
    pending = true
    queueMicrotask(() => {
      const batch = records.slice(delivered, delivered + 64).map(value => ({ ...value })); delivered += batch.length; inFlight = batch.length
      void (async () => { try { await sink(batch) } catch { failures++ }
        finally { pending = false; inFlight = 0; flush() } })()
    })
  }
  return {
    begin(run: string, operation: number, after: number, cause?: string): TutorTrace | undefined {
      try {
        const value = { run, operation, after, span: `${epoch}:${++serial}`, ...(cause ? { cause } : {}) }
        if (!safeTutorObservation({ ...value, epoch, ordinal: 1, source_ms: 0, stage: 'read_request' })) { invalid++; return }
        handles.add(value); return Object.freeze(value)
      } catch { invalid++; return }
    },
    owns(trace: TutorTrace): boolean { return handles.has(trace) },
    record(trace: TutorTrace | undefined, stage: Stage, facts: Facts = {}): string | undefined {
      try {
        if (!trace) return
        if (Object.keys(facts).some(key => !['seq', 'revision', 'event', 'status', 'http_status'].includes(key))) { invalid++; return }
        const value = { ...trace, ...facts, epoch, ordinal: records.length + 1, source_ms: clock(), stage }
        if (!safeTutorObservation(value)) { invalid++; return }
        if (records.length === limit) { omitted++; return }
        records.push(Object.freeze(value)); flush()
        return `${epoch}:${value.ordinal}`
      } catch { invalid++; return }
    },
    snapshot(): TutorObservationSnapshot { return { epoch, records: records.map(value => ({ ...value })), omitted, invalid, delivery_failures: failures, delivery_pending: records.length - delivered + inFlight } },
  }
}

type Host = { __tutorObservationEnabled?: boolean; __tutorDiagnosticMechanism?: (records: TutorObservationRecord[]) => unknown;
  __tutorObservationSnapshot?: () => TutorObservationSnapshot }
let observer: ReturnType<typeof createTutorObservation> | undefined
const renders = new WeakMap<TutorRunView, string>()
function installed() {
  try {
    const host = globalThis as Host
    if (host.__tutorObservationEnabled !== true) return
    if (!observer) {
      observer = createTutorObservation(crypto.randomUUID(), batch => host.__tutorDiagnosticMechanism?.(batch))
      host.__tutorObservationSnapshot = () => observer!.snapshot()
    }
    return observer
  } catch { return }
}
export const tutorTrace = (run: string, operation: number, after: number, cause?: string) => installed()?.begin(run, operation, after, cause)
export function tutorMark(trace: TutorTrace | undefined, stage: Stage, facts?: Facts) { return installed()?.record(trace, stage, facts) }
export function tutorRender(value: TutorRunView, trace: TutorTrace | undefined, stage: 'snapshot_accepted' | 'event_applied') {
  const token = tutorMark(trace, stage, { seq: value.run.last_seq, revision: value.job_revision, status: value.run.status })
  if (token) renders.set(value, token)
}
export const tutorRenderToken = (value: TutorRunView) => installed() ? renders.get(value) : undefined

export const activeTutorTrace = (trace: TutorTrace | undefined) => trace && installed()?.owns(trace) ? trace : undefined
