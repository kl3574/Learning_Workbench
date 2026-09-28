import { afterEach, expect, test, vi } from 'vitest'
import { editClient } from './editClient'
import { editFixture } from './editFixtures'
afterEach(() => vi.unstubAllGlobals())
test('generated dedicated edit GET preserves exact revision and has no body; current uses a separate GET', async () => {
  const calls: { path: string; init: RequestInit }[] = []
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => { calls.push({ path, init }); return new Response(JSON.stringify(editFixture())) }))
  await editClient.read('draft_edit_synthetic', 1); await editClient.read('draft_edit_synthetic')
  expect(calls.map(c => c.path)).toEqual(['/api/v1/draft-edits/draft_edit_synthetic?revision=1', '/api/v1/draft-edits/draft_edit_synthetic'])
  expect(calls.every(c => c.init.method === 'GET' && c.init.body === undefined && c.init.credentials === 'same-origin')).toBe(true)
})
test.each(['missing-owner', 'foreign-field', 'wrong-hash'])('strict generated read rejects %s', async fault => {
  const value = editFixture()
  if (fault === 'missing-owner') Reflect.deleteProperty(value, 'owner')
  if (fault === 'foreign-field') Object.assign(value, { actor_id: 'synthetic_actor' })
  if (fault === 'wrong-hash') value.payload.title += ' changed'
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(value))))
  await expect(editClient.read('draft_edit_synthetic', 1)).rejects.toThrow()
})
