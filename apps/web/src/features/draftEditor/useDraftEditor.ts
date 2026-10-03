import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { ContentRef, EditDraftSnapshot, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import { sameValue, validIdentity } from '../providers/providerSchema'
import { editClient, type EditPort } from './editClient'
import { checkedEdit, editSnapshot, editText, snapshotText, type EditText } from './editSchema'
import { decodeBuffer, decodeCommand, editBuffers, editCommands, editPage, editRoute, patchBody, persistCommand, readCommand, type EditBuffer, type EditCommand } from './editJournal'
import { discardEditMemory, editMemoryVersion, pendingEditMemory, recoverableEditMemory, releaseEditMemory, retainEditMemory, subscribeEditMemory } from './editMemory'

type Conflict = { command: EditCommand; base: EditDraftSnapshot; server: EditDraftSnapshot; local: EditText }
const denied = (e: unknown) => e instanceof ApiError && ([401, 403].includes(e.status) || ['POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED'].includes(e.code ?? ''))
export function useDraftEditor(workspace: string, baseRef: ContentRef, paused: boolean, port: EditPort = editClient) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  useSyncExternalStore(subscribeEditMemory, editMemoryVersion, editMemoryVersion)
  const owner = JSON.stringify([workspace, baseRef, access]), scope = useRef({ owner, paused }); scope.current = { owner, paused }
  const live = useRef(false), admitted = useRef(false), working = useRef(false), sequence = useRef(0), abort = useRef(new AbortController())
  const queue = useRef<Promise<void>>(Promise.resolve()), revisions = useRef(new Map<string, number>()), work = useRef<EditBuffer | null>(null), saveSerial = useRef(0), localDurable = useRef(true)
  const [renderOwner, setRenderOwner] = useState(owner), [allowed, setAllowed] = useState(false), [busy, setBusy] = useState(false), [error, setError] = useState('')
  const [commands, setCommands] = useState<EditCommand[]>([]), [buffers, setBuffers] = useState<EditBuffer[]>([]), [buffer, setBuffer] = useState<EditBuffer | null>(null)
  const [saving, setSaving] = useState(false), [storageFailed, setStorageFailed] = useState(false), [conflict, setConflict] = useState<Conflict | null>(null)
  const [reviewSnapshot, setReviewSnapshot] = useState<EditDraftSnapshot | null>(null)
  const memorySession = useRef(''), actorSession = useRef('')
  const pendingMemory = pendingEditMemory(workspace, baseRef)
  const ready = renderOwner === owner && allowed && !paused
  admitted.current = ready
  const current = (subject = true) => live.current && scope.current.owner === owner && getSessionGeneration() === access && (!subject || admitted.current && !scope.current.paused)
  const retain = () => { if (work.current && !localDurable.current && memorySession.current) retainEditMemory(work.current, memorySession.current) }
  const clear = () => { retain(); admitted.current = false; setAllowed(false); setBuffer(null); work.current = null; memorySession.current = ''; actorSession.current = ''; setBuffers([]); setCommands([]); setConflict(null); setReviewSnapshot(null); abort.current.abort() }
  const fail = (e: unknown) => {
    if (denied(e)) clear()
    setError(denied(e) ? '当前权限或测试策略不允许编辑，正文已收起，本机原记录保留。'
      : '本次操作未确认或数据无法核验；原命令、本机文字与基准保留，未自动重发或覆盖。')
  }
  const begin = (subject = true, memoryRecovery = false) => { if (!current(subject) || working.current) return null; if (work.current && !localDurable.current || !memoryRecovery && pendingEditMemory(workspace, baseRef)) { setError('本机文字尚未安全保存，请先重试本机保存或恢复隔离副本；未替换文字或精确基准。'); return null }; working.current = true; setBusy(true); setError(''); return ++sequence.current }
  const valid = (token: number, subject = true) => token === sequence.current && current(subject)
  const finish = (token: number) => { if (valid(token, false)) { working.current = false; setBusy(false) } }
  const guard = () => ({ allowed: () => current(), signal: abort.current.signal })
  const loadCommands = async () => Object.values(await editCommands.load(workspace)).map(r => readCommand(r, workspace)).filter(c => sameValue(c.base_ref, baseRef))
  const loadBuffers = async () => Object.values(await editBuffers.load(workspace)).flatMap(r => [r.text, ...r.conflicts.map(c => c.text)].map(x => decodeBuffer(x, workspace))).filter(b => sameValue(b.base_ref, baseRef))
  const refresh = async () => {
    const token = begin(false, true); if (token === null) return
    clear(); abort.current = new AbortController()
    try {
      const session = checkedEdit<SessionResponse>('SessionResponse', await port.session())
      if (!valid(token, false)) return
      if (session.workspace_id !== workspace) throw new Error('Workspace changed')
      const can = session.role === 'author' && !session.active_independent_attempt_id && !session.active_open_book_attempt_id && !scope.current.paused
      const [cs, bs] = can ? await Promise.all([loadCommands(), loadBuffers()]) : [[], []]
      if (valid(token, false)) { memorySession.current = can ? session.csrf_token : ''; actorSession.current = can ? session.actor_session_id : ''; setAllowed(can); setCommands(cs); setBuffers(bs) }
    } catch (e) { if (valid(token, false)) fail(e) } finally { finish(token) }
  }
  useEffect(() => {
    live.current = true; ++sequence.current; working.current = false; setRenderOwner(owner); clear(); localDurable.current = true; setBusy(false); setSaving(false); setStorageFailed(false); setError('')
    if (!paused) void refresh()
    const stop = subscribeSessionAccess(() => abort.current.abort())
    return () => { retain(); live.current = false; ++sequence.current; working.current = false; abort.current.abort(); stop() }
  }, [owner, paused, port])
  const saveBuffer = (next: EditBuffer) => {
    if (!current()) return Promise.resolve()
    localDurable.current = false; work.current = next; setBuffer(next); setSaving(true); setStorageFailed(false)
    const serial = ++saveSerial.current, writeGuard = guard()
    const pending = queue.current.catch(() => {}).then(async () => {
      const result = await editBuffers.save(workspace, next.id, JSON.stringify(decodeBuffer(JSON.stringify(next), workspace)), revisions.current.get(next.id) ?? 0, [], writeGuard)
      if (result.kind !== 'saved' || result.record.conflicts.length) throw new Error('Local concurrent edit retained')
      revisions.current.set(next.id, result.record.revision)
      if (current() && serial === saveSerial.current) { localDurable.current = true; setSaving(false); setStorageFailed(false); const saved = await loadBuffers(); if (current() && serial === saveSerial.current) setBuffers(saved) }
    })
    queue.current = pending
    void pending.catch(e => { if (current() && serial === saveSerial.current) { setSaving(false); setStorageFailed(true); fail(e) } })
    return pending
  }
  const adopt = async (baseline: EditDraftSnapshot, local = snapshotText(baseline)) => {
    setReviewSnapshot(null)
    const next: EditBuffer = { version: 1, workspace, id: `editbuf_${crypto.randomUUID()}`, base_ref: baseRef, baseline, local }
    await saveBuffer(next)
  }
  const read = async (id: string, revision?: number) => {
    const token = begin(); if (token === null) return
    try {
      if (!validIdentity(id)) throw new Error('Invalid draft identity')
      const snapshot = editSnapshot(await port.read(id, revision), baseRef, id, revision)
      if (valid(token)) { await adopt(snapshot); if (valid(token)) setConflict(null) }
    } catch (e) { if (valid(token, false)) fail(e) } finally { finish(token) }
  }
  const restore = async (saved: EditBuffer) => {
    const token = begin(); if (token === null) return
    try {
      const b = decodeBuffer(JSON.stringify(saved), workspace)
      if (!sameValue(b.base_ref, baseRef)) throw new Error('Wrong base')
      const exact = editSnapshot(await port.read(b.baseline.candidate.draft_id, b.baseline.candidate.draft_revision), baseRef, b.baseline.candidate.draft_id, b.baseline.candidate.draft_revision)
      if (!sameValue(exact.candidate, b.baseline.candidate) || !sameValue(exact.payload, b.baseline.payload)) throw new Error('Historical baseline changed')
      if (valid(token)) { await adopt(exact, b.local); if (valid(token)) setConflict(null) }
    } catch (e) { if (valid(token, false)) fail(e) } finally { finish(token) }
  }
  const recoverMemory = async () => {
    const token = begin(true, true); if (token === null) return
    const session = memorySession.current
    try {
      const saved = recoverableEditMemory(workspace, baseRef, session)
      if (!saved) throw new Error('No memory copy for the current session')
      const exact = editSnapshot(await port.read(saved.baseline.candidate.draft_id, saved.baseline.candidate.draft_revision), baseRef, saved.baseline.candidate.draft_id, saved.baseline.candidate.draft_revision)
      if (!sameValue(exact.candidate, saved.baseline.candidate) || !sameValue(exact.payload, saved.baseline.payload)) throw new Error('Historical baseline changed')
      if (valid(token) && memorySession.current === session) {
        await adopt(exact, saved.local)
        if (valid(token) && memorySession.current === session) { releaseEditMemory(saved.id, session); setConflict(null) }
      }
    } catch (e) { if (valid(token, false)) fail(e) } finally { finish(token) }
  }
  const update = (local: EditText) => {
    if (!current() || working.current || !work.current || conflict || work.current.baseline.state !== 'draft') return
    setReviewSnapshot(null); void saveBuffer({ ...work.current, local }).catch(() => {})
  }
  const loadConflict = async (command: EditCommand, token: number) => {
    const stored = (await loadCommands()).find(c => c.key === command.key)
    if (!stored || stored.rejection !== 412 || stored.operation.kind !== 'patch') throw new Error('An actual retained 412 is required')
    const o = stored.operation, id = o.baseline.candidate.draft_id
    const [rawBase, rawServer] = await Promise.all([port.read(id, o.body.expected_revision), port.read(id)])
    const base = editSnapshot(rawBase, baseRef, id, o.body.expected_revision), server = editSnapshot(rawServer, baseRef, id)
    if (!sameValue(base.candidate, o.baseline.candidate) || !sameValue(base.payload, o.baseline.payload)
        || server.candidate.draft_revision < base.candidate.draft_revision || server.base_material_sha256 !== base.base_material_sha256
        || server.payload.body_path !== base.payload.body_path || !sameValue(server.payload.citations, base.payload.citations)) throw new Error('Conflicting immutable baseline')
    if (valid(token)) { setConflict({ command: stored, base, server, local: o.local }); setError('原 412 已保留。请逐项核对三方内容，明确解决后再提交新命令。') }
  }
  const readConflict = async (command: EditCommand) => {
    const token = begin(); if (token === null) return
    setConflict(null)
    try { await loadConflict(command, token) } catch (e) { if (valid(token, false)) fail(e) } finally { finish(token) }
  }
  const belongs = (command: EditCommand) => sameValue(command.base_ref, baseRef) && (command.version === 2
    ? command.workspace_id === workspace && command.actor_session_id === actorSession.current
    : command.workspace === workspace && command.page === editPage && command.access === access)
  const execute = async (command: EditCommand) => {
    if (!current() || !belongs(command)) { if (current()) setError('原操作者或旧格式的页面绑定无法确认，此命令只读保留。'); return }
    const token = begin(); if (token === null) return
    let sent = false
    try {
      let session: SessionResponse
      try { session = checkedEdit('SessionResponse', await port.session()) }
      catch (e) { if (valid(token, false)) clear(); throw e }
      if (!valid(token)) return
      if (session.workspace_id !== workspace || session.actor_session_id !== actorSession.current || session.role !== 'author'
          || session.active_independent_attempt_id || session.active_open_book_attempt_id) throw new ApiError(403, 'Current actor or Policy changed', 'POLICY_DENIED')
      if (command.version === 2 && (command.page !== editPage || command.access !== access) && command.operation.kind === 'patch') {
        const baseline = command.operation.baseline
        const exact = editSnapshot(await port.read(baseline.candidate.draft_id, baseline.candidate.draft_revision), baseRef,
          baseline.candidate.draft_id, baseline.candidate.draft_revision)
        if (!sameValue(exact.candidate, baseline.candidate) || !sameValue(exact.payload, baseline.payload)) throw new Error('Original baseline changed')
        if (!valid(token)) return
      }
      if (command.version === 2 && (command.page !== editPage || command.access !== access) && command.operation.kind === 'create') {
        await port.verifyBase(command.base_ref)
        if (!valid(token)) return
      }
      const original = await persistCommand(command, guard())
      if (!valid(token)) return
      const loadedCommands = await loadCommands(); if (valid(token)) setCommands(loadedCommands)
      if (!valid(token)) return
      const o = original.operation
      sent = true
      const ack = o.kind === 'create' ? await port.create(o.body, original.key) : await port.patch(o.baseline.candidate.draft_id, o.body, original.key)
      if (!valid(token)) return
      const confirmed = decodeCommand(JSON.stringify({ ...original, ack, rejection: null }), workspace)
      await persistCommand(confirmed, guard())
      if (valid(token)) { const loadedCommands = await loadCommands(); if (valid(token)) { setCommands(loadedCommands); setError('原命令 ACK 已保存；另行读取草稿头后再编辑，不把原 ACK 当作当前状态。') } }
    } catch (e) {
      if (valid(token, false)) {
        if (sent && !command.ack && !denied(e) && e instanceof ApiError && [400, 409, 412, 422].includes(e.status)) {
          try { await persistCommand({ ...command, rejection: e.status }, guard()); if (valid(token)) { const loadedCommands = await loadCommands(); if (valid(token)) setCommands(loadedCommands) } } catch { /* Originals remain. */ }
        }
        if (valid(token, false)) fail(e)
        if (sent && valid(token) && e instanceof ApiError && e.status === 412 && command.operation.kind === 'patch') {
          try { await loadConflict(command, token) } catch (readError) { if (valid(token, false)) fail(readError) }
        }
      }
    } finally { finish(token) }
  }
  const make = (operation: EditCommand['operation']): EditCommand => decodeCommand(JSON.stringify({ version: 2, workspace_id: workspace, actor_session_id: actorSession.current, key: `editcmd_${crypto.randomUUID()}`, route: editRoute(operation), page: editPage, access, base_ref: baseRef, operation, ack: null, rejection: null }), workspace)
  const create = async (title: string) => {
    if (!current() || working.current) return
    const captured = sequence.current
    try {
      const all = await loadCommands()
      if (!current() || working.current || sequence.current !== captured) return
      if (all.some(c => c.operation.kind === 'create' && !c.ack && c.rejection === null)) { setError('已有结果未知的创建命令，原 key 保留；先处理原命令。'); return }
      await execute(make({ kind: 'create', body: { kind: 'block', base_ref: baseRef, title } }))
    } catch (e) { if (current()) fail(e) }
  }
  const submit = async () => {
    if (!current() || working.current || !work.current || conflict) return
    const b = work.current, captured = sequence.current
    try {
      await queue.current
      const all = await loadCommands()
      if (!current() || working.current || sequence.current !== captured || work.current !== b) return
      editText(b.local)
      if (b.baseline.state !== 'draft' || sameValue(snapshotText(b.baseline), b.local)) return
      if (all.some(c => c.operation.kind === 'patch' && c.operation.baseline.candidate.draft_id === b.baseline.candidate.draft_id
          && (!c.ack && c.rejection === null || c.rejection === 412 && c.operation.body.expected_revision === b.baseline.candidate.draft_revision))) {
        setError('已有未知结果或此基准的 412 原命令；先恢复原命令或明确解决三方冲突。'); return
      }
      await execute(make({ kind: 'patch', baseline: b.baseline, local: b.local, body: patchBody(b.baseline, b.local) }))
    } catch (e) { if (current()) fail(e) }
  }
  const resolve = async (local: EditText) => {
    if (!conflict || conflict.server.state !== 'draft') return
    const token = begin(); if (token === null) return
    try {
      editText(local)
      await adopt(conflict.server, local)
      if (valid(token)) { setConflict(null); setError('解决结果已保存为本机工作副本；尚未提交。服务端若再次变化仍会返回冲突。') }
    } catch (e) { if (valid(token, false)) fail(e) } finally { finish(token) }
  }
  const dirty = !!buffer && !sameValue(snapshotText(buffer.baseline), buffer.local) || commands.some(c => !c.ack && c.rejection === null)
  const selectReview = async () => {
    if (!work.current || conflict || dirty || !localDurable.current) return
    const token = begin(); if (token === null) return
    const saved = work.current.baseline; setReviewSnapshot(null)
    try {
      const [rawExact, rawHead] = await Promise.all([port.read(saved.candidate.draft_id, saved.candidate.draft_revision), port.read(saved.candidate.draft_id)])
      const exact = editSnapshot(rawExact, baseRef, saved.candidate.draft_id, saved.candidate.draft_revision)
      const head = editSnapshot(rawHead, baseRef, saved.candidate.draft_id)
      if (!sameValue(exact, head) || !sameValue(exact.candidate, saved.candidate) || !sameValue(exact.payload, saved.payload)
          || exact.state !== 'draft') throw new Error('Only the independently checked saved current edit can enter review')
      if (valid(token)) setReviewSnapshot(exact)
    } catch (e) { if (valid(token, false)) fail(e) } finally { finish(token) }
  }
  return { ready, busy: renderOwner === owner && busy, saving: ready && saving, safe: !pendingMemory && (!ready || !busy && !saving && !storageFailed), pendingMemory,
    canRecoverMemory: ready && !!recoverableEditMemory(workspace, baseRef, memorySession.current), recoverMemory,
    discardMemory: () => { if (current(false) && !working.current) discardEditMemory(workspace, baseRef) },
    error: renderOwner === owner ? error : '', buffer: ready ? buffer : null, buffers: ready ? buffers : [], commands: ready ? commands : [], conflict: ready ? conflict : null, dirty: ready && dirty,
    refresh, read, restore, update, create, submit, execute, readConflict, resolve, selectReview, reviewSnapshot: ready ? reviewSnapshot : null,
    retrySave: () => work.current && saveBuffer(work.current).catch(() => {}),
    canReplay: (c: EditCommand) => ready && belongs(c) }
}
