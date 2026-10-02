import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'
import type { DraftCandidate, DraftReviewWrite, JobSnapshot, ReviewDecisionWrite, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
import { ApiError, getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import { controlledDownloadPath } from '../imports/recovery'
import { sameValue, validIdentity } from '../providers/providerSchema'
import { reviewClient, type ReviewPort } from './reviewClient'
import { knownReviewJobs, makeReviewCommand, persistReviewCommand, readReviewCommand, rememberReviewJob, reviewCommandStore, reviewControlStore, sameReviewActorPage, type ReviewCommand, type ReviewCommandInput } from './reviewCommands'
import { reviewMemoryVersion, pendingReviewMemory, recoverableReviewMemory, releaseReviewMemory, retainReviewMemory, subscribeReviewMemory } from './reviewMemory'
import { reviewJob, reviewReceipt } from './reviewSchema'

const terminal = (job: JobSnapshot | null) => !!job && ['completed', 'failed', 'cancelled'].includes(job.status)
const accessDenied = (error: unknown) => error instanceof ApiError && ([401, 403].includes(error.status)
  || ['ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED', 'POLICY_DENIED'].includes(error.code ?? ''))
type Report = { path: string; text: string; sha256: string }

export function useReview(workspace: string, paused: boolean, port: ReviewPort = reviewClient) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  useSyncExternalStore(subscribeReviewMemory, reviewMemoryVersion, reviewMemoryVersion)
  const sessionIdentity = useRef('')
  const owner = `${workspace}:${access}`, scope = useRef({ owner, paused }); scope.current = { owner, paused }
  const live = useRef(false), academicRef = useRef(false), sequence = useRef(0), working = useRef(false)
  const jobReads = useRef(0), jobSelection = useRef(0)
  const writers = useRef(new Set<AbortController>()), urls = useRef(new Set<string>())
  const [renderOwner, setRenderOwner] = useState(owner), [allowed, setAllowed] = useState(false), [ready, setReady] = useState(false)
  const [controlsReady, setControlsReady] = useState(false), [commands, setCommands] = useState<ReviewCommand[]>([])
  const [ids, setIds] = useState<string[]>([]), [selected, setSelected] = useState(''), [job, setJob] = useState<JobSnapshot | null>(null)
  const [receipt, setReceipt] = useState<StoredReviewReceipt | null>(null), [report, setReport] = useState<Report | null>(null)
  const [busy, setBusy] = useState(false), [error, setError] = useState(''), [pollRevision, setPollRevision] = useState(0)
  const academic = renderOwner === owner && allowed && !paused
  academicRef.current = academic
  const current = (subject = false) => live.current && scope.current.owner === owner && getSessionGeneration() === access
    && (!subject || academicRef.current && !scope.current.paused)
  const revokeSubject = () => {
    academicRef.current = false; sessionIdentity.current = ''; setAllowed(false); setReady(false); setReceipt(null); setReport(null)
    setCommands(old => old.filter(value => value.kind === 'cancel'))
    for (const controller of writers.current) controller.abort()
    for (const url of urls.current) URL.revokeObjectURL(url)
    urls.current.clear()
  }
  const fail = (reason: unknown) => {
    if (accessDenied(reason)) revokeSubject()
    const code = reason instanceof ApiError && /^[A-Z][A-Z0-9_]{0,79}$/.test(reason.code ?? '') ? `${reason.code}：` : ''
    setError(code + (accessDenied(reason) ? '当前权限或测试策略不允许审核内容。原命令保留，安全任务仍可另行读取或取消。'
      : reason instanceof ApiError && reason.status === 412 ? '审核基准已改变。原命令保留；请另行读取当前回执，再明确准备新决定。'
        : '本次操作未确认或记录无法核验。原命令保留；未自动创建新 key 或重新发送。'))
  }
  const loadCommands = async (subject: boolean) => {
    const controls = Object.values(await reviewControlStore.load(workspace)).map(value => readReviewCommand(value, workspace))
    if (controls.some(value => value.kind !== 'cancel')) throw new Error('审核控制缓存不能包含学科命令。')
    if (!subject) return controls
    const privateCommands = Object.values(await reviewCommandStore.load(workspace)).map(value => readReviewCommand(value, workspace))
    if (privateCommands.some(value => value.kind === 'cancel')) throw new Error('审核命令归属不一致。')
    return [...controls, ...privateCommands]
  }
  const begin = (subject: boolean, recovering = false) => {
    if (!current(subject) || working.current || subject && !recovering && pendingReviewMemory(workspace)) return null
    working.current = true; setBusy(true); setError(''); return ++sequence.current
  }
  const finish = (token: number) => { if (current() && token === sequence.current) { working.current = false; setBusy(false) } }
  const refresh = async () => {
    const token = begin(false); if (token === null) return
    revokeSubject()
    try {
      const [known, controls] = await Promise.all([knownReviewJobs(workspace), loadCommands(false)])
      if (!current() || token !== sequence.current) return
      setIds(known); setCommands(controls); setControlsReady(true)
      const session = await port.session()
      if (!current() || token !== sequence.current) return
      if (session.workspace_id !== workspace) throw new Error('当前审核工作区已改变。')
      const canRead = session.role === 'author' && session.active_independent_attempt_id === null && session.active_open_book_attempt_id === null && !scope.current.paused
      const values = canRead ? await loadCommands(true) : controls
      if (!current() || token !== sequence.current) return
      sessionIdentity.current = canRead ? session.csrf_token : ''; setCommands(values); setAllowed(canRead); setReady(canRead)
    } catch (reason) { if (current() && token === sequence.current) fail(reason) } finally { finish(token) }
  }
  useEffect(() => {
    live.current = true; ++sequence.current; working.current = false
    setRenderOwner(owner); setAllowed(false); setReady(false); setControlsReady(false); setCommands([]); setIds([])
    setSelected(''); setJob(null); setReceipt(null); setReport(null); setBusy(false); setError('')
    if (workspace) void refresh()
    return () => {
      live.current = false; ++sequence.current; working.current = false
      for (const controller of writers.current) controller.abort()
      for (const url of urls.current) URL.revokeObjectURL(url)
      urls.current.clear()
    }
  }, [owner, paused, port])
  useEffect(() => {
    if (!selected || renderOwner !== owner) return
    let valid = true, reading = false, done = false
    const selection = jobSelection.current
    const read = async () => {
      if (reading || done || working.current || selection !== jobSelection.current) return
      reading = true
      const request = ++jobReads.current
      try {
        const value = reviewJob(await port.job(selected), workspace, selected)
        if (valid && current() && selection === jobSelection.current && request === jobReads.current) { setJob(value); done = terminal(value) }
      } catch (reason) { if (valid && current() && selection === jobSelection.current && request === jobReads.current) { done = true; fail(reason) } }
      finally { reading = false }
    }
    void read()
    const timer = setInterval(() => void read(), 2000)
    return () => { valid = false; clearInterval(timer) }
  }, [owner, renderOwner, selected, pollRevision, port])
  const selectJob = async (id: string) => {
    if (!validIdentity(id)) return
    const token = begin(false); if (token === null) return
    const request = ++jobReads.current
    ++jobSelection.current
    setReceipt(null); setReport(null)
    try {
      // Safe GET validates unknown manually entered IDs before remembering them.
      const value = reviewJob(await port.job(id), workspace, id)
      if (!current() || token !== sequence.current || request !== jobReads.current) return
      await rememberReviewJob(workspace, id)
      if (!current() || token !== sequence.current) return
      const known = await knownReviewJobs(workspace)
      if (!current() || token !== sequence.current) return
      setIds(known)
      setSelected(id); setJob(value); setReceipt(null); setReport(null)
    } catch (reason) { if (current() && token === sequence.current) fail(reason) }
    finally { if (current() && token === sequence.current) setPollRevision(old => old + 1); finish(token) }
  }
  const execute = async (command: ReviewCommand) => {
    const subject = command.kind !== 'cancel'
    if (command.workspace_id !== workspace || !(subject ? ready : controlsReady)) return
    if (!sameReviewActorPage(command, access)) { setError('无法核对原操作者。保留原 body、key 和已知审核 ID，只读恢复；本页不会把新会话的同 key 发送冒充原命令重放。'); return }
    const token = begin(subject); if (token === null) return
    const originalSession = sessionIdentity.current
    ++jobSelection.current
    const controller = subject ? new AbortController() : null
    if (controller) writers.current.add(controller)
    const guard = controller ? { allowed: () => current(true) && token === sequence.current, signal: controller.signal } : undefined
    const unsubscribe = controller ? subscribeSessionAccess(() => controller.abort()) : undefined
    if (subject) { setReceipt(null); setReport(null) }
    try {
      if (subject) retainReviewMemory(command, originalSession)
      const retained = await persistReviewCommand(command, undefined, guard)
      if (subject) releaseReviewMemory(command.command_id, originalSession)
      const pending = await loadCommands(academicRef.current)
      if (!current(subject) || token !== sequence.current) return
      setCommands(pending)
      const ack = retained.ack ?? (retained.kind === 'create' ? await port.create(retained.candidate.draft_id, retained.body, retained.command_id)
        : retained.kind === 'decision' ? await port.decide(retained.review_id, retained.body, retained.command_id)
          : await port.cancel(retained.review_id, retained.body, retained.command_id))
      if (!current(subject) || token !== sequence.current) return
      if (subject) retainReviewMemory({ ...retained, rejection: null, ack } as ReviewCommand, originalSession)
      const confirmed = await persistReviewCommand({ ...retained, rejection: null, ack } as ReviewCommand, undefined, guard)
      if (subject) releaseReviewMemory(command.command_id, originalSession)
      if (!current(subject) || token !== sequence.current) return
      const id = confirmed.kind === 'create' ? confirmed.ack!.id : confirmed.review_id
      await rememberReviewJob(workspace, id)
      const [known, values] = await Promise.all([knownReviewJobs(workspace), loadCommands(academicRef.current)])
      if (!current(subject) || token !== sequence.current) return
      setIds(known); setCommands(values); setSelected(id); setJob(null)
      setError('原审核命令已确认。原 ACK 不替代当前任务或审核回执；请另行读取。')
    } catch (reason) {
      if (current() && token === sequence.current) {
        if (!accessDenied(reason) && reason instanceof ApiError && [400, 409, 412, 422].includes(reason.status)) {
          try {
            const code = /^[A-Z][A-Z0-9_]{0,79}$/.test(reason.code ?? '') ? reason.code! : null
            const rejected = { ...command, rejection: { status: reason.status, code } }
            if (subject) retainReviewMemory(rejected, originalSession)
            await persistReviewCommand(rejected, undefined, guard)
            if (subject) releaseReviewMemory(command.command_id, originalSession)
            const values = await loadCommands(academicRef.current)
            if (current(subject) && token === sequence.current) setCommands(values)
          } catch { /* Original committed command remains intact. */ }
        }
        if (current() && token === sequence.current) fail(reason)
      }
    } finally {
      unsubscribe?.(); if (controller) writers.current.delete(controller)
      if (current() && token === sequence.current) setPollRevision(old => old + 1)
      finish(token)
    }
  }
  const saveMemory = async () => {
    const token = begin(true, true); if (token === null) return
    const session = sessionIdentity.current, controller = new AbortController(); writers.current.add(controller)
    const guard = { allowed: () => current(true) && token === sequence.current && sessionIdentity.current === session, signal: controller.signal }
    const unsubscribe = subscribeSessionAccess(() => controller.abort())
    try {
      for (const command of recoverableReviewMemory(workspace, session)) {
        await persistReviewCommand(command, undefined, guard)
        if (!current(true) || token !== sequence.current) return
        releaseReviewMemory(command.command_id, session)
        if (command.ack) await rememberReviewJob(workspace, command.kind === 'create' ? command.ack.id : command.review_id)
      }
      const [known, values] = await Promise.all([knownReviewJobs(workspace), loadCommands(true)])
      if (current(true) && token === sequence.current) { setIds(known); setCommands(values) }
    } catch (reason) { if (current() && token === sequence.current) fail(reason) }
    finally { unsubscribe(); writers.current.delete(controller); finish(token) }
  }
  const createCommand = async (input: ReviewCommandInput) => {
    if (!current(input.kind !== 'cancel') || working.current) return
    const pending = commands.find(value => !value.ack && !value.rejection && value.kind === input.kind
      // A foreign-page unknown control cannot lock out a new explicit stop of
      // the currently read Job. Its old actor-bound command stays read-only.
      && (input.kind !== 'cancel' || sameReviewActorPage(value, access))
      && (value.kind === 'create' && input.kind === 'create' ? sameValue(value.candidate, input.candidate)
        : value.kind !== 'create' && input.kind !== 'create' && value.review_id === input.review_id))
    if (pending) { setError('已有结果未知的原审核命令。保留原基准与 key，未创建第二份命令。'); return }
    try { await execute(makeReviewCommand(workspace, access, input)) } catch (reason) { if (current()) fail(reason) }
  }
  const read = async (id: string) => {
    const token = begin(true); if (token === null) return
    setReceipt(null); setReport(null)
    try {
      const value = reviewReceipt(await port.read(id), id)
      if (current(true) && token === sequence.current) setReceipt(value)
    } catch (reason) { if (current() && token === sequence.current) fail(reason) } finally { finish(token) }
  }
  const artifact = async (path: string, download: boolean) => {
    if (!receipt || !receipt.evidence_paths.includes(path)) return
    const basis = receipt, token = begin(true); if (token === null) return
    setReport(null)
    try {
      const admitted = controlledDownloadPath(path, location.origin), id = admitted.split('/')[4]
      const response = await port.artifact(id)
      if (!current(true) || token !== sequence.current) return
      const digest = bytesToHex(sha256(new Uint8Array(await response.data.arrayBuffer())))
      if (response.etag !== `"${digest}"`) throw new Error('审核附件字节未匹配本次实际 ETag。')
      const fresh = reviewReceipt(await port.read(basis.id), basis.id, basis.candidate)
      if (!sameValue(fresh, basis)) throw new Error('审核回执已变化，请重新读取。')
      if (!current(true) || token !== sequence.current) return
      if (download) {
        const url = URL.createObjectURL(response.data); urls.current.add(url)
        const link = document.createElement('a'); link.href = url; link.download = `review-${id}.${path === basis.evidence_paths[0] ? 'json' : 'bin'}`; link.click()
        setTimeout(() => { URL.revokeObjectURL(url); urls.current.delete(url) }, 60000)
      } else {
        const text = await response.data.text()
        if (current(true) && token === sequence.current) setReport({ path, text, sha256: digest })
      }
    } catch (reason) { if (current() && token === sequence.current) fail(reason) } finally { finish(token) }
  }
  return { pendingMemory: pendingReviewMemory(workspace), canSaveMemory: academic && recoverableReviewMemory(workspace, sessionIdentity.current).length > 0, saveMemory, academic, ready: academic && ready, controlsReady: renderOwner === owner && controlsReady, busy,
    commands: renderOwner === owner ? commands.filter(value => academic || value.kind === 'cancel') : [],
    ids: renderOwner === owner ? ids : [], selected: renderOwner === owner ? selected : '', job: renderOwner === owner ? job : null,
    receipt: academic ? receipt : null, report: academic ? report : null, error: renderOwner === owner ? error : '',
    refresh, selectJob, read, execute, artifact, canReplay: (value: ReviewCommand) => sameReviewActorPage(value, access),
    create: (candidate: DraftCandidate, body: DraftReviewWrite) => createCommand({ kind: 'create', candidate, body }),
    decide: (body: ReviewDecisionWrite) => receipt && academic && body.expected_revision === receipt.revision && body.candidate_sha256 === receipt.candidate.candidate_sha256
      ? createCommand({ kind: 'decision', review_id: receipt.id, candidate: receipt.candidate, body }) : Promise.resolve(),
    cancel: () => job && !terminal(job) ? createCommand({ kind: 'cancel', review_id: job.id, body: { expected_revision: job.revision } }) : Promise.resolve(),
  }
}
