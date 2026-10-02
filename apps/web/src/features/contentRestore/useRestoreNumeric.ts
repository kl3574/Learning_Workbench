import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { ApprovalDecision, ContentRestoreDraftSnapshot, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import type { RestoreNumericCheckView } from '../../../../../packages/contracts/generated/restore-numeric-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import { sameValue } from '../providers/providerSchema'
import { checkedRestore } from './restoreSchema'
import { publicationRef } from '../draftPublication/publicationSchema'
import { restoreNumericClient, type RestoreNumericPort } from './restoreNumericClient'
import { restoreNumericCheck, restoreNumericDecisionAck, restoreNumericPreviewAck, restoreNumericSnapshot } from './restoreNumericSchema'
import { makeRestoreNumericCommand, persistRestoreNumericCommand, readRestoreNumericCommand, restoreNumericCommandStore, sameRestoreNumericActorPage, type RestoreNumericCommand } from './restoreNumericStore'
import * as memory from './restoreNumericMemory'
import * as forms from './restoreNumericFormMemory'
import { blankRestoreNumericForm, restoreNumericFormMaterial, type RestoreNumericForm } from './restoreNumericForm'

const denied = (error: unknown) => error instanceof ApiError && ([401, 403].includes(error.status) || ['POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED'].includes(error.code ?? ''))
const immutable = ({ numeric_material: _material, numeric_check_ids: _checks, state: _state, published_ref: _published, ...value }: ContentRestoreDraftSnapshot) => value
export function useRestoreNumeric(workspace: string, blockId: string, paused: boolean, port: RestoreNumericPort = restoreNumericClient) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  useSyncExternalStore(memory.subscribeRestoreNumericMemory, memory.restoreNumericMemoryVersion, memory.restoreNumericMemoryVersion)
  useSyncExternalStore(forms.subscribeRestoreNumericForms, forms.restoreNumericFormsVersion, forms.restoreNumericFormsVersion)
  const owner = JSON.stringify([workspace, blockId, access]), scope = useRef({ owner, paused }); scope.current = { owner, paused }
  const live = useRef(false), sequence = useRef(0), working = useRef(false), admitted = useRef(false), session = useRef<SessionResponse | null>(null), writers = useRef(new Set<AbortController>())
  const [renderOwner, setRenderOwner] = useState(owner), [allowed, setAllowed] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [snapshot, setSnapshot] = useState<ContentRestoreDraftSnapshot | null>(null), [check, setCheck] = useState<RestoreNumericCheckView | null>(null)
  const [commands, setCommands] = useState<RestoreNumericCommand[]>([]), [baseCurrent, setBaseCurrent] = useState(false), [formVisible, setFormVisible] = useState(false)
  const ready = renderOwner === owner && allowed && !paused; admitted.current = ready
  const current = (academic = true) => live.current && scope.current.owner === owner && getSessionGeneration() === access && (!academic || admitted.current && !scope.current.paused)
  const valid = (token: number, academic = true) => current(academic) && token === sequence.current
  const clear = () => { admitted.current = false; session.current = null; setAllowed(false); setSnapshot(null); setCheck(null); setCommands([]); setBaseCurrent(false); setFormVisible(false); for (const controller of writers.current) controller.abort() }
  const fail = (reason: unknown) => {
    if (denied(reason)) clear()
    const code = reason instanceof ApiError && /^[A-Z][A-Z0-9_]{0,79}$/.test(reason.code ?? '') ? `${reason.code}：` : ''
    setError(code + (denied(reason) ? '当前权限不允许读取数值材料；原表单与命令隔离保留。'
      : reason instanceof ApiError && reason.status === 412 ? '候选或活动基准已变化；原计划与命令保留，不会自动换基准。'
        : '本次数值操作未确认或材料不符合合同。原表单、命令与已取得事实保留，不自动重发。'))
  }
  const begin = (academic = true, recovering = false) => {
    if (!current(academic) || working.current || academic && !recovering && memory.pendingRestoreNumericMemory(workspace)) return null
    working.current = true; setBusy(true); setError(''); return ++sequence.current
  }
  const finish = (token: number) => { if (valid(token, false)) { working.current = false; setBusy(false) } }
  const load = async () => Object.values(await restoreNumericCommandStore.load(workspace)).map(record => readRestoreNumericCommand(record, workspace))
  const permitted = (value: SessionResponse) => value.workspace_id === workspace && value.role === 'author' && value.active_independent_attempt_id === null && value.active_open_book_attempt_id === null
  const freshSession = async (token: number) => {
    const before = session.current, actual = checkedRestore<SessionResponse>('SessionResponse', await port.session())
    if (!valid(token) || !before) return null
    if (!permitted(actual) || actual.actor_session_id !== before.actor_session_id || actual.csrf_token !== before.csrf_token) { clear(); return null }
    return actual
  }
  const permissions = async () => {
    const token = begin(false); if (token === null) return
    clear()
    try {
      const actual = checkedRestore<SessionResponse>('SessionResponse', await port.session())
      if (!valid(token, false)) return
      const canRead = permitted(actual) && !scope.current.paused
      const values = canRead ? await load() : []
      if (valid(token, false)) { session.current = canRead ? actual : null; setCommands(values); setAllowed(canRead) }
    } catch (reason) { if (valid(token, false)) fail(reason) } finally { finish(token) }
  }
  useEffect(() => {
    live.current = true; ++sequence.current; working.current = false; setRenderOwner(owner); clear(); setBusy(false); setError('')
    if (workspace && !paused) void permissions()
    return () => { live.current = false; ++sequence.current; working.current = false; for (const controller of writers.current) controller.abort() }
  }, [owner, paused, port])
  const readSnapshot = async (id: string) => {
    const value = restoreNumericSnapshot(await port.draft(id), id)
    if (value.source_ref.id !== blockId || value.proposed_block.kind !== 'worked_example') throw new Error('数值材料必须属于本块的真实恢复例题。')
    return value
  }
  const select = async (requested: ContentRestoreDraftSnapshot) => {
    if (forms.pendingRestoreNumericForms(workspace, blockId)) { setError('本块仍有未提交数值材料；请恢复或明确丢弃后另行读取。'); return }
    const token = begin(); if (token === null) return
    setSnapshot(null); setCheck(null); setFormVisible(false)
    try {
      if (!await freshSession(token)) return
      const value = await readSnapshot(requested.candidate.draft_id)
      if (!sameValue(immutable(value), immutable(requested))) throw new Error('重新读取的候选与原件不一致。')
      const active = publicationRef(await port.current(blockId))
      if (valid(token)) { setSnapshot(value); setBaseCurrent(sameValue(active, value.base_ref)); setFormVisible(value.state === 'draft' && value.numeric_material === null) }
    } catch (reason) { if (valid(token, false)) fail(reason) } finally { finish(token) }
  }
  const restoreForm = async () => {
    const token = begin(true, true); if (token === null) return
    try {
      const actor = await freshSession(token); if (!actor) return
      const held = forms.ownRestoreNumericForm(workspace, blockId, actor.actor_session_id); if (!held) return
      const value = await readSnapshot(held.snapshot.candidate.draft_id), active = publicationRef(await port.current(blockId))
      if (!sameValue(immutable(value), immutable(held.snapshot))) throw new Error('原恢复依据已经不完整。')
      if (!valid(token)) return
      forms.retainRestoreNumericForm(workspace, actor.actor_session_id, held.snapshot, { ...held.value, confirmed: false })
      setSnapshot(value); setCheck(null); setFormVisible(true); setBaseCurrent(value.state === 'draft' && sameValue(active, value.base_ref) && sameValue(value.numeric_material, held.snapshot.numeric_material))
      if (value.state !== 'draft' || !sameValue(active, value.base_ref) || !sameValue(value.numeric_material, held.snapshot.numeric_material)) setError('原候选状态、活动基准或唯一材料已改变；保留原手填内容供核对，不能按它再建预览。')
    } catch (reason) { if (valid(token, false)) fail(reason) } finally { finish(token) }
  }
  const execute = async (command: RestoreNumericCommand, submittedForm?: RestoreNumericForm) => {
    if (!current() || !snapshot || command.workspace_id !== workspace || command.draft_id !== snapshot.candidate.draft_id || !session.current
        || !sameRestoreNumericActorPage(command, session.current.actor_session_id, access)) return
    const token = begin(); if (token === null) return
    const originalSession = session.current, controller = new AbortController(); writers.current.add(controller)
    const guard = { allowed: () => valid(token), signal: controller.signal }, unsubscribe = subscribeSessionAccess(() => controller.abort())
    setCheck(null)
    try {
      if (!await freshSession(token)) return
      memory.retainRestoreNumericMemory(command, originalSession.csrf_token)
      const original = await persistRestoreNumericCommand(command, undefined, guard)
      memory.releaseRestoreNumericMemory(original.command_id, originalSession.csrf_token)
      if (!valid(token)) return
      if (submittedForm) { forms.releaseRestoreNumericForm(workspace, blockId, originalSession.actor_session_id, submittedForm); setFormVisible(false) }
      const values = await load(); if (!valid(token)) return; setCommands(values)
      let acknowledged: RestoreNumericCommand
      if (original.kind === 'preview') {
        const ack = restoreNumericPreviewAck(await port.preview(original.draft_id, original.body, original.command_id), original.body)
        acknowledged = { ...original, ack, rejection: null }
      } else {
        const ack = restoreNumericDecisionAck(await port.decide(original.check_id, original.body, original.command_id), original.check_id, original.body)
        acknowledged = { ...original, ack, rejection: null }
      }
      if (!valid(token)) return
      memory.retainRestoreNumericMemory(acknowledged, originalSession.csrf_token)
      await persistRestoreNumericCommand(acknowledged, undefined, guard)
      memory.releaseRestoreNumericMemory(original.command_id, originalSession.csrf_token)
      const confirmed = await load()
      if (valid(token)) { setCommands(confirmed); setError('原数值命令 ACK 已保存；请另行读取恢复稿完整材料及数值检查当前状态，不将原 ACK 当当前事实。') }
    } catch (reason) {
      if (valid(token, false)) {
        if (!command.ack && !denied(reason) && reason instanceof ApiError && [400, 409, 412, 413, 422].includes(reason.status)) {
          try {
            const code = /^[A-Z][A-Z0-9_]{0,79}$/.test(reason.code ?? '') ? reason.code! : null
            const rejected = { ...command, rejection: { status: reason.status, code } }
            memory.retainRestoreNumericMemory(rejected, originalSession.csrf_token)
            await persistRestoreNumericCommand(rejected, undefined, guard)
            memory.releaseRestoreNumericMemory(command.command_id, originalSession.csrf_token)
            const values = await load(); if (valid(token)) setCommands(values)
          } catch { /* Preserve original command/ACK in isolated memory. */ }
        }
        if (valid(token, false)) fail(reason)
      }
    } finally { unsubscribe(); writers.current.delete(controller); finish(token) }
  }
  const preview = async () => {
    if (!current() || working.current || !snapshot || !baseCurrent || snapshot.state !== 'draft' || !session.current) return
    const actor = session.current, form = forms.ownRestoreNumericForm(workspace, blockId, actor.actor_session_id)?.value
    try {
      if (!snapshot.numeric_material && (!formVisible || !form?.confirmed)) return
      const material = snapshot.numeric_material?.material ?? restoreNumericFormMaterial(form!, snapshot)
      if (snapshot.candidate.entity !== 'block') throw new Error('恢复数值候选必须是原内容块。')
      const body = { candidate: { ...snapshot.candidate, entity: 'block' as const }, material }
      if (commands.some(command => command.kind === 'preview' && command.draft_id === snapshot.candidate.draft_id && !command.ack && !command.rejection)) { setError('已有结果未知的原预览命令，须先核对或显式回放原 key，不能创建第二份预览。'); return }
      await execute(makeRestoreNumericCommand(workspace, actor.actor_session_id, access, { kind: 'preview', draft_id: snapshot.candidate.draft_id, body }), snapshot.numeric_material ? undefined : form)
    } catch (reason) { if (current()) { setError(reason instanceof Error ? reason.message : '手填数值材料无法核验。') } }
  }
  const readCheck = async (id: string) => {
    if (!snapshot || forms.pendingRestoreNumericForms(workspace, blockId)) return
    const token = begin(); if (token === null) return; setCheck(null)
    try {
      if (!await freshSession(token)) return
      const value = await readSnapshot(snapshot.candidate.draft_id)
      if (!sameValue(immutable(value), immutable(snapshot)) || !value.numeric_check_ids.includes(id)) throw new Error('数值检查不在本恢复稿的受检账本内。')
      const actual = restoreNumericCheck(await port.check(id), id, value)
      if (valid(token)) { setSnapshot(value); setCheck(actual); setFormVisible(false) }
    } catch (reason) { if (valid(token, false)) fail(reason) } finally { finish(token) }
  }
  const decide = async (body: ApprovalDecision) => {
    if (!current() || working.current || !snapshot?.numeric_material || !check || !session.current || body.expected_revision !== check.revision || body.operation_sha256 !== check.operation_sha256) return
    if (commands.some(command => command.kind === 'decision' && command.check_id === check.id && (!command.rejection || !!command.ack))) { setError('该检查已有原决定命令，请核对原记录；不创建第二份决定。'); return }
    await execute(makeRestoreNumericCommand(workspace, session.current.actor_session_id, access, { kind: 'decision', draft_id: snapshot.candidate.draft_id, check_id: check.id, body }))
  }
  const saveMemory = async () => {
    const token = begin(true, true); if (token === null) return
    const controller = new AbortController(); writers.current.add(controller)
    const guard = { allowed: () => valid(token), signal: controller.signal }, unsubscribe = subscribeSessionAccess(() => controller.abort())
    try {
      const actor = await freshSession(token); if (!actor) return
      for (const command of memory.recoverableRestoreNumericMemory(workspace, actor.csrf_token)) {
        await persistRestoreNumericCommand(command, undefined, guard)
        if (!valid(token)) return
        if (command.kind === 'preview') {
          const form = forms.ownRestoreNumericForm(workspace, blockId, actor.actor_session_id)
          if (form && sameValue(form.snapshot.candidate, command.body.candidate)) {
            try {
              if (sameValue(restoreNumericFormMaterial(form.value, form.snapshot), command.body.material)) {
                forms.releaseRestoreNumericForm(workspace, blockId, actor.actor_session_id, form.value); setFormVisible(false)
              }
            } catch { /* A different or still-incomplete new form stays protected. */ }
          }
        }
        memory.releaseRestoreNumericMemory(command.command_id, actor.csrf_token)
      }
      const values = await load(); if (valid(token)) setCommands(values)
    } catch (reason) { if (valid(token, false)) fail(reason) } finally { unsubscribe(); writers.current.delete(controller); finish(token) }
  }
  const actor = session.current?.actor_session_id ?? '', retained = forms.ownRestoreNumericForm(workspace, blockId, actor)
  return { ready, busy: renderOwner === owner && busy, error: renderOwner === owner ? error : '', snapshot: ready ? snapshot : null, check: ready ? check : null,
    commands: ready && snapshot ? commands.filter(command => command.draft_id === snapshot.candidate.draft_id) : [],
    pendingMemory: memory.pendingRestoreNumericMemory(workspace), pendingForm: forms.pendingRestoreNumericForms(workspace, blockId),
    canSaveMemory: ready && !!session.current && memory.recoverableRestoreNumericMemory(workspace, session.current.csrf_token).length > 0,
    canRestoreForm: ready && !!retained, form: ready && snapshot && formVisible ? retained?.value ?? blankRestoreNumericForm() : null,
    canPreview: ready && baseCurrent && snapshot?.state === 'draft',
    changeForm: (value: RestoreNumericForm) => { if (current() && !working.current && snapshot && formVisible) forms.retainRestoreNumericForm(workspace, actor, retained?.snapshot ?? snapshot, value) },
    discardForm: () => { if (!working.current) { forms.discardRestoreNumericForms(workspace, blockId); setFormVisible(false) } },
    canReplay: (command: RestoreNumericCommand) => ready && !!session.current && sameRestoreNumericActorPage(command, session.current.actor_session_id, access),
    select, restoreForm, preview, readCheck, decide, execute, saveMemory, permissions }
}
