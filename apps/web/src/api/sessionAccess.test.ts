import { afterEach, expect, test, vi } from 'vitest'
import { connectSession, request } from './client'
const deferred = <T,>() => { let resolve!: (value: T) => void, reject!: (reason: unknown) => void; const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no }); return { promise, resolve, reject } }
const response = (role: 'author' | 'learner') => new Response(JSON.stringify({ role, workspace_id: 'workspace_synthetic', csrf_token: 'synthetic_only' }))
afterEach(() => { vi.restoreAllMocks(); vi.unstubAllGlobals() })
test.each(['author', 'learner'] as const)('a fresh session cannot be admitted during a pending role change to %s', async role => {
  const gate = deferred<Response>(); let reads = 0
  vi.stubGlobal('fetch', vi.fn(async (path: string) => { if (path.endsWith('/role')) return gate.promise; reads++; return response(role) }))
  const mutation = request('POST /api/v1/session/role', { role }, { 'Idempotency-Key': 'synthetic-role' })
  const read = request('GET /api/v1/session', undefined)
  try { await Promise.resolve(); await Promise.resolve(); expect(reads).toBe(0) }
  finally { gate.resolve(response(role)); await mutation; await read }
  expect(reads).toBe(1); expect((await read).role).toBe(role)
})
test('two pending access mutations keep session reads fenced while safe job controls remain usable', async () => {
  const first = deferred<Response>(), second = deferred<Response>(); let mutations = 0, reads = 0
  vi.stubGlobal('fetch', vi.fn(async (path: string) => {
    if (path.endsWith('/role')) return ++mutations === 1 ? first.promise : second.promise
    if (path === '/api/v1/session') { reads++; return response('learner') }
    return new Response(JSON.stringify({ id: 'job_synthetic', status: 'cancelled' }))
  }))
  const one = request('POST /api/v1/session/role', { role: 'author' }, { 'Idempotency-Key': 'synthetic-first' })
  const two = request('POST /api/v1/session/role', { role: 'learner' }, { 'Idempotency-Key': 'synthetic-second' })
  const read = request('GET /api/v1/session', undefined)
  try {
    expect((await request('GET /api/v1/jobs/{id}', undefined, undefined, { path: { id: 'job_synthetic' } })).status).toBe('cancelled')
    await request('POST /api/v1/jobs/{id}/cancel', { expected_revision: 1 }, { 'Idempotency-Key': 'synthetic-cancel' }, { path: { id: 'job_synthetic' } })
    first.resolve(response('author')); await one; expect(reads).toBe(0)
  } finally { first.resolve(response('author')); second.resolve(response('learner')); await Promise.all([one, two, read]) }
  expect(reads).toBe(1)
})
test.each(['network', 'abort', 'http'] as const)('failed %s mutation releases the fence and requires an actual fresh session response', async mode => {
  const gate = deferred<Response>(); let reads = 0
  vi.stubGlobal('fetch', vi.fn(async (path: string) => { if (path.endsWith('/role')) return gate.promise; reads++; return response('learner') }))
  const mutation = request('POST /api/v1/session/role', { role: 'learner' }, { 'Idempotency-Key': 'synthetic-failed' }).catch(error => error)
  const read = request('GET /api/v1/session', undefined)
  try { await Promise.resolve(); expect(reads).toBe(0) }
  finally {
    if (mode === 'http') gate.resolve(new Response(JSON.stringify({ error: { code: 'POLICY_DENIED' } }), { status: 403 }))
    else gate.reject(mode === 'abort' ? new DOMException('Synthetic cancellation', 'AbortError') : new Error('Synthetic network failure'))
    await mutation; await read
  }
  expect(reads).toBe(1); expect((await read).role).toBe('learner')
})
test('initial session and CSRF acquisition do not deadlock the first explicit role request', async () => {
  const calls: string[] = []
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => { calls.push(path); if (path.endsWith('/role')) expect(new Headers(init.headers).get('X-CSRF-Token')).toBe('synthetic_only'); return response('author') }))
  expect(await connectSession()).toBe('workspace_synthetic')
  await request('POST /api/v1/session/role', { role: 'author' }, { 'Idempotency-Key': 'synthetic-first-role' })
  expect((await request('GET /api/v1/session', undefined)).role).toBe('author')
  expect(calls).toEqual(['/api/v1/session', '/api/v1/session/role', '/api/v1/session'])
})

test('bootstrap can settle while simultaneous session readers wait, then the first role operation proceeds', async () => {
  const gate = deferred<Response>(); let reads = 0
  history.replaceState(null, '', '/#bootstrap=synthetic_bootstrap_only')
  vi.stubGlobal('fetch', vi.fn(async (path: string) => { if (path.endsWith('/bootstrap')) return gate.promise; if (path === '/api/v1/session') reads++; return response('author') }))
  const boot = connectSession(), read = request('GET /api/v1/session', undefined)
  try { await Promise.resolve(); expect(reads).toBe(0) }
  finally { gate.resolve(response('author')); await boot; await read }
  await request('POST /api/v1/session/role', { role: 'author' }, { 'Idempotency-Key': 'synthetic-bootstrap-role' })
  expect(reads).toBe(1); expect(location.hash).toBe('')
})
