import { useEffect, useRef, useState } from 'react'
import type { ContentRef } from '../../../../../packages/contracts/generated/api-types'
import { ReviewPanel } from '../draftReview/ReviewPanel'
import { pendingReviewMemory } from '../draftReview/reviewMemory'
import { emptyReviewPanelState, pendingReviewForms, discardReviewForms, type ReviewPanelState } from '../draftReview/reviewFormMemory'
import type { RestorePort } from './restoreClient'
import { useRestoreDrafts } from './useRestoreDrafts'
import { pendingRestoreCreateMemory, discardRestoreCreateMemory } from './restoreCreateMemory'
import { pendingRestorePublicationMemory } from './restorePublicationMemory'
import { pendingRestoreForms, discardRestoreForms } from './restoreFormMemory'
import './restore.css'

export type RestoreStatus = { dirty: boolean; safe: boolean; closeSafe: boolean }
const pendingRestoreCommands = (workspace: string) => pendingRestoreCreateMemory(workspace) || pendingRestorePublicationMemory(workspace) || pendingReviewMemory(workspace)
export const pendingRestoreMemory = (workspace: string) => pendingRestoreCommands(workspace) || pendingRestoreForms(workspace) || pendingReviewForms(workspace)
export function RestorePanel({ workspace, blockId, selectedSource, paused, onState, port }: {
  workspace: string; blockId: string; selectedSource: ContentRef | null; paused: boolean; onState?: (value: RestoreStatus) => void; port?: RestorePort
}) {
  const state = useRestoreDrafts(workspace, paused, blockId, port)
  const [draftId, setDraftId] = useState('')
  const [reviewOpen, setReviewOpen] = useState(false), [discarding, setDiscarding] = useState(false), [discardingForm, setDiscardingForm] = useState(false)
  const [reviewState, setReviewState] = useState<ReviewPanelState>(emptyReviewPanelState), [discardingReview, setDiscardingReview] = useState(false)
  const reviewScope = `restore:${blockId}`, heldReviewForms = pendingReviewForms(workspace, reviewScope)
  const callback = useRef(onState); callback.current = onState
  const pending = pendingRestoreMemory(workspace), safe = !state.busy && !pendingRestoreCommands(workspace) && reviewState.safe
  const { reason, confirmed } = state.form ?? { reason: '', confirmed: false }, formDirty = state.pendingForm
  const dirty = formDirty || pending || reviewState.dirty || state.commands.some(command => !command.ack && !command.rejection)
  useEffect(() => { callback.current?.({ dirty, safe: pending || safe, closeSafe: safe && !formDirty && !heldReviewForms }) }, [dirty, safe, pending, formDirty, heldReviewForms])
  useEffect(() => () => { const held = pendingRestoreMemory(workspace); callback.current?.({ dirty: held, safe: true, closeSafe: !held }) }, [workspace, blockId])
  useEffect(() => {
    if (!dirty && safe) return
    const guard = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = '' }
    window.addEventListener('beforeunload', guard); return () => window.removeEventListener('beforeunload', guard)
  }, [dirty, safe])
  const blocked = !safe || reviewState.dirty && !reviewState.isolated
  return <section className="restore-panel" aria-label="历史内容块恢复与审核"><h3>将历史公开块恢复为新修订</h3>
    <p>仅恢复同一块的完整历史字段和正文，建立独立待审恢复稿。旧审核和数值结果不转授；不会回滚旧题、私解、作答或成绩，也不更新 Lesson/Course 的原精确引用。</p>
    {state.busy && <p role="status">正在核对恢复原件与准确基准…</p>}{state.error && <p role="alert">{state.error}</p>}
    {state.pendingMemory && <><p role="alert">恢复创建命令或 ACK 尚未落盘，隔离保留在本页内存。请保持页面打开，恢复原会话后只保存原记录。</p><button disabled={state.busy} onClick={() => setDiscarding(true)}>放弃未落盘恢复创建记录</button></>}
    {state.canSaveMemory && <button disabled={state.busy} onClick={() => void state.saveMemory()}>保存原会话的恢复创建内存记录</button>}
    {discarding && <div role="dialog" aria-label="放弃未落盘恢复创建记录"><p>明确放弃尚未落盘的原恢复创建命令或 ACK，无法恢复；已保存命令和服务端内容不变。</p><button disabled={state.busy} onClick={() => { discardRestoreCreateMemory(workspace); setDiscarding(false) }}>确认放弃恢复创建内存</button><button onClick={() => setDiscarding(false)}>取消放弃恢复创建内存</button></div>}
    {formDirty && !state.basis && <div role="alert"><p>本页保留了未提交的恢复理由和原依据。权限受限或会话改变时不显示原内容；恢复会重新核验权限和原件，不会自动创建或采用新基准。</p><button disabled={state.busy || !state.canRestoreForm} onClick={() => void state.restoreForm()}>重新核验并恢复原会话的恢复表单</button><button disabled={state.busy} onClick={() => setDiscardingForm(true)}>明确放弃未提交恢复表单</button></div>}
    {discardingForm && <div role="dialog" aria-label="放弃未提交恢复表单"><p>明确丢弃本页此工作区、此内容块的未提交恢复理由和原依据；不删除已保存原命令或回执。</p><button disabled={state.busy} onClick={() => { discardRestoreForms(workspace, blockId); setDiscardingForm(false) }}>确认放弃未提交恢复表单</button><button onClick={() => setDiscardingForm(false)}>继续保留恢复表单</button></div>}
    {!state.ready ? <p>需要当前作者权限和允许的学科 Policy；历史正文和候选已收起，原记录仍保留。</p> : <>
      {selectedSource && <p>比较中明确选定的来源：{selectedSource.id} · r{selectedSource.revision} · <code>{selectedSource.sha256}</code></p>}
      <button disabled={blocked || formDirty || !selectedSource} onClick={() => { if (selectedSource) void state.prepare(selectedSource) }}>重新读取当前基准并核验所选历史原件</button>
      {state.basis && <section aria-label="恢复创建的准确基准"><p>历史来源 r{state.basis.source_ref.revision} → 活动当前 r{state.basis.base_ref.revision} → 拟发布 r{state.basis.base_ref.revision + 1}。最终由服务端强 CAS 再核，当前变化将拒绝。</p>
        <div className="restore-comparison">{[{ name: '历史来源', value: state.basis.source }, { name: '当前基准', value: state.basis.current }].map(side => <section key={side.name}><h4>{side.name}完整元数据</h4><pre aria-label={`${side.name}完整元数据`}>{JSON.stringify(side.value.metadata, null, 2)}</pre><h4>{side.name}完整正文</h4><pre aria-label={`${side.name}完整正文`}>{side.value.body_markdown}</pre></section>)}</div>
        <p>kind、概念、引用、依赖和正文均来自历史来源；不沿用当前字段，不判断数学等价。</p>
        <label>本次恢复理由<textarea disabled={blocked} value={reason} onChange={event => state.changeForm({ reason: event.target.value, confirmed: false })} /></label>
        <label><input type="checkbox" disabled={blocked} checked={confirmed} onChange={event => state.changeForm({ reason, confirmed: event.target.checked })} />我已核对历史来源、当前基准与全部字段，明确创建独立待审恢复稿。</label>
        <button disabled={blocked || !state.canCreate || !confirmed || !reason.trim() || [...reason].length > 2000} onClick={() => void state.create(reason)}>明确创建本次历史恢复稿</button>
        {formDirty && <button disabled={blocked} onClick={state.clearForm}>明确清除未提交的恢复表单</button>}
      </section>}
      <label>读取已有恢复稿 ID<input value={draftId} onChange={event => setDraftId(event.target.value)} /></label><button disabled={blocked || formDirty || !draftId.trim()} onClick={() => void state.read(draftId)}>另行读取准确恢复稿</button>
      {state.commands.map(command => <article key={command.command_id}><p><code>{command.command_id}</code> · {command.ack ? '原恢复创建 ACK 已保存' : command.rejection ? `原恢复创建被拒绝：${command.rejection.status}` : '创建结果未知，原 key 与完整命令保留'}</p>
        <details><summary>核对原恢复创建命令</summary><pre>{JSON.stringify(command.body, null, 2)}</pre>{command.ack && <pre>{JSON.stringify(command.ack, null, 2)}</pre>}</details>
        {!state.canReplay(command) && <p>原页面或访问代次已改变，不能用当前会话冒充原命令；原件只读保留。</p>}
        <button disabled={blocked || formDirty || !state.canReplay(command) || !!command.ack || !!command.rejection} onClick={() => void state.execute(command)}>显式回放原恢复创建命令 {command.command_id}</button>
        {command.ack && <button disabled={blocked || formDirty} onClick={() => void state.read(command.ack!.candidate.draft_id)}>另行读取恢复稿 {command.ack.candidate.draft_id}</button>}
      </article>)}
      {state.draft && <section aria-label="实际读取的恢复候选"><h4>{state.draft.owner} · {state.draft.state}</h4><p>{state.draft.candidate.draft_id} · 候选 r{state.draft.candidate.draft_revision} · <code>{state.draft.candidate.candidate_sha256}</code></p><p>来源 r{state.draft.source_ref.revision}；基准 r{state.draft.base_ref.revision}；来源材料 SHA <code>{state.draft.source_material_sha256}</code></p><p>原创建理由：{state.draft.reason}</p><pre aria-label="恢复候选完整元数据">{JSON.stringify(state.draft.proposed_block, null, 2)}</pre><pre aria-label="恢复候选完整正文">{state.draft.body_markdown}</pre>
        {state.draft.warnings.map((warning, index) => <p key={index}>{warning.severity} · {warning.code} · {warning.message}</p>)}
        {state.draft.proposed_block.kind === 'worked_example' && <p>例题恢复不继承历史数值执行；本次候选没有真实数值执行记录时仍为 NOT_RUN，服务端阻止发布。</p>}
        {state.draft.published_ref && <p>实际发布引用：{state.draft.published_ref.id} · r{state.draft.published_ref.revision} · {state.draft.published_ref.sha256}；不是父章节已更新。</p>}
      </section>}
    </>}
    <button disabled={state.busy || formDirty} onClick={() => setReviewOpen(true)}>打开恢复审核与发布恢复</button>
    {heldReviewForms && <button disabled={state.busy || !reviewState.safe} onClick={() => setDiscardingReview(true)}>明确放弃本块未提交审核表单</button>}
    {discardingReview && <div role="dialog" aria-label="放弃本块未提交审核表单"><p>仅丢弃本工作区、此恢复块的未提交审核备注和理由；原审核命令、回执与服务端事实保留。</p><button disabled={state.busy || !reviewState.safe} onClick={() => { reviewState.discardForms(); discardReviewForms(workspace, reviewScope); setDiscardingReview(false) }}>确认放弃本块未提交审核表单</button><button onClick={() => setDiscardingReview(false)}>继续保留本块审核表单</button></div>}
    {reviewOpen && <ReviewPanel formScope={reviewScope} workspace={workspace} paused={paused || !state.ready} candidate={state.draft?.state === 'draft' ? state.draft.candidate : null}
      candidateState={state.draft?.state ?? '尚未明确读取恢复候选'} restoreDraft={state.draft} restoreBlockId={blockId} onState={setReviewState} />}
    <button disabled={blocked || formDirty} onClick={() => void state.refresh()}>重新核对恢复权限与原记录</button>
  </section>
}
