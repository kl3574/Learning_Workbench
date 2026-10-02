import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { DraftCandidate, ContentRestoreDraftSnapshot, EditDraftSnapshot, ImportDraftSnapshot } from '../../../../../packages/contracts/generated/api-types'
import { Dialog } from '../../workbench/Controls'
import { sameValue, validIdentity } from '../providers/providerSchema'
import type { ReviewPort } from './reviewClient'
import { ReviewCreateForm, ReviewDecisionForm, emptyCreateForm, emptyDecisionForm, createFormDirty, decisionFormDirty, type CreateFormValue, type DecisionFormValue } from './ReviewForms'
import { useReview } from './useReview'
import { PublicationPanel } from '../draftPublication/PublicationPanel'
import { RestorePublicationPanel } from '../contentRestore/RestorePublicationPanel'
import { EditPublicationPanel } from '../editPublication/EditPublicationPanel'
import { discardReviewMemory, pendingReviewMemory } from './reviewMemory'
import './review.css'
import { discardReviewForms, pendingReviewForms, retainReviewForm, reviewCandidateKey as candidateKey, reviewDecisionKey, reviewFormMemoryVersion, subscribeReviewForms, type ReviewFormOwner, type ReviewPanelState, type VerifiedReviewForm } from './reviewFormMemory'

