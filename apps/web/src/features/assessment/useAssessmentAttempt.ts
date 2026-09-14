import { useEffect, useRef, useState } from 'react'
import { request } from '../../api/client'
import type { ResponseDraft } from '../../../../../packages/contracts/generated/types'
import { sameRef } from '../reader/target'
import { normalizeResponses, sameResponses } from '../../shared/responses'
import { assessmentDirty, assessmentKey, decodeAssessmentEnvelope, useAssessmentDrafts, type AssessmentEnvelope } from './assessmentDrafts'
import { readAttempt, validateAttempt, type AttemptRead } from './assessmentClient'
import type { AssessmentTarget } from './target'
export type AssessmentConflict = { base: ResponseDraft[] | null; local: ResponseDraft[]; remote: AttemptRead }
export type AssessmentSaveState = 'loading' | 'saved' | 'dirty' | 'saving' | 'offline' | 'conflict'
const message = (error: unknown) => error instanceof Error ? error.message : '测试操作尚未完成。'
const policyEqual = (left: AssessmentEnvelope['policy'], right: AssessmentEnvelope['policy']) => left.mode === right.mode && left.tutor_scope === right.tutor_scope && left.allow_web === right.allow_web && left.allow_materials === right.allow_materials && left.solution_release === right.solution_release && (left.policy_version ?? '1.0.0') === (right.policy_version ?? '1.0.0')
export function useAssessmentAttempt(workspace: string, target: AssessmentTarget & { attempt_id: string }) {
  const journal = useAssessmentDrafts(workspace), journalRef = useRef(journal); journalRef.current = journal
  const [data, setData] = useState<AttemptRead | null>(null), [responses, setResponses] = useState<ResponseDraft[]>([])
  const [state, setState] = useState<AssessmentSaveState>('loading'), [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const [conflict, setConflict] = useState<AssessmentConflict | null>(null), [claimed, setClaimed] = useState(false)
  const active = useRef(false), epoch = useRef(0), baseline = useRef<AttemptRead | null>(null), candidate = useRef<ResponseDraft[]>([])
  const editing = useRef(false), writing = useRef(false), envelope = useRef<AssessmentEnvelope | null>(null)
  const pending = useRef<{ revision: number; responses: ResponseDraft[]; key: string } | null>(null)
  const pendingAction = useRef<{ fingerprint: string; key: string } | null>(null)
  const key = assessmentKey(target.attempt_id), stored = journal.records[key], localConflicts = stored?.conflicts ?? []
  let storedEnvelope: AssessmentEnvelope | null = null, recoveryError = ''
  const validEnvelope = (value: AssessmentEnvelope) => {
    if (value.attempt_id !== target.attempt_id || !sameRef(value.assessment_ref, target.assessment_ref) || (value.course_ref || target.course_ref) && !sameRef(value.course_ref, target.course_ref)) throw new Error('本机作答实例或精确父链与当前标签不同，原记录保留。')
    return value
  }
  try { if (stored) storedEnvelope = validEnvelope(decodeAssessmentEnvelope(stored.text, workspace)) } catch (reason) { recoveryError = message(reason) }
  const needsRecovery = !claimed && !!storedEnvelope && assessmentDirty(storedEnvelope)
  const draft = (base: AttemptRead, values: ResponseDraft[]): AssessmentEnvelope => ({ version: 1, workspace_id: workspace, attempt_id: base.snapshot.id, assessment_ref: base.snapshot.assessment_ref, course_ref: target.course_ref ?? null, policy: base.snapshot.policy, base_revision: base.snapshot.revision, base_status: base.snapshot.status as AssessmentEnvelope['base_status'], base_responses: normalizeResponses(base.responses), candidate_responses: normalizeResponses(values) })
  const persist = (value: AssessmentEnvelope) => { envelope.current = value; journalRef.current.save(value) }
  const show = (remote: AttemptRead, values = remote.responses, keep = false) => {
    baseline.current = remote; setData(remote); candidate.current = normalizeResponses(values); setResponses(candidate.current)
    editing.current = !sameResponses(values, remote.responses)
    setState(editing.current ? remote.snapshot.status === 'active' ? 'dirty' : 'offline' : 'saved')
    if (keep) persist(draft(remote, values))
  }
  const reconcile = (remote: AttemptRead) => {
    if (!editing.current) { show(remote); return }
    const base = baseline.current, frozen = envelope.current
    const revision = base?.snapshot.revision ?? frozen?.base_revision, baseResponses = base?.responses ?? frozen?.base_responses
    if (candidate.current.some(item => !remote.snapshot.questions.some(question => question.id === item.question_id))) { setData(remote); setConflict({ base: baseResponses ?? null, local: candidate.current, remote }); setState('conflict'); setError('本机作答包含未分配题号，未写入。'); return }
    if (sameResponses(candidate.current, remote.responses)) { show(remote, remote.responses, true); pending.current = null; return }
    if (remote.snapshot.status === 'active' && (revision === remote.snapshot.revision && baseResponses && sameResponses(baseResponses, remote.responses) || pending.current && sameResponses(pending.current.responses, remote.responses))) { show(remote, candidate.current, true); pending.current = null; return }
    setData(remote); setConflict({ base: baseResponses ?? null, local: candidate.current, remote }); setState('conflict')
  }
  const retry = async () => {
    if (writing.current) return
    const owner = epoch.current; setBusy(true); setError('')
    try { const remote = await readAttempt(workspace, target); if (active.current && owner === epoch.current) reconcile(remote) }
    catch (reason) { if (active.current && owner === epoch.current) { setError(message(reason)); setState('offline') } }
    finally { if (active.current && owner === epoch.current) setBusy(false) }
  }
  useEffect(() => {
    active.current = true; ++epoch.current; baseline.current = null; candidate.current = []; editing.current = false; writing.current = false; pending.current = null; pendingAction.current = null; envelope.current = null
    setData(null); setResponses([]); setClaimed(false); setConflict(null); setState('loading'); void retry()
    return () => { active.current = false; ++epoch.current }
  }, [workspace, JSON.stringify(target)])
  const update = (value: ResponseDraft) => {
    const base = baseline.current
    if (!base || base.snapshot.status !== 'active' || !journal.ready || busy || conflict || needsRecovery || localConflicts.length || recoveryError) return
    try {
      if (!base.snapshot.questions.some(question => question.id === value.question_id)) throw new Error('题号不属于当前冻结测试。')
      const values = normalizeResponses([...candidate.current.filter(item => item.question_id !== value.question_id), value])
      candidate.current = values; setResponses(values); editing.current = true; setClaimed(true); setError(''); setState('dirty'); persist(draft(base, values))
    } catch (reason) { setError(message(reason)) }
  }
  const save = async () => {
    const base = baseline.current
    if (!active.current || !base || base.snapshot.status !== 'active' || writing.current || busy || conflict || needsRecovery || journalRef.current.records[key]?.conflicts.length || !editing.current) return
    const owner = epoch.current, captured = normalizeResponses(candidate.current)
    const command = pending.current && pending.current.revision === base.snapshot.revision && sameResponses(pending.current.responses, captured) ? pending.current : { revision: base.snapshot.revision, responses: captured, key: crypto.randomUUID() }
    pending.current = command; writing.current = true; setState('saving'); setError('')
    try {
      const snapshot = validateAttempt(await request('PUT /api/v1/attempts/{id}/responses', { expected_revision: command.revision, responses: command.responses }, { 'Idempotency-Key': command.key }, { path: { id: target.attempt_id } }), target, workspace)
      if (!active.current || owner !== epoch.current) return
      if (snapshot.revision !== command.revision + 1 || snapshot.status !== 'active') throw new Error('保存回执与作答命令不匹配，请重新读取。')
      // The response is an actual CAS acknowledgement for precisely this body.
      pending.current = null; show({ snapshot, responses: captured, saved_at: null }, candidate.current, true)
    } catch (reason) {
      if (!active.current || owner !== epoch.current) return
      setError(`作答尚未确认保存：${message(reason)}`); setState('offline')
      if (reason && typeof reason === 'object' && 'status' in reason && (reason.status === 412 || reason.status === 409)) {
        try { const remote = await readAttempt(workspace, target); if (active.current && owner === epoch.current) { setData(remote); setConflict({ base: base.responses, local: candidate.current, remote }); setState('conflict') } } catch (failure) { if (active.current && owner === epoch.current) setError(message(failure)) }
      }
    } finally { if (active.current && owner === epoch.current) writing.current = false }
  }
  useEffect(() => { if (state !== 'dirty' || busy || conflict || needsRecovery || localConflicts.length || journal.saving) return; const timer = setTimeout(() => void save(), 450); return () => clearTimeout(timer) }, [state, responses, busy, conflict, needsRecovery, localConflicts.length, journal.saving])
  const restore = async (value: AssessmentEnvelope) => {
    try {
      validEnvelope(value)
      const remote = baseline.current
      if (remote && (!policyEqual(value.policy, remote.snapshot.policy) || value.candidate_responses.some(item => !remote.snapshot.questions.some(question => question.id === item.question_id)))) throw new Error('本机候选冻结策略或题号不匹配，原记录保留。')
      setClaimed(true); editing.current = true; envelope.current = value; candidate.current = value.candidate_responses; setResponses(value.candidate_responses); setError('')
      if (!remote) { setState('offline'); return }
      if (remote.snapshot.status !== 'active' || value.base_revision !== remote.snapshot.revision || !sameResponses(value.base_responses, remote.responses)) { setConflict({ base: value.base_responses, local: value.candidate_responses, remote }); setState('conflict') }
      else show(remote, value.candidate_responses, true)
    } catch (reason) { setError(message(reason)) }
  }
  const resolveLocal = async (text: string) => {
    const owner = epoch.current; setBusy(true)
    try { const value = await journalRef.current.resolve(key, text); if (active.current && owner === epoch.current) await restore(value) }
    catch (reason) { if (active.current && owner === epoch.current) setError(message(reason)) }
    finally { if (active.current && owner === epoch.current) setBusy(false) }
  }
  const resolveServer = (keepLocal: boolean) => {
    if (!conflict) return
    const values = keepLocal ? candidate.current : conflict.remote.responses
    setClaimed(true); setConflict(null); setError(''); pending.current = null; show(conflict.remote, values, true)
    if (keepLocal && conflict.remote.snapshot.status !== 'active') setError('测试已经结束。本机候选保留，绝不会修改已提交或已放弃的作答快照。')
  }
  const commandReady = journal.ready && !!data && state === 'saved' && !busy && !writing.current && !editing.current && !needsRecovery && !conflict && !localConflicts.length && !recoveryError && !journal.saving
  const abandonReady = !!data && data.snapshot.status === 'active' && !busy && !writing.current && !journal.unsafe
  const transition = async (kind: 'submit' | 'abandon') => {
    const base = baseline.current
    if (!active.current || !base || base.snapshot.status !== 'active' || !(kind === 'submit' ? commandReady : abandonReady)) return
    const owner = epoch.current; setBusy(true); setError('')
    try {
      const fingerprint = JSON.stringify([base.snapshot.id, base.snapshot.revision, kind])
      if (pendingAction.current?.fingerprint !== fingerprint) pendingAction.current = { fingerprint, key: crypto.randomUUID() }
      const route = kind === 'submit' ? 'POST /api/v1/attempts/{id}/submit' : 'POST /api/v1/attempts/{id}/abandon'
      const snapshot = validateAttempt(await request(route, { expected_revision: base.snapshot.revision }, { 'Idempotency-Key': pendingAction.current.key }, { path: { id: base.snapshot.id } }), target, workspace)
      if (!active.current || owner !== epoch.current) return
      if (snapshot.status !== (kind === 'submit' ? 'submitted' : 'abandoned')) throw new Error('终态回执不匹配，请重新读取。')
      // Both commands freeze the already acknowledged server responses. Local
      // candidates are journalled separately and never copied into the receipt.
      show({ ...base, snapshot }, candidate.current, editing.current); pendingAction.current = null
    } catch (reason) {
      if (!active.current || owner !== epoch.current) return
      setError(`操作尚未确认：${message(reason)}。重新核对后再明确操作，不会自动重放提交或放弃。`)
      try { const remote = await readAttempt(workspace, target); if (active.current && owner === epoch.current) reconcile(remote) } catch { if (active.current && owner === epoch.current) setState('offline') }
    } finally { if (active.current && owner === epoch.current) setBusy(false) }
  }
  return { snapshot: data?.snapshot ?? null, serverResponses: data?.responses ?? [], responses, state, error, busy, conflict, stored, storedEnvelope, localConflicts, needsRecovery, commandReady, abandonReady,
    update, save, retry, restore, resolveLocal, resolveServer, submit: () => transition('submit'), abandon: () => transition('abandon'),
    localReady: journal.ready, localError: recoveryError || journal.error, localSaving: journal.saving, dirty: editing.current || needsRecovery || localConflicts.length > 0, safe: !journal.unsafe,
    retryLocal: () => { if (envelope.current) journal.save(envelope.current) },
  }
}
