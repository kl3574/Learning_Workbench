import type { Page, TestInfo } from '<DIAGNOSIS_CACHE>/fixed-source-01/apps/web/node_modules/@playwright/test/index.mjs'
import { writeFileSync } from 'node:fs'
const captures = new WeakMap<Page, { events: unknown[]; pending: Promise<void>[]; started: number }>()
export function startObserver(page: Page, info: TestInfo) {
  const state = { events: [] as unknown[], pending: [] as Promise<void>[], started: Date.now() }; captures.set(page, state)
  page.on('pageerror', error => state.events.push({ kind: 'pageerror', elapsed_ms: Date.now()-state.started, message: error.message }))
  page.on('response', response => {
    const url = new URL(response.url()); if (!url.pathname.startsWith('/api/v1/routes')) return
    const request = response.request(), headers = request.headers()
    state.pending.push((async () => {
      let body: unknown
      try { body = await response.json() } catch { body = await response.text().catch(() => '<response body unavailable>') }
      state.events.push({ kind: 'routes_response', elapsed_ms: Date.now()-state.started, path: url.pathname+url.search, method: request.method(), status: response.status(), command_id: headers['idempotency-key'] ?? null, if_match: headers['if-match'] ?? null, request_body: request.postData(), response_body: body })
      writeFileSync(info.outputPath('observer-network.json'), JSON.stringify(state.events, null, 2))
    })())
  })
}
export async function finishObserver(page: Page, info: TestInfo) {
  const state = captures.get(page); if (!state) return
  await Promise.allSettled(state.pending)
  const visible = await page.evaluate(() => ({ title: document.title, dialogs: Array.from(document.querySelectorAll('dialog[open]')).map(value => ({ label: value.getAttribute('aria-label'), text: value.textContent })), alerts: Array.from(document.querySelectorAll('[role=alert]')).map(value => value.textContent), statuses: Array.from(document.querySelectorAll('[role=status]')).map(value => value.textContent), buttons: Array.from(document.querySelectorAll('dialog[open] button')).map(value => ({ text: value.textContent, disabled: (value as HTMLButtonElement).disabled })) })).catch(error => ({ unavailable: String(error) }))
  writeFileSync(info.outputPath('observer-final.json'), JSON.stringify({ scope: 'Read-only observer on original route case; no responses replaced; route bodies contain original synthetic fixture state, no auth/cookie/CSRF/bootstrap headers captured.', outcome: info.status, expected: info.expectedStatus, events: state.events, visible }, null, 2))
  await page.screenshot({ path: info.outputPath('observer-final.png') })
}
