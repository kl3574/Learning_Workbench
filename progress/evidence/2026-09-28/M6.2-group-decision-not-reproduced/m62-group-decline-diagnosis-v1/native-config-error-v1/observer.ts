// Private [DEBUG-group-decline] probe: no payload, header, cookie or secret reads.
import { writeFileSync } from 'node:fs'
import { performance } from 'node:perf_hooks'

const started = performance.now()
const rows: object[] = []
let omitted = 0, serial = 0
const requests = new WeakMap<object, number>()
const add = (value: object) => { if (rows.length < 2048) rows.push({ delivered_ms: performance.now() - started, ...value }); else omitted++ }
const safePath = (url: string) => {
  const path = new URL(url).pathname
  return /^\/api\/v1\/authoring(?:\/[A-Za-z0-9_/-]{1,240})?$/.test(path) || path === '/api/v1/session' ? path : null
}
export async function installGroupDeclineObservation(context: any) {
  await context.exposeBinding('__groupDeclineProbe', (_: unknown, value: unknown) => {
    if (!value || typeof value !== 'object') return
    const item = value as Record<string, unknown>
    if (Object.keys(item).some(k => !['stage','source_ms','trusted','numeric_present','decline_present','decline_disabled','button_in_view','alert_present','command_conflict','ack_present','selected_state'].includes(k))) return
    if (!['state','pointerdown','pointerup','click'].includes(String(item.stage))) return
    if (typeof item.source_ms !== 'number' || !Number.isFinite(item.source_ms)) return
    for (const [key, val] of Object.entries(item)) if (!['stage','source_ms','selected_state'].includes(key) && typeof val !== 'boolean') return
    if (item.selected_state !== undefined && !['pending','approve_once','decline','absent'].includes(String(item.selected_state))) return
    add({ kind: 'browser', ...item })
  })
  context.on('request', (request: any) => {
    const path = safePath(request.url()); if (!path) return
    const id = ++serial; requests.set(request, id)
    add({ kind: 'request', id, method: request.method(), path })
  })
  context.on('response', (response: any) => { const id = requests.get(response.request()); if (id !== undefined) add({ kind: 'response', id, status: response.status() }) })
  context.on('requestfinished', (request: any) => { const id = requests.get(request); if (id !== undefined) add({ kind: 'finished', id }) })
  context.on('requestfailed', (request: any) => {
    const id = requests.get(request), raw = request.failure()?.errorText ?? ''
    if (id !== undefined) add({ kind: 'failed', id, code: /^net::ERR_[A-Z_]+$/.test(raw) ? raw : 'REQUEST_FAILED' })
  })
  for (const page of context.pages()) page.on('pageerror', (error: Error) => add({ kind: 'pageerror', name: ['Error','TypeError','RangeError','SyntaxError'].includes(error.name) ? error.name : 'OTHER' }))
  await context.addInitScript(() => {
    const send = (value: object) => { try { void (globalThis as any).__groupDeclineProbe(value).catch(() => undefined) } catch { /* observation only */ } }
    const facts = () => {
      const panel = document.querySelector('[aria-label="独立数值执行批准"]')
      const button = [...(panel?.querySelectorAll('button') ?? [])].find(b => b.textContent === '明确拒绝本次数值执行')
      const rect = button?.getBoundingClientRect()
      const text = panel?.textContent ?? ''
      return { numeric_present: !!panel, decline_present: !!button, decline_disabled: button ? button.disabled : false,
        button_in_view: !!rect && rect.top >= 0 && rect.bottom <= innerHeight && rect.left >= 0 && rect.right <= innerWidth,
        alert_present: !!document.querySelector('[role="alert"]'), command_conflict: document.body?.textContent?.includes('已有未知结果的原命令，请先回放') === true,
        ack_present: document.body?.textContent?.includes('原命令已确认。请另行读取当前详情') === true,
        selected_state: text.match(/当前决定：(pending|approve_once|decline)/)?.[1] ?? 'absent' }
    }
    let previous = '', delivered = 0
    const inspect = () => {
      const value = facts(), next = JSON.stringify(value)
      if (next !== previous && delivered < 256) { previous = next; delivered++; send({ stage: 'state', source_ms: performance.now(), ...value }) }
    }
    for (const kind of ['pointerdown','pointerup','click']) document.addEventListener(kind, event => {
      const target = event.target instanceof Element ? event.target.closest('button') : null
      if (target?.textContent === '明确拒绝本次数值执行') send({ stage: kind, source_ms: performance.now(), trusted: event.isTrusted, ...facts() })
    }, true)
    new MutationObserver(inspect).observe(document, { subtree: true, childList: true, characterData: true, attributes: true, attributeFilter: ['disabled'] })
    document.addEventListener('scroll', inspect, true)
    inspect()
  })
}
export function flushGroupDeclineObservation() {
  writeFileSync(process.env.LEARNING_GROUP_DECLINE_OBSERVATION!, JSON.stringify({ version: 1, scope: 'Private bounded metadata observation; independent browser source and Node delivery clocks; no payload/header/private text captured. Not original-run evidence.', rows, omitted }, null, 2)+'\n')
}
