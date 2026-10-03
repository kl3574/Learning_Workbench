import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { ContentRef, EditDraftSnapshot, SessionResponse, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import { sameValue } from '../providers/providerSchema'
import { reviewReceipt } from '../draftReview/reviewSchema'
import { editPublicationClient, type EditPublicationPort } from './editPublicationClient'
import { makeEditPublicationCommand, persistEditPublicationCommand, editPublicationCommandStore, readEditPublicationCommand, sameEditPublicationActorPage, type EditPublicationCommand } from './editPublicationCommands'
import { checkedPublication, publicationRef } from '../draftPublication/publicationSchema'
import { editSnapshot } from '../draftEditor/editSchema'
import { matchesEditCandidate, prepareEditBasis, type EditPublicationBasis } from './editPublicationSchema'
import { editPublicationMemoryVersion, pendingEditPublicationMemory, recoverableEditPublicationMemory, releaseEditPublicationMemory, retainEditPublicationMemory, subscribeEditPublicationMemory } from './editPublicationMemory'

const denied = (error: unknown) => error instanceof ApiError && ([401, 403].includes(error.status) || ['POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED'].includes(error.code ?? ''))
export function useEditPublication(workspace: string, paused: boolean, selection: string, port: EditPublicationPort = editPublicationClient) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  useSyncExternalStore(subscribeEditPublicationMemory, editPublicationMemoryVersion, editPublicationMemoryVersion)
  const sessionIdentity = useRef('')
  const owner = JSON.stringify([workspace, access, selection]), scope = useRef({ owner, paused }); scope.current = { owner, paused }
  const live = useRef(false), admitted = useRef(false), sequence = useRef(0), working = useRef(false), writers = useRef(new Set<AbortController>())
  const [renderOwner, setRenderOwner] = useState(owner), [allowed, setAllowed] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [commands, setCommands] = useState<EditPublicationCommand[]>([]), [basis, setBasis] = useState<EditPublicationBasis | null>(null), [preparedAt, setPreparedAt] = useState(0)
  const [currentRead, setCurrentRead] = useState<{ command_id: string; ref: ContentRef } | null>(null)
  const ready = renderOwner === owner && allowed && !paused
  admitted.current = ready
  const current = (subject = true) => live.current && scope.current.owner === owner && getSessionGeneration() === access
    && (!subject || admitted.current && !scope.current.paused)
  const clearProtected = () => {
    admitted.current = false; sessionIdentity.current = ''; setAllowed(false); setCommands([]); setBasis(null); setCurrentRead(null)
    for (const controller of writers.current) controller.abort()
  }
  const fail = (reason: unknown) => {
    if (denied(reason)) clearProtected()
    const code = reason instanceof ApiError && /^[A-Z][A-Z0-9_]{0,79}$/.test(reason.code ?? '') ? `${reason.code}：` : ''
    setError(code + (denied(reason) ? '当前权限或测试策略不允许发布资料，保护内容已收起，原命令仍保留。'
      : reason instanceof ApiError && reason.status === 412 ? '候选或审核基准已变化。原命令保留；请重新选择并读取基准，再明确准备新发布。'
        : '本次发布操作未确认或记录无法核验。原 body 与 key 保留，不自动重发或创建新命令。'))
  }
  const load = async () => Object.values(await editPublicationCommandStore.load(workspace)).map(value => readEditPublicationCommand(value, workspace))
  const begin = (subject = true, recovering = false) => { if (!current(subject) || working.current || subject && !recovering && pendingEditPublicationMemory(workspace)) return null; working.current = true; setBusy(true); setError(''); return ++sequence.current }
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
      if (valid(token, false)) { sessionIdentity.current = canRead ? session.csrf_token : ''; setAllowed(canRead); setCommands(values) }
    } catch (reason) { if (valid(token, false)) fail(reason) } finally { finish(token) }
  }
  useEffect(() => {
    live.current = true; ++sequence.current; working.current = false
    setRenderOwner(owner); clearProtected(); setBusy(false); setError('')
    if (workspace && !paused) void refresh()
    return () => { live.current = false; ++sequence.current; working.current = false; for (const controller of writers.current) controller.abort() }
  }, [owner, paused, port])
  const prepare = async (draft: EditDraftSnapshot, selectedReview: StoredReviewReceipt) => {
    const token = begin(); if (token === null) return
    setBasis(null)
    try {
      if (!matchesEditCandidate(draft, selectedReview.candidate)) throw new Error('先选择匹配的审核。')
      const [rawDraft, rawReview, base] = await Promise.all([port.draft(draft.candidate.draft_id), port.review(selectedReview.id), port.base(draft.base_ref)])
      const freshDraft = editSnapshot(rawDraft, draft.base_ref, draft.candidate.draft_id)
      const freshReview = reviewReceipt(rawReview, selectedReview.id, selectedReview.candidate)
      if (!matchesEditCandidate(freshDraft, selectedReview.candidate)) throw new Error('候选已改变。')
      const prepared = prepareEditBasis(freshDraft, base, freshReview)
      if (valid(token)) { setBasis(prepared); setPreparedAt(token) }
    } catch (reason) { if (valid(token, false)) fail(reason) } finally { finish(token) }
  }
  const execute = async (command: EditPublicationCommand) => {
    if (!current() || command.workspace_id !== workspace) return
    if (!sameEditPublicationActorPage(command, access)) { setError('无法核对原操作者。旧页面或旧访问代次的原发布命令只读保留，不用当前会话冒充原 key 回放。'); return }
    const token = begin(); if (token === null) return
    const originalSession = sessionIdentity.current
    const controller = new AbortController(); writers.current.add(controller)
    const guard = { allowed: () => valid(token), signal: controller.signal }, unsubscribe = subscribeSessionAccess(() => controller.abort())
    setCurrentRead(null)
    try {
      retainEditPublicationMemory(command, originalSession)
      const original = await persistEditPublicationCommand(command, undefined, guard)
      releaseEditPublicationMemory(command.command_id, originalSession)
      const values = await load()
      if (!valid(token)) return
      setCommands(values); setBasis(null)
      // Only an explicit user action reaches this write, including known-ACK
      // verification. It uses the permanently retained original four fields/key.
      const ack = publicationRef(await port.publish(original.basis.candidate.draft_id, original.body, original.command_id), original.basis.target)
      if (!valid(token)) return
      retainEditPublicationMemory({ ...original, ack, rejection: null }, originalSession)
      await persistEditPublicationCommand({ ...original, ack, rejection: null }, undefined, guard)
      releaseEditPublicationMemory(command.command_id, originalSession)
      const confirmed = await load()
      if (valid(token)) { setCommands(confirmed); setError('原发布 ACK 已保存。这是历史不可变引用；当前指针需要另行读取。') }
    } catch (reason) {
      if (valid(token, false)) {
        if (!command.ack && !denied(reason) && reason instanceof ApiError && [400, 409, 412, 422].includes(reason.status)) {
          try {
            const code = /^[A-Z][A-Z0-9_]{0,79}$/.test(reason.code ?? '') ? reason.code! : null
            const rejected = { ...command, rejection: { status: reason.status, code } }
            retainEditPublicationMemory(rejected, originalSession)
            await persistEditPublicationCommand(rejected, undefined, guard)
            releaseEditPublicationMemory(command.command_id, originalSession)
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
      for (const command of recoverableEditPublicationMemory(workspace, session)) {
        await persistEditPublicationCommand(command, undefined, guard)
        if (!valid(token)) return
        releaseEditPublicationMemory(command.command_id, session)
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
      await execute(makeEditPublicationCommand(workspace, access, basis, selectedWarnings))
    } catch (reason) { if (current()) fail(reason) }
  }
  const readCurrent = async (command: EditPublicationCommand) => {
    if (!command.ack || command.workspace_id !== workspace) return
    const token = begin(); if (token === null) return
    setCurrentRead(null)
    try {
      const ref = publicationRef(await port.current(command.ack.id))
      if (ref.id !== command.ack.id) throw new Error('当前指针对象不符。')
      if (valid(token)) setCurrentRead({ command_id: command.command_id, ref })
    } catch (reason) { if (valid(token, false)) fail(reason) } finally { finish(token) }
  }
  return { ready, busy: renderOwner === owner && busy, pendingMemory: pendingEditPublicationMemory(workspace),
    canSaveMemory: ready && recoverableEditPublicationMemory(workspace, sessionIdentity.current).length > 0, saveMemory,
    error: renderOwner === owner ? error : '',
    commands: ready ? commands : [], basis: ready ? basis : null, preparedAt,
    currentRead: ready ? currentRead : null, refresh, prepare, publish, execute, readCurrent,
    canReplay: (value: EditPublicationCommand) => ready && sameEditPublicationActorPage(value, access) }
}
