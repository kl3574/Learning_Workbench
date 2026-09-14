import { act, cleanup, renderHook, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { IDBFactory } from 'fake-indexeddb'
import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'
import { DraftStorageError, DraftStore, type DraftRecord } from '../../workbench/DraftStore'
import type { Note } from '../../../../../packages/contracts/generated/types'

const binding = vi.hoisted(() => ({ store: null as DraftStore | null }))
vi.mock('./noteDrafts', async original => {
  const actual = await original<typeof import('./noteDrafts')>()
  return { ...actual, noteDraftStore: {
    load: (...args: Parameters<DraftStore['load']>) => binding.store!.load(...args),
    save: (...args: Parameters<DraftStore['save']>) => binding.store!.save(...args),
    subscribe: (...args: Parameters<DraftStore['subscribe']>) => binding.store!.subscribe(...args),
  } }
})
import { decodeNoteEnvelope, type NoteEnvelope } from './noteDrafts'
import { useNoteDrafts } from './useNoteDrafts'

let workspace: string
let store: DraftStore
let factory: IDBFactory
let name: string
const opened: DraftStore[] = []

beforeEach(async () => {
  factory = new IDBFactory(); name = 'note-hook-' + crypto.randomUUID()
  store = new DraftStore({ name, factory }); opened.push(store); binding.store = store
  workspace = 'workspace_' + crypto.randomUUID().replaceAll('-', '')
  await store.load(workspace)
})
afterEach(async () => { cleanup(); vi.restoreAllMocks(); await Promise.all(opened.splice(0).map(value => value.close())) })

function envelope(text: string, id = 'note_local', scope = workspace): NoteEnvelope {
  return { version: 1, base_ref: null, base_note: null, creation_key: `create-${id}`, candidate: {
    schema_version: '3.0.0', entity: 'note', id, revision: 1, workspace_id: scope, markdown: text, anchor_state: 'exact',
    anchor: { ref: { entity: 'block', id: 'block_synthetic', revision: 3, sha256: 'a'.repeat(64) }, exact_quote: '🧠é', start_codepoint: 2, end_codepoint: 5, prefix: '甲乙', suffix: '丙' },
  } }
}
const allTexts = (record: DraftRecord) => [record.text, ...record.conflicts.map(item => item.text)]
const markdowns = (record: DraftRecord) => allTexts(record).map(text => decodeNoteEnvelope(text, workspace).candidate.markdown)
async function mount(scope = workspace) {
  const hook = renderHook(({ id }) => useNoteDrafts(id), { initialProps: { id: scope } })
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 10)) })
  return hook
}
async function settle(hook: Awaited<ReturnType<typeof mount>>) {
  await waitFor(() => expect(hook.result.current.saving).toBe(false))
  await act(async () => { await new Promise(resolve => setTimeout(resolve, 10)) })
}
function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>(yes => { resolve = yes })
  return { promise, resolve }
}
function canonical(value: unknown): string {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']'
  if (value !== null && typeof value === 'object') return '{' + Object.entries(value).sort(([a], [b]) => a < b ? -1 : a > b ? 1 : 0).map(([key, item]) => JSON.stringify(key) + ':' + canonical(item)).join(',') + '}'
  return JSON.stringify(value)
}

