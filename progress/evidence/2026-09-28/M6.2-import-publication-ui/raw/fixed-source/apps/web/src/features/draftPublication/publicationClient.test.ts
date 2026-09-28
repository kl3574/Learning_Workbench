import { afterEach, expect, test, vi } from 'vitest'
import { connectSession } from '../../api/client'
import { reviewSession } from '../draftReview/reviewFixtures'
import { publicationClient } from './publicationClient'
import { publicationDraft, publicationReceipt, publicationRef } from './publicationFixtures'

afterEach(() => vi.unstubAllGlobals())
test('actual generated publication/current routes preserve exact four fields, original key and session transport', async () => {
  const session = reviewSession('workspace_publication_transport'), requests: { path: string; init: RequestInit }[] = []
  const responses = [session, session, publicationDraft, publicationReceipt, publicationRef, { ...publicationRef, revision: 2 }]
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => { requests.push({ path, init }); return new Response(JSON.stringify(responses.shift())) }))
  await connectSession(); await publicationClient.session(); await publicationClient.draft(publicationDraft.id); await publicationClient.review(publicationReceipt.id)
  const body = { expected_revision: 1, expected_content_sha256: publicationDraft.candidate_sha256, review_receipt_id: publicationReceipt.id, acknowledged_warning_codes: ['SOURCE_CONFIRM'] }
  await publicationClient.publish(publicationDraft.id, body, 'original_publication_key'); await publicationClient.current(publicationRef.id)
  expect(requests.map(value => `${value.init.method} ${value.path}`)).toEqual(['GET /api/v1/session', 'GET /api/v1/session', `GET /api/v1/drafts/${publicationDraft.id}`, `GET /api/v1/reviews/${publicationReceipt.id}`, `POST /api/v1/drafts/${publicationDraft.id}/publish`, `GET /api/v1/objects/${publicationRef.id}/current`])
  expect(JSON.parse(String(requests[4].init.body))).toEqual(body)
  expect(new Headers(requests[4].init.headers).get('Idempotency-Key')).toBe('original_publication_key')
  expect(new Headers(requests[4].init.headers).get('X-CSRF-Token')).toBe(session.csrf_token)
  expect(requests.every(value => value.init.credentials === 'same-origin')).toBe(true)
})

test('unrecognized response fields and extra publish fields are rejected at the generated HTTP boundary', async () => {
  const fetch = vi.fn(async () => new Response(JSON.stringify({ ...publicationRef, private_payload: 'synthetic' }))); vi.stubGlobal('fetch', fetch)
  await expect(publicationClient.current(publicationRef.id)).rejects.toThrow()
  await expect(publicationClient.publish(publicationDraft.id, { expected_revision: 1, expected_content_sha256: publicationDraft.candidate_sha256, review_receipt_id: publicationReceipt.id, acknowledged_warning_codes: [], mathematical: 'NOT_APPLICABLE' } as never, 'synthetic_key')).rejects.toThrow()
  expect(fetch).toHaveBeenCalledTimes(1)
})
