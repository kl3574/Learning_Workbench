import { afterEach, expect, test, vi } from 'vitest'
import { compareClient } from './compareClient'
import { versions } from './fixtures'

afterEach(() => vi.unstubAllGlobals())
test('reads the selected exact revision with real generated GET paths and verifies body bytes', async () => {
  const selected = versions[0], calls: { path: string; init: RequestInit }[] = []
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => {
    calls.push({ path, init })
    return path.includes('/body?')
      ? new Response(selected.body, { headers: { ETag: `"${selected.data.block.body_sha256}"` } })
      : new Response(JSON.stringify(selected.data), { headers: { ETag: `"${selected.ref.sha256}"` } })
  }))
  const result = await compareClient.block(selected.ref)
  expect(result.body).toBe('old α\nshared\n')
  expect(result.block_ref).toEqual(selected.ref)
  expect(calls.map(call => call.path)).toEqual(['/api/v1/blocks/block_compare?include_provenance=true&revision=1', '/api/v1/blocks/block_compare/body?revision=1'])
  expect(calls.every(call => call.init.method === 'GET' && call.init.credentials === 'same-origin')).toBe(true)
})

test.each(['changed-title', 'extra-field'])('rejects %s even with a matching ETag and body', async fault => {
  const selected = versions[0]
  const data = structuredClone(selected.data)
  if (fault === 'changed-title') data.block.title = 'Changed metadata without changed reference'
  else Object.assign(data, { unregistered_payload: 'synthetic unexpected field' })
  vi.stubGlobal('fetch', vi.fn(async (path: string) => path.includes('/body?')
    ? new Response(selected.body, { headers: { ETag: `"${selected.data.block.body_sha256}"` } })
    : new Response(JSON.stringify(data), { headers: { ETag: `"${selected.ref.sha256}"` } })))
  await expect(compareClient.block(selected.ref)).rejects.toThrow()
})

test.each(['body-hash', 'etag', 'projection-ref', 'missing-default', 'unsafe-revision'])('rejects %s without rendering a fallback version', async fault => {
  const selected = versions[0], data = structuredClone(selected.data)
  if (fault === 'projection-ref') data.block_ref = versions[1].ref
  if (fault === 'missing-default') delete data.block.concepts
  if (fault === 'unsafe-revision') data.block.revision = 9007199254740992
  vi.stubGlobal('fetch', vi.fn(async (path: string) => path.includes('/body?')
    ? new Response(fault === 'body-hash' ? 'altered body' : selected.body, { headers: { ETag: `"${data.block.body_sha256}"` } })
    : new Response(JSON.stringify(data), { headers: { ETag: fault === 'etag' ? `W/"${selected.ref.sha256}"` : `"${selected.ref.sha256}"` } })))
  await expect(compareClient.block(selected.ref)).rejects.toThrow()
})
test.each(['other-id', 'duplicate-revision', 'unknown-field', 'boolean-revision'])('history rejects %s rather than manufacturing a usable option', async fault => {
  const row = { ref: versions[0].ref, created_at: '2026-09-28T00:00:00Z', review_state: 'unreviewed', lifecycle: 'active' }
  const page = { items: [structuredClone(row)], next_cursor: null }
  if (fault === 'other-id') page.items[0].ref.id = 'block_other'
  if (fault === 'duplicate-revision') page.items.push(structuredClone(row))
  if (fault === 'unknown-field') Object.assign(page, { unsafe_extra: 'unexpected' })
  if (fault === 'boolean-revision') Object.assign(page.items[0].ref, { revision: true })
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(page))))
  await expect(compareClient.history('block_compare', null)).rejects.toThrow()
})
