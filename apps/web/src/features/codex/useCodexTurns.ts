import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import type { CodexCurrentSessionView, CodexTurnControlView, CodexTurnPage, CodexTurnPreparationView } from '../../../../../packages/contracts/generated/codex-turn-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import type { DraftStore, DraftWriteGuard } from '../../workbench/DraftStore'
import { sameValue } from '../providers/providerSchema'
import { checkedBootstrap } from './bootstrapClient'
import { checkedTurn, turnClient, type TurnPort } from './turnClient'
import { decodeTurnCommand, persistTurnCommand, readTurnCommand, turnCancelCommand, turnIdentity, turnInterruptCommand, turnPrepareCommand, turnStore, type TurnCommand } from './turnCommands'
import { decodeTurnForm, emptyTurnFields, persistTurnForm, readTurnForm, snapshotTurnForm, turnFormBody, turnFormStore, type TurnFields, type TurnForm } from './turnForms'
import { heldTurnCommands, heldTurnForms, releaseTurnCommand, releaseTurnForm, retainTurnCommand, retainTurnForm, subscribeTurnMemory, turnMemoryVersion } from './turnMemory'

const academic = (s: SessionResponse) => s.role === 'author' && !s.active_independent_attempt_id && !s.active_open_book_attempt_id
const denied = (e: unknown) => e instanceof ApiError && ([401, 403].includes(e.status) || ['POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED'].includes(e.code ?? ''))
export function useCodexTurns(workspace: string, writeAdmitted: boolean, port: TurnPort = turnClient, store: DraftStore = turnStore, formStore: DraftStore = turnFormStore) {
 const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
 useSyncExternalStore(subscribeTurnMemory, turnMemoryVersion, turnMemoryVersion)
 const priorAdmission = useRef(writeAdmitted), revocation = useRef(0)
 if (priorAdmission.current && !writeAdmitted) ++revocation.current
 priorAdmission.current = writeAdmitted
 const owner = JSON.stringify([workspace, access, revocation.current]), scope = useRef({ owner, port, store, formStore }); scope.current = { owner, port, store, formStore }
 const live = useRef(false), working = useRef(false), sequence = useRef(0), writers = useRef(new Set<AbortController>())
 const [renderScope, setRenderScope] = useState({ owner, port, store, formStore }), [identity, setIdentity] = useState<SessionResponse | null>(null)
 const actorRef = useRef<SessionResponse | null>(null)
 const [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('')
 const [commands, setCommands] = useState<TurnCommand[]>([]), [forms, setForms] = useState<TurnForm[]>([])
 const [selected, setSelected] = useState(''), [form, setForm] = useState<TurnForm | null>(null), formRef = useRef<TurnForm | null>(null)
 const [current, setCurrent] = useState<CodexCurrentSessionView | null>(null), [page, setPage] = useState<CodexTurnPage | null>(null)
 const [controls, setControls] = useState<Record<string, CodexTurnControlView>>({}), [detail, setDetail] = useState<CodexTurnPreparationView | null>(null)
 const currentScope = () => live.current && scope.current.owner === owner && scope.current.port === port && scope.current.store === store && scope.current.formStore === formStore && access === getSessionGeneration()
 const valid = (token: number) => currentScope() && sequence.current === token
 const visible = renderScope.owner === owner && renderScope.port === port && renderScope.store === store && renderScope.formStore === formStore
 const ready = visible && identity !== null, allowed = ready && writeAdmitted && academic(identity)
 const hide = () => { actorRef.current = null; setIdentity(null); setCurrent(null); setPage(null); setControls({}); setDetail(null); setCommands([]); setForms([]) }
 const acceptIdentity = (value: SessionResponse) => { actorRef.current = value; setIdentity(value) }
 const begin = () => { if (!currentScope() || !workspace || working.current) return null; working.current = true; setBusy(true); setError(''); setMessage(''); return ++sequence.current }
 const finish = (token: number) => { if (valid(token)) { working.current = false; setBusy(false) } }
 const fail = (reason: unknown) => {
  if (denied(reason)) hide()
  setError(denied(reason) ? '当前权限或原 actor 已变化；原回合命令与表单保留，请重新读取权限。'
   : reason instanceof ApiError && reason.status === 412 ? '版本已变化（412）；原 key、完整命令与只读基准保留。请独立读取当前状态。'
   : reason instanceof ApiError && reason.status === 409 ? '操作绑定冲突（409）；原 key 与基准保留，不自动另建回合。'
   : '操作结果或本机保存尚未确认；原命令和表单保留，不自动重发。')
 }
 async function fresh(token: number, write: boolean, actor?: string) {
  const value = checkedBootstrap<SessionResponse>('SessionResponse', await port.session())
  if (!valid(token)) throw new Error('Scope changed')
  if (value.workspace_id !== workspace || actor && value.actor_session_id !== actor || write && (!writeAdmitted || !academic(value))) {
   hide(); throw new ApiError(403, 'Original turn access changed')
  }
  acceptIdentity(value); return value
 }
 const loadCommands = async () => Object.values(await store.load(workspace)).map(v => readTurnCommand(v, workspace))
 const loadForms = async () => Object.values(await formStore.load(workspace)).map(v => readTurnForm(v, workspace))
 function writer(allowed: () => boolean) {
  const controller = new AbortController(); writers.current.add(controller)
  const unsubscribe = subscribeSessionAccess(() => controller.abort())
  return { guard: { allowed, signal: controller.signal } satisfies DraftWriteGuard,
   done: () => { unsubscribe(); writers.current.delete(controller) } }
 }
 useEffect(() => {
  live.current = true; ++sequence.current; working.current = false; setRenderScope({ owner, port, store, formStore })
  hide(); setSelected(''); setForm(null); formRef.current = null; setBusy(false); setError(''); setMessage('')
  return () => { live.current = false; ++sequence.current; working.current = false; for (const value of writers.current) value.abort() }
 }, [owner, port, store, formStore])
 const refresh = async () => {
  const token = begin(); if (token === null) return
  hide()
  try {
   const session = await fresh(token, false), values = await loadCommands(), drafts = await loadForms()
   await fresh(token, false, session.actor_session_id)
   if (valid(token)) { setCommands(values); setForms(drafts); setMessage('已读取本机记录；当前 session、回合与准备须分别显式读取。') }
  } catch (reason) { if (valid(token)) fail(reason) } finally { finish(token) }
 }
 const edit = (patch: Partial<TurnFields>) => {
  if (!allowed || working.current || !currentScope()) return
  const previous = formRef.current?.actor_session_id === identity.actor_session_id ? formRef.current : null
  const next = snapshotTurnForm(workspace, identity.actor_session_id, { ...(previous?.fields ?? emptyTurnFields()), session_id: selected, ...patch }, previous)
  formRef.current = next; setForm(next); retainTurnForm(next)
  const admitted = () => currentScope() && actorRef.current?.actor_session_id === next.actor_session_id && academic(actorRef.current) && writeAdmitted
  const saving = writer(admitted)
  void persistTurnForm(next, formStore, saving.guard).then(() => {
   releaseTurnForm(next)
   if (currentScope()) setForms(values => [...values.filter(v => v.snapshot_id !== next.snapshot_id), next])
  }).catch(() => { if (admitted()) setError('表单尚未全部保存；原输入保留在隔离内存中，离开前请仅保存本机事实。') }).finally(saving.done)
 }
 const select = (id: string) => {
  if (!ready || working.current) return
  edit({ session_id: id }); setSelected(id); setCurrent(null); setPage(null); setControls({}); setDetail(null)
 }
 const restoreForm = async (value: TurnForm) => {
  if (!allowed || value.workspace_id !== workspace || value.actor_session_id !== identity.actor_session_id) return
  const actor = identity.actor_session_id, token = begin(); if (token === null) return
  const saving = writer(() => valid(token) && actorRef.current?.actor_session_id === actor && academic(actorRef.current) && writeAdmitted)
  try {
   const original = decodeTurnForm(JSON.stringify(value), workspace)
   await fresh(token, true, actor)
   const record = (await formStore.load(workspace))[original.snapshot_id]
   if (!valid(token)) return
   const held = heldTurnForms(workspace).find(v => v.snapshot_id === original.snapshot_id)
   // A displayed list item is not a fresh local baseline. Recheck the complete
   // immutable original; damaged durable data cannot fall back to memory.
   const checked = record ? readTurnForm(record, workspace) : held
   if (!checked || !sameValue(checked, original) || held && !sameValue(held, original)) throw new Error('Saved form changed')
   await fresh(token, true, actor)
   // Only an admitted restore creates a new branch. Its original always stays.
   const next = snapshotTurnForm(workspace, actor, original.fields, null)
   retainTurnForm(next)
   await persistTurnForm(next, formStore, saving.guard); releaseTurnForm(next)
   if (!valid(token)) return
   await fresh(token, true, actor)
   if (valid(token)) {
    formRef.current = next; setForm(next); setSelected(original.fields.session_id); setCurrent(null); setPage(null); setControls({}); setDetail(null)
    setForms(v => [...v, next]); setMessage('原表单已核验并恢复为独立本机分支；未发送准备或取消请求。')
   }
  } catch (reason) { if (valid(token)) fail(reason) } finally { saving.done(); finish(token) }
 }
 const readCurrent = async () => {
  if (!ready || !turnIdentity(selected)) return
  const id = selected, actor = identity.actor_session_id, token = begin(); if (token === null) return
  setCurrent(null)
  try {
   await fresh(token, false, actor)
   const value = checkedBootstrap<CodexCurrentSessionView>('CodexCurrentSessionView', await port.current(id))
   if (value.id !== id) throw new Error('Wrong session')
   await fresh(token, false, actor)
   if (valid(token)) setCurrent(value)
  } catch (reason) { if (valid(token)) fail(reason) } finally { finish(token) }
 }
 const readPage = async (next = false) => {
  if (!ready || !turnIdentity(selected) || next && !page?.next_cursor) return
  const id = selected, actor = identity.actor_session_id, token = begin(); if (token === null) return
  const cursor = next ? page!.next_cursor! : undefined
  setPage(null); setControls({})
  try {
   await fresh(token, false, actor)
   const value = checkedTurn('CodexTurnPage', await port.turns(id, cursor ? { cursor, limit: 20 } : { limit: 20 }))
   if (value.items.some(v => v.session_id !== id)) throw new Error('Wrong page')
   await fresh(token, false, actor)
   if (valid(token)) setPage(value)
  } catch (reason) { if (valid(token)) fail(reason) } finally { finish(token) }
 }
 const readControl = async (id: string) => {
  if (!ready || !turnIdentity(id)) return
  const sessionId = selected, actor = identity.actor_session_id, token = begin(); if (token === null) return
  setControls(values => { const next = { ...values }; delete next[id]; return next })
  try {
   await fresh(token, false, actor)
   const value = checkedTurn('CodexTurnControlView', await port.control(id))
   if (value.id !== id || value.session_id !== sessionId) throw new Error('Wrong control')
   await fresh(token, false, actor)
   if (valid(token)) setControls(values => ({ ...values, [id]: value }))
  } catch (reason) { if (valid(token)) fail(reason) } finally { finish(token) }
 }
 const readPreparation = async (command: TurnCommand) => {
  if (!allowed || command.kind !== 'prepare' || !command.ack || command.actor_session_id !== identity.actor_session_id) return
  const id = command.ack.id, actor = identity.actor_session_id, token = begin(); if (token === null) return
  setDetail(null)
  try {
   await fresh(token, true, actor)
   const value = checkedTurn('CodexTurnPreparationView', await port.preparation(id))
   // Current projections may change validity and Job status, never the frozen input.
   if (value.id !== id || value.actor_session_id !== actor || value.session_id !== command.session_id
    || value.preparation_sha256 !== command.ack.preparation_sha256 || value.turn_id !== command.ack.turn_id || value.job.id !== command.ack.job.id
    || value.created_at !== command.ack.created_at || value.session_revision !== command.ack.session_revision
    || !sameValue(value.request, command.ack.request) || !sameValue(value.summary, command.ack.summary)) throw new Error('Wrong preparation')
   await fresh(token, true, actor)
   if (valid(token)) setDetail(value)
  } catch (reason) { if (valid(token)) fail(reason) } finally { finish(token) }
 }
 const execute = async (command: TurnCommand) => {
  if (!ready || command.workspace_id !== workspace || command.actor_session_id !== identity.actor_session_id || command.ack || command.kind === 'prepare' && !allowed) return
  const token = begin(); if (token === null) return
  const saving = writer(() => valid(token)); let original = command
  try {
   await fresh(token, command.kind === 'prepare', command.actor_session_id)
   retainTurnCommand(command)
   original = await persistTurnCommand(command, store, saving.guard)
   releaseTurnCommand(original)
   if (!valid(token)) return
   const values = await loadCommands()
   if (!valid(token)) return
   setCommands(values)
   await fresh(token, original.kind === 'prepare', original.actor_session_id)
   if (original.ack) return
   if (original.kind === 'prepare' || original.kind === 'interrupt') setCurrent(null)
   if (original.kind !== 'prepare') {
    const target = original.kind === 'cancel' ? original.basis.id : original.basis.turn.id
    setControls(values => { const next = { ...values }; delete next[target]; return next })
   }
   const raw = original.kind === 'prepare' ? await port.prepare(original.session_id, original.body, original.command_id)
    : original.kind === 'cancel' ? await port.cancel(original.basis.job.id, original.body.expected_revision, original.command_id)
    : await port.interrupt(original.session_id, original.body, original.command_id)
   // Preserve the checked original fact before any scope/access check. A late
   // response belongs to its original actor even after unmount or revocation.
   const acknowledged = decodeTurnCommand(JSON.stringify({ ...original, ack: raw, error: null }), workspace)
   retainTurnCommand(acknowledged)
   if (!valid(token)) return
   await fresh(token, original.kind === 'prepare', original.actor_session_id)
   const saved = await persistTurnCommand(acknowledged, store, saving.guard); releaseTurnCommand(saved)
   const confirmed = await loadCommands()
   if (valid(token)) { setCommands(confirmed); setMessage(original.kind === 'prepare' ? '准备原 ACK 已保存；只预约 Job，未执行。当前状态须独立 GET。' : original.kind === 'cancel' ? '取消原 ACK 已保存；当前控制须独立 GET，取消请求不证明远端已停止。' : '中断原 ACK 已保存；当前 session 与回合控制须分别独立 GET，中断请求不证明远端已停止。') }
  } catch (reason) {
   if (reason instanceof ApiError && reason.status >= 400 && reason.status <= 599 && !heldTurnCommands(workspace).some(v => v.command_id === original.command_id && v.ack)) {
    const rejected = decodeTurnCommand(JSON.stringify({ ...original, error: { status: reason.status,
     code: /^[A-Z][A-Z0-9_]{0,79}$/.test(reason.code ?? '') && reason.code?.trim() === reason.code ? reason.code : null } }), workspace)
    retainTurnCommand(rejected)
    if (valid(token) && !denied(reason)) {
     try { const saved = await persistTurnCommand(rejected, store, saving.guard); releaseTurnCommand(saved); const values = await loadCommands(); if (valid(token)) setCommands(values) } catch { /* Retained original fact remains isolated. */ }
    }
   }
   if (valid(token)) fail(reason)
  } finally { saving.done(); finish(token) }
 }
 const prepare = async () => {
  const input = formRef.current
  if (!allowed || !input || input.actor_session_id !== identity.actor_session_id || input.workspace_id !== workspace || input.fields.session_id !== selected
   || !current || current.id !== selected || current.status !== 'ready' || current.active_turn_id !== null || working.current) return
  try { await execute(turnPrepareCommand(workspace, identity.actor_session_id, current, turnFormBody(input.fields, current.revision))) }
  catch { setError('请保留原 Unicode 文字，填写 Provider ID、0..16 次工具与 1..300 秒；只允许明确选择的精确公开块。') }
 }
 const cancel = async (value: CodexTurnControlView) => {
  if (!ready || working.current || controls[value.id] !== value) return
  await execute(turnCancelCommand(workspace, identity.actor_session_id, value))
 }
 const canInterrupt = (value: CodexTurnControlView) => ready && !working.current && controls[value.id] === value
  && current !== null && current.id === selected && current.id === value.session_id
  && (value.execution === 'terminal' || current.active_turn_id === value.id)
 const interrupt = async (value: CodexTurnControlView) => {
  if (!canInterrupt(value) || !current) return
  await execute(turnInterruptCommand(workspace, identity!.actor_session_id, current, value))
 }
 const saveMemory = async () => {
  if (!ready) return
  const actor = identity.actor_session_id, token = begin(); if (token === null) return
  const saving = writer(() => valid(token))
  try {
   await fresh(token, false, actor)
   // Blind local persistence is recovery, not access to another actor's prompt,
   // a role transition, a remote replay, or consent to any server operation.
   for (const value of heldTurnCommands(workspace)) { const saved = await persistTurnCommand(value, store, saving.guard); releaseTurnCommand(saved) }
   for (const value of heldTurnForms(workspace)) { await persistTurnForm(value, formStore, saving.guard); releaseTurnForm(value) }
   const values = await loadCommands(), drafts = await loadForms()
   await fresh(token, false, actor)
   if (valid(token)) { setCommands(values); setForms(drafts); setMessage('仅保存原 actor 的本机事实和表单；未发送准备或取消请求。') }
  } catch (reason) { if (valid(token)) fail(reason) } finally { saving.done(); finish(token) }
 }
 const held = heldTurnCommands(workspace), heldForms = heldTurnForms(workspace)
 const all = new Map(commands.map(v => [v.command_id, v]))
 for (const value of held) if (!all.get(value.command_id)?.ack || value.ack) all.set(value.command_id, value)
 const allForms = new Map([...forms, ...heldForms].map(v => [v.snapshot_id, v]))
 const latest = new Map<string, TurnForm>()
 for (const value of allForms.values()) if (allowed && value.actor_session_id === identity.actor_session_id && (!latest.has(value.draft_id) || latest.get(value.draft_id)!.sequence < value.sequence)) latest.set(value.draft_id, value)
 const visibleCommands = ready ? [...all.values()].filter(v => v.kind !== 'prepare' || allowed && v.actor_session_id === identity.actor_session_id) : []
 const retained = held.length + heldForms.length
 let canPrepare = false
 try { if (allowed && form?.actor_session_id === identity.actor_session_id && form.workspace_id === workspace && form.fields.session_id === selected
  && current?.id === selected && current.status === 'ready' && current.active_turn_id === null) { turnFormBody(form.fields, current.revision); canPrepare = true } } catch { /* The original form remains editable and saved. */ }
 return { ready, allowed, busy: visible && busy, actor: ready ? identity.actor_session_id : null, selected: ready ? selected : '',
  fields: allowed && form?.actor_session_id === identity.actor_session_id ? form.fields : emptyTurnFields(), forms: [...latest.values()], commands: visibleCommands,
  current: ready ? current : null, page: ready ? page : null, controls: ready ? controls : {}, detail: allowed ? detail : null,
  error: visible ? error : '', message: visible ? message : '', canPrepare,
  dirty: retained > 0 || allForms.size > 0 || [...all.values()].some(v => !v.ack), safe: !working.current && retained === 0, isolated: !working.current && retained > 0,
  retained, canSave: ready && retained > 0, refresh, edit, select, restoreForm, readCurrent, readPage, readControl, readPreparation, execute, prepare, cancel, interrupt, canInterrupt, saveMemory,
  canReplay: (value: TurnCommand) => ready && value.actor_session_id === identity.actor_session_id && (value.kind !== 'prepare' || allowed) && !value.ack && !held.some(v => v.command_id === value.command_id && v.ack),
 }
}
