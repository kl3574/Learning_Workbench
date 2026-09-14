import { useEffect, useRef, useState } from 'react'
import { request } from '../../api/client'
import type { ResponseDraft } from '../../../../../packages/contracts/generated/types'
import type { PracticeHint, PracticeSession, PracticeSolution } from '../../../../../packages/contracts/generated/api-types'
import { sameRef } from '../reader/target'
import { decodePracticeEnvelope, normalizeResponses, practiceDirty, practiceKey, sameResponses, type PracticeEnvelope } from './practiceDrafts'
import { usePracticeDrafts } from './usePracticeDrafts'
import type { PracticeTarget } from './target'
export type PracticeConflict = { base: ResponseDraft[] | null; local: ResponseDraft[]; remote: PracticeSession }
export type PracticeSaveState = 'loading' | 'saved' | 'dirty' | 'saving' | 'offline' | 'conflict'
const message = (reason: unknown) => reason instanceof Error ? reason.message : '练习请求未完成。'
export function usePracticeSession(workspace: string, target: PracticeTarget & { session_id: string }) {
  const journal = usePracticeDrafts(workspace)
  const journalRef = useRef(journal); journalRef.current = journal
  const [snapshot, setSnapshot] = useState<PracticeSession | null>(null)
  const [responses, setResponses] = useState<ResponseDraft[]>([])
  const [state, setState] = useState<PracticeSaveState>('loading')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [conflict, setConflict] = useState<PracticeConflict | null>(null)
  const [claimed, setClaimed] = useState(false)
  const [hints, setHints] = useState<Record<string, PracticeHint>>({})
  const [solutions, setSolutions] = useState<Record<string, PracticeSolution>>({})
  const active = useRef(false), epoch = useRef(0)
  const baseline = useRef<PracticeSession | null>(null)
  const candidate = useRef<ResponseDraft[]>([])
  const envelope = useRef<PracticeEnvelope | null>(null)
  const editing = useRef(false), writing = useRef(false)
  const pendingAction = useRef<{ fingerprint: string; key: string } | null>(null)
  const pending = useRef<{ revision: number; responses: ResponseDraft[]; key: string } | null>(null)
  const key = practiceKey(target.session_id)
  const stored = journal.records[key]
  const localConflicts = stored?.conflicts ?? []
  let storedEnvelope: PracticeEnvelope | null = null
  let recoveryError = ''
  try { if (stored) { storedEnvelope = decodePracticeEnvelope(stored.text, workspace); if (!sameRef(storedEnvelope.practice_ref, target.practice_ref)) throw new Error('本机作答题集哈希与当前标签不一致；原记录保留。') } } catch (reason) { recoveryError = message(reason) }
  const needsRecovery = !claimed && !!storedEnvelope && practiceDirty(storedEnvelope)
  const valid = (value: PracticeSession) => {
    if (value.id !== target.session_id || !sameRef(value.practice_ref, target.practice_ref) || !sameRef(value.lesson_ref, target.lesson_ref)) throw new Error('服务端会话与精确题集引用不一致，未替换当前标签。')
    return value
  }
  const draft = (base: PracticeSession, values: ResponseDraft[]): PracticeEnvelope => ({ version: 1, workspace_id: workspace, session_id: base.id, practice_ref: base.practice_ref, base_revision: base.revision, base_responses: normalizeResponses(base.responses), candidate_responses: normalizeResponses(values) })
  const persist = (value: PracticeEnvelope) => { envelope.current = value; journalRef.current.save(value) }
  const show = (remote: PracticeSession, values = remote.responses, keep = false) => {
    baseline.current = remote; setSnapshot(remote); candidate.current = normalizeResponses(values); setResponses(candidate.current)
    const dirty = !sameResponses(candidate.current, remote.responses)
    editing.current = dirty; setState(dirty ? remote.status === 'active' ? 'dirty' : 'offline' : 'saved')
    if (keep) persist(draft(remote, candidate.current))
  }
  const read = async () => valid(await request('GET /api/v1/practice/sessions/{id}', undefined, undefined, { path: { id: target.session_id } }))
  const reconcile = (remote: PracticeSession) => {
    const base = baseline.current
    const frozen = envelope.current
    if (!editing.current) { show(remote); return }
    const baseRevision = base?.revision ?? frozen?.base_revision
    const baseResponses = base?.responses ?? frozen?.base_responses
    if (candidate.current.some(item => !remote.questions.some(question => question.id === item.question_id))) { setSnapshot(remote); setState('conflict'); setError('本机候选包含未分配的题号，未自动写入。'); setConflict({ base: baseResponses ?? null, local: candidate.current, remote }); return }
    if (sameResponses(candidate.current, remote.responses)) { show(remote, remote.responses, true); pending.current = null; return }
    if (baseRevision === remote.revision && baseResponses && sameResponses(baseResponses, remote.responses) || pending.current && sameResponses(pending.current.responses, remote.responses)) { show(remote, candidate.current, true); pending.current = null; return }
    setSnapshot(remote); setConflict({ base: baseResponses ?? null, local: candidate.current, remote }); setState('conflict')
  }
  const retry = async () => {
    if (writing.current) return
    setBusy(true); setError(''); const owner = epoch.current
    try { const remote = await read(); if (active.current && owner === epoch.current) reconcile(remote) }
    catch (reason) { if (active.current && owner === epoch.current) { setError(message(reason)); setState('offline'); setHints({}); setSolutions({}) } }
    finally { if (active.current && owner === epoch.current) setBusy(false) }
  }
  useEffect(() => {
    active.current = true; ++epoch.current; baseline.current = null; candidate.current = []; envelope.current = null; editing.current = false; writing.current = false; pending.current = null; pendingAction.current = null
    setSnapshot(null); setResponses([]); setConflict(null); setClaimed(false); setHints({}); setSolutions({}); setState('loading'); void retry()
    return () => { active.current = false; ++epoch.current }
  }, [workspace, target.session_id, target.practice_ref.sha256, target.lesson_ref.sha256])
  const update = (value: ResponseDraft) => {
    if (baseline.current?.status !== 'active' || !journal.ready || busy || conflict || needsRecovery || localConflicts.length || recoveryError) return
    let values: ResponseDraft[]
    try { values = normalizeResponses([...candidate.current.filter(item => item.question_id !== value.question_id), value]) } catch (reason) { setError(message(reason)); return }
    if (!baseline.current.questions.some(question => question.id === value.question_id)) { setError('题号不属于当前冻结会话。'); return }
    candidate.current = values; setResponses(values); setClaimed(true); editing.current = true; setError(''); setState('dirty')
    persist(draft(baseline.current, values))
  }
  const save = async () => {
    const base = baseline.current
    if (!active.current || !base || base.status !== 'active' || writing.current || busy || conflict || needsRecovery || journalRef.current.records[key]?.conflicts.length || !editing.current) return
    writing.current = true; setState('saving'); setError(''); const owner = epoch.current
    const captured = normalizeResponses(candidate.current)
    const command = pending.current && pending.current.revision === base.revision && sameResponses(pending.current.responses, captured) ? pending.current : { revision: base.revision, responses: captured, key: crypto.randomUUID() }
    pending.current = command
    try {
      const acknowledgement = await request('PUT /api/v1/practice/sessions/{id}/responses', { expected_revision: command.revision, responses: command.responses }, { 'Idempotency-Key': command.key }, { path: { id: target.session_id } })
      if (!active.current || owner !== epoch.current) return
      if (acknowledgement.id !== base.id || acknowledgement.revision !== command.revision + 1) throw new Error('保存回执不匹配当前练习与基准，请重新读取。')
      pending.current = null
      show({ ...base, revision: acknowledgement.revision, responses: captured }, candidate.current, true)
    } catch (reason) {
      if (!active.current || owner !== epoch.current) return
      setError(`作答尚未确认保存：${message(reason)}`)
      if (reason && typeof reason === 'object' && 'status' in reason && reason.status === 412) {
        try { const remote = await read(); if (active.current && owner === epoch.current) { setSnapshot(remote); setConflict({ base: base.responses, local: candidate.current, remote }); setState('conflict') } } catch (failure) { if (active.current && owner === epoch.current) { setError(message(failure)); setState('offline') } }
      } else setState('offline')
    } finally { if (active.current && owner === epoch.current) writing.current = false }
  }
  useEffect(() => {
    if (state !== 'dirty' || busy || conflict || needsRecovery || localConflicts.length || journal.saving) return
    const timer = setTimeout(() => { void save() }, 450)
    return () => clearTimeout(timer)
  }, [state, responses, busy, conflict, needsRecovery, localConflicts.length, journal.saving])
  const restore = async (value: PracticeEnvelope) => {
    if (!sameRef(value.practice_ref, target.practice_ref) || value.session_id !== target.session_id) { setError('候选作答所属会话或题集不一致，原记录保留。'); return }
    if (snapshot && value.candidate_responses.some(item => !snapshot.questions.some(question => question.id === item.question_id))) { setError('本机候选包含本会话未分配的题号，未自动保存。'); return }
    setClaimed(true); editing.current = true; envelope.current = value; candidate.current = value.candidate_responses; setResponses(value.candidate_responses); setError('')
    if (!snapshot) { setState('offline'); return }
    if (value.base_revision !== snapshot.revision || !sameResponses(value.base_responses, snapshot.responses)) { setConflict({ base: value.base_responses, local: value.candidate_responses, remote: snapshot }); setState('conflict') }
    else { show(snapshot, value.candidate_responses, true) }
  }
  const resolveLocal = async (text: string) => {
    setBusy(true); const owner = epoch.current
    try { const value = await journalRef.current.resolve(key, text); if (active.current && owner === epoch.current) await restore(value) }
    catch (reason) { if (active.current && owner === epoch.current) setError(message(reason)) }
    finally { if (active.current && owner === epoch.current) setBusy(false) }
  }
  const resolveServer = (keepLocal: boolean) => {
    if (!conflict) return
    const values = keepLocal ? candidate.current : conflict.remote.responses
    setClaimed(true); setConflict(null); setError(''); pending.current = null; show(conflict.remote, values, true)
    if (keepLocal && conflict.remote.status !== 'active') setError('练习已提交，未同步作答仍保留在本机；不会修改已提交快照。')
  }
  const commandReady = journal.ready && !!snapshot && state === 'saved' && !busy && !writing.current && !editing.current && !needsRecovery && !conflict && !localConflicts.length && !recoveryError && !journal.saving
  const mutate = async (kind: 'submit' | 'hint' | 'solution', questionId?: string, level?: 1 | 2 | 3) => {
    const base = baseline.current
    if (!active.current || !base || !commandReady || base.status === 'abandoned' || kind === 'submit' && base.status !== 'active') return
    setBusy(true); setError(''); const owner = epoch.current
    try {
      const fingerprint = JSON.stringify([base.id, base.revision, kind, questionId, level])
      if (pendingAction.current?.fingerprint !== fingerprint) pendingAction.current = { fingerprint, key: crypto.randomUUID() }
      const headers = { 'Idempotency-Key': pendingAction.current.key }
      if (kind === 'submit') await request('POST /api/v1/practice/sessions/{id}/submit', { expected_revision: base.revision }, headers, { path: { id: base.id } })
      else if (kind === 'hint' && questionId && level) { const hint = await request('POST /api/v1/practice/sessions/{id}/hints', { question_id: questionId, expected_revision: base.revision, level }, headers, { path: { id: base.id } }); if (active.current && owner === epoch.current) setHints(old => ({ ...old, [questionId]: hint })) }
      else if (kind === 'solution' && questionId) { const solution = await request('POST /api/v1/practice/sessions/{id}/solutions', { question_id: questionId, expected_revision: base.revision }, headers, { path: { id: base.id } }); if (active.current && owner === epoch.current) setSolutions(old => ({ ...old, [questionId]: solution })) }
      const remote = await read()
      if (active.current && owner === epoch.current) { show(remote); pendingAction.current = null }
    } catch (reason) {
      if (!active.current || owner !== epoch.current) return
      setError(`操作未确认完成：${message(reason)}。请重新读取状态后再明确操作。`)
      try { const remote = await read(); if (active.current && owner === epoch.current) reconcile(remote) } catch { if (active.current && owner === epoch.current) setState('offline') }
    } finally { if (active.current && owner === epoch.current) setBusy(false) }
  }
  return { snapshot, responses, state, error, busy, conflict, needsRecovery, storedEnvelope, localConflicts, stored, hints, solutions, commandReady, update, save, retry, restore, resolveLocal, resolveServer,
    submit: () => mutate('submit'), hint: (id: string, level: 1 | 2 | 3) => mutate('hint', id, level), reveal: (id: string) => mutate('solution', id),
    hideSolution: (id: string) => setSolutions(old => { const next = { ...old }; delete next[id]; return next }),
    localReady: journal.ready, localError: recoveryError || journal.error, localSaving: journal.saving, retryLocal: () => { if (envelope.current) journal.save(envelope.current) },
    dirty: editing.current || needsRecovery || localConflicts.length > 0, safe: !journal.unsafe,
  }
}
