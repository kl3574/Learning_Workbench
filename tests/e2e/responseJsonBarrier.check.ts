import { expect, test, type Page } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { createServer } from 'node:http'
import { readFileSync } from 'node:fs'
import { stripTypeScriptTypes } from 'node:module'
import { resolve } from 'node:path'

// Controlled loopback mechanism checks, explicitly selected by their private
// config. They are not extra Review business flows in the normal *.spec suite.
const root = resolve(import.meta.dirname, '../..'), target = '/api/v1/attempts/attempt_barrier/result'
type Observation = { wait(): Promise<{ outcome: string }>; dispose(): Promise<void> }
async function observation(page: Page): Promise<Observation> {
  if (process.env.REVIEW_BARRIER === 'handler') return { wait: async () => { await page.unrouteAll({ behavior: 'wait' }); return { outcome: 'fulfilled' } }, dispose: async () => {} }
  const { observeNextResponseJson } = await import('./responseJsonBarrier')
  return observeNextResponseJson(page, target)
}
async function fixture(page: Page, invalid = false) {
  let requests = 0
  const server = createServer((req, res) => {
    if (req.url === target) { requests++; res.setHeader('Content-Type', 'application/json'); res.end(invalid ? '{' : '{"synthetic":true}'); return }
    if (req.url === '/apps/web/src/api/client.ts' || req.url === '/packages/contracts/generated/api-client') {
      const path = req.url === '/apps/web/src/api/client.ts' ? 'apps/web/src/api/client.ts' : 'packages/contracts/generated/api-client.ts'
      res.setHeader('Content-Type', 'text/javascript'); res.end(stripTypeScriptTypes(readFileSync(resolve(root, path), 'utf8'))); return
    }
    res.setHeader('Content-Type', 'text/html'); res.end('<!doctype html><p id="guard">not processed</p>')
  })
  await new Promise<void>(ok => server.listen(0, '127.0.0.1', ok))
  const address = server.address(); if (!address || typeof address === 'string') throw new Error('Missing owned loopback port')
  await page.goto(`http://127.0.0.1:${address.port}`)
  await page.evaluate(async target => {
    const request = (await import('/apps/web/src/api/' + 'client.ts')).request
    const nativeJson = Response.prototype.json, nativeFetch = window.fetch
    let release!: () => void
    const gate = new Promise<void>(resolve => { release = resolve })
    const state = { started: false, processed: false, returnedSameValue: false, caughtSameError: false, jsonPromise: null as Promise<unknown> | null, rawValue: undefined as unknown, rawError: undefined as unknown }
    Response.prototype.json = function () {
      const parsed = nativeJson.call(this)
      if (new URL(this.url).pathname !== target) return parsed
      state.started = true
      void parsed.then(value => { state.rawValue = value }, error => { state.rawError = error })
      const gated = gate.then(() => parsed); state.jsonPromise = gated
      return gated
    }
    Object.assign(window, { barrierFixture: {
      state, release, nativeFetch,
      start: () => { void (async () => {
        try { const value = await request('GET /api/v1/attempts/{id}/result', undefined, undefined, { path: { id: 'attempt_barrier' } }); state.returnedSameValue = value === state.rawValue }
        catch (error) { state.caughtSameError = error === state.rawError }
        // Same synchronous terminal continuation shape as the hook's current()
        // branch, after the actual client transport/generated-client chain.
        state.processed = true; document.querySelector('#guard')!.textContent = 'processed'
      })() },
      restore: () => { Response.prototype.json = nativeJson },
    } })
  }, target)
  return { requests: () => requests, close: () => new Promise<void>((ok, reject) => server.close(error => error ? reject(error) : ok())) }
}
for (const invalid of [false, true]) test(`JSON ${invalid ? 'rejection' : 'value'} reaches the actual client continuation before the observation completes`, async ({ page }, info) => {
  const owned = await fixture(page, invalid), barrier = await observation(page)
  let captured!: () => void; const capturedResponse = new Promise<void>(ok => { captured = ok })
  await page.route(`**${target}`, async route => { const response = await route.fetch(); await route.fulfill({ response }); captured() })
  try {
    await page.evaluate(() => (window as any).barrierFixture.start()); await capturedResponse; await page.unrouteAll({ behavior: 'wait' })
    await expect.poll(() => page.evaluate(() => (window as any).barrierFixture.state.started)).toBe(true)
    let completed = false; const completion = barrier.wait().then(value => { completed = true; return value })
    // A posted browser task is causal, not a sleep or a guessed microtask count.
    await page.evaluate(() => new Promise<void>(resolve => { const channel = new MessageChannel(); channel.port1.onmessage = () => { channel.port1.close(); channel.port2.close(); resolve() }; channel.port2.postMessage(null) }))
    const early = await page.evaluate(() => ({ jsonStarted: (window as any).barrierFixture.state.started, clientProcessed: (window as any).barrierFixture.state.processed }))
    await info.attach('handler-versus-client.json', { body: JSON.stringify({ handlerCompleted: true, ...early, barrierCompleted: completed }), contentType: 'application/json' })
    expect(early).toEqual({ jsonStarted: true, clientProcessed: false })
    expect(completed, 'route completion must not be mistaken for client JSON consumption').toBe(false)
    await page.evaluate(() => (window as any).barrierFixture.release())
    expect((await completion).outcome).toBe(invalid ? 'rejected' : 'fulfilled')
    expect(await page.evaluate(() => { const s = (window as any).barrierFixture.state; return { processed: s.processed, same: s.returnedSameValue || s.caughtSameError } })).toEqual({ processed: true, same: true })
    await expect(page.locator('#guard')).toHaveText('processed'); expect(owned.requests()).toBe(1)
  } finally {
    await page.evaluate(() => { (window as any).barrierFixture.release(); (window as any).barrierFixture.restore() })
    await barrier.dispose(); await page.unrouteAll({ behavior: 'wait' }); await owned.close()
  }
})

