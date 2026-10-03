import { randomUUID } from 'node:crypto'
import { performance } from 'node:perf_hooks'
import { rename, writeFile } from 'node:fs/promises'
import type { Page, Request, Response, TestInfo } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { safeAuthoringObservation, type AuthoringObservationRecord } from '../../apps/web/src/features/authoring/authoringObservation'

async function within<T>(operation: Promise<T>, milliseconds: number, fallback: T): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined
  try { return await Promise.race([operation, new Promise<T>(resolve => { timer = setTimeout(() => resolve(fallback), milliseconds) })]) }
  finally { clearTimeout(timer) }
}

/** Explicitly installed only by synthetic E2E. No HTTP request, body read or header
 * is added. The WeakMap joins only the same actual Playwright Request object. */
export async function observeAuthoringPrepare(page: Page) {
  const epoch = randomUUID(), started = performance.now(), startedAt = new Date().toISOString()
  const requests = new WeakMap<Request, number>(), events: object[] = []
  const records: Array<AuthoringObservationRecord & { delivered_ms: number }> = []
  let serial = 0, active = true, used = false, omitted = 0, invalid = 0, deliveryOmitted = 0, observerErrors = 0
  const elapsed = () => performance.now() - started
  const add = (value: object) => { if (active) { if (events.length < 2000) events.push({ elapsed_ms: elapsed(), ...value }); else omitted++ } }
  const safely = (action: () => void) => { try { action() } catch { if (active) observerErrors++ } }
  const requested = (request: Request) => safely(() => {
    if (!active || request.frame() !== page.mainFrame()) return
    const pathname = new URL(request.url()).pathname, method = request.method()
    const path = pathname === '/api/v1/authoring/jobs' ? '/api/v1/authoring/jobs'
      : pathname === '/api/v1/authoring/group-jobs' ? '/api/v1/authoring/group-jobs'
        : pathname === '/api/v1/session' ? '/api/v1/session'
          : /^\/api\/v1\/authoring\/jobs\/[^/]+$/.test(pathname) ? '/api/v1/authoring/jobs/:id' : null
    if (!path || !['GET', 'POST'].includes(method)) return
    const id = ++serial; requests.set(request, id); add({ kind: 'request', id, method, path })
  })
  const responded = (response: Response) => safely(() => { const id = requests.get(response.request()); if (id !== undefined) add({ kind: 'response', id, status: response.status() }) })
  const finished = (request: Request) => safely(() => { const id = requests.get(request); if (id !== undefined) add({ kind: 'finished', id }) })
  const failed = (request: Request) => safely(() => {
    const id = requests.get(request)
    if (id === undefined) return
    const raw = request.failure()?.errorText
    add({ kind: 'failed', id, failure: raw === 'net::ERR_ABORTED' || raw === 'net::ERR_FAILED' ? raw : 'REQUEST_FAILED' })
  })
  page.on('request', requested); page.on('response', responded)
  page.on('requestfinished', finished); page.on('requestfailed', failed)
  const dispose = () => { active = false; page.off('request', requested); page.off('response', responded); page.off('requestfinished', finished); page.off('requestfailed', failed) }
  try {
    await page.exposeBinding('__authoringDiagnosticMechanism', (source, batch: unknown) => safely(() => {
      if (!active) return
      if (source.frame !== page.mainFrame() || !Array.isArray(batch) || batch.length > 64) { invalid++; return }
      for (const item of batch) {
        if (!safeAuthoringObservation(item)) { invalid++; continue }
        if (records.length === 1024) { deliveryOmitted++; continue }
        records.push({ ...item, delivered_ms: elapsed() })
      }
    }))
    const install = () => { (globalThis as { __authoringObservationEnabled?: boolean }).__authoringObservationEnabled = true }
    await page.addInitScript(install); await page.evaluate(install)
  } catch { observerErrors++ }
  return {
    async around(info: TestInfo, assertion: () => Promise<unknown>) {
      // A diagnostic is one assertion boundary, never an assertion retry.
      if (used) { await assertion(); return }
      used = true
      const assertionStarted = elapsed()
      let original: unknown, assertionFailed = false
      try { await assertion() } catch (error) { original = error; assertionFailed = true }
      // No await occurs between original completion and freezing delivered facts.
      const frozenAt = elapsed(), frozenEvents = [...events], frozenRecords = [...records]
      dispose()
      try {
        const record = { version: 1, started_at: startedAt, node_epoch: epoch,
          assertion: { verdict: assertionFailed ? 'failed' : 'passed', started_ms: assertionStarted, frozen_at_ms: frozenAt, original_click_timeout_ms: 10000 },
          frozen_observation: { events: frozenEvents, omitted_events: omitted, event_capacity: 2000, observer_errors: observerErrors },
          mechanism: { frozen_browser_records: frozenRecords, invalid_deliveries: invalid, omitted_deliveries: deliveryOmitted,
            node_record_capacity: 1024, browser_ring_capacity_per_epoch: 512, source_delivery_completeness: 'unknown' },
          scope: 'Synthetic metadata only. No request/response bodies, header values, cookies, credentials, object IDs or query strings. Request finished means body transfer ended, not parsed or accepted. Hook records retain their own browser epoch and clock; delivered_ms and network events use only the Node clock. No guessed matching between HTTP requests and hook sequences. Missing or delayed deliveries remain unknown. No post-assertion reads or HTTP requests.' }
        const target = info.outputPath('authoring-prepare-diagnostic.json'), pending = target + '.pending', abort = new AbortController()
        const saved = await within((async () => {
          await writeFile(pending, JSON.stringify(record, null, 2) + '\n', { signal: abort.signal })
          if (abort.signal.aborted) return false
          await rename(pending, target)
          await info.attach('authoring-prepare-diagnostic', { path: target, contentType: 'application/json' })
          return true
        })().catch(() => false), 250, false)
        if (!saved) { abort.abort(); console.error('Authoring prepare diagnostic incomplete; original assertion verdict is unchanged.') }
      } catch { console.error('Authoring prepare diagnostic incomplete; original assertion verdict is unchanged.') }
      finally { if (assertionFailed) throw original }
    },
    dispose,
  }
}
