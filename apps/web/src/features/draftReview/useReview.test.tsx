import 'fake-indexeddb/auto'
import { Blob as NodeBlob } from 'node:buffer'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { JobSnapshot, ReviewJobAck, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
import { getSessionGeneration, request } from '../../api/client'
import { ApiError } from '../../api/client'
import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'
import { makeReviewCommand, persistReviewCommand, readReviewCommand, reviewCommandStore, reviewControlStore, reviewJobStore, rememberReviewJob } from './reviewCommands'
import type { ReviewPort } from './reviewClient'
import { machineReceipt, reviewCandidate, reviewSession, safeReviewJob } from './reviewFixtures'
import { useReview } from './useReview'

afterEach(async () => { cleanup(); vi.useRealTimers(); vi.restoreAllMocks(); vi.unstubAllGlobals(); await Promise.all([reviewCommandStore.close(), reviewControlStore.close(), reviewJobStore.close()]) })
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>(done => { resolve = done }); return { promise, resolve } }
function fixture() {
  const workspace = `workspace_${crypto.randomUUID()}`
  const port: ReviewPort = {
    session: vi.fn(async () => reviewSession(workspace)), create: vi.fn(async () => ({ id: machineReceipt.id, status: 'queued' as const })),
    read: vi.fn(async () => structuredClone(machineReceipt)), decide: vi.fn(async () => { throw new Error('No implicit decision') }),
    job: vi.fn(async () => safeReviewJob(workspace)), cancel: vi.fn(async () => ({ ...safeReviewJob(workspace), status: 'cancelled' as const })),
    artifact: vi.fn(async () => { throw new Error('No implicit download') }),
  }
  return { workspace, port, body: { expected_revision: 1, checks: ['structure'] as ['structure'], reviewer_note: 'Synthetic private original' } }
}

