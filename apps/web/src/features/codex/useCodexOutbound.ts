import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import type { CodexConsentProposalView, CodexConsentView, CodexCurrentSessionView, CodexTurnControlView, CodexTurnResultView } from '../../../../../packages/contracts/generated/codex-turn-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import type { DraftStore, DraftWriteGuard } from '../../workbench/DraftStore'
import { checkedProvider, sameValue } from '../providers/providerSchema'
import { checkedBootstrap } from './bootstrapClient'
import { checkedTurn } from './turnClient'
import { checkedOutbound, outboundTime, turnOutboundClient, type TurnOutboundPort } from './turnOutboundClient'
import { decodeOutboundCommand, dispatchOutboundCommand, makeOutboundCommand, outboundStore, persistOutboundCommand, readOutboundCommand, validateOutboundInput, type OutboundCommand, type OutboundCommandInput } from './turnOutboundCommands'
import { decodeOutboundForm, emptyOutboundFields, outboundFormStore, persistOutboundForm, readOutboundForm, snapshotOutboundForm, type OutboundFields, type OutboundForm } from './turnOutboundForms'
import { heldOutboundCommands, heldOutboundForms, outboundMemoryVersion, releaseOutboundCommand, releaseOutboundForm, retainOutboundCommand, retainOutboundForm, subscribeOutboundMemory } from './turnOutboundMemory'

