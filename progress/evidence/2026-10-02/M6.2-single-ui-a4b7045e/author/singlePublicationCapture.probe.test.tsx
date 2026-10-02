// Private acceptance capture probe; not included in delivered production/tests.
import 'fake-indexeddb/auto'
import { writeFile } from 'node:fs/promises'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { singlePublicationFixture } from './singlePublicationFixtures'
import { singlePublicationClient } from './singlePublicationClient'
import { useSinglePublication } from './useSinglePublication'
import { singlePublicationCommandStore } from './singlePublicationCommands'
test('capture controlled UI transport only, with no claim of physical execution or SQLite publication', async () => {
  const f = singlePublicationFixture(), requests: { method: string; path: string; body: unknown; status: number; response: unknown }[] = []
  let published = false
  vi.stubGlobal('fetch', vi.fn(async (path: string, init: RequestInit) => {
    let value: unknown, status = 200
    if (path === '/api/v1/session') return new Response(JSON.stringify(f.session))
    if (path === `/api/v1/authoring/drafts/${f.draft.candidate.draft_id}`) value = published ? { ...f.draft, state: 'published', published_ref: f.ack } : f.draft
    else if (path === `/api/v1/authoring/jobs/${f.draft.source_job_id}`) value = f.generation
    else if (path === `/api/v1/authoring/numeric-checks/${f.numeric.id}`) value = f.numeric
    else if (path === `/api/v1/reviews/${f.receipt.id}`) value = f.receipt
    else if (path === `/api/v1/drafts/${f.draft.candidate.draft_id}/publish`) { published = true; value = f.ack; status = 201 }
    else if (path === `/api/v1/objects/${f.ack.id}/current`) value = { ...f.ack, revision: 2, sha256: '3'.repeat(64) }
    else throw new Error('Unexpected route')
    requests.push({ method: init.method!, path, body: init.body ? JSON.parse(init.body as string) : null, status, response: structuredClone(value) })
    return new Response(JSON.stringify(value), { status })
  }))
  const hook = renderHook(() => useSinglePublication(f.workspace, false, 'capture', singlePublicationClient, f.draft.candidate.draft_id))
  await waitFor(() => expect(hook.result.current.ready).toBe(true)); await act(() => hook.result.current.prepare(f.draft, f.receipt)); expect(hook.result.current.basis).not.toBeNull()
  await act(() => hook.result.current.publish([0, 1])); const command = hook.result.current.commands[0]; expect(command.ack).toEqual(f.ack)
  expect(hook.result.current.publicationRead).toBeNull(); expect(hook.result.current.currentRead).toBeNull()
  await act(() => hook.result.current.readPublication(f.draft.candidate, f.ack)); await act(() => hook.result.current.readCurrent(command))
  expect(hook.result.current.publicationRead?.published_ref).toEqual(f.ack); expect(hook.result.current.currentRead?.ref.revision).toBe(2)
  expect(requests.filter(row => row.method === 'POST')).toHaveLength(1)
  const evidence = { schema_version: 1, scope: 'controlled UI fixture transport; synthetic responses; real frontend hook/client and fake IndexedDB', status: 'PASS',
    limits: { backend_sqlite: 'NOT_RUN', physical_numeric_runtime: 'NOT_RUN', human_content_quality: 'NOT_RUN', native_browser: 'NOT_RUN' },
    generation_job: f.generation.summary, numeric_job: f.numeric.job, numeric_result: f.numeric.result, review: f.receipt,
    request_results: requests, original_ack: command.ack, independent_publication_get: hook.result.current.publicationRead, current_get: hook.result.current.currentRead?.ref }
  await writeFile('$HOME/.cache/learning-workbench-acceptance/m62-single-publication-ui-evidence-oct02/single-publication-actual.json', JSON.stringify(evidence, null, 2) + '\n')
  cleanup(); vi.unstubAllGlobals(); await singlePublicationCommandStore.close()
})
