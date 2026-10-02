import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { ContentRef, AuthoringDraftView, SessionResponse, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import { sameValue } from '../providers/providerSchema'
import { reviewReceipt } from '../draftReview/reviewSchema'
import { singlePublicationClient, type SinglePublicationPort } from './singlePublicationClient'
import { makeSinglePublicationCommand, persistSinglePublicationCommand, singlePublicationCommandStore, readSinglePublicationCommand, sameSinglePublicationActorPage, type SinglePublicationCommand } from './singlePublicationCommands'
import { checkedPublication, publicationRef } from '../draftPublication/publicationSchema'
import { SinglePublicationUnavailable, singleSnapshot, singlePublishedRef } from './singlePublicationSchema'
import { matchesSingleCandidate, prepareSingleBasis, type SinglePublicationBasis } from './singlePublicationSchema'
import { singlePublicationMemoryVersion, pendingSinglePublicationMemory, recoverableSinglePublicationMemory, releaseSinglePublicationMemory, retainSinglePublicationMemory, subscribeSinglePublicationMemory,
  pendingSinglePublicationForms, recoverableSinglePublicationForms, retainSinglePublicationForm, releaseSinglePublicationForm, originalSinglePublicationForm, type SinglePublicationForm } from './singlePublicationMemory'

const denied = (error: unknown) => error instanceof ApiError && ([401, 403].includes(error.status) || ['POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED'].includes(error.code ?? ''))
export function useSinglePublication(workspace: string, paused: boolean, selection: string, port: SinglePublicationPort = singlePublicationClient, draftId?: string) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  useSyncExternalStore(subscribeSinglePublicationMemory, singlePublicationMemoryVersion, singlePublicationMemoryVersion)
  const sessionIdentity = useRef('')
  const owner = JSON.stringify([workspace, access, selection, draftId]), scope = useRef({ owner, paused }); scope.current = { owner, paused }
  const live = useRef(false), admitted = useRef(false), sequence = useRef(0), working = useRef(false), writers = useRef(new Set<AbortController>())
  const [renderOwner, setRenderOwner] = useState(owner), [allowed, setAllowed] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [commands, setCommands] = useState<SinglePublicationCommand[]>([]), [basis, setBasis] = useState<SinglePublicationBasis | null>(null), [preparedAt, setPreparedAt] = useState(0)
  const [publicationRead, setPublicationRead] = useState<AuthoringDraftView | null>(null)
  const [currentRead, setCurrentRead] = useState<{ command_id: string; ref: ContentRef } | null>(null)
  const ready = renderOwner === owner && allowed && !paused
  admitted.current = ready
  const current = (subject = true) => live.current && scope.current.owner === owner && getSessionGeneration() === access
    && (!subject || admitted.current && !scope.current.paused)
  const clearProtected = () => {
    admitted.current = false; sessionIdentity.current = ''; setAllowed(false); setCommands([]); setBasis(null); setCurrentRead(null); setPublicationRead(null)
    for (const controller of writers.current) controller.abort()
  }
  const fail = (reason: unknown) => {
    if (denied(reason)) clearProtected()
    const code = reason instanceof ApiError && /^[A-Z][A-Z0-9_]{0,79}$/.test(reason.code ?? '') ? `${reason.code}：` : ''
    setError(code + (reason instanceof SinglePublicationUnavailable ? reason.message : denied(reason) ? '当前权限或测试策略不允许发布资料，保护内容已收起，原命令仍保留。'
      : reason instanceof ApiError && reason.status === 412 ? '候选或审核基准已变化。原命令保留；请核对当前引用；请明确重新读取候选并创建新的审核和人工决定，不能替换原命令基准。'
        : '本次发布操作未确认或记录无法核验。原 body 与 key 保留，不自动重发或创建新命令。'))
  }
  const load = async () => Object.values(await singlePublicationCommandStore.load(workspace)).map(value => readSinglePublicationCommand(value, workspace)).filter(value => !draftId || value.basis.candidate.draft_id === draftId)
  const begin = (subject = true, recovering = false) => { if (!current(subject) || working.current || subject && !recovering && pendingSinglePublicationMemory(workspace)) return null; working.current = true; setBusy(true); setError(''); return ++sequence.current }
  const valid = (token: number, subject = true) => current(subject) && token === sequence.current
  const finish = (token: number) => { if (valid(token, false)) { working.current = false; setBusy(false) } }
  const refresh = async () => {
    const token = begin(false); if (token === null) return
    clearProtected()
    try {
      const session = checkedPublication<SessionResponse>('SessionResponse', await port.session())
      if (!valid(token, false)) return
      if (session.workspace_id !== workspace) throw new Error('发布工作区已变化。')
      const canRead = session.role === 'author' && !session.active_independent_attempt_id && !session.active_open_book_attempt_id && !scope.current.paused
      const values = canRead ? await load() : []
      if (valid(token, false)) { sessionIdentity.current = canRead ? session.actor_session_id : ''; setAllowed(canRead); setCommands(values) }
    } catch (reason) { if (valid(token, false)) fail(reason) } finally { finish(token) }
  }
  useEffect(() => {
    live.current = true; ++sequence.current; working.current = false
    setRenderOwner(owner); clearProtected(); setBusy(false); setError('')
    if (workspace && !paused) void refresh()
    return () => { live.current = false; ++sequence.current; working.current = false; for (const controller of writers.current) controller.abort() }
  }, [owner, paused, port])
  const readBasis = async (draft: AuthoringDraftView, selectedReview: StoredReviewReceipt) => {
    if (draftId && draft.candidate.draft_id !== draftId || !matchesSingleCandidate(draft, selectedReview.candidate)) throw new Error('先选择匹配的单块候选与审核。')
    const [rawDraft, rawReview, generation] = await Promise.all([port.draft(draft.candidate.draft_id), port.review(selectedReview.id), port.generation(draft.source_job_id)])
    const freshDraft = singleSnapshot(rawDraft, draft.candidate)
    const freshReview = reviewReceipt(rawReview, selectedReview.id, selectedReview.candidate)
    if (!sameValue(freshDraft, draft) || !sameValue(freshReview, selectedReview)) throw new Error('候选或所选人工决定已变化，请另行读取。')
    const checks = await Promise.all(freshDraft.numeric_check_ids.map(id => port.numeric(id)))
    return prepareSingleBasis(freshDraft, generation, freshReview, checks)
  }
  const prepare = async (draft: AuthoringDraftView, selectedReview: StoredReviewReceipt) => {
    const token = begin(); if (token === null) return
    setBasis(null)
    try { const prepared = await readBasis(draft, selectedReview); if (valid(token)) { setBasis(prepared); setPreparedAt(token) } }
    catch (reason) { if (valid(token, false)) fail(reason) } finally { finish(token) }
  }
  const execute = async (command: SinglePublicationCommand) => {
    if (!current() || command.workspace_id !== workspace || draftId && command.basis.candidate.draft_id !== draftId) return
    if (!sameSinglePublicationActorPage(command, access)) { setError('无法核对原操作者。旧页面或旧访问代次的原发布命令只读保留，不用当前会话冒充原 key 回放。'); return }
    const token = begin(); if (token === null) return
    const originalSession = sessionIdentity.current
    const controller = new AbortController(); writers.current.add(controller)
    const guard = { allowed: () => valid(token), signal: controller.signal }, unsubscribe = subscribeSessionAccess(() => controller.abort())
    setCurrentRead(null)
    try {
      retainSinglePublicationMemory(command, originalSession)
      releaseSinglePublicationForm(workspace, originalSession, command.basis)
      const original = await persistSinglePublicationCommand(command, undefined, guard)
      releaseSinglePublicationMemory(command.command_id, originalSession)
      const values = await load()
      if (!valid(token)) return
      setCommands(values); setBasis(null)
      // Only an explicit user action reaches this write, including known-ACK
      // verification. It uses the permanently retained original four fields/key.
      const ack = singlePublishedRef(await port.publish(original.basis.candidate.draft_id, original.body, original.command_id))
      if (original.ack && !sameValue(original.ack, ack)) throw new Error('原发布回执不能替换。')
      retainSinglePublicationMemory({ ...original, ack, rejection: null }, originalSession)
      if (!valid(token)) return
      await persistSinglePublicationCommand({ ...original, ack, rejection: null }, undefined, guard)
      releaseSinglePublicationMemory(command.command_id, originalSession)
      const confirmed = await load()
      if (valid(token)) { setCommands(confirmed); setError('原发布 ACK 已保存。这是历史不可变引用；当前指针需要另行读取。') }
    } catch (reason) {
      if (valid(token, false)) {
        if (!command.ack && !denied(reason) && reason instanceof ApiError && [400, 409, 412, 422].includes(reason.status)) {
          try {
            const code = /^[A-Z][A-Z0-9_]{0,79}$/.test(reason.code ?? '') ? reason.code! : null
            const rejected = { ...command, rejection: { status: reason.status, code } }
            retainSinglePublicationMemory(rejected, originalSession)
            await persistSinglePublicationCommand(rejected, undefined, guard)
            releaseSinglePublicationMemory(command.command_id, originalSession)
            const values = await load(); if (valid(token)) setCommands(values)
          } catch { /* Already committed originals are preserved. */ }
        }
        if (valid(token, false)) fail(reason)
      }
    } finally { unsubscribe(); writers.current.delete(controller); finish(token) }
  }
  const saveMemory = async () => {
    const token = begin(true, true); if (token === null) return
    const session = sessionIdentity.current, controller = new AbortController(); writers.current.add(controller)
    const guard = { allowed: () => valid(token) && sessionIdentity.current === session, signal: controller.signal }
    const unsubscribe = subscribeSessionAccess(() => controller.abort())
    try {
      // Save retained facts only. This never changes origin/page/access or sends
      // HTTP, even if the current access generation differs from the original.
      for (const command of recoverableSinglePublicationMemory(workspace, session)) {
        await persistSinglePublicationCommand(command, undefined, guard)
        if (!valid(token)) return
        releaseSinglePublicationMemory(command.command_id, session)
      }
      const values = await load(); if (valid(token)) setCommands(values)
    } catch (reason) { if (valid(token, false)) fail(reason) }
    finally { unsubscribe(); writers.current.delete(controller); finish(token) }
  }
  const publish = async (selectedWarnings: number[]) => {
    if (!current() || working.current || !basis) return
    const selectedAt = sequence.current
    try {
      // Re-read the ledger: another panel must not be silently replaced by a
      // second key. Server owns cross-page transactions and candidate uniqueness.
      const values = await load()
      if (!current() || working.current || sequence.current !== selectedAt) return
      setCommands(values)
      if (values.some(value => sameValue(value.basis.candidate, basis.candidate) && !value.rejection)) {
        setError('已有同候选原发布命令。保留原 key、结果和基准；请使用原命令恢复，不创建第二次发布。'); return
      }
      await execute(makeSinglePublicationCommand(workspace, access, basis, selectedWarnings))
    } catch (reason) { if (current()) fail(reason) }
  }
  const readCurrent = async (command: SinglePublicationCommand) => {
    if (!command.ack || command.workspace_id !== workspace || draftId && command.basis.candidate.draft_id !== draftId) return
    const token = begin(); if (token === null) return
    setCurrentRead(null)
    try {
      const ref = publicationRef(await port.current(command.ack.id))
      if (ref.id !== command.ack.id) throw new Error('当前指针对象不符。')
      if (valid(token)) setCurrentRead({ command_id: command.command_id, ref })
    } catch (reason) { if (valid(token, false)) fail(reason) } finally { finish(token) }
  }
  const readPublication = async (candidate: AuthoringDraftView['candidate'], ack?: ContentRef) => {
    if (draftId && candidate.draft_id !== draftId) return
    const token = begin(); if (token === null) return
    setPublicationRead(null)
    try {
      const draft = singleSnapshot(await port.draft(candidate.draft_id), candidate)
      if (ack && !sameValue(draft.published_ref, ack)) throw new Error('独立GET的发布关联与原ACK不一致。')
      if (valid(token)) { setPublicationRead(draft); return draft }
    } catch (reason) { if (valid(token, false)) fail(reason) } finally { finish(token) }
  }
  const retainForm = (selected: number[], confirmed: boolean) => {
    if (current() && basis && sessionIdentity.current) retainSinglePublicationForm(workspace, sessionIdentity.current, basis, selected, confirmed)
  }
  const recoverForm = async (form: SinglePublicationForm) => {
    const token = begin(); if (token === null) return
    setBasis(null)
    try {
      if (!originalSinglePublicationForm(form, workspace, sessionIdentity.current)) throw new Error('无法核对原表单会话。')
      const fresh = await readBasis(form.basis.snapshot, form.basis.review)
      if (!sameValue(fresh, form.basis)) throw new Error('原数值或审核基准已变化；保留原表单，不迁移确认。')
      if (valid(token)) { setBasis(fresh); setPreparedAt(token); retainSinglePublicationForm(workspace, sessionIdentity.current, fresh, form.selected, false); return { key: token, selected: form.selected } }
    } catch (reason) { if (valid(token, false)) fail(reason) } finally { finish(token) }
  }
  return { ready, busy: renderOwner === owner && busy, pendingMemory: pendingSinglePublicationMemory(workspace),
    pendingForms: pendingSinglePublicationForms(workspace), forms: ready ? recoverableSinglePublicationForms(workspace, sessionIdentity.current) : [], retainForm, recoverForm,
    canSaveMemory: ready && recoverableSinglePublicationMemory(workspace, sessionIdentity.current).length > 0, saveMemory,
    error: renderOwner === owner ? error : '',
    commands: ready ? commands : [], basis: ready ? basis : null, preparedAt,
    publicationRead: ready ? publicationRead : null, currentRead: ready ? currentRead : null, refresh, prepare, publish, execute, readCurrent, readPublication,
    canReplay: (value: SinglePublicationCommand) => ready && value.workspace_id === workspace && (!draftId || value.basis.candidate.draft_id === draftId) && sameSinglePublicationActorPage(value, access) }
}
