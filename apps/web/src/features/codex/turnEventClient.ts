import type { CodexTurnEvent } from '../../../../../packages/contracts/generated/codex-turn-types'
import { createApiClient } from '../../../../../packages/contracts/generated/api-client'
import { sameValue, validIdentity } from '../providers/providerSchema'
import { checkedCodexEvent } from './turnEventSchema'
import { turnClient } from './turnClient'
import type { SessionResponse } from '../../../../../packages/contracts/generated/api-types'

export type { CodexTurnEvent }
export class CodexStreamError extends Error {
 constructor(readonly status: number | null = null) { super('Codex 事件连接中断，任务状态未知。'); this.name = 'CodexStreamError' }
}
const invalid = (): never => { throw new CodexStreamError() }
function cursor(turn: string, run: string, after: number) {
 if (!validIdentity(turn) || !validIdentity(run) || !Number.isSafeInteger(after) || after < 0) invalid()
}
function json(text: string): unknown {
 const value: unknown = JSON.parse(text), stack: Array<Set<string> | null> = []
 for (let i = 0; i < text.length; i++) {
  if (text[i] === '{') stack.push(new Set())
  else if (text[i] === '[') stack.push(null)
  else if (text[i] === '}' || text[i] === ']') stack.pop()
  else if (text[i] === '"') {
   const start = i++
   while (i < text.length && text[i] !== '"') { if (text[i] === '\\') i++; i++ }
   let next = i + 1
   while (next < text.length && /\s/.test(text[next])) next++
   if (text[next] === ':') {
    const keys = stack.at(-1), key: unknown = JSON.parse(text.slice(start, i + 1))
    if (!keys || typeof key !== 'string' || keys.has(key)) invalid()
    keys!.add(key as string)
   }
  }
 }
 return value
}
/** Independent Codex framing/union. It never widens or calls the Tutor decoder. */
export async function* decodeCodexEvents(stream: ReadableStream<Uint8Array>, turn: string, run: string, after = 0, signal?: AbortSignal): AsyncGenerator<CodexTurnEvent> {
 cursor(turn, run, after)
 const reader = stream.getReader(), decoder = new TextDecoder('utf-8', { fatal: true }), observed = new Map<number, CodexTurnEvent>()
 const abort = () => { void reader.cancel().catch(() => undefined) }
 signal?.addEventListener('abort', abort, { once: true })
 let buffer = '', lines: string[] = [], size = 0, last = after, terminal: CodexTurnEvent | null = null
 function frame(): CodexTurnEvent | null {
  const fields: Record<string, string> = {}
  for (const line of lines) {
   const split = line.indexOf(':'), name = line.slice(0, split), raw = line.slice(split + 1)
   if (split < 1 || !['id', 'event', 'data'].includes(name) || Object.hasOwn(fields, name)) invalid()
   fields[name] = raw.startsWith(' ') ? raw.slice(1) : raw
  }
  lines = []; size = 0
  if (!Object.keys(fields).length) return null
  if (Object.keys(fields).length !== 3) invalid()
  const value = checkedCodexEvent(json(fields.data))
  if (value.turn_id !== turn || value.run_id !== run || fields.id !== `${run}:${value.seq}` || fields.event !== value.payload.type) invalid()
  if (value.seq <= last) { if (observed.has(value.seq) && !sameValue(observed.get(value.seq), value)) invalid(); return null }
  if (terminal || value.seq !== last + 1) invalid()
  observed.set(value.seq, value); last = value.seq
  if (value.payload.type === 'terminal') { terminal = value; return null }
  return value
 }
 try {
  if (signal?.aborted) { abort(); return }
  let done = false
  while (!done) {
   const chunk = await reader.read(); if (signal?.aborted) return
   done = chunk.done; buffer += done ? decoder.decode() : decoder.decode(chunk.value, { stream: true })
   if (buffer.length > 4 * 1024 * 1024) invalid()
   while (true) {
    const match = /[\r\n]/.exec(buffer); if (!match) break
    const at = match.index
    if (buffer[at] === '\r' && at + 1 === buffer.length && !done) break
    const line = buffer.slice(0, at), skip = buffer[at] === '\r' && buffer[at + 1] === '\n' ? 2 : 1
    buffer = buffer.slice(at + skip)
    if (line && !line.startsWith(':')) {
     size += line.length; if (size > 4 * 1024 * 1024 || lines.length >= 3) invalid(); lines.push(line)
    } else if (!line) { const event = frame(); if (event) yield event }
   }
  }
  if (buffer || lines.length) invalid()
  if (terminal) yield terminal
 } catch (error) { if (!signal?.aborted) throw error instanceof CodexStreamError ? error : new CodexStreamError() }
 finally { signal?.removeEventListener('abort', abort); await reader.cancel().catch(() => undefined); reader.releaseLock() }
}
export function createCodexEventsClient(fetcher: typeof fetch = (...args) => fetch(...args)) {
 return async function* events(turn: string, run: string, after: number, signal: AbortSignal): AsyncGenerator<CodexTurnEvent> {
  cursor(turn, run, after)
  if (signal.aborted) return
  const client = createApiClient(async (path, init, kind) => {
   if (kind !== 'sse') invalid()
   const response = await fetcher(path, { ...init, signal, credentials: 'same-origin', cache: 'no-store', redirect: 'error', headers: { ...init.headers, Accept: 'text/event-stream' } })
   if (response.status !== 200 || response.headers.get('Content-Type')?.split(';', 1)[0].trim().toLowerCase() !== 'text/event-stream' || !response.body) {
    await response.body?.cancel().catch(() => undefined); throw new CodexStreamError(response.status)
   }
   return decodeCodexEvents(response.body, turn, run, after, signal)
  })
  try { yield* await client('GET /api/v1/codex/turns/{id}/events', undefined, {}, { path: { id: turn }, query: { after_seq: after } }) }
  catch (error) { if (!signal.aborted) throw error instanceof CodexStreamError ? error : new CodexStreamError() }
 }
}
export type CodexEventPort = { session(): Promise<SessionResponse>; events: ReturnType<typeof createCodexEventsClient> }
export const codexEventClient: CodexEventPort = { session: turnClient.session, events: createCodexEventsClient() }
