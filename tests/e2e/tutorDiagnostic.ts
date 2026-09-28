import { randomUUID } from 'node:crypto'
import { safeTutorObservation, type TutorObservationRecord } from '../../apps/web/src/features/tutor/tutorObservation'
import { performance } from 'node:perf_hooks'
import { rename, writeFile } from 'node:fs/promises'
import type { Page, Request, Response, TestInfo } from '../../apps/web/node_modules/@playwright/test/index.mjs'

type ReadResult = { state: 'complete'; value: unknown } | { state: 'timeout' | 'failed' }
type SafeDOM = { run_status: string | null; tutor_present: boolean; observing: boolean; answer_present: boolean; grant_ack_present: boolean; consent_linked: boolean }
type ReadPort = { readRun?: (id: string) => Promise<unknown>; readRuntime: () => Promise<unknown> }
const states = new Set(['queued', 'running', 'awaiting_approval', 'completed', 'failed', 'cancelled'])
const integer = (value: unknown) => typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value : null

async function within<T>(operation: Promise<T>, milliseconds: number, fallback: T): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined
  try { return await Promise.race([operation, new Promise<T>(resolve => { timer = setTimeout(() => resolve(fallback), milliseconds) })]) }
  finally { clearTimeout(timer) }
}

/** Pick safe facts only; never serialize the Run response body or result text. */
export function safeRun(value: unknown, expected: string) {
  const outer = value as Record<string, unknown> | null, run = outer?.run as Record<string, unknown> | undefined
  if (!run || run.id !== expected || typeof run.status !== 'string' || !states.has(run.status)
    || integer(run.last_seq) === null || integer(outer?.job_revision) === null) throw new Error('INVALID_SAFE_PROJECTION')
  const result = outer?.result as Record<string, unknown> | undefined, provider = result?.provider as Record<string, unknown> | null
  const usage = result?.usage as Record<string, unknown> | undefined
  return { id: expected, status: run.status, last_seq: run.last_seq, job_revision: outer?.job_revision,
    consent_present: typeof outer?.consent_id === 'string', answer_present: typeof run.answer_markdown === 'string' && run.answer_markdown.length > 0,
    provider_receipt_present: typeof provider?.receipt_id === 'string',
    provider_outcome: typeof provider?.outcome === 'string' && ['complete', 'refused', 'incomplete', 'error'].includes(provider.outcome) ? provider.outcome : null,
    input_tokens: integer(usage?.input_tokens), output_tokens: integer(usage?.output_tokens) }
}

export function safeRuntime(value: unknown) {
  const item = value as Record<string, unknown> | null
  if (!item || item.test_only !== true) throw new Error('INVALID_RUNTIME_OBSERVATION')
  const names = ['received_request_count', 'validated_request_count', 'invalid_request_count'] as const
  if (names.some(name => integer(item[name]) === null)) throw new Error('INVALID_RUNTIME_OBSERVATION')
  return { test_only: true, received_request_count: item.received_request_count,
    validated_request_count: item.validated_request_count, invalid_request_count: item.invalid_request_count }
}

