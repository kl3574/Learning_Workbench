import { performance } from 'node:perf_hooks'
import { rename, writeFile } from 'node:fs/promises'
import type { Page, Request, Response, TestInfo } from '../../apps/web/node_modules/@playwright/test/index.mjs'

async function within<T>(operation: Promise<T>, milliseconds: number, fallback: T): Promise<T> {
  let timer: ReturnType<typeof setTimeout> | undefined
  try {
    return await Promise.race([operation, new Promise<T>(resolve => { timer = setTimeout(() => resolve(fallback), milliseconds) })])
  } finally { clearTimeout(timer) }
}

// Failure-only observation of the synthetic historical Reader case. Never
// intercept traffic or collect headers, cookies, bodies or bootstrap fragments.
export function observeReaderLoad(page: Page) {
  const startedAt = new Date().toISOString(), started = performance.now()
  const requests = new WeakMap<Request, number>()
  const events: object[] = []
  let sequence = 0, omitted = 0
  const add = (value: object) => {
    if (events.length < 2000) events.push({ elapsed_ms: performance.now() - started, ...value })
    else omitted++
  }
  const startedRequest = (request: Request) => {
    const url = new URL(request.url())
    if (request.method() !== 'GET' || !url.pathname.startsWith('/api/v1/')) return
    const id = ++sequence
    requests.set(request, id)
    add({ kind: 'request', id, path: url.pathname, revision: url.searchParams.get('revision') })
  }
  const received = (response: Response) => {
    const id = requests.get(response.request())
    if (id !== undefined) add({ kind: 'response', id, status: response.status() })
  }
  const finished = (request: Request) => {
    const id = requests.get(request)
    if (id !== undefined) add({ kind: 'finished', id })
  }
  const failed = (request: Request) => {
    const id = requests.get(request)
    if (id !== undefined) add({ kind: 'failed', id, failure: request.failure()?.errorText ?? null })
  }
  page.on('request', startedRequest)
  page.on('response', received)
  page.on('requestfinished', finished)
  page.on('requestfailed', failed)
  return {
    async capture(info: TestInfo) {
      const captureStartedMs = performance.now() - started
      const state = await within(page.evaluate(() => ({
        reader_count: document.querySelectorAll('.real-reader').length,
        headings: [...document.querySelectorAll('.empty-content h1')].map(node => node.textContent),
        active_tab: document.querySelector('[role="tab"][aria-selected="true"]')?.textContent ?? null,
        loading_text: [...document.querySelectorAll('.reader-scroll > p, .empty-content > p')].map(node => node.textContent?.slice(0, 500)),
        alerts: [...document.querySelectorAll('.save-alert, [role="alert"]')].map(node => node.textContent?.slice(0, 500)),
        exact_reader_link_present: new URLSearchParams(location.search).has('reader'),
      })).catch(() => ({ capture_error: 'PAGE_UNAVAILABLE' })), 250, { capture_error: 'PAGE_OBSERVATION_TIMEOUT' })
      const target = info.outputPath('reader-load-diagnostic.json'), pending = target + '.pending'
      const abort = new AbortController()
      const body = JSON.stringify({
        version: 1, started_at: startedAt, capture_started_ms: captureStartedMs,
        scope: 'Post-failure observation; original navigation and five-second assertion unchanged. GET timing uses one observer clock. No request bodies, headers, credentials or URL fragments collected.',
        observer_wait_limits_ms: { page: 250, file: 250 },
        state, events, omitted_events: omitted,
      }, null, 2) + '\n'
      const saved = await within((async () => {
        await writeFile(pending, body, { signal: abort.signal })
        if (abort.signal.aborted) return false
        await rename(pending, target)
        return true
      })().catch(() => false), 250, false)
      if (!saved) {
        abort.abort()
        console.error('Historical Reader diagnostic incomplete: file write failed or exceeded the observer wait limit; original test failure is unchanged.')
      }
    },
    dispose() {
      page.off('request', startedRequest)
      page.off('response', received)
      page.off('requestfinished', finished)
      page.off('requestfailed', failed)
    },
  }
}