export function ReviewPanel({ workspace, paused, candidate, candidateState = '未重新读取', importDraft, editDraft, restoreDraft, restoreBlockId, port, onState, formScope, formOwner }: {
  workspace: string; paused: boolean; candidate: DraftCandidate | null; candidateState?: string; port?: ReviewPort
  formScope?: string; formOwner?: ReviewFormOwner; onState?: (value: ReviewPanelState) => void
} & ({ importDraft?: ImportDraftSnapshot | null; editDraft?: never; restoreDraft?: never; restoreBlockId?: never } | { editDraft: EditDraftSnapshot | null; importDraft?: never; restoreDraft?: never; restoreBlockId?: never } | { restoreDraft: ContentRestoreDraftSnapshot | null; restoreBlockId: string; editDraft?: never; importDraft?: never })) {
  const owner: ReviewFormOwner = formOwner ?? (importDraft !== undefined ? 'import' : editDraft !== undefined ? 'edit' : restoreDraft !== undefined ? 'restore' : 'authoring_single')
  const scope = formScope ?? owner
  useSyncExternalStore(subscribeReviewForms, reviewFormMemoryVersion, reviewFormMemoryVersion)
  const pendingForms = pendingReviewForms(workspace, scope)
  const [recovered, setRecovered] = useState<VerifiedReviewForm[]>([])
  const state = useReview(workspace, paused, port), [manualId, setManualId] = useState('')
  const [creates, setCreates] = useState<Record<string, CreateFormValue>>({}), [decisions, setDecisions] = useState<Record<string, DecisionFormValue>>({})
  const [confirmRefresh, setConfirmRefresh] = useState(false), [discardMemory, setDiscardMemory] = useState(false)
  const [publicationState, setPublicationState] = useState({ dirty: false, safe: true })
  const callback = useRef(onState); callback.current = onState
  const formCount = Object.values(creates).filter(createFormDirty).length + Object.values(decisions).filter(decisionFormDirty).length
  const dirty = pendingForms || state.pendingMemory || publicationState.dirty || state.academic && (formCount > 0 || state.commands.some(value => !value.ack && !value.rejection))
  const safe = !state.pendingMemory && publicationState.safe && state.controlsReady && !state.busy
  const discardForms = useCallback(() => { discardReviewForms(workspace, scope); setCreates({}); setDecisions({}); setRecovered([]); setConfirmRefresh(false) }, [workspace, scope])
  useEffect(() => { if (!state.academic) { setCreates({}); setDecisions({}); setRecovered([]); setConfirmRefresh(false) } }, [state.academic])
  useEffect(() => { setCreates({}); setDecisions({}); setRecovered([]); setConfirmRefresh(false) }, [workspace, scope])
  const isolated = pendingForms && !publicationState.dirty && !state.commands.some(value => !value.ack && !value.rejection) && formCount === 0 && recovered.every(row => !sameValue(row.form.candidate, row.currentCandidate) || row.form.kind === 'decision' && !sameValue(row.form.receipt, row.currentReceipt)) && safe
  const latestSafe = useRef(safe); latestSafe.current = safe
  useEffect(() => {
    if (!dirty && safe) return
    const protect = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', protect)
    return () => window.removeEventListener('beforeunload', protect)
  }, [dirty, safe])
  useEffect(() => { callback.current?.({ dirty, safe, isolated, discardForms }) }, [dirty, safe, isolated, discardForms])
  useEffect(() => () => callback.current?.({ dirty: pendingReviewForms(workspace, scope) || pendingReviewMemory(workspace) || !latestSafe.current, safe: latestSafe.current && !pendingReviewMemory(workspace), isolated: pendingReviewForms(workspace, scope) && latestSafe.current && !pendingReviewMemory(workspace), discardForms }), [workspace, scope, discardForms])
  const receipt = state.receipt, job = state.job
  const matches = receipt && candidate && sameValue(receipt.candidate, candidate)
  const createKey = candidate ? candidateKey(candidate) : ''
  const decisionKey = receipt ? reviewDecisionKey(receipt) : ''
  const retainCreate = (basis: DraftCandidate, value: CreateFormValue, sourceOwner = owner) => { setCreates(old => ({ ...old, [candidateKey(basis)]: value })); retainReviewForm({ workspace, scope, actor: state.formActor, owner: sourceOwner, candidate: basis, kind: 'create', value }, createFormDirty(value)) }
  const retainDecision = (basis: NonNullable<typeof receipt>, value: DecisionFormValue, sourceOwner = owner) => { setDecisions(old => ({ ...old, [reviewDecisionKey(basis)]: value })); retainReviewForm({ workspace, scope, actor: state.formActor, owner: sourceOwner, candidate: basis.candidate, kind: 'decision', receipt: basis, value }, decisionFormDirty(value)) }
  return <section className="review-panel" aria-label="候选审核与原命令恢复"><h3>候选审核与恢复</h3>
    <p>机器检查、人工决定与内容发布分别记录。审核回执已保存不代表草稿状态已推进或教材已发布。</p>
    <button disabled={state.busy || !publicationState.safe} onClick={() => { if ((formCount || publicationState.dirty) && state.academic) setConfirmRefresh(true); else void state.refresh() }}>刷新审核权限与本机恢复记录</button>
    {state.academic && confirmRefresh && <Dialog title="刷新前保留审核表单" close={() => setConfirmRefresh(false)}><p>重新核验权限会清空当前页面的临时审核及发布确认。已经安全保存的原命令仍保留；返回可以继续编辑。</p><button onClick={() => setConfirmRefresh(false)}>返回保留审核表单</button><button onClick={() => { discardForms(); void state.refresh() }}>明确丢弃临时审核表单并刷新权限</button></Dialog>}
    {pendingForms && <p role="status">未提交的审核表单保留在本页原会话内存，权限受限时隔离收起；刷新或关闭浏览器仍可能丢失。仅原会话恢复作者权限后，可明确核验原候选与审核记录；不会自动提交。</p>}
    {state.academic && pendingForms && <button disabled={state.busy || !publicationState.safe || state.pendingMemory} onClick={() => void state.recoverForms(scope, rows => { setCreates({}); setDecisions({}); setRecovered(rows) })}>核验原会话与准确基准，恢复临时审核表单</button>}
    {state.pendingMemory && <><p role="alert">原审核命令或回执尚未落盘，隔离保留在本页内存；刷新可能丢失，权限恢复后只保存原记录。</p><button disabled={state.busy} onClick={() => setDiscardMemory(true)}>放弃未落盘审核记录</button></>}
    {state.canSaveMemory && <button disabled={state.busy} onClick={() => void state.saveMemory()}>保存原会话的审核内存记录</button>}
    {discardMemory && <Dialog title="放弃未落盘审核记录" close={() => setDiscardMemory(false)}><p>明确放弃当前工作区尚未落盘的原审核命令或回执；已保存记录与服务端内容不变。此内存无法恢复。</p><button disabled={state.busy} onClick={() => { discardReviewMemory(workspace); setDiscardMemory(false) }}>确认放弃未落盘审核记录</button></Dialog>}
    {state.error && <p role="status">{state.error}</p>}
    <section aria-label="安全审核任务"><h4>已知审核任务</h4>
      <p>这里只保存实际审核 ID。当前状态另从服务端读取；刷新不会重新创建任务。</p>
      <p>无法核对旧取消命令的操作者时，旧命令只读保留。另行读取当前任务后，可明确发起新的取消命令；这不是原 key 回放。</p>
      {state.ids.map(id => <button key={id} disabled={state.busy || !publicationState.safe || !state.controlsReady} onClick={() => void state.selectJob(id)}>读取审核任务 {id}</button>)}
      <label>已有服务端审核 ID<input value={manualId} onChange={event => setManualId(event.target.value)} /></label>
      <button disabled={state.busy || !publicationState.safe || !state.controlsReady || !validIdentity(manualId)} onClick={() => void state.selectJob(manualId)}>读取这个审核任务</button>
      {job && <article><p>任务 {job.id} · {job.status} · 任务 r{job.revision}</p><p>{job.progress.label}</p>
        <button disabled={state.busy || !publicationState.safe} onClick={() => void state.selectJob(job.id)}>另行刷新审核任务当前状态</button>
        <button disabled={state.busy || !publicationState.safe || !state.controlsReady || ['completed', 'failed', 'cancelled'].includes(job.status)} onClick={() => void state.cancel()}>明确取消这个审核任务</button>
        <button disabled={state.busy || !publicationState.safe || !state.ready || job.status !== 'completed'} onClick={() => void state.read(job.id)}>另行读取当前审核回执</button></article>}
    </section>
    <section aria-label="原审核命令"><h4>本机保留的原审核命令</h4>{state.commands.map(command => <article key={command.command_id}>
      <p>{command.kind === 'create' ? '创建审核' : command.kind === 'decision' ? '人工决定' : '取消审核任务'} · {command.ack ? '原 ACK 已保存' : command.rejection ? '服务端拒绝，原基准保留' : '结果未知，原 key 与完整命令保留'}</p>
      <details><summary>核对原审核命令</summary><p>{command.command_id}</p><pre>{JSON.stringify(command.body, null, 2)}</pre>{command.kind !== 'cancel' && <pre>{JSON.stringify(command.candidate, null, 2)}</pre>}{command.ack && <p>原 ACK 不是当前状态。请另外读取实际任务与审核回执。</p>}</details>
      {!state.canReplay(command) && !command.ack && <p>无法核对原操作者；刷新或访问代次变化后的原命令仅保留只读，不用新会话同 key 冒充原回放。</p>}
      <button disabled={state.busy || !publicationState.safe || !!command.ack || !state.canReplay(command) || !(command.kind === 'cancel' ? state.controlsReady : state.ready)} onClick={() => void state.execute(command)}>显式回放原审核命令 {command.command_id}</button>
    </article>)}</section>
    {!state.academic ? <p role="status">当前只开放安全审核任务控制。候选、备注、审核回执与报告已收起；权限恢复后请明确重新读取。</p> : <>
      {formCount > 0 && <p>当前页面保留 {formCount} 份临时审核表单，各自绑定原候选或原回执版本。重新读取相同基准可以继续编辑；新基准不会套用旧理由。</p>}
      {candidate ? recovered.some(row => row.form.kind === 'create' && sameValue(row.form.candidate, candidate)) ? null : <ReviewCreateForm key={createKey} candidate={candidate} candidateState={candidateState} busy={state.busy || !publicationState.safe || !state.ready || state.pendingMemory} value={creates[createKey] ?? emptyCreateForm()} change={value => retainCreate(candidate, value)} submit={body => void state.create(candidate, body)} />
        : <p>请从已有导入或创作入口明确读取准确候选，再准备审核。已有审核任务仍可只读恢复。</p>}
      {receipt && <section aria-label="当前审核回执"><h4>实际审核回执 r{receipt.revision}</h4><p>{receipt.id} · {receipt.candidate.draft_id} · 候选 r{receipt.candidate.draft_revision}</p><code>{receipt.candidate.candidate_sha256}</code>
        <dl><dt>结构检查</dt><dd>{receipt.structural}</dd><dt>数学人工决定</dt><dd>{receipt.mathematical}</dd><dt>来源人工决定</dt><dd>{receipt.sources}</dd><dt>独立教学验收</dt><dd>NOT_RUN</dd></dl>
        <p>记录操作者：{receipt.reviewer}；原回执创建时间：{receipt.created_at}</p><p>已保存理由：{receipt.decision_reason || '尚无人工作出决定。'}</p>
        <button disabled={state.busy || !publicationState.safe} onClick={() => void state.read(receipt.id)}>重新读取审核回执</button>
        {receipt.evidence_paths.map((path, index) => <div key={path}><p>{index === 0 ? '实际机器审核报告' : `已绑定证据附件 ${index}`}</p>{index === 0 && <button disabled={state.busy || !publicationState.safe} onClick={() => void state.artifact(path, false)}>读取受控审核报告</button>}<button disabled={state.busy || !publicationState.safe} onClick={() => void state.artifact(path, true)}>下载审核附件 {index + 1}</button></div>)}
        {state.report && <details open><summary>已取得的原报告文本</summary><p>本次字节 SHA256：<code>{state.report.sha256}</code></p><pre>{state.report.text}</pre></details>}
        {matches ? recovered.some(row => row.form.kind === 'decision' && sameValue(row.form.receipt, receipt)) ? null : <ReviewDecisionForm key={decisionKey} receipt={receipt} busy={state.busy || !publicationState.safe || !state.ready || state.pendingMemory} value={decisions[decisionKey] ?? emptyDecisionForm()} change={value => retainDecision(receipt, value)} submit={body => void state.decide(body)} />
          : <p>当前候选入口尚未读到与本回执完全相同的候选；这里只读展示回执，请先核对准确候选后再记录决定。</p>}
      </section>}
    </>}
    {state.academic && recovered.map((row, index) => {
      const form = row.form, current = sameValue(form.candidate, row.currentCandidate) && (form.kind === 'create' || sameValue(form.receipt, row.currentReceipt))
      const unavailable = state.busy || !publicationState.safe || !state.ready || state.pendingMemory || !current
      return <section key={`${form.kind}:${candidateKey(form.candidate)}:${index}`} aria-label={`恢复的临时审核表单 ${index + 1}`}><h4>原临时表单 · {form.candidate.draft_id} · 候选 r{form.candidate.draft_revision}</h4>
        {!current && <p role="alert">服务端候选或审核记录已变化。以下原文只读保留，不会套用到新基准；请另行读取并准备新的表单。</p>}
        <details><summary>核对原基准与本次读取</summary><pre>{JSON.stringify({ original: form.candidate, current: row.currentCandidate, original_review: form.kind === 'decision' ? form.receipt : null, current_review: row.currentReceipt }, null, 2)}</pre></details>
        {form.kind === 'create' ? <ReviewCreateForm candidate={form.candidate} candidateState="本次重新核验" busy={unavailable}
          value={creates[candidateKey(form.candidate)] ?? { ...form.value, confirmed: false }} change={value => retainCreate(form.candidate, value, form.owner)} submit={body => void state.create(form.candidate, body)} />
          : <ReviewDecisionForm receipt={form.receipt} busy={unavailable} value={decisions[reviewDecisionKey(form.receipt)] ?? { ...form.value, confirmed: false }}
            change={value => retainDecision(form.receipt, value, form.owner)} submit={body => void state.decideRecovered(form.receipt, body)} />}
      </section>
    })}
    {importDraft !== undefined && <PublicationPanel workspace={workspace} paused={paused || !state.academic} blocked={state.busy}
      draft={state.academic ? importDraft : null} receipt={receipt} onState={setPublicationState} />}
    {editDraft !== undefined && <EditPublicationPanel workspace={workspace} paused={paused || !state.academic} blocked={state.busy}
      draft={state.academic ? editDraft : null} receipt={receipt} onState={setPublicationState} />}
    {restoreDraft !== undefined && <RestorePublicationPanel blockId={restoreBlockId} workspace={workspace} paused={paused || !state.academic} blocked={state.busy}
      draft={state.academic ? restoreDraft : null} receipt={receipt} onState={setPublicationState} />}
    <p>未提交的表单保留在当前页面的原会话内存；明确提交时先保存完整原命令。关闭不会自动批准或发布。</p>
  </section>
}
