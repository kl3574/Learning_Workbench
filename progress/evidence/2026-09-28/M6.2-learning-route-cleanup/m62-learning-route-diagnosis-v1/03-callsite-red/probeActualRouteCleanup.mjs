import { chromium } from '<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-learning-route-diagnosis-active/apps/web/node_modules/playwright-core/index.mjs'
import { createServer } from 'node:http'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'
const source = readFileSync('<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-learning-route-diagnosis-active/tests/e2e/learning-state.spec.ts', 'utf8')
const marker = '} finally { release(); await page.unroute'
assert.equal(source.split(marker).length, 2, 'exactly one actual cleanup callsite')
const start = source.indexOf(marker) + '} finally { '.length
const end = source.indexOf(' }\n})', start)
assert.ok(end > start)
const cleanupBody = source.slice(start, end)
const cleanup = new (Object.getPrototypeOf(async function () {}).constructor)('release', 'page', 'other', cleanupBody)
const sourceSha256 = createHash('sha256').update(source).digest('hex')
const server = createServer((req, res) => { res.writeHead(200, { 'content-type': req.url.includes('concept-states') ? 'application/json' : 'text/html' }); res.end(req.url.includes('concept-states') ? '{"items":[]}' : '<!doctype html><title>Synthetic route lifecycle probe</title>') })
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
const origin = `http://127.0.0.1:${server.address().port}`
const browser = await chromium.launch({ headless: true, executablePath: '/usr/bin/google-chrome' })
const results = []
try {
  for (let i = 0; i < 3; i++) {
    const page = await browser.newPage()
    await page.goto(origin)
    const events = []
    let release, captured, ended, handlerError
    const gate = new Promise(resolve => { release = resolve })
    const ready = new Promise(resolve => { captured = resolve })
    const done = new Promise(resolve => { ended = resolve })
    await page.route('**/api/v1/learning/concept-states*', async route => {
      try {
        const response = await route.fetch(); events.push('fetch-complete'); captured(); await gate
        events.push('fulfill-start'); await route.fulfill({ response }); events.push('fulfill-complete')
      } catch (error) { handlerError = error.message; events.push('fulfill-error:' + error.message) }
      finally { ended() }
    })
    await page.evaluate(() => { void fetch('/api/v1/learning/concept-states').catch(() => {}) })
    await ready
    const other = await browser.newPage()
    const observedPage = new Proxy(page, { get(target, key) {
      const value = target[key]
      if (key === 'unroute' || key === 'unrouteAll') return async (...args) => { events.push('cleanup-' + key + '-start'); const result = await value.apply(target, args); events.push('cleanup-' + key + '-complete'); return result }
      return typeof value === 'function' ? value.bind(target) : value
    } })
    await cleanup(() => { events.push('cleanup-release'); release() }, observedPage, other)
    await done
    results.push({ iteration: i + 1, events, handlerError: handlerError ?? null })
    await page.close()
  }
} finally { await browser.close(); await new Promise(resolve => server.close(resolve)) }
console.log(JSON.stringify({ scope: 'actual Chromium and pinned Playwright; execute extracted actual test finally cleanup, no app/session/timeout or abort fixture', sourceSha256, cleanupBody, results }, null, 2))
assert.equal(results.filter(row => row.handlerError !== null).length, 0, 'Held route cleanup must complete without Route is already handled')
