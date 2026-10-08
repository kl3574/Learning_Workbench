import { createServer } from 'node:http'
import { writeFileSync } from 'node:fs'
import assert from 'node:assert/strict'
import { chromium } from '$HOME/.cache/learning-workbench-acceptance/m63-review-route-original412-observation-oct05/apps/web/node_modules/playwright-core/index.mjs'

const events = []
const server = createServer((req, res) => {
  res.writeHead(200, { 'content-type': req.url === '/delayed' ? 'text/plain' : 'text/html' })
  res.end(req.url === '/delayed' ? 'bounded synthetic route body' : '<!doctype html><title>Controlled route order</title><p>Static local fixture</p>')
})
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
const origin = `http://127.0.0.1:${server.address().port}`
const browser = await chromium.launch({ headless: true, executablePath: '/usr/bin/google-chrome' })
const results = []
try {
  for (const cleanupBeforeFulfill of [true, false]) {
    const page = await browser.newPage()
    const mode = cleanupBeforeFulfill ? 'remove_before_fulfill' : 'fulfill_before_remove'
    let release, captured, completed
    const gate = new Promise(resolve => { release = resolve })
    const ready = new Promise(resolve => { captured = resolve })
    const done = new Promise(resolve => { completed = resolve })
    const result = { mode, fetch_status: null, fulfill_error: null, callback_completed: false }
    const pattern = '**/delayed'
    await page.route(pattern, async route => {
      try {
        const response = await route.fetch()
        result.fetch_status = response.status()
        events.push({ mode, event: 'route_fetch_completed' })
        captured()
        await gate
        events.push({ mode, event: 'fulfill_started' })
        await route.fulfill({ response })
        events.push({ mode, event: 'fulfill_completed' })
      } catch (error) {
        result.fulfill_error = error.message
        events.push({ mode, event: 'fulfill_rejected', error: error.message })
      } finally {
        result.callback_completed = true
        completed()
      }
    })
    await page.goto(origin)
    await page.evaluate(() => { window.controlledRouteRequest = fetch('/delayed').then(response => response.text()) })
    await ready
    if (cleanupBeforeFulfill) {
      events.push({ mode, event: 'unroute_started' })
      await page.unroute(pattern)
      events.push({ mode, event: 'unroute_completed' })
      release()
      await done
    } else {
      release()
      await done
      events.push({ mode, event: 'unroute_started' })
      await page.unroute(pattern)
      events.push({ mode, event: 'unroute_completed' })
    }
    assert.equal(result.fetch_status, 200)
    assert.equal(result.callback_completed, true)
    if (cleanupBeforeFulfill) assert.match(result.fulfill_error ?? '', /Route is already handled!/)
    else assert.equal(result.fulfill_error, null)
    results.push(result)
    await page.close()
  }
  writeFileSync(new URL('route-order-result.json', import.meta.url), JSON.stringify({
    scope: 'Two static loopback HTTP and native Chrome route-order cases; dependency mechanism only',
    original_full_suite_cause: 'UNKNOWN - original execution had no retained callback/unroute ordering',
    product_assertions_replaced: false, source_modified: false, model_requests: 0,
    cases: results, events,
  }, null, 2) + '\n')
  console.log('PASS: controlled remove-before-fulfill reproduces the exact route error; fulfill-before-remove completes. Original full-suite cause remains UNKNOWN.')
} finally {
  await browser.close()
  await new Promise(resolve => server.close(resolve))
}
