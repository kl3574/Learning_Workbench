import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { DraftStore } from './source/workbench/DraftStore'
import { createResponseDraftJournal } from './source/shared/createResponseDraftJournal'

type Envelope = { workspace: string; key: string; text: string; dirty: boolean }
function deferred() { let release!: () => void; const promise = new Promise<void>(done => { release = done }); return { promise, release } }
function decode(raw: string, workspace: string): Envelope {
  const value: unknown = JSON.parse(raw)
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('Invalid synthetic envelope')
  const row = value as Record<string, unknown>
  if (Object.keys(row).sort().join(',') !== 'dirty,key,text,workspace' || row.workspace !== workspace || typeof row.key !== 'string' || typeof row.text !== 'string' || typeof row.dirty !== 'boolean') throw new Error('Wrong synthetic envelope identity')
  return row as Envelope
}

test('an old resolve ACK cannot remove an already observed peer candidate while its preservation write waits', async () => {
  const workspace = 'workspace_resolve_late_ack', key = 'same_route'
  const store = new DraftStore({ name: 'independent-resolve-ack-v1' })
  const other = new DraftStore({ name: 'independent-resolve-ack-v1' })
  const useJournal = createResponseDraftJournal({ store, decode, key: value => value.key, dirty: value => value.dirty })
  const encode = (text: string) => JSON.stringify({ workspace, key, text, dirty: true })
  const a = encode('synthetic local A'), b = encode('synthetic earlier peer B'), c = encode('synthetic current peer C')
  const first = await store.save(workspace, key, a, 0)
  expect(first.kind).toBe('saved')
  expect((await other.save(workspace, key, b, 0)).kind).toBe('conflict')
  const savedResolve = deferred(), releaseResolve = deferred(), preservationStarted = deferred(), releasePreservation = deferred()
  const events: string[] = []
  const originalSave = store.save.bind(store), originalLoad = store.load.bind(store)
  const save = vi.spyOn(store, 'save').mockImplementation(async (...args) => {
    if (args[4]?.length) {
      const actual = await originalSave(...args)
      expect(actual.record.revision).toBe(2)
      events.push('resolve_r2_committed_ACK_held'); savedResolve.release()
      await releaseResolve.promise
      events.push('resolve_r2_ACK_returned'); return actual
    }
    events.push('preservation_write_started_and_held'); preservationStarted.release()
    await releasePreservation.promise
    return originalSave(...args)
  })
  const view = renderHook(() => useJournal(workspace))
  let pending: Promise<Envelope | Error> | undefined
  try {
    await waitFor(() => expect(view.result.current.ready).toBe(true))
    expect(view.result.current.records[key].conflicts.map(item => item.text)).toContain(b)
    act(() => { pending = view.result.current.resolve(key, a).catch(error => error as Error) })
    await savedResolve.promise
    const newer = await other.save(workspace, key, c, 2)
    expect(newer.kind).toBe('saved'); expect(newer.record.revision).toBe(3)
    act(() => window.dispatchEvent(new Event('focus')))
    await waitFor(() => expect(view.result.current.records[key].conflicts.map(item => item.text)).toContain(c))
    events.push('hook_observed_peer_r3_before_old_ACK')
    expect(view.result.current.unsafe).toBe(true)
    await act(async () => { releaseResolve.release(); await preservationStarted.promise; await pending })
    // Starting the queued preservation call proves the earlier resolve ACK was
    // consumed. Disk remains real r3 C because this next write has not executed.
    const disk = (await originalLoad(workspace))[key]
    expect(disk.revision).toBe(3); expect(disk.text).toBe(c)
    const after = view.result.current.records[key]
    console.log(JSON.stringify({ events, disk_revision: disk.revision, disk_has_current_peer: disk.text === c, hook_revision: after.revision, hook_retains_peer: [after.text, ...after.conflicts.map(item => item.text)].includes(c), unsafe: view.result.current.unsafe }))
    expect([after.text, ...after.conflicts.map(item => item.text)]).toContain(c)
    expect(view.result.current.unsafe).toBe(true)
  } finally {
    await act(async () => { releaseResolve.release(); releasePreservation.release(); if (pending) await pending })
    await waitFor(() => expect(view.result.current.saving).toBe(false))
    view.unmount(); save.mockRestore(); cleanup(); await store.close(); await other.close()
  }
})
