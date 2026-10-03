import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { IDBFactory } from 'fake-indexeddb'
import type { ContentRef, Note, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import { DraftStore } from '../../workbench/DraftStore'
import { canonical, digest } from '../retrieval/retrievalModel'
import { versions } from '../reader/versionCompare/fixtures'

const binding = vi.hoisted(() => ({ store: null as DraftStore | null }))
vi.mock('./noteDrafts', async original => {
  const actual = await original<typeof import('./noteDrafts')>()
  return { ...actual, noteDraftStore: {
    load: (...args: Parameters<DraftStore['load']>) => binding.store!.load(...args),
    save: (...args: Parameters<DraftStore['save']>) => binding.store!.save(...args),
    subscribe: (...args: Parameters<DraftStore['subscribe']>) => binding.store!.subscribe(...args),
  } }
})
import { decodeNoteEnvelope } from './noteDrafts'
import { NotesPanel } from './NotesPanel'

let store: DraftStore, factory: IDBFactory, name: string, workspace: string
beforeEach(async () => {
  factory = new IDBFactory(); name = 'note-reanchor-' + crypto.randomUUID(); workspace = 'workspace_' + crypto.randomUUID().replaceAll('-', '')
  store = new DraftStore({ name, factory }); binding.store = store; await store.load(workspace)
})
afterEach(async () => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals(); await store.close() })
const deferred = <T,>() => { let resolve!: (value: T) => void; const promise = new Promise<T>(yes => { resolve = yes }); return { promise, resolve } }
async function setup() {
  const old = versions[0], newer = versions[1]
  const note: Note = { schema_version: '3.0.0', entity: 'note', id: 'note_reanchor', workspace_id: workspace, revision: 2, markdown: '已保存的原笔记', anchor_state: 'stale', anchor: { ref: old.ref, exact_quote: old.body, start_codepoint: 0, end_codepoint: Array.from(old.body).length, prefix: '', suffix: '' } }
  const ref: ContentRef = { entity: 'note', id: note.id, revision: 2, sha256: digest(canonical(note)) }
  const session: SessionResponse = { workspace_id: workspace, actor_session_id: 'actor_synthetic', role: 'learner', csrf_token: 'synthetic', active_independent_attempt_id: null, active_open_book_attempt_id: null }
  const response = (url: string) => {
    if (url === '/api/v1/session') return new Response(JSON.stringify(session))
    if (url.startsWith('/api/v1/notes')) return new Response(JSON.stringify({ items: [note], next_cursor: null }))
    if (url.endsWith('/current')) return new Response(JSON.stringify(url.includes(note.id) ? ref : newer.ref))
    if (url.includes('/body?')) return new Response(newer.body, { headers: { ETag: `"${newer.data.block.body_sha256}"` } })
    return new Response(JSON.stringify(newer.data), { headers: { ETag: `"${newer.ref.sha256}"` } })
  }
  const fetch = vi.fn(async (url: string, _init: RequestInit) => response(url)); vi.stubGlobal('fetch', fetch)
  const onState = vi.fn(), props = { workspace, selection: null, openAnchor: vi.fn(), onState, onSaved: vi.fn() }
  const view = render(<NotesPanel {...props} />)
  await waitFor(() => expect((screen.getByRole('button', { name: /已保存的原笔记/ }) as HTMLButtonElement).disabled).toBe(false))
  fireEvent.click(screen.getByRole('button', { name: /已保存的原笔记/ })); await screen.findByLabelText('笔记正文')
  return { note, ref, session, response, fetch, onState, props, ...view }
}
async function selectNewSource() {
  fireEvent.click(screen.getByRole('button', { name: '读取此块当前修订以手工重锚' }))
  const input = await screen.findByLabelText('当前准确修订的完整原文') as HTMLTextAreaElement
  input.focus(); input.setSelectionRange(0, input.value.length); fireEvent.select(input)
  await waitFor(() => expect((screen.getByRole('button', { name: '将这份准确新选文采用到本机笔记' }) as HTMLButtonElement).disabled).toBe(false))
}
async function localCandidate() { return decodeNoteEnvelope((await store.load(workspace))['note:note_reanchor'].text, workspace) }

