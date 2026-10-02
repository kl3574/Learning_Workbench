import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import type { SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import { request } from '../../api/client'
import { digest } from '../retrieval/retrievalModel'
import { versions } from '../reader/versionCompare/fixtures'
import { NoteReanchor } from './NoteReanchor'

afterEach(() => { cleanup(); vi.useRealTimers(); vi.unstubAllGlobals() })
const deferred = <T,>() => { let resolve!: (value: T) => void; const promise = new Promise<T>(yes => { resolve = yes }); return { promise, resolve } }
const raw = '🧠 前缀\r\ne\u0301 target\r\n后缀'
function setup(role: SessionResponse['role'] = 'learner', openBook = false) {
  const session: SessionResponse = { workspace_id: 'workspace_notes', actor_session_id: 'actor_notes', role, csrf_token: 'synthetic-session', active_independent_attempt_id: null, active_open_book_attempt_id: openBook ? 'attempt_open' : null }
  const value = structuredClone(versions[1]), hash = digest(raw); value.body = raw; value.data.block.body_sha256 = hash
  const calls: { path: string; method: string }[] = []
  const response = (url: string) => {
    if (url === '/api/v1/session') return new Response(JSON.stringify(session))
    if (url.endsWith('/current')) return new Response(JSON.stringify(value.ref))
    if (url.includes('/body?')) return new Response(value.body, { headers: { ETag: `"${hash}"` } })
    return new Response(JSON.stringify(value.data), { headers: { ETag: `"${value.ref.sha256}"` } })
  }
  const fetch = vi.fn(async (url: string, init: RequestInit) => { calls.push({ path: url, method: init.method! }); return response(url) }); vi.stubGlobal('fetch', fetch)
  const adopt = vi.fn(), props = { workspace: session.workspace_id, noteId: 'note_original', original: versions[0].ref, disabled: false, adopt }
  const view = render(<NoteReanchor {...props} />)
  return { session, value, calls, fetch, response, adopt, props, ...view }
}
async function read() { fireEvent.click(screen.getByRole('button', { name: '读取此块当前修订以手工重锚' })); return screen.findByLabelText('当前准确修订的完整原文') as Promise<HTMLTextAreaElement> }
function select(input: HTMLTextAreaElement) { input.focus(); const start = input.value.indexOf('target'); input.setSelectionRange(start, start + 6); fireEvent.select(input) }
test.each([['learner', false], ['author', false], ['learner', true]] as const)('explicit %s/open-book=%s exact source selection and local adoption never writes or changes parent references', async (role, openBook) => {
  const f = setup(role, openBook); expect(f.fetch).not.toHaveBeenCalled()
  const input = await read(); expect(input.value).toBe(raw.replaceAll('\r\n', '\n')); select(input)
  expect(f.adopt).not.toHaveBeenCalled(); fireEvent.click(screen.getByRole('button', { name: '将这份准确新选文采用到本机笔记' }))
  await waitFor(() => expect(f.adopt).toHaveBeenCalledWith({ ref: f.value.ref, exact_quote: 'target', prefix: '🧠 前缀\r\ne\u0301 ', suffix: '\r\n后缀', start_codepoint: 9, end_codepoint: 15 }))
  expect(f.calls.every(call => call.method === 'GET')).toBe(true); expect(f.calls.filter(call => call.path === '/api/v1/session')).toHaveLength(3)
})
test.each(['independent', 'workspace', 'unknown', 'malformed'] as const)('unconfirmed or denied %s session cannot read current metadata or text', async fault => {
  const f = setup()
  if (fault === 'independent') f.session.active_independent_attempt_id = 'attempt_locked'
  if (fault === 'workspace') f.session.workspace_id = 'workspace_other'
  if (fault === 'unknown') f.fetch.mockRejectedValueOnce(new TypeError('offline'))
  if (fault === 'malformed') f.fetch.mockResolvedValueOnce(new Response('{}'))
  fireEvent.click(screen.getByRole('button', { name: '读取此块当前修订以手工重锚' })); await screen.findByRole('alert')
  expect(f.calls.every(call => call.path === '/api/v1/session')).toBe(true); expect(screen.queryByLabelText('当前准确修订的完整原文')).toBeNull(); expect(f.adopt).not.toHaveBeenCalled()
})
test.each(['body', 'metadata', 'foreign_ref', 'actor_after_read'] as const)('bad %s cannot be shown or adopted as a verified new anchor', async fault => {
  const f = setup(); let sessions = 0
  f.fetch.mockImplementation(async (url, init) => {
    f.calls.push({ path: url, method: init.method! })
    if (fault === 'body' && url.includes('/body?')) return new Response('damaged source', { headers: { ETag: `"${digest(raw)}"` } })
    if (fault === 'metadata' && url.includes('/blocks/') && !url.includes('/body?')) return new Response(JSON.stringify(f.value.data), { headers: { ETag: '"wrong"' } })
    if (fault === 'foreign_ref' && url.endsWith('/current')) return new Response(JSON.stringify({ ...f.value.ref, id: 'block_foreign' }))
    if (fault === 'actor_after_read' && url === '/api/v1/session' && ++sessions > 1) return new Response(JSON.stringify({ ...f.session, actor_session_id: 'another_actor' }))
    return f.response(url)
  })
  fireEvent.click(screen.getByRole('button', { name: '读取此块当前修订以手工重锚' })); await screen.findByRole('alert')
  expect(screen.queryByLabelText('当前准确修订的完整原文')).toBeNull(); expect(f.adopt).not.toHaveBeenCalled()
})
test.each(['current', 'body'] as const)('late %s response is hidden across Note/workspace/access/unmount boundaries', async stage => {
  for (const change of ['note', 'workspace', 'access', 'unmount'] as const) {
    const f = setup(), gate = deferred<Response>()
    f.fetch.mockImplementation(async (url, init) => { f.calls.push({ path: url, method: init.method! }); return stage === 'current' ? url.endsWith('/current') ? gate.promise : f.response(url) : url.includes('/body?') ? gate.promise : f.response(url) })
    fireEvent.click(screen.getByRole('button', { name: '读取此块当前修订以手工重锚' }))
    await waitFor(() => expect(f.calls.some(call => stage === 'current' ? call.path.endsWith('/current') : call.path.includes('/body?'))).toBe(true))
    if (change === 'note') f.rerender(<NoteReanchor {...f.props} noteId="note_other" />)
    else if (change === 'workspace') f.rerender(<NoteReanchor {...f.props} workspace="workspace_other" />)
    else if (change === 'access') await act(() => request('POST /api/v1/session/role', { role: 'author' }, { 'Idempotency-Key': 'synthetic_access_change' }))
    else f.unmount()
    await act(async () => { gate.resolve(f.response(stage === 'current' ? '/current' : '/body?')); await Promise.resolve() })
    expect(screen.queryByLabelText('当前准确修订的完整原文')).toBeNull(); expect(f.adopt).not.toHaveBeenCalled(); f.unmount()
  }
})
test.each(['disabled', 'actor', 'policy'] as const)('fresh adoption refuses %s changes and never dispatches a stale selection', async change => {
  const f = setup(), input = await read(); select(input)
  if (change === 'disabled') f.rerender(<NoteReanchor {...f.props} disabled />)
  if (change === 'actor') f.session.actor_session_id = 'new_actor'
  if (change === 'policy') f.session.active_independent_attempt_id = 'attempt_locked'
  fireEvent.click(screen.getByRole('button', { name: '将这份准确新选文采用到本机笔记' })); if (change !== 'disabled') await screen.findByRole('alert')
  expect(f.adopt).not.toHaveBeenCalled(); expect(f.calls.every(call => call.method === 'GET')).toBe(true)
})
test('polling permission loss and browser focus discard the read-only text and temporary selection', async () => {
  const f = setup(), input = await read(); select(input); f.session.active_independent_attempt_id = 'attempt_locked'
  await waitFor(() => expect(screen.queryByLabelText('当前准确修订的完整原文')).toBeNull(), { timeout: 3000 }); expect(f.adopt).not.toHaveBeenCalled()
  f.session.active_independent_attempt_id = null; await read(); fireEvent(window, new Event('focus')); expect(screen.queryByLabelText('当前准确修订的完整原文')).toBeNull()
})
test('a fresh adoption permission timeout removes temporary payload and cannot accept its late successful response', async () => {
  const f = setup(), input = await read(); select(input); const gate = deferred<Response>(); f.fetch.mockReturnValueOnce(gate.promise); vi.useFakeTimers()
  fireEvent.click(screen.getByRole('button', { name: '将这份准确新选文采用到本机笔记' })); await act(async () => { await vi.advanceTimersByTimeAsync(2000) })
  expect(screen.queryByLabelText('当前准确修订的完整原文')).toBeNull(); await act(async () => { gate.resolve(f.response('/api/v1/session')); await Promise.resolve() }); expect(f.adopt).not.toHaveBeenCalled()
})
test('a later current revision never silently substitutes the already verified exact source selection', async () => {
  const f = setup(), input = await read(); select(input)
  const frozen = structuredClone(f.value.ref), later = { ...f.value.ref, revision: 3, sha256: 'e'.repeat(64) }
  f.fetch.mockImplementation(async (url, init) => { f.calls.push({ path: url, method: init.method! }); return url.endsWith('/current') ? new Response(JSON.stringify(later)) : f.response(url) })
  expect(screen.getByText(/当前指针之后变化不会自动替换/)).toBeTruthy()
  fireEvent.click(screen.getByRole('button', { name: '将这份准确新选文采用到本机笔记' }))
  await waitFor(() => expect(f.adopt).toHaveBeenCalledWith(expect.objectContaining({ ref: frozen, exact_quote: 'target' })))
  expect(f.calls.filter(call => call.path.endsWith('/current'))).toHaveLength(1)
  expect(f.calls.every(call => call.method === 'GET')).toBe(true)
})