test('lost ACK retains one original key/body and permits only explicit same-page replay', async () => {
  const { workspace, port, body } = fixture()
  vi.mocked(port.create).mockRejectedValueOnce(new Error('Synthetic response loss'))
  const hook = renderHook(() => useReview(workspace, false, port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.create(reviewCandidate, body))
  const pending = hook.result.current.commands[0]
  expect(pending.ack).toBeNull()
  const durable = readReviewCommand((await reviewCommandStore.load(workspace))[pending.command_id], workspace)
  expect(durable).toEqual(pending)
  await act(() => hook.result.current.create(reviewCandidate, body))
  expect(port.create).toHaveBeenCalledTimes(1)
  await act(() => hook.result.current.execute(pending))
  expect(port.create).toHaveBeenCalledTimes(2)
  expect(vi.mocked(port.create).mock.calls[0]).toEqual(vi.mocked(port.create).mock.calls[1])
  await waitFor(() => expect(hook.result.current.job?.status).toBe('completed'))
  const confirmed = hook.result.current.commands[0]
  expect(confirmed.kind === 'create' && confirmed.ack?.status).toBe('queued')
  expect(port.read).not.toHaveBeenCalled(); expect(port.decide).not.toHaveBeenCalled()
})

test('storage failure stops before any HTTP write', async () => {
  const { workspace, port, body } = fixture()
  const hook = renderHook(() => useReview(workspace, false, port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  vi.spyOn(reviewCommandStore, 'save').mockRejectedValueOnce(new Error('Synthetic quota failure'))
  await act(() => hook.result.current.create(reviewCandidate, body))
  expect(port.create).not.toHaveBeenCalled()
  expect(await reviewCommandStore.load(workspace)).toEqual({})
})

test('real session access notification discards a late ACK and makes the durable original command read-only', async () => {
  const { workspace, port, body } = fixture(), pending = deferred<ReviewJobAck>()
  vi.mocked(port.create).mockReturnValueOnce(pending.promise)
  const hook = renderHook(() => useReview(workspace, false, port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  let sending!: Promise<void>; act(() => { sending = hook.result.current.create(reviewCandidate, body) })
  await waitFor(() => expect(port.create).toHaveBeenCalledTimes(1))
  const command = hook.result.current.commands[0]
  vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(reviewSession(workspace)))))
  await act(() => request('POST /api/v1/session/role', { role: 'author' }, { 'Idempotency-Key': 'synthetic_access_change' }))
  await act(async () => { pending.resolve({ id: machineReceipt.id, status: 'queued' }); await sending })
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  const retained = readReviewCommand((await reviewCommandStore.load(workspace))[command.command_id], workspace)
  expect(retained.ack).toBeNull(); expect(retained.body).toEqual(body)
  expect(hook.result.current.canReplay(retained)).toBe(false)
  await act(() => hook.result.current.execute(retained))
  expect(port.create).toHaveBeenCalledTimes(1)
})

test('a prior page command is read-only after reload while known job and receipt remain readable', async () => {
  const { workspace, port, body } = fixture()
  const original = makeReviewCommand(workspace, getSessionGeneration(), { kind: 'create', candidate: reviewCandidate, body })
  original.origin.page_id = 'page_closed'
  await persistReviewCommand(original); await rememberReviewJob(workspace, machineReceipt.id)
  const hook = renderHook(() => useReview(workspace, false, port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  expect(hook.result.current.canReplay(hook.result.current.commands[0])).toBe(false)
  await act(() => hook.result.current.execute(hook.result.current.commands[0]))
  await act(() => hook.result.current.create(reviewCandidate, body))
  expect(port.create).not.toHaveBeenCalled()
  await act(() => hook.result.current.selectJob(machineReceipt.id))
  await act(() => hook.result.current.read(machineReceipt.id))
  expect(hook.result.current.receipt).toEqual(machineReceipt)
})

test('Policy pause discards a late create ACK without persisting private acknowledgement', async () => {
  const { workspace, port, body } = fixture(), pending = deferred<ReviewJobAck>()
  vi.mocked(port.create).mockReturnValueOnce(pending.promise)
  const hook = renderHook(({ paused }) => useReview(workspace, paused, port), { initialProps: { paused: false } })
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  let execution!: Promise<void>
  act(() => { execution = hook.result.current.create(reviewCandidate, body) })
  await waitFor(() => expect(port.create).toHaveBeenCalledTimes(1))
  const originals = await reviewCommandStore.load(workspace)
  hook.rerender({ paused: true })
  await act(async () => { pending.resolve({ id: machineReceipt.id, status: 'queued' }); await execution })
  expect(hook.result.current.academic).toBe(false); expect(hook.result.current.commands).toEqual([])
  expect(await reviewCommandStore.load(workspace)).toEqual(originals)
  expect(hook.result.current.receipt).toBeNull()
})

test('late protected receipt cannot enter a different workspace or paused view', async () => {
  const { workspace, port } = fixture(), pending = deferred<StoredReviewReceipt>()
  vi.mocked(port.read).mockReturnValueOnce(pending.promise)
  const hook = renderHook(({ target, paused }) => useReview(target, paused, port), { initialProps: { target: workspace, paused: false } })
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  let reading!: Promise<void>; act(() => { reading = hook.result.current.read(machineReceipt.id) })
  hook.rerender({ target: 'workspace_other', paused: true })
  await act(async () => { pending.resolve(machineReceipt); await reading })
  expect(hook.result.current.receipt).toBeNull(); expect(hook.result.current.report).toBeNull()
})

test('foreign or non-review safe job cannot be remembered as review recovery', async () => {
  const { workspace, port } = fixture()
  vi.mocked(port.job).mockResolvedValueOnce({ ...safeReviewJob(workspace), kind: 'authoring' })
  const hook = renderHook(() => useReview(workspace, false, port))
  await waitFor(() => expect(hook.result.current.controlsReady).toBe(true))
  await act(() => hook.result.current.selectJob(machineReceipt.id))
  expect(hook.result.current.job).toBeNull(); expect(await reviewJobStore.load(workspace)).toEqual({})
})

test('an earlier poll completion cannot overwrite a newer explicit current Job read', async () => {
  const { workspace, port } = fixture(), oldPoll = deferred<JobSnapshot>(), nextPoll = deferred<JobSnapshot>()
  const early = { ...safeReviewJob(workspace), status: 'running' as const, revision: 1 }
  const current = { ...early, revision: 3 }
  vi.mocked(port.job).mockResolvedValueOnce(early).mockReturnValueOnce(oldPoll.promise).mockResolvedValueOnce(current).mockReturnValue(nextPoll.promise)
  const hook = renderHook(() => useReview(workspace, false, port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.selectJob(machineReceipt.id))
  await waitFor(() => expect(port.job).toHaveBeenCalledTimes(2))
  await act(async () => {
    await hook.result.current.selectJob(machineReceipt.id)
    oldPoll.resolve(early)
    await Promise.resolve()
  })
  expect(hook.result.current.job).toEqual(current)
})

test('an old selection timer cannot fetch or apply the previous Job after a new selection succeeds', async () => {
  const { workspace, port } = fixture()
  const early = { ...safeReviewJob(workspace), status: 'running' as const, revision: 1 }
  const current = { ...early, id: 'review_next', revision: 3 }
  vi.mocked(port.job).mockImplementation(async id => id === early.id ? early : current)
  const hook = renderHook(() => useReview(workspace, false, port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
  await act(() => hook.result.current.selectJob(early.id))
  expect(port.job).toHaveBeenCalledTimes(2)
  await act(async () => {
    await hook.result.current.selectJob(current.id)
    vi.advanceTimersByTime(2000)
    await Promise.resolve()
  })
  expect(hook.result.current.selected).toBe(current.id)
  expect(hook.result.current.job).toEqual(current)
  expect(vi.mocked(port.job).mock.calls.slice(2).every(([id]) => id === current.id)).toBe(true)
})

test('polling waits for manual selection and resumes the retained selection after a failed read', async () => {
  const { workspace, port } = fixture(), selecting = deferred<JobSnapshot>()
  const early = { ...safeReviewJob(workspace), status: 'running' as const, revision: 1 }
  const current = { ...early, id: 'review_next', revision: 3 }
  vi.mocked(port.job).mockImplementation(async id => id === early.id ? early : current)
  const hook = renderHook(() => useReview(workspace, false, port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
  await act(() => hook.result.current.selectJob(early.id))
  expect(port.job).toHaveBeenCalledTimes(2)
  vi.mocked(port.job).mockReturnValueOnce(selecting.promise)
  let read!: Promise<void>; act(() => { read = hook.result.current.selectJob(current.id) })
  await act(async () => { vi.advanceTimersByTime(4000); await Promise.resolve() })
  expect(port.job).toHaveBeenCalledTimes(3)
  await act(async () => { selecting.resolve(current); await read })
  expect(hook.result.current.job).toEqual(current)
  vi.mocked(port.job).mockRejectedValueOnce(new Error('Synthetic failed next selection'))
  await act(() => hook.result.current.selectJob('review_unavailable'))
  expect(hook.result.current.selected).toBe(current.id)
  expect(hook.result.current.job).toEqual(current)
  const reads = vi.mocked(port.job).mock.calls.length
  await act(async () => { vi.advanceTimersByTime(2000); await Promise.resolve() })
  expect(vi.mocked(port.job).mock.calls.slice(reads)).toEqual([[current.id]])
})

test('report bytes require actual ETag and a second unchanged currently authorized receipt', async () => {
  const { workspace, port } = fixture(), text = '{"fixture":"synthetic report"}'
  const bytes = new TextEncoder().encode(text), digest = bytesToHex(sha256(bytes))
  vi.mocked(port.artifact).mockImplementation(async () => ({ data: new NodeBlob([text]) as Blob, etag: `"${digest}"` }))
  const hook = renderHook(() => useReview(workspace, false, port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.read(machineReceipt.id))
  await act(() => hook.result.current.artifact('/api/v1/artifacts/artifact_not_in_receipt/download', false))
  expect(port.artifact).not.toHaveBeenCalled()
  await act(() => hook.result.current.artifact(machineReceipt.evidence_paths[0], false))
  expect(hook.result.current.report).toEqual({ path: machineReceipt.evidence_paths[0], text, sha256: digest })
  expect(port.read).toHaveBeenCalledTimes(2)
  vi.mocked(port.artifact).mockResolvedValueOnce({ data: new NodeBlob([text]) as Blob, etag: `"${'b'.repeat(64)}"` })
  await act(() => hook.result.current.artifact(machineReceipt.evidence_paths[0], false))
  expect(hook.result.current.report).toBeNull()
  expect(port.read).toHaveBeenCalledTimes(2)
  vi.mocked(port.read).mockResolvedValueOnce({ ...machineReceipt, revision: 2, decision_reason: 'Changed elsewhere' })
  await act(() => hook.result.current.artifact(machineReceipt.evidence_paths[0], false))
  expect(hook.result.current.report).toBeNull()
})

test('artifact Policy rejection clears already displayed private receipt and stored command projection', async () => {
  const { workspace, port } = fixture(), text = '{}', digest = bytesToHex(sha256(new TextEncoder().encode(text)))
  vi.mocked(port.artifact).mockImplementation(async () => ({ data: new NodeBlob([text]) as Blob, etag: `"${digest}"` }))
  const hook = renderHook(() => useReview(workspace, false, port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.read(machineReceipt.id))
  vi.mocked(port.read).mockRejectedValueOnce(new ApiError(409, 'Synthetic policy block', 'ASSESSMENT_ACTIVE'))
  await act(() => hook.result.current.artifact(machineReceipt.evidence_paths[0], false))
  expect(hook.result.current.academic).toBe(false)
  expect(hook.result.current.receipt).toBeNull(); expect(hook.result.current.report).toBeNull()
  expect(hook.result.current.commands).toEqual([])
})

test('stale decision preserves the original CAS and requires a fresh receipt before another command', async () => {
  const { workspace, port } = fixture()
  vi.mocked(port.decide).mockRejectedValueOnce(new ApiError(412, 'Synthetic concurrent decision', 'REVIEW_REVISION_MISMATCH'))
  const hook = renderHook(() => useReview(workspace, false, port))
  await waitFor(() => expect(hook.result.current.ready).toBe(true))
  await act(() => hook.result.current.read(machineReceipt.id))
  const body = { expected_revision: 1, candidate_sha256: reviewCandidate.candidate_sha256, mathematical: 'REJECTED' as const, sources: 'REJECTED' as const, reason: 'Synthetic explicit rejection', evidence_artifact_ids: [] }
  await act(() => hook.result.current.decide(body))
  expect(hook.result.current.receipt).toBeNull()
  const command = hook.result.current.commands[0]
  expect(command.body).toEqual(body); expect(command.rejection?.status).toBe(412)
  await act(() => hook.result.current.decide(body))
  expect(port.decide).toHaveBeenCalledTimes(1)
  expect(readReviewCommand((await reviewCommandStore.load(workspace))[command.command_id], workspace).body).toEqual(body)
})

test('learner can recover and cancel safe known review work without reading academic commands', async () => {
  const { workspace, port } = fixture()
  vi.mocked(port.session).mockResolvedValue({ ...reviewSession(workspace), role: 'learner' })
  vi.mocked(port.job).mockResolvedValue({ ...safeReviewJob(workspace), status: 'queued', revision: 1 })
  await rememberReviewJob(workspace, machineReceipt.id)
  const privateLoad = vi.spyOn(reviewCommandStore, 'load')
  const hook = renderHook(() => useReview(workspace, true, port))
  await waitFor(() => expect(hook.result.current.controlsReady && !hook.result.current.busy).toBe(true))
  await act(() => hook.result.current.selectJob(machineReceipt.id))
  await act(() => hook.result.current.cancel())
  expect(port.cancel).toHaveBeenCalledTimes(1)
  expect(privateLoad).not.toHaveBeenCalled(); expect(port.read).not.toHaveBeenCalled()
  expect(Object.keys(await reviewControlStore.load(workspace))).toHaveLength(1)
})

test('an unknown old-page cancel never prevents a new explicit current-Job cancellation', async () => {
  const { workspace, port } = fixture()
  const original = makeReviewCommand(workspace, getSessionGeneration(), { kind: 'cancel', review_id: machineReceipt.id, body: { expected_revision: 1 } })
  original.origin.page_id = 'page_closed_before_cancel_delivery'
  await persistReviewCommand(original); await rememberReviewJob(workspace, machineReceipt.id)
  vi.mocked(port.session).mockResolvedValue({ ...reviewSession(workspace), role: 'learner' })
  vi.mocked(port.job).mockResolvedValue({ ...safeReviewJob(workspace), status: 'running', revision: 2 })
  const hook = renderHook(() => useReview(workspace, true, port))
  await waitFor(() => expect(hook.result.current.controlsReady && !hook.result.current.busy).toBe(true))
  await act(() => hook.result.current.selectJob(machineReceipt.id))
  await act(() => hook.result.current.execute(original))
  expect(port.cancel).not.toHaveBeenCalled()
  await act(() => hook.result.current.cancel())
  expect(port.cancel).toHaveBeenCalledTimes(1)
  const [id, body, key] = vi.mocked(port.cancel).mock.calls[0]
  expect(id).toBe(machineReceipt.id); expect(body).toEqual({ expected_revision: 2 }); expect(key).not.toBe(original.command_id)
  const retained = await reviewControlStore.load(workspace)
  expect(readReviewCommand(retained[original.command_id], workspace)).toEqual(original)
  const current = readReviewCommand(retained[key], workspace)
  expect(current.kind === 'cancel' && current.ack?.status).toBe('cancelled')
})
