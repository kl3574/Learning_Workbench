import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from 'react'
import type { SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import { getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import { checkedBootstrap } from './bootstrapClient'
import { codexEventClient, CodexStreamError, type CodexEventPort, type CodexTurnEvent } from './turnEventClient'
import { checkedCodexEvent } from './turnEventSchema'

type Reading = { actor: string | null; events: CodexTurnEvent[]; cursor: number; phase: 'idle' | 'connecting' | 'connected' | 'disconnected' | 'terminal' | 'denied' }
const empty = (): Reading => ({ actor: null, events: [], cursor: 0, phase: 'idle' })
const academic = (s: SessionResponse) => s.role === 'author' && !s.active_independent_attempt_id && !s.active_open_book_attempt_id
/** Ephemeral read channel. No command journal, permission grant or automatic reconnect. */
export function useCodexTurnEvents(workspace: string, turn: string, run: string, admitted: boolean, port: CodexEventPort = codexEventClient) {
 const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
 const scope = useMemo(() => ({ workspace, turn, run, admitted, access, port }), [workspace, turn, run, admitted, access, port])
 const current = useRef(scope); current.current = scope
 const live = useRef(false), serial = useRef(0), connection = useRef<AbortController | null>(null)
 const reading = useRef<Reading>(empty()), [view, setView] = useState({ scope, value: reading.current })
 const publish = (value: Reading) => { reading.current = value; setView({ scope, value }) }
 const terminal = () => reading.current.phase === 'terminal'
 const valid = (token: number) => live.current && current.current === scope && scope.admitted && scope.workspace !== '' && getSessionGeneration() === access && serial.current === token
 useEffect(() => {
  live.current = true; reading.current = empty(); setView({ scope, value: reading.current })
  const unsubscribe = subscribeSessionAccess(() => { ++serial.current; connection.current?.abort(); connection.current = null; reading.current = empty(); setView({ scope, value: reading.current }) })
  return () => { live.current = false; ++serial.current; connection.current?.abort(); connection.current = null; unsubscribe() }
 }, [scope])
 const fresh = async (token: number, actor?: string) => {
  try {
   const session = checkedBootstrap<SessionResponse>('SessionResponse', await port.session())
   if (!valid(token)) throw new Error('Stale event read')
   if (session.workspace_id !== workspace || !academic(session) || actor !== undefined && session.actor_session_id !== actor) throw new Error('Event access changed')
   return session.actor_session_id
  } catch {
   if (valid(token)) { publish({ ...empty(), phase: 'denied' }); connection.current?.abort() }
   throw new Error('Event permission not verified')
  }
 }
 const connect = async () => {
  if (!live.current || current.current !== scope || !admitted || !workspace || connection.current || getSessionGeneration() !== access || reading.current.phase === 'terminal') return
  const controller = new AbortController(), token = ++serial.current, original = reading.current
  connection.current = controller
  publish({ ...original, phase: 'connecting' })
  try {
   const actor = await fresh(token, original.actor ?? undefined)
   if (!valid(token)) return
   publish({ ...original, actor, phase: 'connected' })
   for await (const raw of port.events(turn, run, original.cursor, controller.signal)) {
    if (!valid(token)) return
    // Even an injected adapter must retain the closed wire and exact sequence.
    const event = checkedCodexEvent(raw)
    if (event.turn_id !== turn || event.run_id !== run || event.seq !== reading.current.cursor + 1 || terminal()) throw new CodexStreamError()
    await fresh(token, actor)
    if (!valid(token)) return
    publish({ actor, cursor: event.seq, events: [...reading.current.events, event], phase: event.payload.type === 'terminal' ? 'terminal' : 'connected' })
   }
   if (!valid(token)) return
   await fresh(token, actor)
   if (valid(token) && !terminal()) publish({ ...reading.current, phase: 'disconnected' })
  } catch (error) {
   if (!valid(token) || reading.current.phase === 'denied') return
   if (error instanceof CodexStreamError && [401, 403, 404].includes(error.status ?? 0)) { publish({ ...empty(), phase: 'denied' }); controller.abort(); return }
   // HTTP denial, EOF and transport loss are never converted into Job outcomes.
   try { await fresh(token, reading.current.actor ?? undefined) } catch { return }
   if (valid(token)) publish({ ...reading.current, phase: 'disconnected' })
  } finally { if (serial.current === token) connection.current = null }
 }
 const disconnect = () => {
  if (current.current !== scope) return
  ++serial.current; connection.current?.abort(); connection.current = null
  if (reading.current.phase !== 'terminal' && reading.current.phase !== 'denied') publish({ ...reading.current, phase: 'disconnected' })
 }
 const visible = view.scope === scope && admitted && getSessionGeneration() === access
 return { ...(visible ? view.value : empty()), allowed: admitted && !!workspace, connect, disconnect }
}
