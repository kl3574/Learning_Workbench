import { createHash, randomUUID } from 'node:crypto'
import { performance } from 'node:perf_hooks'
import { rename, writeFile } from 'node:fs/promises'

type Status = 'queued' | 'running' | 'awaiting_approval' | 'completed' | 'failed' | 'cancelled' | 'UNKNOWN'
type Target = {
  outputPath(name: string): string
  attach(name: string, attachment: { path: string; contentType: string }): Promise<unknown>
}
type Event = { kind: 'grant_ack' | 'poll_start' | 'poll_status'; elapsed_ms: number | null; status?: number | Status; poll_number?: number }
type Core = {
  version: 1; boundary: 'original grant helper resolution'; node_epoch: string; verdict: 'passed' | 'failed'; frozen_ms: number | null
  clock: { source: 'Node monotonic clock'; origin: 'observer construction'; unit: 'ms'; invalid_reads: number }
  poll: { original_default_timeout_ms: 5000; nominal_deadline_ms: number | null; actual_framework_deadline: 'NOT_OBSERVED'; provider_budget_seconds: 10 }
  events: ReadonlyArray<Event>; event_capacity: 64; omitted_events: number
  invalid_inputs: number
  last_status: { status: Status; observed_ms: number | null; poll_number: number } | null
}
type FinallyMarker = { kind: 'test_finally_enter'; entered_ms: number | null; node_epoch: string; frozen_core_sha256: string | null }
type Artifact = { version: 1; diagnostic_wait_budget_ms: 250; core: Core | null; core_sha256: string | null; finally_marker: FinallyMarker | null }
type Options = { clock?: () => number; persist?: (artifact: Artifact, target: Target, signal: AbortSignal) => Promise<unknown> }
const incomplete = () => { try { console.error('Authoring grant diagnostic incomplete; original assertion verdict is unchanged.') } catch { /* Diagnostic reporting cannot mask an assertion. */ } }

function immutable<T>(value: T): T {
  if (value && typeof value === 'object') {
    for (const nested of Object.values(value)) immutable(nested)
    Object.freeze(value)
  }
  return value
}

async function persist(artifact: Artifact, target: Target, signal: AbortSignal) {
  const path = target.outputPath('authoring-grant-diagnostic.json'), pending = path + '.pending'
  await writeFile(pending, JSON.stringify(artifact, null, 2) + '\n', { signal })
  if (signal.aborted) return
  await rename(pending, path)
  if (signal.aborted) return
  await target.attach('authoring-grant-diagnostic', { path, contentType: 'application/json' })
}

/** Test-only scalar input. No Page, Response, body, header, URL, object ID,
 * runtime control or additional HTTP/API operation is accepted or performed. */
export function createAuthoringGrantDiagnostic(options: Options = {}) {
  const clock = options.clock ?? (() => performance.now()), save = options.persist ?? persist
  let epoch: string
  try { epoch = randomUUID() } catch { epoch = 'NOT_OBSERVED' }
  let origin: number | null = null, invalidReads = 0, lastElapsed = 0
  try { const value = clock(); if (Number.isFinite(value)) origin = value; else invalidReads++ } catch { invalidReads++ }
  const elapsed = () => {
    try {
      const value = clock(), result = origin === null ? null : value - origin
      if (result === null || !Number.isFinite(result) || result < lastElapsed) { invalidReads++; return null }
      lastElapsed = result; return result
    } catch { invalidReads++; return null }
  }
  const events: Event[] = []
  let omitted = 0, invalidInputs = 0, pollNumber = 0, deadline: number | null = null, used = false, pollStarted = false, closed = false
  let lastStatus: Core['last_status'] = null, core: Core | null = null, hash: string | null = null, marker: FinallyMarker | null = null
  let finalizing: Promise<boolean> | null = null
  const add = (event: Event) => { if (events.length < 64) events.push(event); else omitted++ }
  const freeze = (verdict: Core['verdict']) => {
    if (closed) return
    closed = true
    const frozen = elapsed()
    core = immutable<Core>({ version: 1, boundary: 'original grant helper resolution', node_epoch: epoch, verdict, frozen_ms: frozen,
      clock: { source: 'Node monotonic clock', origin: 'observer construction', unit: 'ms', invalid_reads: invalidReads },
      poll: { original_default_timeout_ms: 5000, nominal_deadline_ms: deadline, actual_framework_deadline: 'NOT_OBSERVED', provider_budget_seconds: 10 },
      events: events.map(value => ({ ...value })), event_capacity: 64, omitted_events: omitted, invalid_inputs: invalidInputs,
      last_status: lastStatus ? { ...lastStatus } : null })
    try { hash = createHash('sha256').update(JSON.stringify(core)).digest('hex') } catch { hash = null }
  }
  const freezeSafely = (verdict: Core['verdict']) => { try { freeze(verdict) } catch { /* Incomplete metadata never changes the original result/error. */ } }
  const snapshot = (): Artifact => immutable<Artifact>({ version: 1, diagnostic_wait_budget_ms: 250, core, core_sha256: hash, finally_marker: marker })
  return {
    grantAck(status: unknown) {
      if (closed || marker) return
      const safe = typeof status === 'number' && Number.isInteger(status) && status >= 100 && status <= 599 ? status : 'UNKNOWN'
      if (safe === 'UNKNOWN') invalidInputs++
      add({ kind: 'grant_ack', elapsed_ms: elapsed(), status: safe })
    },
    pollStart() {
      if (closed || marker) return
      if (pollStarted) { invalidInputs++; return }
      pollStarted = true
      const start = elapsed(); deadline = start === null ? null : start + 5000
      add({ kind: 'poll_start', elapsed_ms: start })
    },
    pollStatus(status: unknown) {
      if (closed || marker) return
      const safe: Status = typeof status === 'string' && ['queued', 'running', 'awaiting_approval', 'completed', 'failed', 'cancelled'].includes(status) ? status as Status : 'UNKNOWN'
      if (safe === 'UNKNOWN') invalidInputs++
      const at = elapsed(); lastStatus = { status: safe, observed_ms: at, poll_number: ++pollNumber }
      add({ kind: 'poll_status', elapsed_ms: at, status: safe, poll_number: pollNumber })
    },
    async around<T>(operation: () => Promise<T>): Promise<T> {
      if (used) return operation()
      used = true
      try {
        const result = await operation()
        freezeSafely('passed')
        return result
      } catch (original) {
        // Freeze synchronously in this catch, before any storage/finally await.
        freezeSafely('failed')
        throw original
      }
    },
    finallyEnter(target: Target): Promise<boolean> {
      if (finalizing) return finalizing
      try { marker = immutable<FinallyMarker>({ kind: 'test_finally_enter', entered_ms: elapsed(), node_epoch: epoch, frozen_core_sha256: hash }) }
      catch { incomplete(); return Promise.resolve(false) }
      finalizing = (async () => {
        let abort: AbortController | undefined
        let timer: ReturnType<typeof setTimeout> | undefined
        try {
          abort = new AbortController()
          const signal = abort.signal
          const operation = Promise.resolve().then(() => save(snapshot(), target, signal)).then(() => true, () => false)
          const saved = await Promise.race([operation, new Promise<boolean>(resolve => { timer = setTimeout(() => resolve(false), 250) })])
          if (!saved) incomplete()
          return saved
        } catch { incomplete(); return false }
        finally { clearTimeout(timer); try { abort?.abort() } catch { /* Preserve the original assertion. */ } }
      })()
      return finalizing
    },
    snapshot,
  }
}
