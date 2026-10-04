import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import type { CodexTurnControlView, GenericApprovalView } from '../../../../../packages/contracts/generated/codex-turn-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import type { DraftStore, DraftWriteGuard } from '../../workbench/DraftStore'
import { sameValue } from '../providers/providerSchema'
import { checkedBootstrap } from './bootstrapClient'
import { checkedTurn } from './turnClient'
import { checkedApproval, approvalClient, type ApprovalPort } from './approvalClient'
import { decodeApprovalCommand, dispatchApprovalCommand, makeApprovalCommand, approvalStore, persistApprovalCommand, readApprovalCommand, type ApprovalCommand } from './approvalCommands'
import { decodeApprovalForm, emptyApprovalFields, approvalFormStore, persistApprovalForm, readApprovalForm, snapshotApprovalForm, type ApprovalFields, type ApprovalForm } from './approvalForms'
import { heldApprovalCommands, heldApprovalForms, approvalMemoryVersion, releaseApprovalCommand, releaseApprovalForm, retainApprovalCommand, retainApprovalForm, subscribeApprovalMemory } from './approvalMemory'

const academic = (s: SessionResponse) => s.role === 'author' && !s.active_independent_attempt_id && !s.active_open_book_attempt_id
const denied = (e: unknown) => e instanceof ApiError && ([401, 403].includes(e.status) || ['POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED'].includes(e.code ?? ''))
export function useCodexApprovals(workspace: string, writeAdmitted: boolean, port: ApprovalPort = approvalClient, store: DraftStore = approvalStore, formStore: DraftStore = approvalFormStore) {
 const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
 useSyncExternalStore(subscribeApprovalMemory, approvalMemoryVersion, approvalMemoryVersion)
 const admission = useRef(writeAdmitted), revocation = useRef(0)
 if (admission.current && !writeAdmitted) ++revocation.current
 admission.current = writeAdmitted
 const owner = JSON.stringify([workspace, access, revocation.current]), scope = useRef({ owner, port, store, formStore }); scope.current = { owner, port, store, formStore }
 const live = useRef(false), working = useRef(false), sequence = useRef(0), writers = useRef(new Set<AbortController>())
 const [renderScope, setRenderScope] = useState({ owner, port, store, formStore }), [identity, setIdentity] = useState<SessionResponse | null>(null), actorRef = useRef<SessionResponse | null>(null)
 const [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('')
 const [commands, setCommands] = useState<ApprovalCommand[]>([]), [forms, setForms] = useState<ApprovalForm[]>([])
 const [form, setForm] = useState<ApprovalForm | null>(null), formRef = useRef<ApprovalForm | null>(null)
 const [control, setControl] = useState<CodexTurnControlView | null>(null), [detail, setDetail] = useState<GenericApprovalView | null>(null)
 const currentScope = () => live.current && scope.current.owner === owner && scope.current.port === port && scope.current.store === store && scope.current.formStore === formStore && access === getSessionGeneration()
 const valid = (token: number) => currentScope() && sequence.current === token
 const visible = renderScope.owner === owner && renderScope.port === port && renderScope.store === store && renderScope.formStore === formStore
 const ready = visible && identity !== null, allowed = ready && writeAdmitted && academic(identity)
 const clearReads = () => { setControl(null); setDetail(null) }
 const hide = () => { actorRef.current = null; setIdentity(null); clearReads(); setCommands([]); setForms([]) }
 const begin = () => { if (!currentScope() || !workspace || working.current) return null; working.current = true; setBusy(true); setError(''); setMessage(''); return ++sequence.current }
 const finish = (token: number) => { if (valid(token)) { working.current = false; setBusy(false) } }
 const fail = (reason: unknown, reading = false) => {
  if (denied(reason)) hide()
  setError(denied(reason) ? '审批当前权限或原 actor 已变化；原命令和表单隔离保留。'
   : reason instanceof ApiError && reason.status === 503 ? 'BLOCKED：当前操作或固定运行证明不可用；没有执行操作，也未替换原命令。'
   : reason instanceof ApiError && reason.status === 412 ? '审批版本已变化（412）；原 key、完整 body 和只读基准保留，请独立 GET。'
   : reason instanceof ApiError && reason.status === 409 ? '审批绑定或阶段冲突（409）；原命令保留，不自动换 key 或重新批准。'
   : reading ? '当前审批读取未完成或完整绑定不符；没有交付新详情，原记录保留。'
   : '审批结果或本机保存未知；原命令保留，只能显式回放原 key。')
 }
 async function fresh(token: number, subject: boolean, actor?: string) {
  const value = checkedBootstrap<SessionResponse>('SessionResponse', await port.session())
  if (!valid(token)) throw new Error('Scope changed')
  if (value.workspace_id !== workspace || actor && value.actor_session_id !== actor || subject && (!writeAdmitted || !academic(value))) { hide(); throw new ApiError(403, 'Original approval access changed') }
  actorRef.current = value; setIdentity(value); return value
 }
 function writer(check: () => boolean) {
  const c = new AbortController(); writers.current.add(c); const unsubscribe = subscribeSessionAccess(() => c.abort())
  return { guard: { allowed: check, signal: c.signal } satisfies DraftWriteGuard, done: () => { unsubscribe(); writers.current.delete(c) } }
 }
 const loadCommands = async () => Object.values(await store.load(workspace)).map(v => readApprovalCommand(v, workspace))
 const loadForms = async () => Object.values(await formStore.load(workspace)).map(v => readApprovalForm(v, workspace))
 useEffect(() => {
  live.current = true; ++sequence.current; working.current = false; setRenderScope({ owner, port, store, formStore }); hide(); setForm(null); formRef.current = null; setBusy(false); setError(''); setMessage('')
  return () => { live.current = false; ++sequence.current; working.current = false; for (const value of writers.current) value.abort() }
 }, [owner, port, store, formStore])
 const refresh = async () => {
  const token = begin(); if (token === null) return
  hide()
  try { const session = await fresh(token, false), values = await loadCommands(), drafts = await loadForms(); await fresh(token, false, session.actor_session_id)
   if (valid(token)) { setCommands(values); setForms(drafts); setMessage('审批本机记录已读取；只恢复原事实，没有自动 POST。') }
  } catch (e) { if (valid(token)) fail(e) } finally { finish(token) }
 }
 const edit = (patch: Partial<ApprovalFields>) => {
  if (!ready || !currentScope() || working.current) return
  const previous = formRef.current?.actor_session_id === identity.actor_session_id ? formRef.current : null
  const next = snapshotApprovalForm(workspace, identity.actor_session_id, { ...(previous?.fields ?? emptyApprovalFields()), ...patch }, previous)
  formRef.current = next; setForm(next); retainApprovalForm(next); clearReads()
  const sameActor = () => currentScope() && actorRef.current?.actor_session_id === next.actor_session_id
  const saving = writer(sameActor)
  void persistApprovalForm(next, formStore, saving.guard).then(() => { releaseApprovalForm(next); if (sameActor()) setForms(v => [...v.filter(f => f.snapshot_id !== next.snapshot_id), next]) })
   .catch(() => { if (sameActor()) setError('审批表单尚未落盘；原输入保留在隔离内存，离开前请仅保存本机事实。') }).finally(saving.done)
 }
 const restore = async (value: ApprovalForm) => {
  if (!ready || value.workspace_id !== workspace || value.actor_session_id !== identity.actor_session_id) return
  const actor = identity.actor_session_id, token = begin(); if (token === null) return
  const prior = formRef.current?.snapshot_id, saving = writer(() => valid(token) && actorRef.current?.actor_session_id === actor)
  try {
   const original = decodeApprovalForm(JSON.stringify(value), workspace); await fresh(token, false, actor)
   const record = (await formStore.load(workspace))[original.snapshot_id]; if (!valid(token)) return
   const held = heldApprovalForms(workspace).find(v => v.snapshot_id === original.snapshot_id), actual = record ? readApprovalForm(record, workspace) : held
   if (!actual || !sameValue(actual, original) || held && !sameValue(held, original)) throw new Error('Original form changed')
   await fresh(token, false, actor)
   const next = snapshotApprovalForm(workspace, actor, original.fields, null); retainApprovalForm(next)
   await persistApprovalForm(next, formStore, saving.guard); releaseApprovalForm(next); await fresh(token, false, actor)
   if (valid(token)) { setForms(v => [...v, next]); if (formRef.current?.snapshot_id === prior) { formRef.current = next; setForm(next); clearReads() }; setMessage('原审批表单已核验并保存独立分支；没有 POST。') }
  } catch (e) { if (valid(token)) fail(e) } finally { saving.done(); finish(token) }
 }
 const readControl = async () => {
  if (!ready || !form || form.actor_session_id !== identity.actor_session_id) return
  const captured = form, actor = identity.actor_session_id, token = begin(); if (token === null) return
  clearReads()
  try {
   await fresh(token, false, actor)
   const v = checkedTurn('CodexTurnControlView', await port.control(captured.fields.turn_id))
   if (v.id !== captured.fields.turn_id) throw new Error('Wrong turn control')
   await fresh(token, false, actor)
   if (valid(token) && formRef.current?.snapshot_id === captured.snapshot_id) setControl(v)
  } catch (e) { if (valid(token)) fail(e, true) } finally { finish(token) }
 }
 const read = async (id: string, source: CodexTurnControlView | GenericApprovalView | null = control) => {
  if (!allowed || !source) return
  const actor = identity.actor_session_id, token = begin(); if (token === null) return
  setDetail(null)
  try {
   const basis = 'approval_controls' in source ? source.approval_controls.find(a => a.id === id) : source.id === id ? source : null
   if (!basis) throw new Error('Missing full approval control')
   await fresh(token, true, actor)
   const v = checkedApproval('GenericApprovalView', await port.read(id))
   if (v.id !== id || v.operation_sha256 !== basis.operation_sha256 || v.actor_session_id !== source.actor_session_id || v.session_id !== source.session_id
    || v.turn_id !== ('approval_controls' in source ? source.id : source.turn_id) || v.job.id !== source.job.id) throw new Error('Wrong approval source')
   await fresh(token, true, actor)
   if (valid(token)) setDetail(v)
  } catch (e) { if (valid(token)) fail(e, true) } finally { finish(token) }
 }
 async function execute(command: ApprovalCommand, existingToken?: number) {
  if (!ready || command.workspace_id !== workspace || command.actor_session_id !== identity.actor_session_id || command.ack || command.body.decision === 'approve_once' && !allowed) return
  const token = existingToken ?? begin(); if (token === null) return
  const saving = writer(() => valid(token)), subject = command.body.decision === 'approve_once'
  try {
   await fresh(token, subject, command.actor_session_id); retainApprovalCommand(command)
   const saved = await dispatchApprovalCommand(command, port, store, { guard: saving.guard,
    beforePost: async () => { const values = await loadCommands(); await fresh(token, subject, command.actor_session_id); if (valid(token)) setCommands(values) },
    onAck: retainApprovalCommand, beforeDelivery: async () => { await fresh(token, subject, command.actor_session_id) } })
   releaseApprovalCommand(saved); const values = await loadCommands(); await fresh(token, subject, command.actor_session_id)
   if (valid(token)) { setCommands(values); setMessage('审批原 ACK 已保存：仅是决定事实；执行状态须独立 GET，拒绝也不证明远端已经停止。') }
  } catch (e) {
   if (e instanceof ApiError && e.status >= 400 && e.status <= 599 && !heldApprovalCommands(workspace).some(v => v.command_id === command.command_id && v.ack)) {
    const rejected = decodeApprovalCommand(JSON.stringify({ ...command, error: { status: e.status, code: /^[A-Z][A-Z0-9_]{0,79}$/.test(e.code ?? '') && e.code?.trim() === e.code ? e.code : null } }), workspace)
    retainApprovalCommand(rejected)
    if (valid(token) && !denied(e)) { try { const saved = await persistApprovalCommand(rejected, store, saving.guard); releaseApprovalCommand(saved); const values = await loadCommands(); if (valid(token)) setCommands(values) } catch { /* Original remains isolated. */ } }
   }
   if (valid(token)) fail(e)
  } finally { saving.done(); finish(token) }
 }
 const held = heldApprovalCommands(workspace), heldForms = heldApprovalForms(workspace), all = new Map(commands.map(v => [v.command_id, v]))
 for (const value of held) if (!all.get(value.command_id)?.ack || value.ack) all.set(value.command_id, value)
 const hasCommand = (id: string) => [...all.values()].some(c => c.actor_session_id === identity?.actor_session_id && c.target_id === id)
 const decide = async (id: string, decision: 'approve_once' | 'decline') => {
  if (!ready || hasCommand(id) || decision === 'approve_once' && !allowed) return
  const basis: ApprovalCommand['basis'] | null = decision === 'decline' && control ? { kind: 'decline', control } : decision === 'approve_once' && detail?.id === id ? { kind: 'approve', view: detail } : null
  if (!basis) return
  const token = begin(); if (token === null) return
  try { await execute(makeApprovalCommand(workspace, identity.actor_session_id, basis, id), token) } catch (e) { if (valid(token)) fail(e); finish(token) }
 }
 const saveMemory = async () => {
  if (!ready) return
  const actor = identity.actor_session_id, token = begin(); if (token === null) return
  const saving = writer(() => valid(token))
  try { await fresh(token, false, actor)
   for (const value of heldApprovalCommands(workspace)) { const saved = await persistApprovalCommand(value, store, saving.guard); releaseApprovalCommand(saved) }
   for (const value of heldApprovalForms(workspace)) { await persistApprovalForm(value, formStore, saving.guard); releaseApprovalForm(value) }
   const values = await loadCommands(), drafts = await loadForms(); await fresh(token, false, actor)
   if (valid(token)) { setCommands(values); setForms(drafts); setMessage('仅保存审批原 actor 的本机事实和表单；未发送任何 POST。') }
  } catch (e) { if (valid(token)) fail(e) } finally { saving.done(); finish(token) }
 }
 const allForms = new Map([...forms, ...heldForms].map(v => [v.snapshot_id, v])), latest = new Map<string, ApprovalForm>()
 for (const value of allForms.values()) if (ready && value.actor_session_id === identity.actor_session_id && (!latest.has(value.draft_id) || latest.get(value.draft_id)!.sequence < value.sequence)) latest.set(value.draft_id, value)
 const retained = held.length + heldForms.length
 return { ready, allowed, busy: visible && busy, actor: ready ? identity.actor_session_id : null,
  fields: ready && form?.actor_session_id === identity.actor_session_id ? form.fields : emptyApprovalFields(), forms: [...latest.values()],
  commands: ready ? [...all.values()].filter(c => c.body.decision === 'decline' || allowed && c.actor_session_id === identity.actor_session_id) : [],
  control: ready ? control : null, detail: allowed ? detail : null,
  error: visible ? error : '', message: visible ? message : '', retained, dirty: retained > 0 || allForms.size > 0 || [...all.values()].some(v => !v.ack), safe: !working.current && retained === 0, isolated: !working.current && retained > 0,
  canSave: ready && retained > 0, hasCommand, canReplay: (c: ApprovalCommand) => ready && c.actor_session_id === identity.actor_session_id && !c.ack && (c.body.decision === 'decline' || allowed) && !held.some(v => v.command_id === c.command_id && v.ack),
  refresh, edit, restore, readControl, read, execute, decide, saveMemory }
}
