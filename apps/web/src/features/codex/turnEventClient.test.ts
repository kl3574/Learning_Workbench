import { expect, test, vi } from 'vitest'
import { CodexStreamError, createCodexEventsClient, decodeCodexEvents, type CodexTurnEvent } from './turnEventClient'
const event = (seq: number, payload: CodexTurnEvent['payload']): CodexTurnEvent => ({ turn_id: 'turn_test', run_id: 'job_turn_test', seq, occurred_at: '2026-10-05T00:00:00Z', payload })
const frame = (v: CodexTurnEvent) => `id: ${v.run_id}:${v.seq}\nevent: ${v.payload.type}\ndata: ${JSON.stringify(v)}\n\n`
test('real fetch stream uses the Codex route and preserves a whitespace-only answer delta', async () => {
 const values = [event(1, { type: 'answer_delta', text: ' \n\t' }), event(2, { type: 'terminal', outcome: 'completed', error_code: null })]
 const fetcher = vi.fn<typeof fetch>(async () => new Response(values.map(frame).join(''), { headers: { 'Content-Type': 'text/event-stream' } }))
 const signal = new AbortController().signal, actual = []
 for await (const v of createCodexEventsClient(fetcher)('turn_test', 'job_turn_test', 0, signal)) actual.push(v)
 expect(actual).toEqual(values)
 expect(fetcher).toHaveBeenCalledOnce()
 expect(fetcher.mock.calls[0][0]).toBe('/api/v1/codex/turns/turn_test/events?after_seq=0')
 expect(fetcher.mock.calls[0][1]).toMatchObject({ method: 'GET', signal, credentials: 'same-origin', cache: 'no-store', redirect: 'error' })
})
const stream = (text: string, width = 1) => {
 const bytes = new TextEncoder().encode(text)
 return new ReadableStream<Uint8Array>({ start(controller) { for (let i = 0; i < bytes.length; i += width) controller.enqueue(bytes.slice(i, i + width)); controller.close() } })
}
const collect = async (text: string, after = 0) => { const result = []; for await (const value of decodeCodexEvents(stream(text), 'turn_test', 'job_turn_test', after)) result.push(value); return result }
test('all six closed variants decode over byte splits, CRLF and comments; raw Unicode is unchanged', async () => {
 const values = [event(1, { type: 'status', job: { id: 'job_turn_test', status: 'running' }, run_revision: 2 }),
  event(2, { type: 'answer_delta', text: '  α\n中文😀\r\n\t' }), event(3, { type: 'approval_required', approval_id: 'approval_test' }),
  event(4, { type: 'usage', usage: { input_tokens: null, output_tokens: 3 } }),
  event(5, { type: 'manifest_ready', manifest_id: 'manifest_test', manifest_sha256: 'a'.repeat(64) }),
  event(6, { type: 'terminal', outcome: 'incomplete', error_code: 'CODEX_NEW_OUTBOUND_CONSENT_REQUIRED' })]
 expect(await collect(': keepalive\r\n\r\n' + values.map(frame).join('').replaceAll('\n', '\r\n'))).toEqual(values)
})
test('explicit cursor permits prior exact replays, deduplicates, and requires the next sequence', async () => {
 const prior = event(1, { type: 'answer_delta', text: 'original' }), next = event(2, { type: 'usage', usage: { input_tokens: null, output_tokens: null } })
 expect(await collect(frame(prior) + frame(next) + frame(next), 1)).toEqual([next])
 await expect(collect(frame(next), 0)).rejects.toThrow(CodexStreamError)
 await expect(collect(frame(prior) + frame(event(1, { type: 'answer_delta', text: 'changed' })))).rejects.toThrow(CodexStreamError)
})
test.each([
 ['Tutor union', { type: 'token', text: 'x' }], ['extra property', { type: 'answer_delta', text: 'x', approval_id: 'approval_test' }],
 ['empty delta', { type: 'answer_delta', text: '' }], ['lone surrogate', { type: 'answer_delta', text: '\ud800' }],
 ['mismatched status job', { type: 'status', job: { id: 'job_other', status: 'running' }, run_revision: 1 }],
 ['unsafe revision', { type: 'status', job: { id: 'job_turn_test', status: 'running' }, run_revision: 9007199254740992 }],
 ['missing usage member', { type: 'usage', usage: { output_tokens: 3 } }], ['negative usage', { type: 'usage', usage: { input_tokens: -1, output_tokens: 0 } }],
 ['extra nested property', { type: 'usage', usage: { input_tokens: 0, output_tokens: 0, raw: 'private' } }],
 ['invalid manifest digest', { type: 'manifest_ready', manifest_id: 'manifest_test', manifest_sha256: 'x'.repeat(64) }],
 ['completed error', { type: 'terminal', outcome: 'completed', error_code: 'CODEX_OUTCOME_UNKNOWN' }],
 ['raw terminal error', { type: 'terminal', outcome: 'failed', error_code: '/private/raw/error' }],
])('rejects %s without exposing the raw frame', async (_label, payload) => {
 const value = { ...event(1, { type: 'answer_delta', text: 'x' }), payload }
 await expect(collect(frame(value as CodexTurnEvent))).rejects.toThrow(CodexStreamError)
})
test.each([
 ['wrong turn', (text: string) => text.replaceAll('turn_test', 'turn_other')],
 ['wrong SSE id', (text: string) => text.replace('id: job_turn_test:1', 'id: turn_test:1')],
 ['wrong SSE event', (text: string) => text.replace('event: answer_delta', 'event: usage')],
 ['duplicate JSON field', (text: string) => text.replace('"seq":1', '"seq":1,"seq":1')],
 ['escaped duplicate JSON field', (text: string) => text.replace('"seq":1', '"seq":1,"s\\u0065q":1')],
 ['duplicate SSE field', (text: string) => 'id: job_turn_test:1\n' + text],
 ['unknown SSE field', (text: string) => 'retry: 100\n' + text],
 ['partial frame', (text: string) => text.slice(0, -1)],
 ['invalid UTC', (text: string) => text.replace('2026-10-05', '2026-02-30')],
])('rejects %s', async (_label, change) => {
 await expect(collect(change(frame(event(1, { type: 'answer_delta', text: 'x' }))))).rejects.toThrow(CodexStreamError)
})
test('terminal is unique and final; EOF alone cannot invent it', async () => {
 const terminal = event(1, { type: 'terminal', outcome: 'unknown', error_code: 'CODEX_OUTCOME_UNKNOWN' })
 expect(await collect(frame(terminal) + frame(terminal))).toEqual([terminal])
 await expect(collect(frame(terminal) + frame(event(2, { type: 'answer_delta', text: 'late' })))).rejects.toThrow(CodexStreamError)
 expect(await collect(frame(event(1, { type: 'answer_delta', text: 'partial' })))).toHaveLength(1)
})
test.each([401, 403, 404, 409, 503])('HTTP %s is a safe stream failure; no reconnect or POST', async status => {
 const fetcher = vi.fn<typeof fetch>(async () => new Response('private server error', { status }))
 const result = createCodexEventsClient(fetcher)('turn_test', 'job_turn_test', 3, new AbortController().signal)
 await expect(result.next()).rejects.toMatchObject({ name: 'CodexStreamError', status })
 expect(fetcher).toHaveBeenCalledOnce()
 expect(fetcher.mock.calls[0][0]).toContain('after_seq=3')
})
test('invalid path/cursor, wrong content type, bad UTF8 and aborted pending reads fail closed', async () => {
 const fetcher = vi.fn<typeof fetch>(async () => new Response('private HTML', { headers: { 'Content-Type': 'text/html' } }))
 await expect(createCodexEventsClient(fetcher)('../turn', 'job_turn_test', 0, new AbortController().signal).next()).rejects.toThrow(CodexStreamError)
 expect(fetcher).not.toHaveBeenCalled()
 await expect(createCodexEventsClient(fetcher)('turn_test', 'job_turn_test', -1, new AbortController().signal).next()).rejects.toThrow(CodexStreamError)
 await expect(createCodexEventsClient(fetcher)('turn_test', 'job_turn_test', 0, new AbortController().signal).next()).rejects.toThrow(CodexStreamError)
 const invalid = new ReadableStream<Uint8Array>({ start(c) { c.enqueue(new Uint8Array([0xff])); c.close() } })
 await expect(decodeCodexEvents(invalid, 'turn_test', 'job_turn_test').next()).rejects.toThrow(CodexStreamError)
 const cancelled = vi.fn(), controller = new AbortController(), pending = decodeCodexEvents(new ReadableStream({ cancel: cancelled }), 'turn_test', 'job_turn_test', 0, controller.signal).next()
 controller.abort(); expect(await pending).toMatchObject({ done: true }); expect(cancelled).toHaveBeenCalledOnce()
})
test('pre-aborted connection does no GET and transport failures expose no original error', async () => {
 const fetcher = vi.fn<typeof fetch>(async () => { throw new Error('/private/transport/raw') }), controller = new AbortController()
 controller.abort()
 expect(await createCodexEventsClient(fetcher)('turn_test', 'job_turn_test', 0, controller.signal).next()).toMatchObject({ done: true })
 expect(fetcher).not.toHaveBeenCalled()
 await expect(createCodexEventsClient(fetcher)('turn_test', 'job_turn_test', 0, new AbortController().signal).next()).rejects.toThrow(CodexStreamError)
})