type PreviewBasis = Extract<OutboundCommand, { kind: 'preview' }>['basis']
const academic = (s: SessionResponse) => s.role === 'author' && !s.active_independent_attempt_id && !s.active_open_book_attempt_id
const denied = (e: unknown) => e instanceof ApiError && ([401, 403].includes(e.status) || ['POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED'].includes(e.code ?? ''))
export function useCodexOutbound(workspace: string, writeAdmitted: boolean, port: TurnOutboundPort = turnOutboundClient, store: DraftStore = outboundStore, formStore: DraftStore = outboundFormStore) {
 const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
 useSyncExternalStore(subscribeOutboundMemory, outboundMemoryVersion, outboundMemoryVersion)
 const admission = useRef(writeAdmitted), revocation = useRef(0)
 if (admission.current && !writeAdmitted) ++revocation.current
 admission.current = writeAdmitted
 const owner = JSON.stringify([workspace, access, revocation.current]), scope = useRef({ owner, port, store, formStore }); scope.current = { owner, port, store, formStore }
 const live = useRef(false), working = useRef(false), sequence = useRef(0), writers = useRef(new Set<AbortController>())
 const [renderScope, setRenderScope] = useState({ owner, port, store, formStore }), [identity, setIdentity] = useState<SessionResponse | null>(null), actorRef = useRef<SessionResponse | null>(null)
 const [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('')
 const [commands, setCommands] = useState<OutboundCommand[]>([]), [forms, setForms] = useState<OutboundForm[]>([])
 const [form, setForm] = useState<OutboundForm | null>(null), formRef = useRef<OutboundForm | null>(null)
 const [basis, setBasis] = useState<PreviewBasis | null>(null), [proposal, setProposal] = useState<CodexConsentProposalView | null>(null)
 const [consent, setConsent] = useState<CodexConsentView | null>(null), [current, setCurrent] = useState<CodexCurrentSessionView | null>(null)
 const [control, setControl] = useState<CodexTurnControlView | null>(null), [result, setResult] = useState<CodexTurnResultView | null>(null)
 const currentScope = () => live.current && scope.current.owner === owner && scope.current.port === port && scope.current.store === store && scope.current.formStore === formStore && access === getSessionGeneration()
 const valid = (token: number) => currentScope() && sequence.current === token
 const visible = renderScope.owner === owner && renderScope.port === port && renderScope.store === store && renderScope.formStore === formStore
 const ready = visible && identity !== null, allowed = ready && writeAdmitted && academic(identity)
 const clearReads = () => { setBasis(null); setProposal(null); setConsent(null); setCurrent(null); setControl(null); setResult(null) }
 const hide = () => { actorRef.current = null; setIdentity(null); clearReads(); setCommands([]); setForms([]) }
 const begin = () => { if (!currentScope() || !workspace || working.current) return null; working.current = true; setBusy(true); setError(''); setMessage(''); return ++sequence.current }
 const finish = (token: number) => { if (valid(token)) { working.current = false; setBusy(false) } }
 const fail = (reason: unknown) => {
  if (denied(reason)) hide()
  setError(denied(reason) ? '外发操作的当前权限或原 actor 已变化；原命令与表单保留。'
   : reason instanceof ApiError && reason.status === 412 ? '外发版本已变化（412）；原 key、完整 body 和只读基准保留，请独立 GET。'
   : reason instanceof ApiError && reason.status === 409 ? '外发绑定冲突（409）；原命令保留，不自动换 key 或新建许可。'
   : reason instanceof ApiError && ['CODEX_INPUT_PROOF_UNAVAILABLE', 'CODEX_RUNTIME_UNAVAILABLE'].includes(reason.code ?? '') ? `BLOCKED：${reason.code}；没有完整证明或可用执行器，未宣称已执行。原命令保留。`
   : '外发结果或本机保存未知；原命令保留，只能显式回放原 key。')
 }
 async function fresh(token: number, subject: boolean, actor?: string) {
  const value = checkedBootstrap<SessionResponse>('SessionResponse', await port.session())
  if (!valid(token)) throw new Error('Scope changed')
  if (value.workspace_id !== workspace || actor && value.actor_session_id !== actor || subject && (!writeAdmitted || !academic(value))) { hide(); throw new ApiError(403, 'Original outbound access changed') }
  actorRef.current = value; setIdentity(value); return value
 }
 function writer(check: () => boolean) {
  const c = new AbortController(); writers.current.add(c); const unsubscribe = subscribeSessionAccess(() => c.abort())
  return { guard: { allowed: check, signal: c.signal } satisfies DraftWriteGuard, done: () => { unsubscribe(); writers.current.delete(c) } }
 }
 const loadCommands = async () => Object.values(await store.load(workspace)).map(v => readOutboundCommand(v, workspace))
 const loadForms = async () => Object.values(await formStore.load(workspace)).map(v => readOutboundForm(v, workspace))
 useEffect(() => {
  live.current = true; ++sequence.current; working.current = false; setRenderScope({ owner, port, store, formStore }); hide(); setForm(null); formRef.current = null; setBusy(false); setError(''); setMessage('')
  return () => { live.current = false; ++sequence.current; working.current = false; for (const value of writers.current) value.abort() }
 }, [owner, port, store, formStore])
 const refresh = async () => {
  const token = begin(); if (token === null) return
  hide()
  try { const session = await fresh(token, false), values = await loadCommands(), drafts = await loadForms(); await fresh(token, false, session.actor_session_id)
   if (valid(token)) { setCommands(values); setForms(drafts); setMessage('外发本机记录已读取；只恢复原事实，没有自动 POST。') }
  } catch (e) { if (valid(token)) fail(e) } finally { finish(token) }
 }
 const edit = (patch: Partial<OutboundFields>) => {
  if (!ready || !currentScope() || !allowed && Object.keys(patch).some(k => k !== 'turn_id')) return
  const previous = formRef.current?.actor_session_id === identity.actor_session_id ? formRef.current : null
  const next = snapshotOutboundForm(workspace, identity.actor_session_id, { ...(previous?.fields ?? emptyOutboundFields()), ...patch }, previous)
  formRef.current = next; setForm(next); retainOutboundForm(next)
  if (Object.keys(patch).some(k => ['preparation_id', 'proposal_id', 'consent_id', 'session_id', 'turn_id'].includes(k))) clearReads()
  const saving = writer(() => currentScope() && actorRef.current?.actor_session_id === next.actor_session_id)
  const sameActor = () => currentScope() && actorRef.current?.actor_session_id === next.actor_session_id
  void persistOutboundForm(next, formStore, saving.guard).then(() => { releaseOutboundForm(next); if (sameActor()) setForms(v => [...v.filter(f => f.snapshot_id !== next.snapshot_id), next]) })
   .catch(() => { if (sameActor()) setError('外发表单尚未落盘；原输入保留在隔离内存，离开前请仅保存本机事实。') }).finally(saving.done)
 }
 const restore = async (value: OutboundForm) => {
  if (!allowed || value.workspace_id !== workspace || value.actor_session_id !== identity.actor_session_id) return
  const actor = identity.actor_session_id, token = begin(); if (token === null) return
  const prior = formRef.current?.snapshot_id, saving = writer(() => valid(token) && actorRef.current?.actor_session_id === actor && academic(actorRef.current) && writeAdmitted)
  try {
   const original = decodeOutboundForm(JSON.stringify(value), workspace); await fresh(token, true, actor)
   const record = (await formStore.load(workspace))[original.snapshot_id]; if (!valid(token)) return
   const held = heldOutboundForms(workspace).find(v => v.snapshot_id === original.snapshot_id), actual = record ? readOutboundForm(record, workspace) : held
   if (!actual || !sameValue(actual, original) || held && !sameValue(held, original)) throw new Error('Original form changed')
   await fresh(token, true, actor)
   const next = snapshotOutboundForm(workspace, actor, original.fields, null); retainOutboundForm(next)
   await persistOutboundForm(next, formStore, saving.guard); releaseOutboundForm(next); await fresh(token, true, actor)
   if (valid(token)) { setForms(v => [...v, next]); if (formRef.current?.snapshot_id === prior) { formRef.current = next; setForm(next); clearReads() }; setMessage('原外发表单已核验并保存独立分支；较新的输入保持，没有 POST。') }
  } catch (e) { if (valid(token)) fail(e) } finally { saving.done(); finish(token) }
 }
 const read = async (kind: 'basis' | 'proposal' | 'consent' | 'current' | 'control' | 'result') => {
  if (!ready || kind !== 'control' && !allowed || !form || form.actor_session_id !== identity.actor_session_id) return
  const captured = form, f = captured.fields, actor = identity.actor_session_id, subject = kind !== 'control', token = begin(); if (token === null) return
  if (kind === 'basis') setBasis(null); if (kind === 'proposal') setProposal(null); if (kind === 'consent') setConsent(null); if (kind === 'current') setCurrent(null); if (kind === 'control') setControl(null); if (kind === 'result') setResult(null)
  try {
   await fresh(token, subject, actor)
   let deliver: () => void
   if (kind === 'basis') {
    const p = checkedTurn('CodexTurnPreparationView', await port.preparation(f.preparation_id)), c = checkedTurn('CodexTurnControlView', await port.control(p.turn_id)), config = checkedProvider<PreviewBasis['provider']>('ProviderConfigView', await port.config(p.request.provider_id))
    if (p.id !== f.preparation_id || c.id !== p.turn_id || c.session_id !== p.session_id || c.job.id !== p.job.id || config.id !== p.request.provider_id) throw new Error('Wrong preview basis')
    deliver = () => setBasis({ preparation: p, control: c, provider: config })
   } else if (kind === 'proposal') { const v = checkedOutbound('CodexConsentProposalView', await port.proposal(f.proposal_id)); if (v.id !== f.proposal_id) throw new Error('Wrong proposal'); deliver = () => setProposal(v) }
   else if (kind === 'consent') { const v = checkedOutbound('CodexConsentView', await port.consent(f.consent_id)); if (v.id !== f.consent_id) throw new Error('Wrong consent'); deliver = () => setConsent(v) }
   else if (kind === 'current') { const v = checkedBootstrap<CodexCurrentSessionView>('CodexCurrentSessionView', await port.current(f.session_id)); if (v.id !== f.session_id) throw new Error('Wrong current'); deliver = () => setCurrent(v) }
   else if (kind === 'control') { const v = checkedTurn('CodexTurnControlView', await port.control(f.turn_id)); if (v.id !== f.turn_id) throw new Error('Wrong control'); deliver = () => setControl(v) }
   else { if (!basis || basis.preparation.turn_id !== f.turn_id) throw new Error('Read original preparation before result')
    const v = checkedOutbound('CodexTurnResultView', await port.result(f.turn_id)); if (v.control.id !== f.turn_id || v.preparation_id !== basis.preparation.id || v.control.session_id !== basis.preparation.session_id || v.control.job.id !== basis.preparation.job.id) throw new Error('Wrong result'); deliver = () => setResult(v) }
   await fresh(token, subject, actor)
   if (valid(token) && formRef.current?.snapshot_id === captured.snapshot_id) deliver()
  } catch (e) { if (valid(token)) fail(e) } finally { finish(token) }
 }
 async function execute(command: OutboundCommand, existingToken?: number) {
  if (!ready || command.workspace_id !== workspace || command.actor_session_id !== identity.actor_session_id || command.ack || command.kind !== 'revoke' && !allowed) return
  const token = existingToken ?? begin(); if (token === null) return
  const saving = writer(() => valid(token)), subject = command.kind !== 'revoke'
  try {
   await fresh(token, subject, command.actor_session_id); retainOutboundCommand(command)
   const saved = await dispatchOutboundCommand(command, port, store, { guard: saving.guard,
    beforePost: async () => { const values = await loadCommands(); await fresh(token, subject, command.actor_session_id); if (valid(token)) setCommands(values) },
    onAck: retainOutboundCommand, beforeDelivery: async () => { await fresh(token, subject, command.actor_session_id) } })
   releaseOutboundCommand(saved); const values = await loadCommands(); await fresh(token, subject, command.actor_session_id)
   if (valid(token)) { setCommands(values); setMessage(`外发 ${command.kind} 原 ACK 已保存；不是当前 GET，也不证明模型或工具已完成。`) }
  } catch (e) {
   if (e instanceof ApiError && e.status >= 400 && e.status <= 599 && !heldOutboundCommands(workspace).some(v => v.command_id === command.command_id && v.ack)) {
    const rejected = decodeOutboundCommand(JSON.stringify({ ...command, error: { status: e.status, code: /^[A-Z][A-Z0-9_]{0,79}$/.test(e.code ?? '') && e.code?.trim() === e.code ? e.code : null } }), workspace)
    retainOutboundCommand(rejected)
    if (valid(token) && !denied(e)) { try { const saved = await persistOutboundCommand(rejected, store, saving.guard); releaseOutboundCommand(saved); const values = await loadCommands(); if (valid(token)) setCommands(values) } catch { /* Keep original command isolated. */ } }
   }
   if (valid(token)) fail(e)
  } finally { saving.done(); finish(token) }
 }
 const candidate = (kind: OutboundCommand['kind']): OutboundCommandInput => {
  const f = form?.fields; if (!f || !ready || form.actor_session_id !== identity.actor_session_id) throw new Error('No original form')
  if (kind === 'revoke') { if (!control?.consent_control || control.id !== f.turn_id) throw new Error('Read actual safe consent control'); return { kind, basis: control, body: { expected_revision: control.consent_control.revision } } }
  if (!allowed || !basis || basis.preparation.id !== f.preparation_id || basis.preparation.actor_session_id !== identity.actor_session_id) throw new Error('Read own preparation')
  const p = basis.preparation
  if (kind === 'preview') {
   if ([f.max_input_tokens, f.max_output_tokens, f.max_cost_usd].some(v => v.trim() !== v) || !/^[1-9][0-9]*$/.test(f.max_input_tokens) || !/^[1-9][0-9]*$/.test(f.max_output_tokens) || f.max_cost_usd !== '' && !/^(0|[1-9][0-9]*)(\.[0-9]+)?$/.test(f.max_cost_usd)) throw new Error('Explicit budget required')
   const expires = outboundTime(f.expires_at), now = Date.now(); if (expires <= now || expires > now + 600000) throw new Error('Explicit expiry must be within ten minutes')
   return { kind, basis, body: checkedOutbound('CodexOutboundPreviewWrite', { preparation_id: p.id, preparation_sha256: p.preparation_sha256, expected_job_revision: basis.control.job_revision, expected_provider_revision: basis.provider.revision,
    budget: { max_input_tokens: Number(f.max_input_tokens), max_output_tokens: Number(f.max_output_tokens), max_provider_calls: 1, max_search_calls: 0, max_cost_usd: f.max_cost_usd === '' ? null : Number(f.max_cost_usd) }, expires_at: f.expires_at }) }
  }
  if (kind === 'grant') { if (!proposal || proposal.id !== f.proposal_id || outboundTime(proposal.summary.expires_at) <= Date.now()) throw new Error('Read current unexpired proposal'); return { kind, basis: { preparation: p, proposal }, body: { proposal_id: proposal.id, proposal_sha256: proposal.proposal_sha256 } } }
  if (!consent || consent.id !== f.consent_id || !current || current.id !== f.session_id || outboundTime(consent.expires_at) <= Date.now()) throw new Error('Read current original consent and session')
  return { kind, basis: { preparation: p, current, consent }, body: { preparation_id: p.id, preparation_sha256: p.preparation_sha256, consent_id: consent.id, expected_session_revision: current.revision } }
 }
 const submit = async (kind: OutboundCommand['kind']) => {
  const token = begin(); if (token === null) return
  try { if (!identity) throw new Error('Read permissions'); const command = makeOutboundCommand(workspace, identity.actor_session_id, candidate(kind)); await execute(command, token) }
  catch (e) { if (valid(token)) fail(e); finish(token) }
 }
 const saveMemory = async () => {
  if (!ready) return
  const actor = identity.actor_session_id, token = begin(); if (token === null) return
  const saving = writer(() => valid(token))
  try { await fresh(token, false, actor)
   for (const value of heldOutboundCommands(workspace)) { const saved = await persistOutboundCommand(value, store, saving.guard); releaseOutboundCommand(saved) }
   for (const value of heldOutboundForms(workspace)) { await persistOutboundForm(value, formStore, saving.guard); releaseOutboundForm(value) }
   const values = await loadCommands(), drafts = await loadForms(); await fresh(token, false, actor)
   if (valid(token)) { setCommands(values); setForms(drafts); setMessage('仅保存外发原 actor 的本机事实和表单；未发送任何 POST。') }
  } catch (e) { if (valid(token)) fail(e) } finally { saving.done(); finish(token) }
 }
 const held = heldOutboundCommands(workspace), heldForms = heldOutboundForms(workspace), all = new Map(commands.map(v => [v.command_id, v]))
 for (const value of held) if (!all.get(value.command_id)?.ack || value.ack) all.set(value.command_id, value)
 const allForms = new Map([...forms, ...heldForms].map(v => [v.snapshot_id, v])), latest = new Map<string, OutboundForm>()
 for (const value of allForms.values()) if (allowed && value.actor_session_id === identity.actor_session_id && (!latest.has(value.draft_id) || latest.get(value.draft_id)!.sequence < value.sequence)) latest.set(value.draft_id, value)
 const retained = held.length + heldForms.length
 const can = (kind: OutboundCommand['kind']) => { try { if (!identity || working.current) return false; validateOutboundInput(workspace, identity.actor_session_id, candidate(kind)); return true } catch { return false } }
 return { ready, allowed, busy: visible && busy, actor: ready ? identity.actor_session_id : null,
  fields: ready && form?.actor_session_id === identity.actor_session_id ? form.fields : emptyOutboundFields(), forms: [...latest.values()], commands: ready ? [...all.values()].filter(v => v.kind === 'revoke' || allowed && v.actor_session_id === identity.actor_session_id) : [],
  basis: allowed ? basis : null, proposal: allowed ? proposal : null, consent: allowed ? consent : null, current: allowed ? current : null, control: ready ? control : null, result: allowed ? result : null,
  error: visible ? error : '', message: visible ? message : '', retained, dirty: retained > 0 || allForms.size > 0 || [...all.values()].some(v => !v.ack), safe: !working.current && retained === 0, isolated: !working.current && retained > 0,
  can, canSave: ready && retained > 0, canReplay: (c: OutboundCommand) => ready && c.actor_session_id === identity.actor_session_id && (c.kind === 'revoke' || allowed) && !c.ack && !held.some(v => v.command_id === c.command_id && v.ack),
  refresh, edit, restore, read, execute, submit, saveMemory }
}