test('the exact observer returns the original fetch/json promises and leaves an unrelated request alone', async ({ page }) => {
  const owned = await fixture(page)
  await page.evaluate(() => {
    const fixture = (window as any).barrierFixture, fetch = window.fetch
    fixture.recordingFetch = function (this: Window, ...args: Parameters<typeof fetch>) { const promise = Reflect.apply(fetch, this, args); fixture.fetchPromise = promise; return promise }
    window.fetch = fixture.recordingFetch
  })
  const barrier = await observation(page)
  try {
    const facts = await page.evaluate(async target => {
      const fixture = (window as any).barrierFixture
      const other = fetch('/unrelated'), unrelatedPromiseSame = other === fixture.fetchPromise
      await (await other).text()
      const unrelatedDidNotReadJson = !fixture.state.started
      const request = fetch(target), fetchPromiseSame = request === fixture.fetchPromise
      const response = await request, parsed = response.json(), jsonPromiseSame = parsed === fixture.state.jsonPromise
      fixture.release(); await parsed
      return { unrelatedPromiseSame, unrelatedDidNotReadJson, fetchPromiseSame, jsonPromiseSame, fetchRestoredAfterOne: window.fetch === fixture.recordingFetch }
    }, target)
    expect(facts).toEqual({ unrelatedPromiseSame: true, unrelatedDidNotReadJson: true, fetchPromiseSame: true, jsonPromiseSame: true, fetchRestoredAfterOne: true })
    expect((await barrier.wait()).outcome).toBe('fulfilled'); expect(owned.requests()).toBe(1)
  } finally {
    await barrier.dispose()
    await page.evaluate(() => { const fixture = (window as any).barrierFixture; fixture.release(); fixture.restore(); window.fetch = fixture.nativeFetch })
    await owned.close()
  }
})
