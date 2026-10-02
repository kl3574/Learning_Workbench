import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { ContentRef, ContentImpactSummary as Summary, ContentImpactView as View, ImpactObjectDecisionWrite as Write, ImpactObjectDecisionReceipt as Receipt } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import { sameValue, validIdentity } from '../providers/providerSchema'
import { impactClient, type ImpactPort } from './client'
import { checked, page, readView, currentRef, eventFacts, receipt, basis as validateBasis, type Basis } from './schema'
import { commandStore, makeCommand, persist, readCommand, samePage, type Command } from './commands'
import * as memory from './memory'
const denied = (e: unknown) => e instanceof ApiError && ([401, 403].includes(e.status) || ['POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED'].includes(e.code ?? ''))
type Reading = { target: string | null; value: View; history: Receipt[]; current_ref: ContentRef | null }
type Listing = { filter: string | null; limit: number; items: Summary[]; next_cursor: string | null }
export function useContentImpacts(workspace: string, paused: boolean, port: ImpactPort = impactClient) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  useSyncExternalStore(memory.subscribe, memory.version, memory.version)
  const owner = JSON.stringify([workspace, access]), scope = useRef({ owner, paused }); scope.current = { owner, paused }
  const live = useRef(false), admitted = useRef(false), working = useRef(false), sequence = useRef(0), sessionId = useRef(''), writers = useRef(new Set<AbortController>())
  const [renderOwner, setRenderOwner] = useState(owner), [allowed, setAllowed] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [listing, setListing] = useState<Listing | null>(null), [adoptionAllowed, setAdoptionAllowed] = useState(false)
  const [commands, setCommands] = useState<Command[]>([]), [reading, setReading] = useState<Reading | null>(null), [frozen, setFrozen] = useState<Basis | null>(null), [basisVersion, setBasisVersion] = useState(0)
  const ready = renderOwner === owner && allowed && !paused; admitted.current = ready
  const current = (subject = true) => live.current && scope.current.owner === owner && getSessionGeneration() === access && (!subject || admitted.current && !scope.current.paused)
  const valid = (n: number, subject = true) => current(subject) && sequence.current === n
  const clear = () => { admitted.current = false; sessionId.current = ''; setAllowed(false); setCommands([]); setListing(null); setReading(null); setFrozen(null); setAdoptionAllowed(false); for (const writer of writers.current) writer.abort() }
  const fail = (e: unknown) => { if (denied(e)) clear(); setError(denied(e) ? '当前权限或测试策略限制内容影响材料。原命令保留，保护内容已收起。' : e instanceof ApiError && e.status === 412 ? '对象修订或决定版本已变化（412）。原决定已保留；请重新读取并比对，明确采用新依据后再更正。' : '本次操作未确认或记录无法核验。原决定保留；若正在分页，请从第一页重新读取。不会自动重发或替换依据。') }
  const load = async () => Object.values(await commandStore.load(workspace)).map(row => readCommand(row, workspace))
  const begin = (subject = true, recovering = false) => { if (!current(subject) || working.current || subject && !recovering && memory.pending(workspace)) return null; working.current = true; setBusy(true); setError(''); return ++sequence.current }
  const finish = (n: number) => { if (valid(n, false)) { working.current = false; setBusy(false) } }
  const refresh = async () => {
    const n = begin(false); if (n === null) return
    clear()
    try {
      const session = checked<Awaited<ReturnType<ImpactPort['session']>>>('SessionResponse', await port.session())
      if (!valid(n, false)) return
      if (session.workspace_id !== workspace) throw new Error('Workspace mismatch')
      const canRead = session.role === 'author' && session.active_independent_attempt_id === null && session.active_open_book_attempt_id === null && !scope.current.paused
      const values = canRead ? await load() : []
      if (valid(n, false)) { sessionId.current = canRead ? session.csrf_token : ''; setAllowed(canRead); setCommands(values) }
    } catch (e) { if (valid(n, false)) fail(e) } finally { finish(n) }
  }
  useEffect(() => { live.current = true; ++sequence.current; working.current = false; setRenderOwner(owner); clear(); setBusy(false); setError(''); if (workspace && !paused) void refresh(); return () => { live.current = false; ++sequence.current; working.current = false; for (const writer of writers.current) writer.abort() } }, [owner, paused, port])
  const discover = async (filter: string | null = null, limit = 20, more = false) => {
    const previous = listing
    if (filter !== null && !validIdentity(filter) || !Number.isSafeInteger(limit) || limit < 1 || limit > 100) { setError('请输入完整对象标识；每页条数须为 1–100 的整数。'); return }
    if (more && (!previous?.next_cursor || previous.filter !== filter || previous.limit !== limit)) return
    const n = begin(true, true); if (n === null) return
    try {
      const value = page(await port.list(filter, limit, more ? previous!.next_cursor! : undefined), filter, limit)
      if (more && value.items.some(x => previous!.items.some(old => old.event_id === x.event_id))) throw new Error('重复事件页，未合并。')
      if (valid(n)) setListing({ filter, limit, items: more ? [...previous!.items, ...value.items] : value.items, next_cursor: value.next_cursor })
    } catch (e) { if (valid(n, false)) fail(e) } finally { finish(n) }
  }
  const read = async (id: string, target: string | null = null, more = false) => {
    if (!validIdentity(id) || target !== null && !validIdentity(target)) return
    const discovered = listing?.items.find(x => x.event_id === id), original = commands.find(c => c.basis.view.event_id === id)
    if (!discovered && !original && reading?.value.event_id !== id) return
    if (target !== null && !(reading?.value.event_id === id && [...reading.value.pending_target_ids, ...reading.value.action_required_target_ids, ...reading.history.map(x => x.target_id)].includes(target))
        && !commands.some(c => c.basis.view.event_id === id && c.body.target_id === target)) return
    const previous = reading
    if (more && (!previous || previous.target !== target || previous.value.event_id !== id || !previous.value.next_cursor)) return
    const n = begin(true, true); if (n === null) return
    try {
      const value = readView(await port.read(id, target, more ? previous!.value.next_cursor! : undefined), id, target)
      const source = discovered ?? original?.basis.view ?? previous?.value
      if (source && !sameValue(eventFacts(value), eventFacts(source))) throw new Error('原事件被替换。')
      if (more) {
        const old = previous!.value
        if (!sameValue([eventFacts(old), old.affected_ids, old.exact_dependency_refs, old.conservative_only_ids], [eventFacts(value), value.affected_ids, value.exact_dependency_refs, value.conservative_only_ids])) throw new Error('原事件依据变化。')
        const last = previous!.history.at(-1), first = value.decisions[0]
        if (last && first && (first.target_id < last.target_id || first.target_id === last.target_id && first.decision_revision <= last.decision_revision)) throw new Error('历史页顺序重复或倒退。')
      }
      const ref = target === null ? null : currentRef(await port.current(target), target)
      if (valid(n)) { setReading({ target, value, current_ref: ref, history: more ? [...previous!.history, ...value.decisions] : value.decisions }); setAdoptionAllowed(true) }
    } catch (e) { if (valid(n, false)) fail(e) } finally { finish(n) }
  }
  const adopt = () => {
    if (!current() || working.current || !adoptionAllowed || !reading?.target || !reading.current_ref || reading.value.evidence_version !== 'owner_frozen_v1' || memory.pending(workspace)) return
    ++sequence.current; setFrozen(validateBasis({ target_id: reading.target, view: reading.value, current_ref: reading.current_ref })); setBasisVersion(v => v + 1)
  }
  const execute = async (command: Command) => {
    if (!current() || command.workspace_id !== workspace) return
    if (!samePage(command, access) || !memory.ownsOriginal(command, sessionId.current)) { setError('页面或授权状态已改变；原决定只读保留，不能借用现在的权限重新发送。'); return }
    const n = begin(); if (n === null) return
    const session = sessionId.current, controller = new AbortController(); writers.current.add(controller)
    const guard = { allowed: () => valid(n), signal: controller.signal }, unsubscribe = subscribeSessionAccess(() => controller.abort())
    try {
      memory.retain(command, session)
      const original = await persist(command, guard)
      memory.release(command.command_id, session)
      const values = await load()
      if (!valid(n)) return
      setCommands(values); setFrozen(null); setAdoptionAllowed(false)
      const ack = receipt(await port.decide(original.basis.view.event_id, original.body, original.command_id), original.basis, original.body)
      if (!valid(n)) return
      memory.retain({ ...original, ack, rejection: null }, session)
      await persist({ ...original, ack, rejection: null }, guard)
      memory.release(command.command_id, session)
      const confirmed = await load()
      if (valid(n)) { setCommands(confirmed); setError('原决定回执已保存。它记录当时的判断；请另行读取当前对象状态，修订和其他复核不会自动完成。') }
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
      if (values.some(c => c.basis.view.event_id === selected.view.event_id && c.body.target_id === selected.target_id && !c.rejection
          && (c.ack === null || c.body.expected_decision_revision === selected.view.target_decision_head))) { setError('这个对象已有结果未知或同一版本的原决定。请恢复原决定，或另行读取已推进的决定版本。'); return }
      const body: Write = { target_id: selected.target_id, observed_ref: selected.current_ref, expected_decision_revision: selected.view.target_decision_head!, expected_event_snapshot_sha256: selected.view.event_snapshot_sha256!, decision, reason, evidence_artifact_ids: ids }
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
  return { ready, canAdopt: ready && adoptionAllowed, listing: ready ? listing : null, busy: renderOwner === owner && busy, error: renderOwner === owner ? error : '', commands: ready ? commands : [], reading: ready ? reading : null, frozen: ready ? frozen : null, basisVersion,
    pendingMemory: memory.pending(workspace), canSaveMemory: ready && memory.recoverable(workspace, sessionId.current).length > 0, saveMemory,
    refresh, discover, read, adopt, submit, execute, clearBasis: () => { if (current() && !working.current) { ++sequence.current; setFrozen(null); setBasisVersion(v => v + 1) } }, canReplay: (c: Command) => ready && samePage(c, access) && memory.ownsOriginal(c, sessionId.current) }
}
