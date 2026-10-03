import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { EvidenceApplicabilityDecisionView as View, EvidenceImpactDecisionWrite as Write, EvidenceImpactDecisionReceipt as Receipt } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import { sameValue, validIdentity } from '../providers/providerSchema'
import { applicabilityClient, type ApplicabilityPort } from './client'
import { checked, readView, receipt, basis as validateBasis, type Basis } from './schema'
import { commandStore, makeCommand, persist, readCommand, samePage, type Command } from './commands'
import * as memory from './memory'
const denied = (e: unknown) => e instanceof ApiError && ([401, 403].includes(e.status) || ['POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED'].includes(e.code ?? ''))
type Reading = { event: string | null; value: View; history: Receipt[] }
export function useApplicability(workspace: string, paused: boolean, port: ApplicabilityPort = applicabilityClient) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  useSyncExternalStore(memory.subscribe, memory.version, memory.version)
  const owner = JSON.stringify([workspace, access]), scope = useRef({ owner, paused }); scope.current = { owner, paused }
  const live = useRef(false), admitted = useRef(false), working = useRef(false), sequence = useRef(0), sessionId = useRef(''), writers = useRef(new Set<AbortController>())
  const [renderOwner, setRenderOwner] = useState(owner), [allowed, setAllowed] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [commands, setCommands] = useState<Command[]>([]), [reading, setReading] = useState<Reading | null>(null), [frozen, setFrozen] = useState<Basis | null>(null), [basisVersion, setBasisVersion] = useState(0)
  const ready = renderOwner === owner && allowed && !paused; admitted.current = ready
  const current = (subject = true) => live.current && scope.current.owner === owner && getSessionGeneration() === access && (!subject || admitted.current && !scope.current.paused)
  const valid = (n: number, subject = true) => current(subject) && sequence.current === n
  const clear = () => { admitted.current = false; sessionId.current = ''; setAllowed(false); setCommands([]); setReading(null); setFrozen(null); for (const writer of writers.current) writer.abort() }
  const fail = (e: unknown) => { if (denied(e)) clear(); setError(denied(e) ? '当前权限或测试策略限制适用性材料。原命令保留，保护内容已收起。' : e instanceof ApiError && e.status === 412 ? '412：原依据或事件决定修订已变化。保留原命令；请另行读取，比对后明确采用新基准准备更正，不自动重发。' : '本次操作未确认或记录无法核验。原命令保留，未自动重发或改用新基准。') }
  const load = async () => Object.values(await commandStore.load(workspace)).map(row => readCommand(row, workspace))
  const begin = (subject = true, recovering = false) => { if (!current(subject) || working.current || subject && !recovering && memory.pending(workspace)) return null; working.current = true; setBusy(true); setError(''); return ++sequence.current }
  const finish = (n: number) => { if (valid(n, false)) { working.current = false; setBusy(false) } }
  const refresh = async () => {
    const n = begin(false); if (n === null) return
    clear()
    try {
      const session = checked<Awaited<ReturnType<ApplicabilityPort['session']>>>('SessionResponse', await port.session())
      if (!valid(n, false)) return
      if (session.workspace_id !== workspace) throw new Error('Workspace mismatch')
      const canRead = session.role === 'author' && session.active_independent_attempt_id === null && session.active_open_book_attempt_id === null && !scope.current.paused
      const values = canRead ? await load() : []
      if (valid(n, false)) { sessionId.current = canRead ? session.csrf_token : ''; setAllowed(canRead); setCommands(values) }
    } catch (e) { if (valid(n, false)) fail(e) } finally { finish(n) }
  }
  useEffect(() => { live.current = true; ++sequence.current; working.current = false; setRenderOwner(owner); clear(); setBusy(false); setError(''); if (workspace && !paused) void refresh(); return () => { live.current = false; ++sequence.current; working.current = false; for (const writer of writers.current) writer.abort() } }, [owner, paused, port])
  const read = async (id: string, event: string | null = null, more = false) => {
    if (!validIdentity(id) || event !== null && !validIdentity(event)) return
    // Filtered IDs must come from this actual selected source or an immutable
    // locally retained original command; never invent a discovery endpoint.
    if (event !== null && !(reading?.value.evidence_id === id && reading.value.relevant_event_ids.includes(event)) && !commands.some(c => c.basis.view.evidence_id === id && c.body.event_id === event)) return
    const previous = reading
    if (more && (!previous || previous.event !== event || previous.value.evidence_id !== id || !previous.value.next_cursor)) return
    const n = begin(true, true); if (n === null) return
    try {
      const value = readView(await port.read(id, event, more ? previous!.value.next_cursor! : undefined), id, event)
      if (more) {
        const old = previous!.value
        if (!sameValue({ ...old, decisions: [], next_cursor: null }, { ...value, decisions: [], next_cursor: null })) throw new Error('分页期间依据已变化，请完整重读。')
        const seen = new Set(previous!.history.map(item => `${item.event_id}:${item.decision_revision}`))
        if (value.decisions.some(item => seen.has(`${item.event_id}:${item.decision_revision}`))) throw new Error('分页重复了历史决定，未合并。')
      }
      if (valid(n)) setReading({ event, value, history: more ? [...previous!.history, ...value.decisions] : value.decisions })
    } catch (e) { if (valid(n, false)) fail(e) } finally { finish(n) }
  }
  const adopt = () => {
    if (!current() || working.current || !reading?.event || memory.pending(workspace)) return
    ++sequence.current; setFrozen(validateBasis({ event_id: reading.event, view: reading.value })); setBasisVersion(v => v + 1)
  }
  const execute = async (command: Command) => {
    if (!current() || command.workspace_id !== workspace) return
    if (!samePage(command, access) || !memory.ownsOriginal(command, sessionId.current)) { setError('原页面或访问代次已改变；原 key/body 只读保留，不能用当前会话冒充原操作者回放。'); return }
    const n = begin(); if (n === null) return
    const session = sessionId.current, controller = new AbortController(); writers.current.add(controller)
    const guard = { allowed: () => valid(n), signal: controller.signal }, unsubscribe = subscribeSessionAccess(() => controller.abort())
    try {
      memory.retain(command, session)
      const original = await persist(command, guard)
      memory.release(command.command_id, session)
      const values = await load()
      if (!valid(n)) return
      setCommands(values); setFrozen(null)
      const ack = receipt(await port.decide(original.basis.view.evidence_id, original.body, original.command_id), original.basis, original.body)
      // A received, checked ACK belongs to the sending session even after access
      // changes. Keep it isolated; stale callbacks still cannot persist or render.
      memory.retain({ ...original, ack, rejection: null }, session)
      if (!valid(n)) return
      await persist({ ...original, ack, rejection: null }, guard)
      memory.release(command.command_id, session)
      const confirmed = await load()
      if (valid(n)) { setCommands(confirmed); setError('原决定 ACK 已保存。它是历史决定；当前多事件适用性须另行读取，原分数与资格未改变。') }
    } catch (e) {
      if (valid(n, false)) {
        if (!command.ack && !denied(e) && e instanceof ApiError && [400, 409, 412, 422].includes(e.status)) {
          try { const rejected = { ...command, rejection: { status: e.status, code: /^[A-Z][A-Z0-9_]{0,79}$/.test(e.code ?? '') ? e.code! : null } }; memory.retain(rejected, session); await persist(rejected, guard); memory.release(command.command_id, session); const values = await load(); if (valid(n)) setCommands(values) } catch { /* Original command and retained response remain recoverable. */ }
        }
        if (valid(n, false)) fail(e)
      }
    } finally { unsubscribe(); writers.current.delete(controller); finish(n) }
  }
  const submit = async (decision: Write['decision'], reason: string, ids: string[]) => {
    if (!current() || working.current || !frozen) return
    const before = sequence.current, selected = frozen
    try {
      const values = await load()
      if (!current() || working.current || sequence.current !== before) return
      // Unknown or acknowledged originals at this exact head must not acquire a
      // replacement key. A fresh explicit GET/adopt is necessary after a change.
      if (values.some(c => c.basis.view.evidence_id === selected.view.evidence_id && c.body.event_id === selected.event_id && !c.rejection
          && (c.ack === null || c.body.expected_decision_revision === selected.view.event_decision_head))) { setError('已有此事件结果未知或同基准的原命令。请保留原 key 恢复，或另行读取已推进的决定头。'); return }
      const body: Write = { event_id: selected.event_id, expected_decision_revision: selected.view.event_decision_head!, expected_current_basis_sha256: selected.view.current_basis_sha256, decision, reason, evidence_artifact_ids: ids }
      const command = makeCommand(workspace, access, selected, body)
      memory.bindOriginal(command, sessionId.current)
      await execute(command)
    } catch (e) { if (current()) fail(e) }
  }
  const saveMemory = async () => {
    const n = begin(true, true); if (n === null) return
    const session = sessionId.current, controller = new AbortController(); writers.current.add(controller)
    const guard = { allowed: () => valid(n) && sessionId.current === session, signal: controller.signal }, unsubscribe = subscribeSessionAccess(() => controller.abort())
    try { for (const command of memory.recoverable(workspace, session)) { await persist(command, guard); if (!valid(n)) return; memory.release(command.command_id, session) }; const values = await load(); if (valid(n)) setCommands(values) } catch (e) { if (valid(n, false)) fail(e) } finally { unsubscribe(); writers.current.delete(controller); finish(n) }
  }
  return { ready, busy: renderOwner === owner && busy, error: renderOwner === owner ? error : '', commands: ready ? commands : [], reading: ready ? reading : null, frozen: ready ? frozen : null, basisVersion,
    pendingMemory: memory.pending(workspace), canSaveMemory: ready && memory.recoverable(workspace, sessionId.current).length > 0, saveMemory,
    refresh, read, adopt, submit, execute, clearBasis: () => { if (current() && !working.current) { ++sequence.current; setFrozen(null); setBasisVersion(v => v + 1) } }, canReplay: (c: Command) => ready && samePage(c, access) && memory.ownsOriginal(c, sessionId.current) }
}
