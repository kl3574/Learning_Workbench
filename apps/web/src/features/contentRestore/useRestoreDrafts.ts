import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { ContentRef, ContentRestoreDraftSnapshot, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import { sameValue } from '../providers/providerSchema'
import { restoreClient, type RestorePort } from './restoreClient'
import { makeRestoreCreateCommand, persistRestoreCreateCommand, restoreCreateCommandStore, readRestoreCreateCommand, sameRestoreCreateActorPage, type RestoreCreateCommand } from './restoreCreateCommands'
import { checkedPublication, publicationRef } from '../draftPublication/publicationSchema'
import { restoreAck, restoreMaterial, restoreRequest, restoreSnapshot, type RestoreMaterial } from './restoreSchema'
type RestoreCreateBasis = { source_ref: ContentRef; base_ref: ContentRef; source: RestoreMaterial; current: RestoreMaterial }
import { restoreCreateMemoryVersion, pendingRestoreCreateMemory, recoverableRestoreCreateMemory, releaseRestoreCreateMemory, retainRestoreCreateMemory, subscribeRestoreCreateMemory } from './restoreCreateMemory'

const denied = (error: unknown) => error instanceof ApiError && ([401, 403].includes(error.status) || ['POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED'].includes(error.code ?? ''))
export function useRestoreDrafts(workspace: string, paused: boolean, blockId: string, port: RestorePort = restoreClient) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  useSyncExternalStore(subscribeRestoreCreateMemory, restoreCreateMemoryVersion, restoreCreateMemoryVersion)
  const sessionIdentity = useRef('')
  const owner = JSON.stringify([workspace, access, blockId]), scope = useRef({ owner, paused }); scope.current = { owner, paused }
  const live = useRef(false), admitted = useRef(false), sequence = useRef(0), working = useRef(false), writers = useRef(new Set<AbortController>())
  const [renderOwner, setRenderOwner] = useState(owner), [allowed, setAllowed] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [commands, setCommands] = useState<RestoreCreateCommand[]>([]), [basis, setBasis] = useState<RestoreCreateBasis | null>(null), [preparedAt, setPreparedAt] = useState(0)
  const [draft, setDraft] = useState<ContentRestoreDraftSnapshot | null>(null)
  const ready = renderOwner === owner && allowed && !paused
  admitted.current = ready
  const current = (subject = true) => live.current && scope.current.owner === owner && getSessionGeneration() === access
    && (!subject || admitted.current && !scope.current.paused)
  const clearProtected = () => {
    admitted.current = false; sessionIdentity.current = ''; setAllowed(false); setCommands([]); setBasis(null); setDraft(null)
    for (const controller of writers.current) controller.abort()
  }
  const fail = (reason: unknown) => {
    if (denied(reason)) clearProtected()
    const code = reason instanceof ApiError && /^[A-Z][A-Z0-9_]{0,79}$/.test(reason.code ?? '') ? `${reason.code}：` : ''
    setError(code + (denied(reason) ? '当前权限或测试策略不允许恢复资料，保护内容已收起，原命令仍保留。'
      : reason instanceof ApiError && reason.status === 412 ? '历史或当前基准已变化。原命令保留；请核对当前引用；当前已变化时须明确重新创建恢复稿，不能改写原稿基准。'
        : '本次恢复操作未确认或记录无法核验。原 body 与 key 保留，不自动重发或创建新命令。'))
  }
  const load = async () => Object.values(await restoreCreateCommandStore.load(workspace)).map(value => readRestoreCreateCommand(value, workspace)).filter(value => value.body.source_ref.id === blockId)
  const begin = (subject = true, recovering = false) => { if (!current(subject) || working.current || subject && !recovering && pendingRestoreCreateMemory(workspace)) return null; working.current = true; setBusy(true); setError(''); return ++sequence.current }
  const valid = (token: number, subject = true) => current(subject) && token === sequence.current
  const finish = (token: number) => { if (valid(token, false)) { working.current = false; setBusy(false) } }
  const refresh = async () => {
    const token = begin(false); if (token === null) return
    clearProtected()
    try {
      const session = checkedPublication<SessionResponse>('SessionResponse', await port.session())
      if (!valid(token, false)) return
      if (session.workspace_id !== workspace) throw new Error('恢复工作区已变化。')
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
  const prepare = async (sourceRef: ContentRef) => {
    const token = begin(); if (token === null) return
    setBasis(null); setDraft(null)
    try {
      if (sourceRef.entity !== 'block' || sourceRef.id !== blockId) throw new Error('仅接受当前比较中明确选定的历史块。')
      const currentRef = publicationRef(await port.current(blockId))
      restoreRequest({ source_ref: sourceRef, expected_current_ref: currentRef, reason: '核验历史基准' })
      const [source, current] = await Promise.all([port.source(sourceRef), port.source(currentRef)])
      restoreMaterial(source, sourceRef); restoreMaterial(current, currentRef)
      if (valid(token)) { setBasis({ source_ref: sourceRef, base_ref: currentRef, source, current }); setPreparedAt(token) }
    } catch (reason) { if (valid(token, false)) fail(reason) } finally { finish(token) }
  }
  const execute = async (command: RestoreCreateCommand) => {
    if (!current() || command.workspace_id !== workspace || command.body.source_ref.id !== blockId) return
    if (!sameRestoreCreateActorPage(command, access)) { setError('无法核对原操作者。旧页面或旧访问代次的原恢复创建命令只读保留，不用当前会话冒充原 key 回放。'); return }
    const token = begin(); if (token === null) return
    const originalSession = sessionIdentity.current
    const controller = new AbortController(); writers.current.add(controller)
    const guard = { allowed: () => valid(token), signal: controller.signal }, unsubscribe = subscribeSessionAccess(() => controller.abort())
    setDraft(null)
    try {
      retainRestoreCreateMemory(command, originalSession)
      const original = await persistRestoreCreateCommand(command, undefined, guard)
      releaseRestoreCreateMemory(command.command_id, originalSession)
      const values = await load()
      if (!valid(token)) return
      setCommands(values); setBasis(null)
      // Only an explicit user action reaches this write, including known-ACK
      // verification. It uses the permanently retained original body and key.
      const ack = restoreAck(await port.create(original.body, original.command_id), original.body)
      if (!valid(token)) return
      retainRestoreCreateMemory({ ...original, ack, rejection: null }, originalSession)
      await persistRestoreCreateCommand({ ...original, ack, rejection: null }, undefined, guard)
      releaseRestoreCreateMemory(command.command_id, originalSession)
      const confirmed = await load()
      if (valid(token)) { setCommands(confirmed); setError('原创建 ACK 已保存；仅说明原恢复稿已创建。请另行读取实际恢复稿，不据此推测当前状态。') }
    } catch (reason) {
      if (valid(token, false)) {
        if (!command.ack && !denied(reason) && reason instanceof ApiError && [400, 409, 412, 422].includes(reason.status)) {
          try {
            const code = /^[A-Z][A-Z0-9_]{0,79}$/.test(reason.code ?? '') ? reason.code! : null
            const rejected = { ...command, rejection: { status: reason.status, code } }
            retainRestoreCreateMemory(rejected, originalSession)
            await persistRestoreCreateCommand(rejected, undefined, guard)
            releaseRestoreCreateMemory(command.command_id, originalSession)
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
      for (const command of recoverableRestoreCreateMemory(workspace, session)) {
        await persistRestoreCreateCommand(command, undefined, guard)
        if (!valid(token)) return
        releaseRestoreCreateMemory(command.command_id, session)
      }
      const values = await load(); if (valid(token)) setCommands(values)
    } catch (reason) { if (valid(token, false)) fail(reason) }
    finally { unsubscribe(); writers.current.delete(controller); finish(token) }
  }
  const create = async (reason: string) => {
    if (!current() || working.current || !basis) return
    const selectedAt = sequence.current
    try {
      const body = restoreRequest({ source_ref: basis.source_ref, expected_current_ref: basis.base_ref, reason })
      const values = await load()
      if (!current() || working.current || sequence.current !== selectedAt) return
      setCommands(values)
      if (values.some(value => sameValue(value.body, body) && !value.rejection)) {
        setError('已有相同恢复原命令，须保留原 key 和基准；请使用原命令恢复或另行读取。'); return
      }
      await execute(makeRestoreCreateCommand(workspace, access, body))
    } catch (reason) { if (current()) fail(reason) }
  }
  const read = async (id: string) => {
    const token = begin(); if (token === null) return
    setDraft(null)
    try {
      const known = (await load()).filter(command => command.ack?.candidate.draft_id === id)
      const value = restoreSnapshot(await port.draft(id), id)
      if (value.source_ref.id !== blockId || known.some(command => !sameValue(command.ack!.candidate, value.candidate)
          || !sameValue(command.body.source_ref, value.source_ref) || !sameValue(command.body.expected_current_ref, value.base_ref)
          || command.body.reason !== value.reason)) throw new Error('恢复稿不匹配原 ACK、块或创建基准。')
      if (valid(token)) setDraft(value)
    } catch (reason) { if (valid(token, false)) fail(reason) } finally { finish(token) }
  }
  return { ready, busy: renderOwner === owner && busy, pendingMemory: pendingRestoreCreateMemory(workspace),
    canSaveMemory: ready && recoverableRestoreCreateMemory(workspace, sessionIdentity.current).length > 0, saveMemory,
    error: renderOwner === owner ? error : '',
    commands: ready ? commands : [], basis: ready ? basis : null, preparedAt,
    draft: ready ? draft : null, refresh, prepare, create, execute, read,
    canReplay: (value: RestoreCreateCommand) => ready && value.workspace_id === workspace && value.body.source_ref.id === blockId && sameRestoreCreateActorPage(value, access) }
}
