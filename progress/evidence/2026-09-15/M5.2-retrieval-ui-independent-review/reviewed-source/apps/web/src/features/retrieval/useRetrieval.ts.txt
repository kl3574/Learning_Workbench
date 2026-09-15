import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { ContentRef, JobSnapshot, RetrievalIndexOverview, RetrievalIndexScopeStatus, RetrievalQueryView } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import type { LoadedBlock } from '../reader/contentClient'
import { canonical } from './retrievalModel'
import { decodeCommand, persistCommand, readCommands, type RetrievalCommand } from './retrievalCommands'
import type { RetrievalPort } from './retrievalClient'

type Data = { owner: string; status: RetrievalIndexScopeStatus | null; view: RetrievalQueryView | null; job: JobSnapshot | null; block: LoadedBlock | null; busy: boolean; error: string; command: RetrievalCommand | null; overview: RetrievalIndexOverview | null }
const empty = (owner: string): Data => ({ owner, status: null, view: null, job: null, block: null, busy: false, error: '', command: null, overview: null })
export function useRetrieval(workspace: string, refs: ContentRef[], paused: boolean, port: RetrievalPort) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  const owner = canonical([workspace, access, refs, paused])
  const scope = useRef({ owner, workspace, paused }); scope.current = { owner, workspace, paused }
  const [stored, setStored] = useState<Data>(() => empty(owner))
  const data = stored.owner === owner && !paused ? stored : empty(owner)
  const live = useRef(data); live.current = data
  const [saved, setSaved] = useState<{ workspace: string; values: RetrievalCommand[] }>({ workspace: '', values: [] })
  const [storageError, setStorageError] = useState('')
  const token = useRef(0), inflight = useRef(''), mounted = useRef(true)
  const previousOwner = useRef(owner)
  if (previousOwner.current !== owner) { previousOwner.current = owner; token.current++; inflight.current = '' }
  const owns = (captured: string, sequence: number) => mounted.current && getSessionGeneration() === access && !scope.current.paused && scope.current.owner === captured && token.current === sequence
  const put = (captured: string, patch: Partial<Data>) => setStored(old => ({ ...(old.owner === captured ? old : empty(captured)), ...patch, owner: captured }))
  const reloadCommands = async () => {
    const values = await readCommands(workspace)
    if (mounted.current && scope.current.workspace === workspace) { setSaved({ workspace, values }); setStorageError('') }
  }
  const run = async (work: (valid: () => boolean, update: (patch: Partial<Data>) => void) => Promise<void>) => {
    if (paused || inflight.current === owner) return
    const captured = owner, sequence = ++token.current
    inflight.current = captured; put(captured, { busy: true, error: '' })
    const valid = () => owns(captured, sequence)
    const update = (patch: Partial<Data>) => { if (valid()) put(captured, patch) }
    try { await work(valid, update) }
    catch (reason) { update({ error: reason instanceof Error ? reason.message : '检索读取未完成，原范围和命令保留。' }) }
    finally { if (valid()) { inflight.current = ''; update({ busy: false }) } }
  }
  const statusAndJob = async (valid: () => boolean, update: (patch: Partial<Data>) => void, explicitJob?: string) => {
    if (!refs.length || !valid()) return
    const status = await port.status(workspace, refs)
    if (!valid()) return
    const previous = live.current.view
    update({ status, view: previous && status.state === 'ready' && previous.corpus_sha256 === status.corpus_sha256 && previous.index_version === status.index_version ? previous : null, block: null })
    const jobId = explicitJob ?? status.latest_job?.job.id
    if (jobId) { const job = await port.job(workspace, jobId); if (valid()) update({ job }) }
    else update({ job: null })
  }
  const refresh = () => run(async (valid, update) => { await statusAndJob(valid, update) })
  const refreshRef = useRef(refresh); refreshRef.current = refresh
  useEffect(() => { mounted.current = true; return () => { mounted.current = false; ++token.current } }, [])
  useEffect(() => {
    void reloadCommands().catch(reason => { if (mounted.current && scope.current.workspace === workspace) setStorageError(reason instanceof Error ? reason.message : '本机命令未能读取。') })
  }, [workspace])
  useEffect(() => { if (!paused && refs.length) void refreshRef.current() }, [owner, port])
  const pendingJob = data.status?.state === 'building' || !!data.job && ['queued', 'running', 'awaiting_approval'].includes(data.job.status)
  useEffect(() => {
    if (paused || !pendingJob) return
    const timer = setInterval(() => void refreshRef.current(), 2000)
    return () => clearInterval(timer)
  }, [owner, paused, pendingJob])
  const query = (text: string) => run(async (valid, update) => {
    if (!refs.length) return
    update({ view: null, block: null })
    const view = await port.query(workspace, { query: text, scope_refs: refs, limit: 20 })
    if (!valid()) return
    update({ view, ...(live.current.status?.corpus_sha256 !== view.corpus_sha256 ? { status: null } : {}) })
  })
  const send = async (command: RetrievalCommand, valid: () => boolean, update: (patch: Partial<Data>) => void) => {
    await persistCommand(command)
    await reloadCommands()
    if (!valid()) return
    update({ command })
    try {
      const ack = command.kind === 'rebuild' ? await port.rebuild(command.body, command.command_id)
        : await port.cancel(workspace, command.job_id, command.body.expected_revision, command.command_id)
      const completed = decodeCommand(JSON.stringify({ ...command, ack }), workspace)
      // Keep a real returned ACK private under its original workspace even if
      // access changed; it cannot update the new view or become current status.
      await persistCommand(completed); await reloadCommands()
      if (!valid()) return
      update({ command: completed })
      await statusAndJob(valid, update, completed.kind === 'rebuild' ? completed.ack!.id : completed.job_id)
    } catch (reason) {
      if (reason instanceof ApiError && reason.status === 412) {
        const rejected = { ...command, rejected: true }
        await persistCommand(rejected); await reloadCommands(); update({ command: rejected })
      }
      if (valid()) update({ error: `原命令尚未完成当前状态核对；原 key、范围和基准保留。${reason instanceof Error ? reason.message : ''}` })
    }
  }
  const begin = (kind: 'rebuild' | 'cancel') => run(async (valid, update) => {
    const commands = await readCommands(workspace)
    const unresolved = commands.some(value => !value.ack && !value.rejected && canonical(value.scope_refs) === canonical(refs))
    if (unresolved) throw new Error('本范围存在未确认的原命令，请先恢复并重试，不能生成替代命令。')
    const base = { version: 1, workspace, command_id: `retrieval_${crypto.randomUUID()}`, scope_refs: refs, rejected: false, ack: null }
    const status = live.current.status, job = live.current.job
    if (kind === 'rebuild' && !status || kind === 'cancel' && (!job || !['queued', 'running', 'awaiting_approval'].includes(job.status))) throw new Error('请先读回可用的范围或任务基准。')
    const command = decodeCommand(JSON.stringify(kind === 'rebuild'
      ? { ...base, kind, body: { scope_refs: refs, expected_corpus_sha256: status!.corpus_sha256, provider_id: null, consent_id: null } }
      : { ...base, kind, job_id: job!.id, body: { expected_revision: job!.revision } }), workspace)
    if (valid()) await send(command, valid, update)
  })
  const retry = (command: RetrievalCommand) => run(async (valid, update) => {
    if (command.workspace !== workspace || canonical(command.scope_refs) !== canonical(refs) || command.ack || command.rejected) throw new Error('请恢复原范围；已确认或已拒绝命令不能冒充新的重试。')
    const originals = await readCommands(workspace)
    if (!originals.some(value => canonical(value) === canonical(command))) throw new Error('原命令未从本机存储读回，未发送。')
    if (valid()) await send(command, valid, update)
  })
  const inspect = (ref: ContentRef) => run(async (valid, update) => {
    update({ block: null }); const block = await port.block(ref); if (valid()) update({ block })
  })
  const loadOverview = (cursor?: string) => run(async (valid, update) => { const value = await port.overview(cursor); if (valid()) update({ overview: value }) })
  return { ...data, commands: !paused && saved.workspace === workspace ? saved.values : [], storageError: paused ? '' : storageError,
    refresh, query, begin, retry, inspect, loadOverview,
    safe: !data.busy && !storageError,
  }
}
