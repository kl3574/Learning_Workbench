import 'fake-indexeddb/auto'
import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { expect, test, vi } from 'vitest'
import { DraftStore } from '../workbench/DraftStore'
import { createResponseDraftJournal } from './createResponseDraftJournal'

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
    expect([after.text, ...after.conflicts.map(item => item.text)]).toContain(c)
    expect(view.result.current.unsafe).toBe(true)
  } finally {
    await act(async () => { releaseResolve.release(); releasePreservation.release(); if (pending) await pending })
    await waitFor(() => expect(view.result.current.saving).toBe(false))
    view.unmount(); save.mockRestore(); cleanup(); await store.close(); await other.close()
  }
})

test('explicit selection of another conflict remains protected after a later peer write wins before the resolve ACK', async () => {
  const workspace = 'workspace_resolve_selected_ack', key = 'same_route'
  const store = new DraftStore({ name: 'independent-resolve-selected-ack-v1' })
  const other = new DraftStore({ name: 'independent-resolve-selected-ack-v1' })
  const useJournal = createResponseDraftJournal({ store, decode, key: value => value.key, dirty: value => value.dirty })
  const encode = (text: string) => JSON.stringify({ workspace, key, text, dirty: true })
  const a = encode('synthetic local A'), b = encode('synthetic earlier peer B'), c = encode('synthetic current peer C')
  const first = await store.save(workspace, key, b, 0)
  expect(first.kind).toBe('saved')
  expect((await other.save(workspace, key, a, 0)).kind).toBe('conflict')
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
    expect(view.result.current.records[key].conflicts.map(item => item.text)).toContain(a)
    act(() => { pending = view.result.current.resolve(key, a).catch(error => error as Error) })
    await savedResolve.promise
    const newer = await other.save(workspace, key, c, 2)
    expect(newer.kind).toBe('saved'); expect(newer.record.revision).toBe(3)
    act(() => window.dispatchEvent(new Event('focus')))
    await waitFor(() => expect(view.result.current.records[key].conflicts.map(item => item.text)).toContain(c))
    events.push('hook_observed_peer_r3_before_old_ACK')
    expect(view.result.current.unsafe).toBe(true)
    await act(async () => { releaseResolve.release(); await preservationStarted.promise; await pending })
    const intermediate = view.result.current.records[key]
    events.push(`after_old_ACK_hook_r${intermediate.revision}`)
    // Let the hook finish the queued preservation of the pre-selection branch B.
    // Selecting A was a real resolve command, not a later edit to this branch.
    await act(async () => { releasePreservation.release() })
    await waitFor(() => expect(view.result.current.saving).toBe(false))
    const disk = (await originalLoad(workspace))[key]
    const after = view.result.current.records[key]
    const diskTexts = [disk.text, ...disk.conflicts.map(item => item.text)]
    const hookTexts = [after.text, ...after.conflicts.map(item => item.text)]
    const protectedSelection = diskTexts.includes(a) || hookTexts.includes(a) && view.result.current.unsafe
    expect(diskTexts).toContain(c)
    expect(protectedSelection).toBe(true)
    expect(diskTexts).toEqual(expect.arrayContaining([a, b, c]))
    expect(view.result.current.unsafe).toBe(false)
  } finally {
    await act(async () => { releaseResolve.release(); releasePreservation.release(); if (pending) await pending })
    await waitFor(() => expect(view.result.current.saving).toBe(false))
    view.unmount(); save.mockRestore(); cleanup(); await store.close(); await other.close()
  }
})

