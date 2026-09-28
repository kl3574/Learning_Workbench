import { afterEach, expect, test, vi } from 'vitest'
import { connectSession } from '../../api/client'
import { reviewClient } from './reviewClient'
import { reviewCandidate, reviewSession, machineReceipt, safeReviewJob } from './reviewFixtures'

afterEach(() => vi.unstubAllGlobals())
test('generated transport owns all seven real routes, credentials, write keys and exact bodies', async () => {
  const session = reviewSession('workspace_transport'), job = safeReviewJob(session.workspace_id)
  const requests: { path: string; init: RequestInit }[] = []
  const body = { expected_revision: 1, checks: ['structure'] as ['structure'], reviewer_note: 'Synthetic note' }
  const decision = { expected_revision: 1, candidate_sha256: reviewCandidate.candidate_sha256, mathematical: 'REJECTED' as const, sources: 'REJECTED' as const, reason: 'Synthetic rejection', evidence_artifact_ids: [] }
  const responses: unknown[] = [session, session, { id: machineReceipt.id, status: 'queued' }, machineReceipt, { ...machineReceipt, revision: 2, mathematical: 'REJECTED', sources: 'REJECTED', decision_reason: decision.reason }, job, { ...job, status: 'cancelled' }]
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => {
    requests.push({ path, init })
    return path.endsWith('/download') ? new Response('synthetic bytes', { headers: { ETag: '"actual-etag"' } })
      : new Response(JSON.stringify(responses.shift()), { headers: { 'Content-Type': 'application/json' } })
  }))
  await connectSession(); await reviewClient.session()
  await reviewClient.create(reviewCandidate.draft_id, body, 'original_create')
  await reviewClient.read(machineReceipt.id); await reviewClient.decide(machineReceipt.id, decision, 'original_decision')
  await reviewClient.job(job.id); await reviewClient.cancel(job.id, { expected_revision: 3 }, 'original_cancel')
  const artifact = await reviewClient.artifact('artifact_synthetic')
  expect(artifact.etag).toBe('"actual-etag"'); expect(artifact.data.size).toBe(15)
  expect(requests.map(value => [value.init.method, value.path])).toEqual([
    ['GET', '/api/v1/session'], ['GET', '/api/v1/session'], ['POST', `/api/v1/drafts/${reviewCandidate.draft_id}/review`],
    ['GET', `/api/v1/reviews/${machineReceipt.id}`], ['POST', `/api/v1/reviews/${machineReceipt.id}/decision`],
    ['GET', `/api/v1/jobs/${job.id}`], ['POST', `/api/v1/jobs/${job.id}/cancel`], ['GET', '/api/v1/artifacts/artifact_synthetic/download'],
  ])
  expect(requests.every(value => value.init.credentials === 'same-origin')).toBe(true)
  expect(requests.slice(1).every(value => new Headers(value.init.headers).get('X-CSRF-Token') === session.csrf_token)).toBe(true)
  for (const [index, key, expected] of [[2, 'original_create', body], [4, 'original_decision', decision], [6, 'original_cancel', { expected_revision: 3 }]] as const) {
    expect(new Headers(requests[index].init.headers).get('Idempotency-Key')).toBe(key)
    expect(JSON.parse(String(requests[index].init.body))).toEqual(expected)
  }
})

test('unknown fields and mismatched receipt identity fail before entering UI state', async () => {
  const fetch = vi.fn(async () => new Response(JSON.stringify({ ...machineReceipt, private_payload: 'synthetic' })))
  vi.stubGlobal('fetch', fetch)
  await expect(reviewClient.read(machineReceipt.id)).rejects.toThrow()
  fetch.mockImplementationOnce(async () => new Response(JSON.stringify({ ...machineReceipt, id: 'review_other' })))
  await expect(reviewClient.read(machineReceipt.id)).rejects.toThrow()
  await expect(reviewClient.create(reviewCandidate.draft_id, { expected_revision: 1, checks: ['structure'], reviewer_note: '', reviewer: 'forged' } as never, 'key')).rejects.toThrow()
  expect(fetch).toHaveBeenCalledTimes(2)
})