test('fresh adoption preserves text typed while permission is pending and persists the entire new anchor through remount without a server write', async () => {
  const f = await setup(); await selectNewSource()
  const gate = deferred<Response>(); f.fetch.mockReturnValueOnce(gate.promise)
  fireEvent.click(screen.getByRole('button', { name: '将这份准确新选文采用到本机笔记' }))
  const latest = '等待权限时的新笔记 🧠 e\u0301\n$\\alpha$ 保持原样'
  fireEvent.change(screen.getByLabelText('笔记正文'), { target: { value: latest } })
  await waitFor(async () => expect((await localCandidate()).candidate.markdown).toBe(latest))
  await waitFor(() => expect(f.onState).toHaveBeenLastCalledWith({ dirty: true, safe: true }))
  await act(async () => { gate.resolve(f.response('/api/v1/session')); await gate.promise })
  await waitFor(async () => expect((await localCandidate()).candidate.anchor.ref).toEqual(versions[1].ref))
  const saved = await localCandidate()
  expect(saved).toMatchObject({ base_ref: f.ref, base_note: f.note, candidate: { markdown: latest, anchor_state: 'exact', anchor: { ref: versions[1].ref, exact_quote: versions[1].body } } })
  expect((screen.getByLabelText('笔记正文') as HTMLTextAreaElement).value).toBe(latest)
  f.unmount(); render(<NotesPanel {...f.props} />)
  fireEvent.click(await screen.findByRole('button', { name: /恢复本机笔记草稿/ }))
  await waitFor(() => expect((screen.getByLabelText('笔记正文') as HTMLTextAreaElement).value).toBe(latest))
  expect(screen.getByText(/锚点：block_compare · 修订 2 · exact/)).toBeTruthy()
  expect(f.fetch.mock.calls.every(([, init]) => init.method === 'GET')).toBe(true)
})

test('an actual IndexedDB quota failure retains adopted anchor plus unsaved text, marks close unsafe, and recovers both after unmount', async () => {
  const f = await setup(), latest = '未发送正文 🧠 e\u0301\n第二行'
  fireEvent.change(screen.getByLabelText('笔记正文'), { target: { value: latest } })
  await waitFor(() => expect(f.onState).toHaveBeenLastCalledWith({ dirty: true, safe: true })); await selectNewSource()
  const database = await new Promise<IDBDatabase>((resolve, reject) => { const request = factory.open(name); request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error) })
  const prototype: IDBObjectStore = Object.getPrototypeOf(database.transaction('drafts').objectStore('drafts'))
  vi.spyOn(prototype, 'put').mockImplementationOnce(() => { throw new DOMException('synthetic quota', 'QuotaExceededError') })
  fireEvent.click(screen.getByRole('button', { name: '将这份准确新选文采用到本机笔记' }))
  await screen.findByText(/本机笔记草稿尚未保存/)
  expect((screen.getByLabelText('笔记正文') as HTMLTextAreaElement).value).toBe(latest); expect(screen.getByText(/锚点：block_compare · 修订 2 · exact/)).toBeTruthy()
  expect(f.onState).toHaveBeenLastCalledWith({ dirty: true, safe: false })
  expect((await localCandidate()).candidate.anchor.ref).toEqual(versions[0].ref)
  const unload = new Event('beforeunload', { cancelable: true }); window.dispatchEvent(unload); expect(unload.defaultPrevented).toBe(true)
  f.unmount(); render(<NotesPanel {...f.props} />)
  await waitFor(async () => {
    const record = (await store.load(workspace))['note:note_reanchor']
    expect([record.text, ...record.conflicts.map(item => item.text)].map(text => decodeNoteEnvelope(text, workspace).candidate.anchor.ref)).toContainEqual(versions[1].ref)
  })
  fireEvent.click(await screen.findByRole('button', { name: /恢复本机笔记草稿/ }))
  await waitFor(() => expect((screen.getByLabelText('笔记正文') as HTMLTextAreaElement).value).toBe(latest))
  expect(screen.getByText(/锚点：block_compare · 修订 2 · exact/)).toBeTruthy()
  expect(screen.getByRole('heading', { name: '本机草稿版本冲突' })).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '采用本机候选 1' }))
  await waitFor(async () => expect((await localCandidate()).candidate.anchor.ref).toEqual(versions[1].ref))
  expect((await localCandidate()).candidate.anchor.exact_quote).toBe(versions[1].body)
  expect(f.fetch.mock.calls.every(([, init]) => init.method === 'GET')).toBe(true); database.close()
})
