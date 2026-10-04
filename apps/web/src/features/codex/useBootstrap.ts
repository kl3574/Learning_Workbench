import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import type { CodexBootstrapPreparationView } from '../../../../../packages/contracts/generated/codex-bootstrap-types'
import type { CodexCurrentSessionView } from '../../../../../packages/contracts/generated/codex-turn-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import { type DraftStore } from '../../workbench/DraftStore'
import { validIdentity } from '../providers/providerSchema'
import { bootstrapClient, checkedBootstrap, type BootstrapPort } from './bootstrapClient'
import { bootstrapStore, createCommand, decidedCommand, decodeBootstrapCommand, persistBootstrapCommand, prepareCommand, readBootstrapCommand, type BootstrapCommand } from './bootstrapCommands'
import { bootstrapMemoryVersion, heldBootstrapCommands, releaseBootstrapCommand, retainBootstrapCommand, subscribeBootstrapMemory } from './bootstrapMemory'

const canWrite = (session: SessionResponse) => session.role === 'author' && !session.active_independent_attempt_id && !session.active_open_book_attempt_id
const denied = (reason: unknown) => reason instanceof ApiError && ([401, 403].includes(reason.status) || ['POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED'].includes(reason.code ?? ''))
export function useBootstrap(workspace: string, writeAdmitted: boolean, port: BootstrapPort = bootstrapClient, store: DraftStore = bootstrapStore) {
 const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
 useSyncExternalStore(subscribeBootstrapMemory, bootstrapMemoryVersion, bootstrapMemoryVersion)
 const previousWriteAdmission = useRef(writeAdmitted), writeRevocation = useRef(0)
 // Safe control reads already admit learners and test-policy readers. Initial
 // academic admission becoming ready must not cancel an explicit control GET.
 // A restriction still invalidates every callback and isolates any late ACK.
 if (previousWriteAdmission.current && !writeAdmitted) ++writeRevocation.current
 previousWriteAdmission.current = writeAdmitted
 const owner = JSON.stringify([workspace, access, writeRevocation.current]), scope = useRef({ owner, port, store }); scope.current = { owner, port, store }
 const live = useRef(false), working = useRef(false), sequence = useRef(0), writers = useRef(new Set<AbortController>())
 const [renderScope, setRenderScope] = useState({ owner, port, store }), [identity, setIdentity] = useState<SessionResponse | null>(null)
 const [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('')
 const [commands, setCommands] = useState<BootstrapCommand[]>([]), [current, setCurrent] = useState<CodexBootstrapPreparationView | null>(null)
 const [sessions, setSessions] = useState<Record<string, CodexCurrentSessionView>>({})
 const currentScope = () => live.current && scope.current.owner === owner && scope.current.port === port && scope.current.store === store && access === getSessionGeneration()
 const valid = (token: number) => currentScope() && sequence.current === token
 const visible = renderScope.owner === owner && renderScope.port === port && renderScope.store === store
 const ready = visible && identity !== null
 const allowed = ready && writeAdmitted && canWrite(identity)
 const begin = () => { if (!currentScope() || !workspace || working.current) return null; working.current = true; setBusy(true); setError(''); setMessage(''); return ++sequence.current }
 const finish = (token: number) => { if (valid(token)) { working.current = false; setBusy(false) } }
 const fail = (reason: unknown) => {
  if (denied(reason)) { setIdentity(null); setCurrent(null); setSessions({}); setCommands([]) }
  setError(denied(reason) ? '当前会话无权继续；原命令保留，请重新读取权限。'
   : reason instanceof ApiError && reason.status === 412 ? '准备版本已变化（412）；原 key 与基准保留，请另读当前状态。'
   : reason instanceof ApiError && reason.status === 409 ? '原操作或许可绑定冲突（409）；原命令保留，不自动另建。'
   : '本次操作或结果尚未确认；原命令保留，不自动重发。请显式读取当前状态或回放原 key。')
 }
 const load = async () => Object.values(await store.load(workspace)).map(v => readBootstrapCommand(v, workspace))
 async function fresh(token: number, write: boolean, actor?: string) {
  const session = checkedBootstrap<SessionResponse>('SessionResponse', await port.session())
  if (!valid(token)) throw new Error('Access changed')
  if (session.workspace_id !== workspace || write && (!writeAdmitted || !canWrite(session)) || actor && session.actor_session_id !== actor) {
   setIdentity(null); setCurrent(null); setSessions({}); setCommands([])
   throw new ApiError(403, 'Session no longer admits original operation')
  }
  return session
 }
 const refresh = async () => {
  const token = begin(); if (token === null) return
  setIdentity(null); setCurrent(null); setSessions({}); setCommands([])
  try { const session = await fresh(token, false), values = await load(); if (valid(token)) { setIdentity(session); setCommands(values) } }
  catch (reason) { if (valid(token)) fail(reason) } finally { finish(token) }
 }
 useEffect(() => {
  live.current = true; ++sequence.current; working.current = false; setRenderScope({ owner, port, store })
  setIdentity(null); setCurrent(null); setSessions({}); setCommands([]); setBusy(false); setError(''); setMessage('')
  return () => { live.current = false; ++sequence.current; working.current = false; for (const writer of writers.current) writer.abort() }
 }, [owner, port, store])
 const execute = async (command: BootstrapCommand) => {
  if (!allowed || command.workspace_id !== workspace || command.actor_session_id !== identity.actor_session_id || command.ack) return
  const token = begin(); if (token === null) return
  const controller = new AbortController(); writers.current.add(controller)
  const guard = { allowed: () => valid(token), signal: controller.signal }, unsubscribe = subscribeSessionAccess(() => controller.abort())
  let original = command
  try {
   await fresh(token, true, command.actor_session_id)
   retainBootstrapCommand(command)
   original = await persistBootstrapCommand(command, store, guard)
   releaseBootstrapCommand(original)
   if (!valid(token)) return
   const stored = await load()
   if (!valid(token)) return
   setCommands(stored); setCurrent(null)
   await fresh(token, true, original.actor_session_id)
   if (original.ack) return
   const raw = original.kind === 'prepare' ? await port.prepare(original.body, original.command_id)
    : original.kind === 'decision' ? await port.decide(original.preparation_id, original.body, original.command_id)
    : await port.create(original.body, original.command_id)
   // Strictly verify and retain the received fact under the captured original
   // actor before checking current access; a late ACK must not be discarded.
   const acknowledged = decodeBootstrapCommand(JSON.stringify({ ...original, ack: raw, error: null }), workspace)
   retainBootstrapCommand(acknowledged)
   if (!valid(token)) return
   await fresh(token, true, original.actor_session_id)
   const saved = await persistBootstrapCommand(acknowledged, store, guard)
   releaseBootstrapCommand(saved)
   const values = await load()
   if (valid(token)) { setCommands(values); setMessage(original.kind === 'prepare' ? '准备原 ACK 已保存；须另读当前资格。' : original.kind === 'decision' ? '决定原 ACK 已保存；须另读当前资格。' : '原 201 ACK 已保存；ready 仅表示已核验映射。') }
  } catch (reason) {
   if (valid(token)) {
    if (!denied(reason) && reason instanceof ApiError && reason.status >= 400 && reason.status <= 599 && !heldBootstrapCommands(workspace, original.actor_session_id).some(v => v.command_id === original.command_id && v.ack)) {
     const rejected = decodeBootstrapCommand(JSON.stringify({ ...original, error: { status: reason.status, code: /^[A-Z][A-Z0-9_]{0,79}$/.test(reason.code ?? '') ? reason.code : null } }), workspace)
     retainBootstrapCommand(rejected)
     try { const saved = await persistBootstrapCommand(rejected, store, guard); releaseBootstrapCommand(saved); const stored = await load(); if (valid(token)) setCommands(stored) } catch { /* Held facts retain the complete command. */ }
    }
    if (valid(token)) fail(reason)
   }
  } finally { unsubscribe(); writers.current.delete(controller); finish(token) }
 }
 const make = async (kind: 'prepare' | 'create' | 'approve_once' | 'decline') => {
  if (!allowed || working.current) return
  // No key is allocated until the currently displayed basis is a checked GET.
  if (kind !== 'prepare' && (!current || current.actor_session_id !== identity.actor_session_id)) return
  const command = kind === 'prepare' ? prepareCommand(workspace, identity.actor_session_id)
   : kind === 'create' ? createCommand(workspace, identity.actor_session_id, current!)
   : decidedCommand(workspace, identity.actor_session_id, current!, kind)
  await execute(command)
 }
 const readPreparation = async (id: string) => {
  if (!validIdentity(id)) return
  const token = begin(); if (token === null) return
  setCurrent(null)
  try {
   const session = await fresh(token, false)
   const value = checkedBootstrap<CodexBootstrapPreparationView>('CodexBootstrapPreparationView', await port.preparation(id))
   if (value.id !== id) throw new Error('Wrong preparation')
   if (!valid(token)) return
   setIdentity(session); setCurrent(value)
   let linked: CodexCurrentSessionView | null = null
   if (value.session_id) {
    linked = checkedBootstrap<CodexCurrentSessionView>('CodexCurrentSessionView', await port.read(value.session_id))
    if (linked.id !== value.session_id || linked.adapter_version !== value.scope.adapter_version) throw new Error('Wrong session binding')
   }
   if (valid(token)) { setIdentity(session); setCurrent(value); if (linked) setSessions(previous => ({ ...previous, [linked.id]: linked! })) }
  } catch (reason) { if (valid(token)) fail(reason) } finally { finish(token) }
 }
 const saveMemory = async () => {
  if (!ready) return
  const token = begin(); if (token === null) return
  const controller = new AbortController(); writers.current.add(controller)
  const guard = { allowed: () => valid(token), signal: controller.signal }, unsubscribe = subscribeSessionAccess(() => controller.abort())
  try {
   await fresh(token, false)
   // Saving typed control history is a local read-side recovery action. The
   // original actor/key/basis remain unchanged; this grants no POST authority.
   for (const command of heldBootstrapCommands(workspace)) {
    const saved = await persistBootstrapCommand(command, store, guard); releaseBootstrapCommand(saved)
   }
   const values = await load(); if (valid(token)) { setCommands(values); setMessage('仅保存已收到的原事实；未发送任何写请求。') }
  } catch (reason) { if (valid(token)) fail(reason) }
  finally { unsubscribe(); writers.current.delete(controller); finish(token) }
 }
 const retained = heldBootstrapCommands(workspace)
 const all = ready ? [...commands] : []
 if (ready) for (const value of retained) {
  const index = all.findIndex(v => v.command_id === value.command_id)
  if (index < 0) all.push(value); else if (!all[index].ack || value.ack) all[index] = value
 }
 const ids = [...new Set(all.flatMap(v => v.preparation_id ? [v.preparation_id] : v.kind === 'prepare' && v.ack ? [v.ack.id] : []))]
 return { ready, allowed, busy: visible && busy, error: visible ? error : '', message: visible ? message : '',
  commands: all, ids, current: ready ? current : null, sessions: ready ? Object.values(sessions) : [], actor: ready ? identity.actor_session_id : null,
  dirty: retained.length > 0 || ready && all.some(v => !v.ack), safe: !working.current && retained.length === 0, isolated: !working.current && retained.length > 0,
  canSave: ready && retained.length > 0, refresh, make, execute, readPreparation, saveMemory,
  canReplay: (value: BootstrapCommand) => allowed && value.actor_session_id === identity.actor_session_id && !value.ack && !retained.some(v => v.command_id === value.command_id && v.ack),
  hasOriginal: (kind: 'decision' | 'create', id: string) => all.some(v => v.kind === kind && v.preparation_id === id),
 }
}
