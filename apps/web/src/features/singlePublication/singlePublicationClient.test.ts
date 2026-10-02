import { afterEach, expect, test, vi } from 'vitest'
import { singlePublicationClient } from './singlePublicationClient'
import { singlePublicationFixture } from './singlePublicationFixtures'
const calls: { path: string; method: string; body: unknown }[] = []
afterEach(() => { vi.unstubAllGlobals(); calls.splice(0) })
test('actual typed transport uses existing owner routes and exactly four publish fields', async () => {
  const f = singlePublicationFixture(), outputs = [f.draft, f.generation, f.numeric, f.receipt, f.ack, { ...f.ack, revision: 2 }]
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => { calls.push({ path, method: init.method!, body: init.body ? JSON.parse(init.body as string) : null }); return new Response(JSON.stringify(outputs.shift()), { status: 200 }) }))
  await singlePublicationClient.draft(f.draft.candidate.draft_id); await singlePublicationClient.generation(f.draft.source_job_id); await singlePublicationClient.numeric(f.numeric.id); await singlePublicationClient.review(f.receipt.id)
  const body = { expected_revision: 1, expected_content_sha256: f.draft.candidate.candidate_sha256, review_receipt_id: f.receipt.id, acknowledged_warning_codes: ['SOURCE_CONFIRM'] }
  expect(await singlePublicationClient.publish(f.draft.candidate.draft_id, body, 'singlepublishcmd_synthetic')).toEqual(f.ack)
  expect((await singlePublicationClient.current(f.ack.id)).revision).toBe(2)
  expect(calls.map(call => `${call.method} ${call.path}`)).toEqual([`GET /api/v1/authoring/drafts/${f.draft.candidate.draft_id}`, `GET /api/v1/authoring/jobs/${f.draft.source_job_id}`, `GET /api/v1/authoring/numeric-checks/${f.numeric.id}`, `GET /api/v1/reviews/${f.receipt.id}`, `POST /api/v1/drafts/${f.draft.candidate.draft_id}/publish`, `GET /api/v1/objects/${f.ack.id}/current`])
  expect(calls[4].body).toEqual(body)
})
test('closed current projection rejects missing published_ref and wrong ID without adapting old data', async () => {
  const f = singlePublicationFixture(), old = { ...f.draft } as Partial<typeof f.draft>; delete old.published_ref
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(old))))
  await expect(singlePublicationClient.draft(f.draft.candidate.draft_id)).rejects.toThrow()
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(f.draft))))
  await expect(singlePublicationClient.draft('draft_other')).rejects.toThrow()
})
