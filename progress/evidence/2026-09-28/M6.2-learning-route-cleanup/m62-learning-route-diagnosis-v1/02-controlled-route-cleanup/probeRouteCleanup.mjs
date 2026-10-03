import { chromium } from '<LOCAL_HOME>/.cache/learning-workbench-acceptance/m62-learning-route-diagnosis-active/apps/web/node_modules/playwright-core/index.mjs'
import { createServer } from 'node:http'
import assert from 'node:assert/strict'
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
    events.push('cleanup-release'); release(); events.push('cleanup-unroute-start')
    await page.unroute('**/api/v1/learning/concept-states*'); events.push('cleanup-unroute-complete')
    await done
    results.push({ iteration: i + 1, events, handlerError: handlerError ?? null })
    await page.close()
  }
} finally { await browser.close(); await new Promise(resolve => server.close(resolve)) }
console.log(JSON.stringify({ scope: 'actual Chromium and locked local Playwright, exact original held route cleanup pattern, no app/session/timeout or abort fixture', results }, null, 2))
assert.equal(results.filter(row => row.handlerError !== null).length, 0, 'Held route cleanup must complete without Route is already handled')