/** Validate again at the publication boundary; arbitrary fixture fields never survive. */
export function safeAPIMechanism(value: unknown, expected: string) {
  const item = value as Record<string, unknown> | null
  if (!item || typeof item.epoch !== 'string' || !/^[a-f0-9]{32}$/.test(item.epoch) || item.selected_run !== expected
    || integer(item.snapshot_source_ns) === null || integer(item.omitted) === null || integer(item.invalid) === null || typeof item.snapshot_contended !== 'boolean'
    || !Array.isArray(item.records) || item.records.length > 1024) throw new Error('INVALID_API_MECHANISM')
  const stages = ['run_bound', 'request_entered', 'request_returned', 'request_raised', 'response_started', 'frame_offered', 'asgi_send_returned', 'owner_read_entered', 'owner_read_returned', 'owner_events_entered', 'owner_events_returned', 'owner_authorize_returned', 'provider_terminal_commit_returned', 'consumer_step_returned', 'tutor_terminal_committed']
  const events = ['queued', 'context_ready', 'retrieval_completed', 'answer_delta', 'citation', 'approval_required', 'usage', 'completed', 'failed', 'cancelled']
  const records = item.records.map((raw: unknown, index: number) => {
    const row = raw as Record<string, unknown>
    if (!row || Object.keys(row).some(key => !['epoch', 'ordinal', 'source_ns', 'stage', 'run', 'seq', 'revision', 'after', 'http_status', 'status', 'event', 'request', 'correlation', 'receipt', 'dispatch'].includes(key))
      || row.epoch !== item.epoch || row.run !== expected || row.ordinal !== index + 1 || integer(row.source_ns) === null
      || (typeof row.stage !== 'string' || !stages.includes(row.stage))
      || ['seq', 'revision', 'after', 'http_status'].some(key => row[key] !== undefined && integer(row[key]) === null)
      || row.status !== undefined && (typeof row.status !== 'string' || !states.has(row.status)) || row.event !== undefined && (typeof row.event !== 'string' || !events.includes(row.event))
      || ['request', 'receipt', 'dispatch'].some(key => row[key] !== undefined && (typeof row[key] !== 'string' || !/^[A-Za-z][A-Za-z0-9_-]{0,79}$/.test(row[key])))
      || row.correlation !== undefined && (typeof row.correlation !== 'string' || !/^[A-Za-z0-9_-]{1,96}:\d{1,16}$/.test(row.correlation))) throw new Error('INVALID_API_MECHANISM')
    return { ...row }
  })
  return { epoch: item.epoch, selected_run: expected, snapshot_source_ns: item.snapshot_source_ns, records, omitted: item.omitted, invalid: item.invalid, snapshot_contended: item.snapshot_contended,
    timing: 'API ring from the periodic fixture control file, read after assertion. Capture time is on the API clock and may precede this file read. No cross-clock deadline placement.' }
}

/** Passive metadata only. Request identity is the actual Playwright Request object.
 * SSE request cursors are observed; streamed frames/bodies are deliberately not read. */
