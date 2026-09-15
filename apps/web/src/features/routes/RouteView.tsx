import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { SavedTab } from '../../../../../packages/contracts/generated/types'
import type { LearningProgress, RouteTargetBinding } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, getSessionGeneration, request, subscribeSessionAccess } from '../../api/client'
import { refKey, sameRef, type ReaderTarget } from '../reader/target'
import type { PracticeTarget } from '../practice/target'
import type { AssessmentTarget } from '../assessment/target'
import { completionKey, completionStore, decodeCompletion, useCompletionJournal, type CompletionDraft } from './completionDrafts'
import type { RouteRecord } from './routeClient'
import { readRouteProgress } from './routeClient'
import '../learning/learning.css'
import './routes.css'
const origins = { none: '尚未完成', manual: '人工标记', read: '明确阅读记录', practice_submitted: '真实练习提交', assessment_submitted: '真实测试提交' }
export function RouteView({ workspace, item, progress, tab, latest, refresh, edit, reader, practice, assessment, scrollChanged, onState }: { workspace: string; item: RouteRecord; progress: LearningProgress; tab: SavedTab; latest: boolean; refresh: () => void; edit: () => void; reader: (target: ReaderTarget, pinned?: boolean) => void; practice: (target: PracticeTarget, pinned?: boolean) => void; assessment: (target: AssessmentTarget, pinned?: boolean) => void; scrollChanged: (offset: number) => void; onState: (value: { dirty: boolean; safe: boolean; title: string; goal: string }) => void }) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration), owner = `${workspace}:${refKey(item.ref)}:${access}`, current = useRef(owner); current.current = owner
  const journal = useCompletionJournal(workspace), [pending, setPending] = useState<CompletionDraft | null>(null), [busy, setBusy] = useState(false), [error, setError] = useState(''), [remote, setRemote] = useState<LearningProgress | null>(null)
  const scroll = useRef<HTMLDivElement>(null), restored = useRef(false), notified = useRef<string | null>(null)
  const pendingCandidates: { text: string; value: CompletionDraft }[] = []; let decodeError = ''
  for (const record of Object.values(journal.records)) for (const text of new Set([record.text, ...record.conflicts.map(value => value.text)])) { try { const value = decodeCompletion(text, workspace); if (!value.acknowledged && sameRef(value.route_ref, item.ref)) pendingCandidates.push({ text, value }) } catch (reason) { decodeError = reason instanceof Error ? reason.message : '完成候选无法读取。' } }
  const safe = journal.ready && !journal.unsafe && !journal.error && !decodeError
  const callback = useRef(onState); callback.current = onState
  useEffect(() => { callback.current({ dirty: pendingCandidates.length > 0 || !!pending && !pending.acknowledged, safe, title: item.route.title, goal: item.route.goal }) }, [pendingCandidates.length, pending, safe, item.route.title, item.route.goal])
  useEffect(() => { if (scroll.current && !restored.current) { scroll.current.scrollTop = tab.scroll_offset ?? 0; restored.current = true } }, [])
  const savedCallback = useRef(refresh); savedCallback.current = refresh
  useEffect(() => { if (pending?.acknowledged && safe && notified.current !== pending.command_id) { notified.current = pending.command_id; savedCallback.current() } }, [pending, safe])
  const state = (step: string, source = progress) => source.route_steps.find(value => sameRef(value.route_ref, item.ref) && value.step_id === step)
  const choose = (step: string, completed: boolean) => {
    const before = state(step); if (!before || busy || !safe || pendingCandidates.length) return
    const value: CompletionDraft = { version: 1, workspace_id: workspace, route_ref: item.ref, step_id: step, base_completed: before.completed, expected_progress_revision: progress.revision, completed, command_id: `route_mark_${crypto.randomUUID()}`, acknowledged: null }
    setPending(value); journal.save(value); setRemote(null); setError('')
  }
  const restore = async (text: string, value: CompletionDraft) => {
    if (busy || !safe) return
    const captured = owner; setBusy(true)
    try {
      const key = completionKey(value), persisted = (await completionStore.load(workspace))[key]
      if (!persisted || ![persisted.text, ...persisted.conflicts.map(item => item.text)].includes(text)) throw new Error('该完成候选尚未从本机存储读回。')
      const chosen = persisted.conflicts.length ? await journal.resolve(key, text) : value
      const actual = await readRouteProgress(); if (current.current !== captured) return
      setPending(chosen); setRemote(actual.revision === chosen.expected_progress_revision ? null : actual); setError('')
    } catch (reason) { if (current.current === captured) setError(reason instanceof Error ? reason.message : '完成候选尚未恢复。') } finally { if (current.current === captured) setBusy(false) }
  }
  const confirm = async () => {
    if (!pending || pending.acknowledged || busy || !safe) return
    const captured = owner, value = pending, key = completionKey(value)
    if (journal.records[key]?.conflicts.length) { setError('其他页面有不同标记候选，请先逐项选择。'); return }
    setBusy(true); setError('')
    try {
      const disk = (await completionStore.load(workspace))[key]
      if (!disk || ![disk.text, ...disk.conflicts.map(item => item.text)].includes(JSON.stringify(value))) throw new Error('当前标记命令尚未持久化，不发送。')
      if (current.current !== captured) return
      const acknowledged = await request('POST /api/v1/routes/{id}/steps/{step_id}/complete', { route_revision: value.route_ref.revision, expected_progress_revision: value.expected_progress_revision, completed: value.completed, origin: 'manual' }, { 'Idempotency-Key': value.command_id }, { path: { id: value.route_ref.id, step_id: value.step_id } })
      const saved = decodeCompletion(JSON.stringify({ ...value, acknowledged }), workspace); journal.save(saved)
      if (current.current === captured) { setPending(saved); setRemote(null) }
    } catch (reason) {
      if (current.current !== captured) return
      if (reason instanceof ApiError && reason.status === 412) { try { const actual = await readRouteProgress(); if (current.current === captured) setRemote(actual) } catch { /* original baseline is preserved */ } }
      if (current.current === captured) setError(`人工标记未确认，原候选与命令仍保留。${reason instanceof Error ? reason.message : ''}`)
    } finally { if (current.current === captured) setBusy(false) }
  }
  const open = (option: RouteTargetBinding['navigation_options'][number]) => { if (option.kind === 'reader') reader({ course: option.course_ref, lesson: option.lesson_ref, ...(option.block_ref ? { block: option.block_ref } : {}) }, true); else if (option.kind === 'practice') practice({ course_ref: option.course_ref, lesson_ref: option.lesson_ref, practice_ref: option.practice_ref }, true); else assessment({ assessment_ref: option.assessment_ref, ...(option.course_ref ? { course_ref: option.course_ref } : {}) }, true) }
  return <div ref={scroll} className="reader-scroll" onScroll={event => { if (restored.current) scrollChanged(event.currentTarget.scrollTop) }}><article className="reader-content learning-panel route-content"><div className="eyebrow">学习路线 · {latest ? '最新可读修订' : '历史修订'}</div><h1>{item.route.title}</h1><p>{item.route.goal}</p><p>路线 r{item.ref.revision}。人工完成只表示你的标记；阅读、参与和能力证据分别记录。</p><div className="learning-actions"><button onClick={refresh}>刷新路线完成状态</button><button disabled={!safe} onClick={edit}>编辑路线并保存新修订</button></div>{[error, journal.error, decodeError].filter(Boolean).map((message, index) => <p role="alert" key={index}>{message}</p>)}
    {!pending && pendingCandidates.length > 0 && <section className="route-completion"><h2>发现本机路线标记候选</h2>{pendingCandidates.map((candidate, index) => <div key={candidate.text}><p>{item.route.steps.find(step => step.id === candidate.value.step_id)?.title ?? candidate.value.step_id}：手动{candidate.value.completed ? '已完成' : '未完成'}，基准进度 r{candidate.value.expected_progress_revision}</p><button disabled={!safe || busy} onClick={() => void restore(candidate.text, candidate.value)}>恢复路线标记候选 {index + 1}</button></div>)}</section>}
    {pending && !pending.acknowledged && <section className="route-completion"><h2>确认人工完成标记</h2><p>{item.route.steps.find(step => step.id === pending.step_id)?.title}：将手动标为{pending.completed ? '已完成' : '未完成'}。标记不会授予掌握证据。</p>{remote && <><p>进度基准已变化。原基准：{pending.base_completed ? '已完成' : '未完成'}；本页：{pending.completed ? '已完成' : '未完成'}；服务端：{state(pending.step_id, remote)?.completed ? '已完成' : '未完成'}。</p><button disabled={!safe || busy} onClick={() => { const before = state(pending.step_id, remote); if (!before) return; const value = { ...pending, base_completed: before.completed, expected_progress_revision: remote.revision, command_id: `route_mark_${crypto.randomUUID()}` }; setPending(value); journal.save(value); setRemote(null) }}>保留标记并采用最新进度基准</button></>}<button disabled={!safe || busy || !!remote} onClick={() => void confirm()}>确认保存人工标记</button>{error && <button disabled={!safe || busy} onClick={() => void confirm()}>重试原人工标记命令</button>}<p role="status">{journal.saving ? '本机标记保存中…' : safe ? '本机标记已保存，服务端尚未确认' : '本机标记尚未安全保存'}</p></section>}
    <ol className="route-list">{item.route.steps.map(step => { const currentState = state(step.id), binding = item.bindings.find(value => value.step_id === step.id); return <li key={step.id}><div className="route-step-header"><h2>{step.title}</h2><strong>{currentState ? currentState.completed ? '已完成' : '未完成' : '完成状态尚未读回'}</strong></div>{currentState && <><p className="route-source">来源：{currentState.completion_origin ? origins[currentState.completion_origin] : '尚待来源回读'}{currentState.manual_override === false && ' · 人工未完成优先保留'}{currentState.manual_override === true && ' · 人工已完成优先保留'}。</p>{(currentState.unmet_requires_steps?.length ?? 0) > 0 && <p className="route-reminder">先修提醒：{currentState.unmet_requires_steps!.map(id => item.route.steps.find(value => value.id === id)?.title ?? id).join('、')}尚未完成；仍可打开本任务。</p>}<details><summary>核对完成来源与时间</summary><p>标记更新时间：{currentState.updated_at ?? '尚无'}；完成时间：{currentState.completed_at ?? '尚无'}。</p>{currentState.source_event_ids?.map(id => <p key={id}><code>{id}</code></p>)}<p>新路线修订不继承旧人工标记；精确目标的真实活动可以独立满足自动规则。</p></details></>}<div className="route-navigation-options">{binding?.navigation_options.map((option, index) => <button key={JSON.stringify(option)} disabled={!safe} onClick={() => open(option)}>打开任务{binding.navigation_options.length > 1 ? ` · 父链 ${index + 1}（${option.course_ref?.id ?? '全局测试'} r${option.course_ref?.revision ?? '—'}）` : ''}：{step.title}</button>)}{binding?.unresolved_reason && <p>没有可核验的精确父课程；原目标仍保留，未打开其他版本。</p>}</div><details><summary>精确任务引用</summary><code className="route-reference">{step.target.entity} · {step.target.id} · r{step.target.revision}<br />SHA-256 {step.target.sha256}</code></details><div className="learning-actions"><button disabled={!currentState || !safe || busy || pendingCandidates.length > 0} onClick={() => choose(step.id, true)}>手动标为已完成：{step.title}</button><button disabled={!currentState || !safe || busy || pendingCandidates.length > 0} onClick={() => choose(step.id, false)}>手动标为未完成：{step.title}</button></div></li> })}</ol>
  </article></div>
}
