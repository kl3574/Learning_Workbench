import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import type { CodexArtifactEntry, CodexArtifactManifestView, CodexArtifactImportView } from '../../../../../packages/contracts/generated/codex-turn-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import type { DraftStore, DraftWriteGuard } from '../../workbench/DraftStore'
import { sameValue } from '../providers/providerSchema'
import { checkedBootstrap } from './bootstrapClient'
import { checkedArtifact, artifactHash, artifactClient, type ArtifactPort } from './artifactClient'
import { decodeArtifactCommand, dispatchArtifactCommand, makeArtifactCommand, artifactStore, persistArtifactCommand, readArtifactCommand, readArtifactImport, type ArtifactCommand } from './artifactCommands'
import { decodeArtifactForm, emptyArtifactFields, artifactFormStore, persistArtifactForm, readArtifactForm, snapshotArtifactForm, type ArtifactFields, type ArtifactForm } from './artifactForms'
import { heldArtifactCommands, heldArtifactForms, artifactMemoryVersion, releaseArtifactCommand, releaseArtifactForm, retainArtifactCommand, retainArtifactForm, subscribeArtifactMemory } from './artifactMemory'

const academic = (s: SessionResponse) => s.role === 'author' && !s.active_independent_attempt_id && !s.active_open_book_attempt_id
const denied = (e: unknown) => e instanceof ApiError && ([401, 403].includes(e.status) || ['POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED'].includes(e.code ?? ''))
export function useCodexArtifacts(workspace: string, writeAdmitted: boolean, port: ArtifactPort = artifactClient, store: DraftStore = artifactStore, formStore: DraftStore = artifactFormStore) {
 const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
 useSyncExternalStore(subscribeArtifactMemory, artifactMemoryVersion, artifactMemoryVersion)
 const admission = useRef(writeAdmitted), revocation = useRef(0)
 if (admission.current && !writeAdmitted) ++revocation.current
 admission.current = writeAdmitted
 const owner = JSON.stringify([workspace, access, revocation.current]), scope = useRef({ owner, port, store, formStore }); scope.current = { owner, port, store, formStore }
 const live = useRef(false), working = useRef(false), sequence = useRef(0), writers = useRef(new Set<AbortController>())
 const [renderScope, setRenderScope] = useState({ owner, port, store, formStore }), [identity, setIdentity] = useState<SessionResponse | null>(null), actorRef = useRef<SessionResponse | null>(null)
 const [busy, setBusy] = useState(false), [error, setError] = useState(''), [message, setMessage] = useState('')
 const [commands, setCommands] = useState<ArtifactCommand[]>([]), [forms, setForms] = useState<ArtifactForm[]>([])
 const [form, setForm] = useState<ArtifactForm | null>(null), formRef = useRef<ArtifactForm | null>(null)
 const [manifest, setManifest] = useState<CodexArtifactManifestView | null>(null)
 const [aggregate, setAggregate] = useState<{ command: ArtifactCommand; view: CodexArtifactImportView } | null>(null)
 const urls = useRef(new Set<string>())
 const currentScope = () => live.current && scope.current.owner === owner && scope.current.port === port && scope.current.store === store && scope.current.formStore === formStore && access === getSessionGeneration()
 const valid = (token: number) => currentScope() && sequence.current === token
 const visible = renderScope.owner === owner && renderScope.port === port && renderScope.store === store && renderScope.formStore === formStore
 const ready = visible && identity !== null, allowed = ready && writeAdmitted && academic(identity)
 const clearReads = () => { setManifest(null); setAggregate(null); for (const url of urls.current) URL.revokeObjectURL(url); urls.current.clear() }
 const hide = () => { actorRef.current = null; setIdentity(null); clearReads(); setCommands([]); setForms([]) }
 const begin = () => { if (!currentScope() || !workspace || working.current) return null; working.current = true; setBusy(true); setError(''); setMessage(''); return ++sequence.current }
 const finish = (token: number) => { if (valid(token)) { working.current = false; setBusy(false) } }
 const fail = (reason: unknown) => {
  if (denied(reason)) hide()
  setError(denied(reason) ? '产物操作的当前权限或原 actor 已变化；原命令与表单保留。'
   : reason instanceof ApiError && reason.status === 412 ? '产物版本已变化（412）；原 key、完整 body 和只读基准保留，请独立 GET。'
   : reason instanceof ApiError && reason.status === 409 ? '产物绑定冲突（409）；原命令保留，不自动换 key 或替换选择。'
   : reason instanceof ApiError && ['CODEX_INPUT_PROOF_UNAVAILABLE', 'CODEX_RUNTIME_UNAVAILABLE'].includes(reason.code ?? '') ? `BLOCKED：${reason.code}；没有完整证明或可用执行器，未宣称已执行。原命令保留。`
   : '产物结果或本机保存未知；原命令保留，只能显式回放原 key。')
 }
 async function fresh(token: number, subject: boolean, actor?: string) {
  const value = checkedBootstrap<SessionResponse>('SessionResponse', await port.session())
  if (!valid(token)) throw new Error('Scope changed')
  if (value.workspace_id !== workspace || actor && value.actor_session_id !== actor || subject && (!writeAdmitted || !academic(value))) { hide(); throw new ApiError(403, 'Original artifact access changed') }
  actorRef.current = value; setIdentity(value); return value
 }
 function writer(check: () => boolean) {
  const c = new AbortController(); writers.current.add(c); const unsubscribe = subscribeSessionAccess(() => c.abort())
  return { guard: { allowed: check, signal: c.signal } satisfies DraftWriteGuard, done: () => { unsubscribe(); writers.current.delete(c) } }
 }
 const loadCommands = async () => Object.values(await store.load(workspace)).map(v => readArtifactCommand(v, workspace))
 const loadForms = async () => Object.values(await formStore.load(workspace)).map(v => readArtifactForm(v, workspace))
 useEffect(() => {
  live.current = true; ++sequence.current; working.current = false; setRenderScope({ owner, port, store, formStore }); hide(); setForm(null); formRef.current = null; setBusy(false); setError(''); setMessage('')
  return () => { live.current = false; ++sequence.current; working.current = false; for (const value of writers.current) value.abort(); for (const url of urls.current) URL.revokeObjectURL(url); urls.current.clear() }
 }, [owner, port, store, formStore])
 const refresh = async () => {
  const token = begin(); if (token === null) return
  hide()
  try { const session = await fresh(token, false), values = await loadCommands(), drafts = await loadForms(); await fresh(token, false, session.actor_session_id)
   if (valid(token)) { setCommands(values); setForms(drafts); setMessage('产物本机记录已读取；只恢复原事实，没有自动 POST。') }
  } catch (e) { if (valid(token)) fail(e) } finally { finish(token) }
 }
 const edit = (patch: Partial<ArtifactFields>) => {
  if (!ready || !currentScope() || !allowed || working.current) return
  const previous = formRef.current?.actor_session_id === identity.actor_session_id ? formRef.current : null
  const next = snapshotArtifactForm(workspace, identity.actor_session_id, { ...(previous?.fields ?? emptyArtifactFields()), ...patch, ...(patch.session_id !== undefined || patch.turn_id !== undefined ? { selection: null } : {}) }, previous)
  formRef.current = next; setForm(next); retainArtifactForm(next)
  if (Object.keys(patch).some(k => ['session_id', 'turn_id'].includes(k))) clearReads()
  const saving = writer(() => currentScope() && actorRef.current?.actor_session_id === next.actor_session_id)
  const sameActor = () => currentScope() && actorRef.current?.actor_session_id === next.actor_session_id
  void persistArtifactForm(next, formStore, saving.guard).then(() => { releaseArtifactForm(next); if (sameActor()) setForms(v => [...v.filter(f => f.snapshot_id !== next.snapshot_id), next]) })
   .catch(() => { if (sameActor()) setError('产物表单尚未落盘；原输入保留在隔离内存，离开前请仅保存本机事实。') }).finally(saving.done)
 }
 const restore = async (value: ArtifactForm) => {
  if (!allowed || value.workspace_id !== workspace || value.actor_session_id !== identity.actor_session_id) return
  const actor = identity.actor_session_id, token = begin(); if (token === null) return
  const prior = formRef.current?.snapshot_id, saving = writer(() => valid(token) && actorRef.current?.actor_session_id === actor && academic(actorRef.current) && writeAdmitted)
  try {
   const original = decodeArtifactForm(JSON.stringify(value), workspace); await fresh(token, true, actor)
   const record = (await formStore.load(workspace))[original.snapshot_id]; if (!valid(token)) return
   const held = heldArtifactForms(workspace).find(v => v.snapshot_id === original.snapshot_id), actual = record ? readArtifactForm(record, workspace) : held
   if (!actual || !sameValue(actual, original) || held && !sameValue(held, original)) throw new Error('Original form changed')
   await fresh(token, true, actor)
   const next = snapshotArtifactForm(workspace, actor, original.fields, null); retainArtifactForm(next)
   await persistArtifactForm(next, formStore, saving.guard); releaseArtifactForm(next); await fresh(token, true, actor)
   if (valid(token)) { setForms(v => [...v, next]); if (formRef.current?.snapshot_id === prior) { formRef.current = next; setForm(next); clearReads() }; setMessage('原产物表单已核验并保存独立分支；较新的输入保持，没有 POST。') }
  } catch (e) { if (valid(token)) fail(e) } finally { saving.done(); finish(token) }
 }
 const read = async () => {
  if (!allowed || !form || form.actor_session_id !== identity.actor_session_id) return
  const captured = form, actor = identity.actor_session_id, token = begin(); if (token === null) return
  setManifest(null)
  try {
   await fresh(token, true, actor)
   const v = checkedArtifact('CodexArtifactManifestView', await port.manifest(captured.fields.session_id, captured.fields.turn_id))
   if (v.manifest.session_id !== captured.fields.session_id || v.manifest.turn_id !== captured.fields.turn_id) throw new Error('Wrong manifest')
   await fresh(token, true, actor)
   if (valid(token) && formRef.current?.snapshot_id === captured.snapshot_id) { setManifest(v); setMessage('当前清单已读取；原选择和原 ACK 保持，没有 POST。') }
  } catch (e) { if (valid(token)) fail(e) } finally { finish(token) }
 }
 const readImports = async (command: ArtifactCommand) => {
  if (!allowed || command.actor_session_id !== identity.actor_session_id || !command.ack) return
  const token = begin(); if (token === null) return
  setAggregate(null)
  try {
   await fresh(token, true, command.actor_session_id)
   const v = readArtifactImport(await port.imports(command.ack.id), command)
   await fresh(token, true, command.actor_session_id)
   if (valid(token)) setAggregate({ command, view: v })
  } catch (e) { if (valid(token)) fail(e) } finally { finish(token) }
 }
 const openPreview = async (importId: string) => {
  if (!allowed || !aggregate) return null
  const original = aggregate, actor = identity.actor_session_id, token = begin(); if (token === null) return null
  try {
   await fresh(token, true, actor)
   const view = readArtifactImport(await port.imports(original.view.job.id), original.command)
   const item = view.items.find(i => i.import_id === importId)
   if (!item) throw new Error('Wrong Import child')
   await fresh(token, true, actor)
   if (valid(token)) return { importId: item.import_id, jobId: item.job.id }
  } catch (e) { if (valid(token)) fail(e) } finally { finish(token) }
  return null
 }
 const download = async (entry: CodexArtifactEntry) => {
  if (!allowed || !manifest || !manifest.manifest.entries.some(e => sameValue(e, entry))) return
  const actor = identity.actor_session_id, token = begin(); if (token === null) return
  try {
   await fresh(token, true, actor)
   const blob = await port.download(entry), bytes = new Uint8Array(await blob.arrayBuffer())
   if (blob.size !== entry.size || artifactHash(bytes) !== entry.sha256) throw new Error('Changed bytes')
   await fresh(token, true, actor)
   if (valid(token)) {
    const url = URL.createObjectURL(blob); urls.current.add(url)
    const a = document.createElement('a'); a.href = url; a.download = entry.logical_path.split('/').at(-1)!; a.click()
    setTimeout(() => { URL.revokeObjectURL(url); urls.current.delete(url) }, 15000)
    setMessage('已核对实际字节并发起受控下载；内容仍未审校。')
   }
  } catch (e) { if (valid(token)) fail(e) } finally { finish(token) }
 }
 async function execute(command: ArtifactCommand, existingToken?: number) {
  if (!ready || command.workspace_id !== workspace || command.actor_session_id !== identity.actor_session_id || command.ack || !allowed) return
  const token = existingToken ?? begin(); if (token === null) return
  const saving = writer(() => valid(token)), subject = true
  try {
   await fresh(token, subject, command.actor_session_id); retainArtifactCommand(command)
   const saved = await dispatchArtifactCommand(command, port, store, { guard: saving.guard,
    beforePost: async () => { const values = await loadCommands(); await fresh(token, subject, command.actor_session_id); if (valid(token)) setCommands(values) },
    onAck: retainArtifactCommand, beforeDelivery: async () => { await fresh(token, subject, command.actor_session_id) } })
   releaseArtifactCommand(saved); const values = await loadCommands(); await fresh(token, subject, command.actor_session_id)
   if (valid(token)) { setCommands(values); setMessage('回导原 202 ACK 已保存；聚合和 Import 子项状态须独立 GET，未自动确认入库。') }
  } catch (e) {
   if (e instanceof ApiError && e.status >= 400 && e.status <= 599 && !heldArtifactCommands(workspace).some(v => v.command_id === command.command_id && v.ack)) {
    const rejected = decodeArtifactCommand(JSON.stringify({ ...command, error: { status: e.status, code: /^[A-Z][A-Z0-9_]{0,79}$/.test(e.code ?? '') && e.code?.trim() === e.code ? e.code : null } }), workspace)
    retainArtifactCommand(rejected)
    if (valid(token) && !denied(e)) { try { const saved = await persistArtifactCommand(rejected, store, saving.guard); releaseArtifactCommand(saved); const values = await loadCommands(); if (valid(token)) setCommands(values) } catch { /* Keep original command isolated. */ } }
   }
   if (valid(token)) fail(e)
  } finally { saving.done(); finish(token) }
 }
 const candidate = () => {
  const f = form?.fields
  if (!allowed || !form || !f?.selection || form.actor_session_id !== identity.actor_session_id) throw new Error('Read and select concrete artifacts')
  return makeArtifactCommand(workspace, identity.actor_session_id, f.selection.basis, f.selection.artifact_ids)
 }
 const submit = async () => {
  const token = begin(); if (token === null) return
  try { await execute(candidate(), token) } catch (e) { if (valid(token)) fail(e); finish(token) }
 }
 const chooseManifest = () => { if (manifest && allowed) edit({ selection: { basis: manifest, artifact_ids: [] } }) }
 const select = (id: string, selected: boolean) => {
  const s = form?.fields.selection
  if (!allowed || !s || !manifest || !sameValue(s.basis, manifest)) return
  const ids = new Set(s.artifact_ids); if (selected) ids.add(id); else ids.delete(id)
  edit({ selection: { basis: s.basis, artifact_ids: s.basis.manifest.entries.filter(e => ids.has(e.artifact_id)).map(e => e.artifact_id) } })
 }
 const saveMemory = async () => {
  if (!ready) return
  const actor = identity.actor_session_id, token = begin(); if (token === null) return
  const saving = writer(() => valid(token))
  try { await fresh(token, false, actor)
   for (const value of heldArtifactCommands(workspace)) { const saved = await persistArtifactCommand(value, store, saving.guard); releaseArtifactCommand(saved) }
   for (const value of heldArtifactForms(workspace)) { await persistArtifactForm(value, formStore, saving.guard); releaseArtifactForm(value) }
   const values = await loadCommands(), drafts = await loadForms(); await fresh(token, false, actor)
   if (valid(token)) { setCommands(values); setForms(drafts); setMessage('仅保存产物原 actor 的本机事实和表单；未发送任何 POST。') }
  } catch (e) { if (valid(token)) fail(e) } finally { saving.done(); finish(token) }
 }
 const held = heldArtifactCommands(workspace), heldForms = heldArtifactForms(workspace), all = new Map(commands.map(v => [v.command_id, v]))
 for (const value of held) if (!all.get(value.command_id)?.ack || value.ack) all.set(value.command_id, value)
 const allForms = new Map([...forms, ...heldForms].map(v => [v.snapshot_id, v])), latest = new Map<string, ArtifactForm>()
 for (const value of allForms.values()) if (allowed && value.actor_session_id === identity.actor_session_id && (!latest.has(value.draft_id) || latest.get(value.draft_id)!.sequence < value.sequence)) latest.set(value.draft_id, value)
 const retained = held.length + heldForms.length
 const canSubmit = (() => { try { candidate(); return !working.current } catch { return false } })()
 return { ready, allowed, busy: visible && busy, actor: ready ? identity.actor_session_id : null,
  fields: allowed && form?.actor_session_id === identity.actor_session_id ? form.fields : emptyArtifactFields(), forms: [...latest.values()],
  commands: allowed ? [...all.values()].filter(v => v.actor_session_id === identity.actor_session_id) : [],
  manifest: allowed ? manifest : null, aggregate: allowed ? aggregate : null,
  error: visible ? error : '', message: visible ? message : '', retained, dirty: retained > 0 || allForms.size > 0 || [...all.values()].some(v => !v.ack), safe: !working.current && retained === 0, isolated: !working.current && retained > 0,
  canSubmit, canSave: ready && retained > 0, canReplay: (c: ArtifactCommand) => allowed && c.actor_session_id === identity.actor_session_id && !c.ack && !held.some(v => v.command_id === c.command_id && v.ack),
  refresh, edit, restore, read, readImports, openPreview, download, execute, submit, chooseManifest, select, saveMemory }
}
