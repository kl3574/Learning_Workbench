import { createServer, type ServerResponse } from 'node:http'
import { readFile } from 'node:fs/promises'
import { expect, test } from '../../apps/web/node_modules/@playwright/test/index.mjs'
import { observeAuthoringPrepare } from './authoringDiagnostic'

test('Authoring diagnostic preserves the original ten-second click error and excludes late deliveries and private text', async ({ page }, info) => {
  page.setDefaultTimeout(10_000)
  await page.setContent('<pre>PRIVATE_BODY</pre><input value="PRIVATE_CREDENTIAL">')
  const observer = await observeAuthoringPrepare(page)
  let original: unknown, caught: unknown
  try {
    await page.evaluate(async () => {
      const sink = (globalThis as { __authoringDiagnosticMechanism?: (value: unknown) => Promise<void> }).__authoringDiagnosticMechanism!
      const value = { epoch: 'synthetic', hook: 1, ordinal: 1, source_ms: 7, stage: 'rendered', operation: 3, list_sequence: 2, working: true, busy: true, ready: true, academic: true, job_count: 0 }
      await sink([{ ...value, text: 'PRIVATE_BODY' }]); await sink([value])
    })
    try {
      await observer.around(info, async () => {
        try { await page.getByRole('button', { name: 'Absent prepared detail', exact: true }).click() }
        catch (error) { original = error; throw error }
      })
    } catch (error) { caught = error }
    expect(original).toBeInstanceOf(Error); expect(caught).toBe(original)
    expect(String(caught)).toContain('10000ms')
    const path = info.outputPath('authoring-prepare-diagnostic.json'), raw = await readFile(path, 'utf8'), value = JSON.parse(raw)
    expect(raw).not.toContain('PRIVATE_')
    expect(value.assertion.verdict).toBe('failed'); expect(value.assertion.original_click_timeout_ms).toBe(10000)
    expect(value.frozen_observation.events).toEqual([])
    expect(value.mechanism.invalid_deliveries).toBe(1)
    expect(value.mechanism.frozen_browser_records).toHaveLength(1)
    expect(value.mechanism.frozen_browser_records[0]).toMatchObject({ busy: true, job_count: 0, stage: 'rendered' })
    expect(value.mechanism.frozen_browser_records[0].delivered_ms).toBeLessThanOrEqual(value.assertion.frozen_at_ms)
    await page.evaluate(async () => { await (globalThis as { __authoringDiagnosticMechanism?: (value: unknown) => Promise<void> }).__authoringDiagnosticMechanism!([{ text: 'PRIVATE_LATE' }]) })
    expect(await readFile(path, 'utf8')).toBe(raw)
  } finally { observer.dispose() }
})

test('actual requests retain separate identities and distinguish response headers from body completion at the freeze', async ({ page }, info) => {
  const responses = new Map<string, ServerResponse>()
  const server = createServer((request, response) => {
    if (!request.url?.startsWith('/api/v1/authoring/jobs')) { response.end('<button>Freeze</button>'); return }
    responses.set(new URL(request.url, 'http://127.0.0.1').searchParams.get('which')!, response)
    response.writeHead(200, { 'Content-Type': 'application/json', 'X-Synthetic-Private': 'PRIVATE_RESPONSE_HEADER' })
    response.write('{"private":"PRIVATE_BODY')
  })
  await new Promise<void>(resolve => server.listen(0, '127.0.0.1', resolve))
  const address = server.address()
  if (!address || typeof address === 'string') throw new Error('Missing controlled server')
  let observer: Awaited<ReturnType<typeof observeAuthoringPrepare>> | undefined
  try {
    await page.goto(`http://127.0.0.1:${address.port}`); page.setDefaultTimeout(10_000)
    observer = await observeAuthoringPrepare(page)
    const returned = Promise.all(['first', 'second'].map(name => page.waitForResponse(response => response.url().includes(`which=${name}`))))
    await page.evaluate(() => {
      for (const name of ['first', 'second']) void fetch(`/api/v1/authoring/jobs?which=${name}&cursor=PRIVATE_QUERY`, { headers: { 'X-Synthetic': 'PRIVATE_REQUEST_HEADER' } }).then(response => response.text())
    })
    await returned
    expect(responses.size).toBe(2)
    const bodyFinished = page.waitForEvent('requestfinished', { predicate: request => request.url().includes('which=first') })
    responses.get('first')!.end('"}'); await bodyFinished
    await observer.around(info, () => page.getByRole('button', { name: 'Freeze', exact: true }).click())
    const path = info.outputPath('authoring-prepare-diagnostic.json'), raw = await readFile(path, 'utf8'), value = JSON.parse(raw)
    const events = value.frozen_observation.events as Array<{ kind: string; id: number; path?: string; status?: number; elapsed_ms: number }>
    const requests = events.filter(event => event.kind === 'request'), completions = events.filter(event => event.kind === 'finished')
    expect(requests).toHaveLength(2); expect(new Set(requests.map(event => event.id)).size).toBe(2)
    expect(requests.map(event => event.path)).toEqual(['/api/v1/authoring/jobs', '/api/v1/authoring/jobs'])
    expect(events.filter(event => event.kind === 'response').map(event => event.status)).toEqual([200, 200])
    expect(completions).toHaveLength(1); expect(requests.some(event => event.id === completions[0].id)).toBe(true)
    expect(events.every(event => event.elapsed_ms <= value.assertion.frozen_at_ms)).toBe(true)
    expect(value.assertion.verdict).toBe('passed'); expect(value.frozen_observation.observer_errors).toBe(0)
    expect(value.mechanism.source_delivery_completeness).toBe('unknown'); expect(raw).not.toContain('PRIVATE_')
    const lateFinished = page.waitForEvent('requestfinished', { predicate: request => request.url().includes('which=second') })
    responses.get('second')!.end('"}'); await lateFinished
    expect(await readFile(path, 'utf8')).toBe(raw); expect(responses.size).toBe(2)
  } finally { observer?.dispose(); for (const response of responses.values()) response.end(); server.closeAllConnections(); await new Promise<void>(resolve => server.close(() => resolve())) }
})

test('diagnostic storage failure preserves both a successful assertion and the exact original failure', async ({ page }) => {
  await page.setContent('<button>Available</button>')
  const brokenInfo = { outputPath() { throw new Error('PRIVATE_STORAGE') } } as unknown as Parameters<Awaited<ReturnType<typeof observeAuthoringPrepare>>['around']>[0]
  const first = await observeAuthoringPrepare(page)
  await first.around(brokenInfo, () => page.getByRole('button', { name: 'Available', exact: true }).click())
  first.dispose()
  // A separate page keeps the one-binding-per-page observation contract explicit.
  const other = await page.context().newPage(), second = await observeAuthoringPrepare(other), original = new Error('PRIVATE_ORIGINAL')
  try { await expect(second.around(brokenInfo, async () => { throw original })).rejects.toBe(original) }
  finally { second.dispose(); await other.close() }
})