describe('note draft hook against real IndexedDB transactions', () => {
  it('serializes rapid edits of several notes without self-conflicts or dropping another note', async () => {
    const hook = await mount()
    act(() => {
      hook.result.current.save(envelope('first'))
      hook.result.current.save(envelope('other', 'note_other'))
      hook.result.current.save(envelope('second'))
      hook.result.current.save(envelope('latest 🧠 é'))
    })
    expect(hook.result.current.saving).toBe(true)
    await settle(hook)
    const records = await store.load(workspace)
    expect(markdowns(records['note:note_local'])).toEqual(['latest 🧠 é'])
    expect(records['note:note_local'].revision).toBe(3)
    expect(markdowns(records['note:note_other'])).toEqual(['other'])
    expect(hook.result.current.unsafe).toBe(false)
  })

  it('keeps both pages candidates on the same note and preserves each pages dirty display', async () => {
    const a = await mount(), b = await mount()
    act(() => { a.result.current.save(envelope('page A')); b.result.current.save(envelope('page B')) })
    await settle(a); await settle(b)
    const record = (await store.load(workspace))['note:note_local']
    expect(new Set(markdowns(record))).toEqual(new Set(['page A', 'page B']))
    expect(decodeNoteEnvelope(a.result.current.records['note:note_local'].text, workspace).candidate.markdown).toBe('page A')
    expect(decodeNoteEnvelope(b.result.current.records['note:note_local'].text, workspace).candidate.markdown).toBe('page B')
    act(() => { b.result.current.save(envelope('page B newer')) })
    await settle(b)
    expect(new Set(markdowns((await store.load(workspace))['note:note_local']))).toEqual(new Set(['page A', 'page B', 'page B newer']))
  })

  it('retains an already dirty local draft when a later storage notification replaces the primary', async () => {
    await store.save(workspace, 'note:note_local', JSON.stringify(envelope('local unsent')), 0)
    const hook = await mount()
    await act(async () => { await store.save(workspace, 'note:note_local', JSON.stringify(envelope('other page version')), 1) })
    await waitFor(async () => expect(new Set(markdowns((await store.load(workspace))['note:note_local']))).toEqual(new Set(['local unsent', 'other page version'])))
    expect(decodeNoteEnvelope(hook.result.current.records['note:note_local'].text, workspace).candidate.markdown).toBe('local unsent')
  })

  it('keeps quota-failed text in memory, protects unload, and clears unsafe only after a real retry', async () => {
    const hook = await mount()
    vi.spyOn(store, 'save').mockRejectedValueOnce(new DraftStorageError('QUOTA_EXCEEDED'))
    act(() => hook.result.current.save(envelope('quota candidate')))
    await settle(hook)
    expect(hook.result.current.unsafe).toBe(true)
    expect(hook.result.current.error).toContain('空间不足')
    expect(decodeNoteEnvelope(hook.result.current.records['note:note_local'].text, workspace).candidate.markdown).toBe('quota candidate')
    expect(await store.load(workspace)).toEqual({})
    const event = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
    act(() => hook.result.current.save(envelope('quota candidate')))
    await settle(hook)
    expect(hook.result.current.unsafe).toBe(false)
    expect(hook.result.current.error).toBe('')
    expect(markdowns((await store.load(workspace))['note:note_local'])).toEqual(['quota candidate'])
  })

  it('preserves failed text through a React unmount and recovers it into durable storage', async () => {
    const first = await mount()
    vi.spyOn(store, 'save').mockRejectedValueOnce(new DraftStorageError('OPEN_FAILED'))
    act(() => first.result.current.save(envelope('survive panel unmount')))
    await settle(first); expect(first.result.current.unsafe).toBe(true); first.unmount()
    const reopened = await mount()
    await waitFor(async () => expect(markdowns((await store.load(workspace))['note:note_local'])).toContain('survive panel unmount'))
    await settle(reopened)
    expect(reopened.result.current.unsafe).toBe(false)
  })

  it('does not replace dirty memory after a quota failure and an external save', async () => {
    const hook = await mount()
    vi.spyOn(store, 'save').mockRejectedValueOnce(new DraftStorageError('QUOTA_EXCEEDED'))
    act(() => hook.result.current.save(envelope('memory branch')))
    await settle(hook)
    await act(async () => { await store.save(workspace, 'note:note_local', JSON.stringify(envelope('external branch')), 0) })
    await waitFor(async () => expect(new Set(markdowns((await store.load(workspace))['note:note_local']))).toEqual(new Set(['memory branch', 'external branch'])))
    expect(decodeNoteEnvelope(hook.result.current.records['note:note_local'].text, workspace).candidate.markdown).toBe('memory branch')
    await settle(hook); expect(hook.result.current.unsafe).toBe(false)
  })

  it('leaves corrupt cached envelopes intact and displays a recovery error', async () => {
    await store.save(workspace, 'note:note_local', '{"invalid":"SYNTHETIC"}', 0)
    const hook = await mount()
    expect(hook.result.current.error).not.toBe('')
    expect(hook.result.current.records['note:note_local'].text).toBe('{"invalid":"SYNTHETIC"}')
    act(() => hook.result.current.save(envelope('valid memory candidate')))
    await settle(hook)
    const actual = (await store.load(workspace))['note:note_local']
    expect(actual.text).toBe('{"invalid":"SYNTHETIC"}')
    expect(actual.conflicts).toHaveLength(1)
    await act(async () => { await expect(hook.result.current.resolve('note:note_local', JSON.stringify(envelope('valid memory candidate')))).rejects.toThrow() })
    expect((await store.load(workspace))['note:note_local'].text).toBe('{"invalid":"SYNTHETIC"}')
  })

  it('uses the actual local CAS revision while preserving a distinct formal base ref', async () => {
    const base: Note = { ...envelope('server').candidate, revision: 11 }
    const hash = bytesToHex(sha256(new TextEncoder().encode(canonical(base))))
    const value: NoteEnvelope = { ...envelope('local'), base_ref: { entity: 'note', id: base.id, revision: 11, sha256: hash }, base_note: base, candidate: { ...base, markdown: 'local' } }
    const hook = await mount()
    act(() => hook.result.current.save(value)); await settle(hook)
    const actual = (await store.load(workspace))['note:note_local']
    expect(actual.revision).toBe(1)
    expect(decodeNoteEnvelope(actual.text, workspace).base_ref).toEqual(value.base_ref)
  })

  it('preserves candidates based on different formal revisions under the same note key', async () => {
    const candidate = (revision: number): NoteEnvelope => {
      const base: Note = { ...envelope('server ' + revision).candidate, revision }
      const hash = bytesToHex(sha256(new TextEncoder().encode(canonical(base))))
      return { ...envelope('local ' + revision), base_ref: { entity: 'note', id: base.id, revision, sha256: hash }, base_note: base, candidate: { ...base, markdown: 'local ' + revision } }
    }
    const a = await mount(), b = await mount()
    act(() => { a.result.current.save(candidate(11)); b.result.current.save(candidate(12)) })
    await settle(a); await settle(b)
    const values = allTexts((await store.load(workspace))['note:note_local']).map(text => decodeNoteEnvelope(text, workspace))
    expect(new Set(values.map(value => value.base_ref?.revision))).toEqual(new Set([11, 12]))
    expect(new Set(values.map(value => value.candidate.markdown))).toEqual(new Set(['local 11', 'local 12']))
  })

  it('handles a real IndexedDB put quota exception without changing durable text', async () => {
    await store.save(workspace, 'note:note_local', JSON.stringify(envelope('durable before quota')), 0)
    const database = await new Promise<IDBDatabase>((resolve, reject) => { const request = factory.open(name); request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error) })
    const prototype: IDBObjectStore = Object.getPrototypeOf(database.transaction('drafts').objectStore('drafts'))
    const hook = await mount()
    vi.spyOn(prototype, 'put').mockImplementationOnce(() => { throw new DOMException('synthetic quota', 'QuotaExceededError') })
    act(() => hook.result.current.save(envelope('actual quota candidate')))
    await settle(hook)
    expect(hook.result.current.error).toContain('空间不足')
    expect(hook.result.current.unsafe).toBe(true)
    expect(markdowns((await store.load(workspace))['note:note_local'])).toEqual(['durable before quota'])
    act(() => hook.result.current.save(envelope('actual quota candidate')))
    await settle(hook)
    expect(hook.result.current.unsafe).toBe(false)
    expect(markdowns((await store.load(workspace))['note:note_local'])).toEqual(['actual quota candidate'])
    database.close()
  })

  it('explicitly resolves seen candidates with the persisted revision and retains newly arrived conflicts', async () => {
    await store.save(workspace, 'note:note_local', JSON.stringify(envelope('primary')), 0)
    await store.save(workspace, 'note:note_local', JSON.stringify(envelope('chosen')), 0)
    const hook = await mount(), key = 'note:note_local', chosen = JSON.stringify(envelope('chosen'))
    const actualSave = store.save.bind(store)
    let inserted = false
    vi.spyOn(store, 'load').mockImplementation(async scope => {
      if (!inserted) { inserted = true; await actualSave(scope, key, JSON.stringify(envelope('unseen')), 0) }
      // A separate reader avoids recursive invocation of this spy.
      const reader = new DraftStore({ factory, name }); opened.push(reader)
      return reader.load(scope)
    })
    let result: NoteEnvelope | undefined
    await act(async () => { result = await hook.result.current.resolve(key, chosen) })
    expect(result?.candidate.markdown).toBe('chosen')
    const record = (await store.load(workspace))[key]
    expect(decodeNoteEnvelope(record.text, workspace).candidate.markdown).toBe('chosen')
    expect(record.conflicts.map(item => decodeNoteEnvelope(item.text, workspace).candidate.markdown)).toContain('unseen')
    expect(record.conflicts.map(item => decodeNoteEnvelope(item.text, workspace).candidate.markdown)).not.toContain('chosen')
  })

  it('refuses to overwrite an unseen replacement primary during explicit resolution', async () => {
    await store.save(workspace, 'note:note_local', JSON.stringify(envelope('seen primary')), 0)
    await store.save(workspace, 'note:note_local', JSON.stringify(envelope('chosen')), 0)
    const hook = await mount(), key = 'note:note_local'
    const realLoad = store.load.bind(store), realSave = store.save.bind(store)
    vi.spyOn(store, 'load').mockImplementationOnce(async scope => { await realSave(scope, key, JSON.stringify(envelope('unseen primary')), 1); return realLoad(scope) })
    await act(async () => { await expect(hook.result.current.resolve(key, JSON.stringify(envelope('chosen')))).rejects.toThrow('重新比较') })
    expect(markdowns((await store.load(workspace))[key])).toContain('unseen primary')
  })

  it('ignores a late load from a previous workspace', async () => {
    const other = 'workspace_other_' + crypto.randomUUID().replaceAll('-', '')
    await store.save(other, 'note:note_other', JSON.stringify(envelope('other workspace', 'note_other', other)), 0)
    const gate = deferred<Record<string, DraftRecord>>()
    vi.spyOn(store, 'load').mockImplementationOnce(() => gate.promise)
    const hook = renderHook(({ id }) => useNoteDrafts(id), { initialProps: { id: workspace } })
    hook.rerender({ id: other })
    await waitFor(() => expect(hook.result.current.records['note:note_other']).toBeDefined())
    await act(async () => { gate.resolve({}); await gate.promise })
    expect(Object.keys(hook.result.current.records)).toEqual(['note:note_other'])
  })

  it('does not create a self-conflict when an old refresh finishes after a newer local commit', async () => {
    await store.save(workspace, 'note:note_local', JSON.stringify(envelope('old')), 0)
    const hook = await mount(), stale = await store.load(workspace), gate = deferred<Record<string, DraftRecord>>()
    vi.spyOn(store, 'load').mockImplementationOnce(() => gate.promise)
    act(() => { window.dispatchEvent(new Event('focus')) })
    await act(async () => { await Promise.resolve() })
    act(() => hook.result.current.save(envelope('new local')))
    await waitFor(() => expect(hook.result.current.saving).toBe(false))
    await act(async () => { gate.resolve(stale); await gate.promise })
    await settle(hook)
    expect((await store.load(workspace))['note:note_local'].conflicts).toEqual([])
    expect(hook.result.current.records['note:note_local'].conflicts).toEqual([])
  })

  it('scopes in-flight writes to their original workspace and does not update the new UI epoch', async () => {
    const hook = await mount(), other = 'workspace_other_' + crypto.randomUUID().replaceAll('-', '')
    const gate = deferred<void>(), realSave = store.save.bind(store)
    vi.spyOn(store, 'save').mockImplementationOnce(async (...args) => { await gate.promise; return realSave(...args) })
    act(() => hook.result.current.save(envelope('old workspace candidate')))
    await act(async () => { await Promise.resolve() })
    hook.rerender({ id: other })
    act(() => hook.result.current.save(envelope('new workspace candidate', 'note_other', other)))
    await act(async () => { gate.resolve(); await gate.promise })
    await waitFor(async () => expect((await store.load(workspace))['note:note_local']).toBeDefined())
    await settle(hook)
    expect(Object.keys(hook.result.current.records)).toEqual(['note:note_other'])
    expect(decodeNoteEnvelope((await store.load(workspace))['note:note_local'].text, workspace).candidate.markdown).toBe('old workspace candidate')
  })
})
