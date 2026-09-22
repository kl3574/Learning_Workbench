import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { AuthoringDraftView, AuthoringJobReadView, AuthoringGroupDraftView, AuthoringGroupNumericCheckView, AuthoringPrivateSolutionView, JobSnapshot, NumericCheckView } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import { digest } from '../retrieval/retrievalModel'
import { sameValue } from '../providers/providerSchema'
import { authoringClient, type AuthoringPort } from './authoringClient'
import { authoringCommandStore, authoringControlStore, checkedAuthoring, makeAuthoringCommand, persistAuthoringCommand, readAuthoringCommand, type AuthoringCommand, type AuthoringCommandInput } from './authoringCommands'

const policyDenied = (reason: unknown) => reason instanceof ApiError && (reason.status === 401 || reason.status === 403 || ['ASSESSMENT_ACTIVE', 'POLICY_DENIED', 'ASSESSMENT_ANSWER_PROTECTED'].includes(reason.code ?? ''))

export function useAuthoring(workspace: string, paused: boolean, port: AuthoringPort = authoringClient) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  const owner = JSON.stringify([workspace, access]), scope = useRef({ owner, paused }); scope.current = { owner, paused }
  const operation = useRef(0), working = useRef(false)
  const subjectWrites = useRef(new Set<AbortController>())
  const abortSubjectWrites = () => { for (const controller of subjectWrites.current) controller.abort() }
  const [renderOwner, setRenderOwner] = useState(owner), [permission, setPermission] = useState(false), [denied, setDenied] = useState(false)
  const [jobs, setJobs] = useState<JobSnapshot[]>([]), [cursor, setCursor] = useState<string | null>(null)
  const [detail, setDetail] = useState<AuthoringJobReadView | null>(null), [draft, setDraft] = useState<AuthoringDraftView | AuthoringGroupDraftView | null>(null), [numeric, setNumeric] = useState<NumericCheckView | AuthoringGroupNumericCheckView | null>(null)
  const [privateSolution, setPrivateSolution] = useState<AuthoringPrivateSolutionView | null>(null)
  const groupPort = () => { if (!port.groups) throw new Error('Group Authoring port unavailable'); return port.groups }
  const [subjectReady, setSubjectReady] = useState(false)
  const [commands, setCommands] = useState<AuthoringCommand[]>([]), [ready, setReady] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const academic = renderOwner === owner && permission && !paused && !denied
  const academicRef = useRef(academic); academicRef.current = academic
  const current = (subject = false) => scope.current.owner === owner && getSessionGeneration() === access && (!subject || !scope.current.paused && academicRef.current)
  const clearSubject = () => { academicRef.current = false; abortSubjectWrites(); setDetail(null); setDraft(null); setNumeric(null); setPrivateSolution(null); setSubjectReady(false); setCommands(old => old.filter(v => v.kind === 'cancel')) }
  const fail = (reason: unknown) => {
    const policy = policyDenied(reason)
    if (policy) { academicRef.current = false; setDenied(true); setPermission(false); clearSubject() }
    const code = reason instanceof ApiError && /^[A-Z][A-Z0-9_]{0,79}$/.test(reason.code ?? '') ? `${reason.code}：` : ''
    setError(code + (policy ? '当前权限或测试策略不允许学科读取；已有任务仍可在安全列表中取消。' : reason instanceof ApiError && reason.status === 412 ? '版本冲突：原 key、基准与候选保留。请另行读取当前状态，再明确准备新命令。' : '本次操作未确认或被服务端阻断。原命令保留；请回放原命令或重新读取，不会自动发送新 key。'))
  }
  const checkedJob = (value: JobSnapshot) => {
    const v = checkedAuthoring<JobSnapshot>('JobSnapshot', value)
    if (v.workspace_id !== workspace || !['authoring', 'authoring_numeric_check'].includes(v.kind) || v.result_refs.length || v.warnings.length) throw new Error('Control scope mismatch')
    return v
  }
  const loadCommands = async (subject: boolean) => {
    const control = Object.values(await authoringControlStore.load(workspace)).map(v => readAuthoringCommand(v, workspace))
    if (control.some(v => v.kind !== 'cancel')) throw new Error('Control store contains academic commands')
    if (!subject) return control
    return [...control, ...Object.values(await authoringCommandStore.load(workspace)).map(v => readAuthoringCommand(v, workspace))]
  }
  const loadList = async (more = false) => {
    const page = await port.list(more ? cursor ?? undefined : undefined)
    const values = page.items.map(checkedJob), combined = more ? [...jobs, ...values] : values
    if (new Set(combined.map(v => v.id)).size !== combined.length || more && cursor && page.next_cursor === cursor) throw new Error('Control pagination mismatch')
    if (current()) { setJobs(combined); setCursor(page.next_cursor) }
  }
  useEffect(() => {
    const sequence = ++operation.current; working.current = false; academicRef.current = false
    setRenderOwner(owner); setPermission(false); setDenied(false); clearSubject(); setJobs([]); setCursor(null); setCommands([]); setReady(false); setBusy(false); setError('')
    if (!workspace) return
    let live = true
    const valid = () => live && current() && sequence === operation.current
    void loadCommands(false).then(values => { if (valid()) { setCommands(values); setReady(true) } }).catch(failure => { if (valid()) fail(failure) })
    void loadList().catch(failure => { if (valid()) fail(failure) })
    void port.session().then(async session => {
      if (!valid()) return
      if (session.workspace_id !== workspace) throw new Error('Session workspace mismatch')
      const allowed = session.role === 'author' && session.active_independent_attempt_id === null && session.active_open_book_attempt_id === null && !paused
      setPermission(allowed)
      if (allowed) { const values = await loadCommands(true); if (valid() && !scope.current.paused) { setCommands(values); setSubjectReady(true) } }
    }).catch(failure => { if (valid()) fail(failure) })
    return () => { live = false; ++operation.current; working.current = false; abortSubjectWrites() }
  }, [owner, paused, port])
  const begin = (subject: boolean) => { if (!current(subject) || working.current) return null; working.current = true; setBusy(true); setError(''); return ++operation.current }
  const finish = (sequence: number) => { if (current() && sequence === operation.current) { working.current = false; setBusy(false) } }
  const refresh = async (more = false) => {
    const sequence = begin(false); if (sequence === null) return
    try {
      await loadList(more)
      if (!current() || sequence !== operation.current) return
      const session = await port.session()
      if (!current() || sequence !== operation.current) return
      if (session.workspace_id !== workspace) throw new Error('Session mismatch')
      const allowed = session.role === 'author' && !session.active_independent_attempt_id && !session.active_open_book_attempt_id && !scope.current.paused
      setPermission(allowed); setDenied(false); if (!allowed) clearSubject()
      const local = await loadCommands(allowed)
      if (current() && sequence === operation.current) { setCommands(local); setReady(true); setSubjectReady(allowed) }
    } catch (reason) { if (current() && sequence === operation.current) fail(reason) } finally { finish(sequence) }
  }
  const read = async (id: string) => {
    const sequence = begin(true); if (sequence === null) return
    setDetail(null); setDraft(null); setNumeric(null); setPrivateSolution(null)
    try { const value = checkedAuthoring<AuthoringJobReadView>('AuthoringJobReadView', await port.read(id)); if (value.summary.id !== id || value.summary.kind !== 'authoring') throw new Error('Wrong authoring identity'); if (current(true) && sequence === operation.current) setDetail(value) }
    catch (reason) { if (current() && sequence === operation.current) fail(reason) } finally { finish(sequence) }
  }
  const readDraft = async () => {
    if (!detail?.summary.candidate) return
    const candidate = detail.summary.candidate, job = detail.summary.id, sequence = begin(true); if (sequence === null) return
    setDraft(null); setNumeric(null); setPrivateSolution(null)
    try {
      const value = 'variant' in detail
        ? checkedAuthoring<AuthoringGroupDraftView>('AuthoringGroupDraftView', await groupPort().draft(candidate.draft_id))
        : checkedAuthoring<AuthoringDraftView>('AuthoringDraftView', await port.draft(candidate.draft_id))
      if (value.owner !== 'authoring' || value.source_job_id !== job || !sameValue(value.candidate, candidate)) throw new Error('Wrong candidate identity')
      if ('root' in value) {
        if (!('variant' in detail) || !sameValue(value.plan_ref, detail.plan_ref) || !sameValue(value.content_plan, detail.content_plan)) throw new Error('Wrong frozen group plan')
      } else if (value.body_sha256 !== digest(value.payload.body_markdown)) throw new Error('Wrong candidate body bytes')
      if (current(true) && sequence === operation.current) setDraft(value)
    }
    catch (reason) { if (current() && sequence === operation.current) fail(reason) } finally { finish(sequence) }
  }
  const readNumeric = async (id: string) => {
    if (!draft?.numeric_check_ids.includes(id)) return
    const candidate = draft.candidate, sequence = begin(true); if (sequence === null) return
    setNumeric(null)
    try {
      const value = 'root' in draft
        ? checkedAuthoring<AuthoringGroupNumericCheckView>('AuthoringGroupNumericCheckView', await groupPort().numeric(id))
        : checkedAuthoring<NumericCheckView>('NumericCheckView', await port.numeric(id))
      if (value.id !== id || !sameValue(value.candidate, candidate)) throw new Error('Wrong numeric identity')
      if ('target' in value && (!('root' in draft) || !(draft.root.entity === 'lesson' ? draft.root.blocks : draft.root.questions).some(member => sameValue(member, value.target)))) throw new Error('Wrong numeric group member')
      if (current(true) && sequence === operation.current) setNumeric(value)
    }
    catch (reason) { if (current() && sequence === operation.current) fail(reason) } finally { finish(sequence) }
  }
  const readPrivateSolution = async (member: string) => {
    if (!draft || !('root' in draft)) return
    const expected = draft.private_solution_refs.find(ref => ref.question.member_key === member)
    if (!expected) return
    const candidate = draft.candidate, sequence = begin(true); if (sequence === null) return
    setPrivateSolution(null); setNumeric(null)
    try {
      const value = checkedAuthoring<AuthoringPrivateSolutionView>('AuthoringPrivateSolutionView', await groupPort().solution(candidate.draft_id, member))
      if (!sameValue(value.candidate, candidate) || !sameValue(value.ref, expected) || !sameValue(value.payload.question, expected.question)) throw new Error('Wrong private answer binding')
      if (current(true) && sequence === operation.current) setPrivateSolution(value)
    } catch (reason) { if (current() && sequence === operation.current) fail(reason) } finally { finish(sequence) }
  }
  const execute = async (command: AuthoringCommand) => {
    if (command.workspace_id !== workspace) return
    const subject = command.kind !== 'cancel', sequence = ready && (!subject || subjectReady) ? begin(subject) : null; if (sequence === null) return
    const controller = subject ? new AbortController() : null
    if (controller) subjectWrites.current.add(controller)
    const guard = controller ? { allowed: () => current(true) && sequence === operation.current, signal: controller.signal } : undefined
    const unsubscribe = controller ? subscribeSessionAccess(() => controller.abort()) : undefined
    try {
      const retained = await persistAuthoringCommand(command, undefined, guard)
      const pending = await loadCommands(academicRef.current && subjectReady)
      if (current(subject) && sequence === operation.current) setCommands(pending)
      if (!current(subject) || sequence !== operation.current) return
      const ack = retained.ack ?? (retained.kind === 'prepare' ? await port.prepare(retained.body, retained.command_id)
        : retained.kind === 'cancel' ? await port.cancel(retained.job_id, retained.body, retained.command_id)
          : retained.kind === 'numeric_preview' ? await port.preview(retained.draft_id, retained.body, retained.command_id)
            : retained.kind === 'numeric_decision' ? await port.decide(retained.check_id, retained.body, retained.command_id)
              : retained.kind === 'group_prepare' ? await groupPort().prepare(retained.body, retained.command_id)
                : retained.kind === 'group_numeric_preview' ? await groupPort().preview(retained.draft_id, retained.member_key, retained.body, retained.command_id)
                  : await groupPort().decide(retained.check_id, retained.body, retained.command_id))
      // Admit academic replies only while their original access scope is current.
      // Safe control ACKs remain durable after a Policy change.
      if (subject && (!current(true) || sequence !== operation.current)) return
      await persistAuthoringCommand({ ...retained, rejection: null, ack } as AuthoringCommand, undefined, guard)
      if (!current(subject) || sequence !== operation.current) return
      const values = await loadCommands(academicRef.current && subjectReady)
      if (!current(subject) || sequence !== operation.current) return
      setCommands(values); await loadList()
      if (current(subject) && sequence === operation.current) setError('原命令已确认。请另行读取当前详情；原回执不替代当前状态。')
    } catch (reason) {
      // A Policy rejection invalidates subject writes before even persisting
      // its error receipt. Original durable commands and safe controls remain.
      if (policyDenied(reason) && current() && sequence === operation.current) fail(reason)
      if (!policyDenied(reason) && reason instanceof ApiError && [400, 409, 412, 422].includes(reason.status)) {
        try {
          await persistAuthoringCommand({ ...command, rejection: { status: reason.status, code: reason.code ?? null } }, undefined, guard)
          if (current(subject) && sequence === operation.current) {
            const values = await loadCommands(academicRef.current && subjectReady)
            if (current(subject) && sequence === operation.current) setCommands(values)
          }
        } catch { /* Durable original remains unchanged. */ }
      }
      if (!policyDenied(reason) && current() && sequence === operation.current) fail(reason)
    } finally { unsubscribe?.(); if (controller) subjectWrites.current.delete(controller); finish(sequence) }
  }
  const create = async (input: AuthoringCommandInput) => {
    if (!current(input.kind !== 'cancel') || !ready || input.kind !== 'cancel' && !subjectReady || working.current) return
    const pending = commands.find(v => !v.ack && !v.rejection && v.kind === input.kind && (input.kind !== 'cancel' || v.kind === 'cancel' && v.job_id === input.job_id))
    if (pending) { setError('已有未知结果的原命令，请先回放；未创建新 key。'); return }
    try { await execute(makeAuthoringCommand(workspace, input)) } catch (reason) { if (current()) fail(reason) }
  }
  return { jobs: renderOwner === owner ? jobs : [], cursor, detail: academic ? detail : null, draft: academic ? draft : null, numeric: academic ? numeric : null, privateSolution: academic ? privateSolution : null,
    reportAccessError: (reason: unknown) => { if (current()) fail(reason) },
    commands: renderOwner === owner ? commands.filter(v => academic || v.kind === 'cancel') : [], academic, ready: ready && (!academic || subjectReady), controlReady: ready, busy, error: renderOwner === owner ? error : '', refresh, read, readDraft, readNumeric, readPrivateSolution, execute, create,
    cancel: (job: JobSnapshot) => { const value = checkedJob(job); return create({ kind: 'cancel', job_id: value.id, body: { expected_revision: value.revision } }) },
  }
}