export async function observeTutorCompletion(page: Page, ports: ReadPort) {
  const nodeEpoch = randomUUID()
  const mechanism: Array<TutorObservationRecord & { delivered_ms: number }> = []
  let mechanismInvalid = 0, mechanismOmitted = 0
  const projections: Array<{ token: string; run: string; seq: number; revision: number; status: string; source_ms: number; ordinal: number; delivered_ms: number }> = []
  const started = performance.now(), startedAt = new Date().toISOString()
  const requests = new WeakMap<Request, number>(), events: object[] = []
  let serial = 0, omitted = 0, active = true, runId: string | null = null
  let lastDOM: { elapsed_ms: number; state: SafeDOM } | null = null
  const elapsed = () => performance.now() - started
  const add = (value: object) => { if (!active) return; if (events.length < 2000) events.push({ elapsed_ms: elapsed(), ...value }); else omitted++ }
  const requestStarted = (request: Request) => {
    const url = new URL(request.url())
    if (!url.pathname.startsWith('/api/v1/')) return
    const id = ++serial; requests.set(request, id)
    const cursor = url.pathname.endsWith('/events') ? url.searchParams.get('after_seq') : null
    add({ kind: 'request', id, method: request.method(), path: url.pathname,
      ...(cursor !== null && /^\d{1,16}$/.test(cursor) && Number.isSafeInteger(Number(cursor)) ? { after_seq: Number(cursor) } : {}) })
  }
  const responseReceived = (response: Response) => { const id = requests.get(response.request()); if (id !== undefined) add({ kind: 'response', id, status: response.status() }) }
  const requestFinished = (request: Request) => { const id = requests.get(request); if (id !== undefined) add({ kind: 'finished', id }) }
  const requestFailed = (request: Request) => {
    const id = requests.get(request), raw = request.failure()?.errorText ?? ''
    if (id !== undefined) add({ kind: 'failed', id, failure: /^net::ERR_[A-Z_]+$/.test(raw) ? raw : 'REQUEST_FAILED' })
  }
  page.on('request', requestStarted); page.on('response', responseReceived)
  page.on('requestfinished', requestFinished); page.on('requestfailed', requestFailed)
  // Only this binding's arrival gets a Node-clock timestamp. Browser-clock values
  // are never subtracted from it. No arbitrary DOM text crosses the binding.
  await page.exposeBinding('__tutorDiagnosticMechanism', (_source, batch: unknown) => {
    if (!active) return
    if (!Array.isArray(batch) || batch.length > 64) { mechanismInvalid++; return }
    for (const item of batch) {
      if (!safeTutorObservation(item)) { mechanismInvalid++; continue }
      if (runId && item.run !== runId) continue
      if (mechanism.length >= 1024) { mechanismOmitted++; continue }
      mechanism.push({ ...item, delivered_ms: elapsed() })
    }
  })
  await page.exposeBinding('__tutorDiagnosticDOM', (_source, value: SafeDOM & { projection?: unknown; omitted_dom?: unknown }) => {
    if (!active) return
    if (!value || typeof value !== 'object') return
    if (value.run_status !== null && !states.has(value.run_status)) return
    lastDOM = { elapsed_ms: elapsed(), state: { run_status: value.run_status,
      tutor_present: value.tutor_present === true, observing: value.observing === true,
      answer_present: value.answer_present === true, grant_ack_present: value.grant_ack_present === true,
      consent_linked: value.consent_linked === true } }
    add({ kind: 'dom', state: lastDOM.state, omitted_dom: integer(value.omitted_dom) })
    const projection = value.projection as Record<string, unknown> | null
    if (projection && typeof projection.token === 'string' && /^[A-Za-z0-9_-]{1,96}:\d{1,16}$/.test(projection.token)
      && typeof projection.run === 'string' && /^run_[A-Za-z0-9_-]{1,75}$/.test(projection.run)
      && integer(projection.seq) !== null && integer(projection.revision) !== null && integer(projection.ordinal) !== null
      && typeof projection.source_ms === 'number' && Number.isFinite(projection.source_ms) && projection.source_ms >= 0
      && typeof projection.status === 'string' && states.has(projection.status) && projections.length < 1024) {
      projections.push({ token: projection.token, run: projection.run, seq: projection.seq as number, revision: projection.revision as number,
        ordinal: projection.ordinal as number, source_ms: projection.source_ms, status: projection.status, delivered_ms: elapsed() })
    }
  })
  const install = () => {
    const host = window as unknown as { __tutorDiagnosticDOM?: (value: object) => Promise<void>; __tutorDiagnosticInstalled?: boolean; __tutorObservationEnabled?: boolean }
    if (host.__tutorDiagnosticInstalled) return
    host.__tutorDiagnosticInstalled = true
    host.__tutorObservationEnabled = true
    let ordinal = 0
    let previous = '', pending = false, latest: object | undefined, omitted = 0
    const flush = () => {
      if (pending || !latest) return
      pending = true
      const value = latest; latest = undefined
      void (async () => {
        try { await host.__tutorDiagnosticDOM?.(value) } catch { /* No observer failure escapes. */ }
        finally { pending = false; flush() }
      })()
    }
    const inspect = () => {
      const region = document.querySelector('[aria-label="真实问答线程与任务"]')
      const task = region?.querySelector('[aria-label="当前问答任务"]')
      const token = task?.getAttribute('data-tutor-observation') ?? null
      const tuple = [...(task?.querySelectorAll('p') ?? [])].map(node => node.textContent ?? '').map(text => text.match(/^(run_[A-Za-z0-9_-]{1,75}) · Jobs r(\d+) · 事件水位 (\d+)$/)).find(Boolean)
      const status = region?.querySelector('[aria-label="当前问答任务"] h3')?.textContent?.match(/^真实任务状态：(queued|running|awaiting_approval|completed|failed|cancelled)$/)?.[1] ?? null
      const statuses = [...(region?.querySelectorAll('[role="status"]') ?? [])].map(node => node.textContent ?? '')
      const state = { run_status: status, tutor_present: !!region,
        observing: statuses.some(text => text.startsWith('正在观察任务')),
        answer_present: !!region?.querySelector('[aria-label="本次模型回答原文"]')?.textContent,
        grant_ack_present: [...(region?.querySelectorAll('[aria-label="当前原命令"]') ?? [])].some(node => node.querySelector('h4')?.textContent === '批准授权' && [...node.querySelectorAll('[role="status"]')].some(item => item.textContent?.startsWith('原命令已确认'))),
        consent_linked: [...(region?.querySelectorAll('p') ?? [])].some(node => node.textContent?.startsWith('此 Run 已关联授权 ')) }
      const projection = token && tuple && status ? { token, run: tuple[1], revision: Number(tuple[2]), seq: Number(tuple[3]), status } : null
      const serialized = JSON.stringify({ state, projection })
      if (serialized !== previous) {
        previous = serialized
        const value = { ...state, projection: projection ? { ...projection, ordinal: ++ordinal, source_ms: performance.now() } : null }
        if (latest) omitted++
        latest = { ...value, omitted_dom: omitted }; queueMicrotask(flush)
      }
    }
    new MutationObserver(inspect).observe(document, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ['aria-label', 'role', 'data-tutor-observation'] })
    inspect()
  }
  await page.addInitScript(install)
  await page.evaluate(install)
  const readRun = ports.readRun ?? (async (id: string) => {
    const response = await page.request.get(`/api/v1/runs/${id}`, { timeout: 400 })
    if (!response.ok()) throw new Error('RUN_READ_NOT_OK')
    return response.json()
  })
  const read = async (operation: () => Promise<unknown>): Promise<ReadResult> => {
    try { return { state: 'complete', value: await operation() } }
    catch { return { state: 'failed' } }
  }
  return {
    bindRun(id: string) { if (!/^run_[A-Za-z0-9_-]+$/.test(id)) throw new Error('INVALID_RUN_ID'); runId = id },
    mark(label: 'grant_click' | 'completion_assertion_start') { add({ kind: 'mark', label }) },
    async around(info: TestInfo, assertion: () => Promise<unknown>) {
      let original: unknown, failed = false
      add({ kind: 'mark', label: 'completion_assertion_start' })
      try { await assertion() } catch (error) { original = error; failed = true }
      // Freeze already received metadata synchronously, before starting any
      // post-assertion request. Late callbacks cannot alter this snapshot.
      const frozenAt = elapsed(), frozen = { events: [...events], last_dom_delivered: lastDOM, omitted_events: omitted }
      active = false
      try {
      const postStarted = elapsed()
      let observedRun: ReadResult = { state: 'timeout' }, observedRuntime: ReadResult = { state: 'timeout' }, observedAPI: ReadResult = { state: 'timeout' }, observedBrowser: ReadResult = { state: 'timeout' }
      await within(Promise.all([
        read(async () => { if (!runId) throw new Error('RUN_NOT_BOUND'); return safeRun(await readRun(runId), runId) }).then(value => { observedRun = value }),
        read(async () => {
          const runtime = await ports.readRuntime()
          try { observedAPI = { state: 'complete', value: safeAPIMechanism((runtime as { mechanism?: unknown })?.mechanism, runId ?? '') } } catch { observedAPI = { state: 'failed' } }
          return safeRuntime(runtime)
        }).then(value => { observedRuntime = value }),
        read(async () => {
          const snapshot = await page.evaluate(() => {
            const host = globalThis as { __tutorObservationSnapshot?: () => unknown }
            return { fence_source_ms: performance.now(), snapshot: host.__tutorObservationSnapshot?.() }
          })
          const value = snapshot.snapshot as { epoch?: unknown; records?: unknown; omitted?: unknown; invalid?: unknown; delivery_failures?: unknown; delivery_pending?: unknown }
          if (!value || typeof value.epoch !== 'string' || !/^[A-Za-z0-9_-]{1,96}$/.test(value.epoch) || !Array.isArray(value.records) || value.records.length > 1024
            || value.records.some(item => !safeTutorObservation(item) || item.epoch !== value.epoch)
            || [value.omitted, value.invalid, value.delivery_failures, value.delivery_pending].some(item => integer(item) === null)) throw new Error('INVALID_BROWSER_MECHANISM')
          return { fence_source_ms: snapshot.fence_source_ms, epoch: value.epoch, records: value.records.filter(item => item.run === runId).map(item => ({ ...item })),
            omitted: value.omitted, invalid: value.invalid, delivery_failures: value.delivery_failures, delivery_pending: value.delivery_pending,
            timing: 'Later browser snapshot. Source timestamps are not Node receipt/deadline timestamps.' }
        }).then(value => { observedBrowser = value }),
      ]).then(() => true), 500, false)
      const post = { run: observedRun, runtime: observedRuntime }
      // Individual settled observations survive a slow peer; no timeout is
      // converted to a null/zero/success result.
      const record = { version: 1, started_at: startedAt, clock: 'Node performance.now, milliseconds since observer start',
        assertion: { verdict: failed ? 'failed' : 'passed', frozen_at_ms: frozenAt, original_expect_timeout_ms: 5000 },
        frozen_observation: frozen,
        mechanism: { version: 1, node_epoch: nodeEpoch, frozen_browser_records: mechanism.filter(value => value.run === runId),
          invalid_deliveries: mechanismInvalid, omitted_deliveries: mechanismOmitted,
          frozen_dom_projections: projections.filter(value => value.run === runId).map(value => {
            const matches = mechanism.filter(item => `${item.epoch}:${item.ordinal}` === value.token)
            const source = matches.length === 1 ? matches[0] : undefined
            return { ...value, matched_source: !!source && ['snapshot_accepted', 'event_applied'].includes(source.stage) && source.run === value.run && source.seq === value.seq && source.revision === value.revision && source.status === value.status }
          }), post_assertion_api: observedAPI, post_assertion_browser: observedBrowser,
          boundary: 'Source epochs have independent clocks. Only Node-delivered frozen records precede this assertion boundary. Missing or dropped records are unknown, never evidence of absence.' },
        post_assertion: { phase: failed ? 'post-failure' : 'post-success', started_ms: postStarted, finished_ms: elapsed(), wait_limit_ms: 500, ...post },
        scope: 'Only already delivered metadata is frozen at the assertion boundary. Last DOM receipt is not a synchronous browser-deadline snapshot. Later reads cannot establish earlier backend state. Only explicit non-authoritative observation labels accompany existing GETs. No credential headers, cookies, keys, request/answer bodies or SSE frame payloads captured.' }
      const target = info.outputPath('tutor-completion-diagnostic.json'), pending = target + '.pending', abort = new AbortController()
      const saved = await within((async () => {
        await writeFile(pending, JSON.stringify(record, null, 2) + '\n', { signal: abort.signal })
        if (abort.signal.aborted) return false
        await rename(pending, target)
        await info.attach('tutor-completion-diagnostic', { path: target, contentType: 'application/json' })
        return true
      })().catch(() => false), 250, false)
      if (!saved) { abort.abort(); console.error('Tutor completion diagnostic incomplete; original assertion verdict is unchanged.') }
      } catch { console.error('Tutor completion diagnostic incomplete; original assertion verdict is unchanged.') }
      finally { if (failed) throw original }
    },
    dispose() { active = false; page.off('request', requestStarted); page.off('response', responseReceived); page.off('requestfinished', requestFinished); page.off('requestfailed', requestFailed) },
  }
}
