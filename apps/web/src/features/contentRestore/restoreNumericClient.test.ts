import { afterEach, expect, test, vi } from 'vitest'
import { API_ENDPOINTS } from '../../../../../packages/contracts/generated/api-client'
import { restoreNumericClient } from './restoreNumericClient'
import { numericBody, numericBoundSnapshot, numericPreview } from './restoreNumericFixtures'

afterEach(() => vi.unstubAllGlobals())
test('malformed preview identities never reach fetch', async () => {
  const fetch = vi.fn(); vi.stubGlobal('fetch', fetch)
  await expect(restoreNumericClient.preview('different_draft', numericBody, 'key')).rejects.toThrow()
  await expect(restoreNumericClient.preview(numericBody.candidate.draft_id, { ...numericBody, material: { ...numericBody.material, reason: '' } }, 'key')).rejects.toThrow()
  expect(fetch).not.toHaveBeenCalled()
})
test('numeric client uses only actual generated operations; an unavailable generation cannot silently send', async () => {
  const fetch = vi.fn(async () => new Response(JSON.stringify(numericPreview), { status: 201 })); vi.stubGlobal('fetch', fetch)
  const operation = 'POST /api/v1/content/restore-drafts/{id}/numeric-checks'
  if (Object.hasOwn(API_ENDPOINTS, operation)) {
    expect(await restoreNumericClient.preview(numericBody.candidate.draft_id, numericBody, 'original_key')).toEqual(numericPreview)
    expect(fetch.mock.calls[0]).toEqual([`/api/v1/content/restore-drafts/${numericBody.candidate.draft_id}/numeric-checks`, expect.objectContaining({
      method: 'POST', credentials: 'same-origin', body: JSON.stringify(numericBody), headers: expect.objectContaining({ 'Idempotency-Key': 'original_key' }),
    })])
  } else {
    await expect(restoreNumericClient.preview(numericBody.candidate.draft_id, numericBody, 'original_key')).rejects.toThrow('实际接口尚未生成')
    expect(fetch).not.toHaveBeenCalled()
  }
})
test('snapshot discovery sends GET only and validates complete required numeric discovery', async () => {
  const outgoing: { path: string; init: RequestInit }[] = []
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => {
    outgoing.push({ path, init }); return new Response(JSON.stringify(numericBoundSnapshot), { status: 200 })
  }))
  expect(await restoreNumericClient.draft(numericBody.candidate.draft_id)).toEqual(numericBoundSnapshot)
  expect(outgoing).toHaveLength(1)
  expect(outgoing[0].init.method).toBe('GET'); expect(outgoing[0].init.body).toBeUndefined()
})
