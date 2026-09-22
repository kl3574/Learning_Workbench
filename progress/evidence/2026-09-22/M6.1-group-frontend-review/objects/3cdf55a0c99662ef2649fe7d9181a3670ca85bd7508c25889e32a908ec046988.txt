import { afterEach, expect, test, vi } from 'vitest'
import { authoringClient } from './authoringClient'
afterEach(() => vi.unstubAllGlobals())
test('the generated client sends prepare without consent and resumes only the exact control cursor', async () => {
  const outgoing: { path: string; init: RequestInit }[] = []
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => {
    outgoing.push({ path, init })
    const body = init.method === 'POST' ? { id: 'job_new_authoring', status: 'awaiting_approval' } : { items: [], next_cursor: null }
    return new Response(JSON.stringify(body), { status: init.method === 'POST' ? 202 : 200, headers: { 'Content-Type': 'application/json' } })
  }))
  const body = { topic: '合成主题', prerequisites: [], objectives: ['声明目标'], proof_policy: 'full' as const, output_kind: 'worked_example' as const, source_refs: [], provider_id: 'provider_synthetic' }
  expect(await authoringClient.prepare(body, 'original_prepare_key')).toEqual({ id: 'job_new_authoring', status: 'awaiting_approval' })
  await authoringClient.list('opaque+/server-cursor')
  expect(outgoing[0].path).toBe('/api/v1/authoring/jobs'); expect(JSON.parse(String(outgoing[0].init.body))).toEqual(body)
  expect(new Headers(outgoing[0].init.headers).get('Idempotency-Key')).toBe('original_prepare_key')
  expect(outgoing[1].init.method).toBe('GET'); expect(outgoing[1].init.body).toBeUndefined()
  const query = new URL(outgoing[1].path, 'http://test.invalid').searchParams
  expect(query.get('cursor')).toBe('opaque+/server-cursor'); expect(query.get('limit')).toBe('20')
})