test('a selected candidate survives a quota failure, workspace switch and remount until a real retry', async () => {
  const workspace = 'workspace_resolve_selected_quota_ack', key = 'same_route'
  const store = new DraftStore({ name: 'independent-resolve-selected-quota-ack-v1' })
  const other = new DraftStore({ name: 'independent-resolve-selected-quota-ack-v1' })
  const useJournal = createResponseDraftJournal({ store, decode, key: value => value.key, dirty: value => value.dirty })
  const encode = (text: string) => JSON.stringify({ workspace, key, text, dirty: true })
  const a = encode('synthetic local A'), b = encode('synthetic earlier peer B'), c = encode('synthetic current peer C')
  const first = await store.save(workspace, key, b, 0)
  expect(first.kind).toBe('saved')
  expect((await other.save(workspace, key, a, 0)).kind).toBe('conflict')
  const savedResolve = deferred(), releaseResolve = deferred(), preservationStarted = deferred(), releasePreservation = deferred()
  const events: string[] = []
  let quota = true
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
    if (quota && args[2] === a) throw new DOMException('injected selected preservation quota', 'QuotaExceededError')
    return originalSave(...args)
  })
  let view = renderHook(({ currentWorkspace }) => useJournal(currentWorkspace), { initialProps: { currentWorkspace: workspace } })
  let pending: Promise<Envelope | Error> | undefined
  try {
    await waitFor(() => expect(view.result.current.ready).toBe(true))
    expect(view.result.current.records[key].conflicts.map(item => item.text)).toContain(a)
    act(() => { pending = view.result.current.resolve(key, a).catch(error => error as Error) })
    await savedResolve.promise
    const newer = await other.save(workspace, key, c, 2)
    expect(newer.kind).toBe('saved'); expect(newer.record.revision).toBe(3)
    act(() => window.dispatchEvent(new Event('focus')))
    await waitFor(() => expect(view.result.current.records[key].conflicts.map(item => item.text)).toContain(c))
    events.push('hook_observed_peer_r3_before_old_ACK')
    expect(view.result.current.unsafe).toBe(true)
    await act(async () => { releaseResolve.release(); await preservationStarted.promise; await pending })
    const intermediate = view.result.current.records[key]
    events.push(`after_old_ACK_hook_r${intermediate.revision}`)
    // Let the hook finish the queued preservation of the pre-selection branch B.
    // Selecting A was a real resolve command, not a later edit to this branch.
    await act(async () => { releasePreservation.release() })
    await waitFor(() => expect(view.result.current.saving).toBe(false))
    const disk = (await originalLoad(workspace))[key]
    const after = view.result.current.records[key]
    const diskTexts = [disk.text, ...disk.conflicts.map(item => item.text)]
    const hookTexts = [after.text, ...after.conflicts.map(item => item.text)]
    const protectedSelection = diskTexts.includes(a) || hookTexts.includes(a) && view.result.current.unsafe
    expect(diskTexts).toContain(c)
    expect(protectedSelection).toBe(true)
    expect(diskTexts).not.toContain(a)
    expect(hookTexts).toContain(a)
    expect(view.result.current.unsafe).toBe(true)
    const close = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(close); expect(close.defaultPrevented).toBe(true)
    view.rerender({ currentWorkspace: 'workspace_other' })
    await waitFor(() => expect(view.result.current.ready).toBe(true))
    expect(view.result.current.unsafe).toBe(true)
    expect(view.result.current.workspaceUnsafe).toBe(false)
    view.unmount()
    quota = false
    view = renderHook(({ currentWorkspace }) => useJournal(currentWorkspace), { initialProps: { currentWorkspace: workspace } })
    await waitFor(() => expect(view.result.current.ready && !view.result.current.saving && !view.result.current.unsafe).toBe(true))
    const recovered = (await originalLoad(workspace))[key]
    expect([recovered.text, ...recovered.conflicts.map(item => item.text)]).toEqual(expect.arrayContaining([a, b, c]))
  } finally {
    await act(async () => { releaseResolve.release(); releasePreservation.release(); if (pending) await pending })
    await waitFor(() => expect(view.result.current.saving).toBe(false))
    view.unmount(); save.mockRestore(); cleanup(); await store.close(); await other.close()
  }
})

test('a normal explicit choice succeeds when its own real load is consumed before the resolve ACK', async () => {
  const workspace = 'workspace_resolve_own_notification', key = 'same_route', name = 'resolve-own-notification'
  const store = new DraftStore({ name }), other = new DraftStore({ name })
  const useJournal = createResponseDraftJournal({ store, decode, key: value => value.key, dirty: value => value.dirty })
  const a = JSON.stringify({ workspace, key, text: 'explicit chosen A', dirty: true }), b = JSON.stringify({ workspace, key, text: 'previous B', dirty: true })
  await store.save(workspace, key, b, 0); await other.save(workspace, key, a, 0)
  const committed = deferred(), delivery = deferred(), actualSave = store.save.bind(store)
  let preservationCalls = 0
  const save = vi.spyOn(store, 'save').mockImplementation(async (...args) => {
    if (!args[4]?.length) preservationCalls++
    const actual = await actualSave(...args)
    if (args[4]?.length) { committed.release(); await delivery.promise }
    return actual
  })
  const view = renderHook(() => useJournal(workspace))
  let pending: Promise<Envelope | Error> | undefined
  try {
    await waitFor(() => expect(view.result.current.ready).toBe(true))
    act(() => { pending = view.result.current.resolve(key, a).catch(error => error as Error) })
    await committed.promise
    act(() => window.dispatchEvent(new Event('focus')))
    await waitFor(() => expect(view.result.current.records[key].revision).toBe(2))
    let chosen: Envelope | Error | undefined
    await act(async () => { delivery.release(); chosen = await pending })
    await waitFor(() => expect(view.result.current.saving).toBe(false))
    expect(chosen).toEqual(JSON.parse(a))
    expect(preservationCalls).toBe(0)
    expect(view.result.current.unsafe).toBe(false)
    const disk = (await store.load(workspace))[key]
    expect(disk.text).toBe(a); expect(disk.conflicts).toEqual([])
  } finally {
    await act(async () => { delivery.release(); if (pending) await pending })
    await waitFor(() => expect(view.result.current.saving).toBe(false))
    view.unmount(); save.mockRestore(); cleanup(); await store.close(); await other.close()
  }
})
