import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import type { LoadedBlock } from '../reader/contentClient'
import type { EditPort } from './editClient'
import type { EditText } from './editSchema'
import { useDraftEditor } from './useDraftEditor'
import { pendingEditMemory } from './editMemory'
import { pendingReviewMemory } from '../draftReview/reviewMemory'
import { emptyReviewPanelState, type ReviewPanelState, discardReviewForms, pendingReviewForms, subscribeReviewForms, reviewFormMemoryVersion } from '../draftReview/reviewFormMemory'
import { ReviewPanel } from '../draftReview/ReviewPanel'
import { pendingEditPublicationMemory } from '../editPublication/editPublicationMemory'
import { MarkdownSourceEditor } from './MarkdownSourceEditor'
import './editor.css'

export type EditorStatus = { dirty: boolean; safe: boolean; closeSafe: boolean }
export function DraftEditor({ workspace, block, onState, port, paused = false }: { workspace: string; block: LoadedBlock; onState?: (state: EditorStatus) => void; port?: EditPort; paused?: boolean }) {
  const [open, setOpen] = useState(false), [closing, setClosing] = useState(false), [discarding, setDiscarding] = useState(false), [draftId, setDraftId] = useState('')
  const state = useDraftEditor(workspace, block.block_ref, !open || paused, port), callback = useRef(onState); callback.current = onState
  const [reviewOpen, setReviewOpen] = useState(false)
  useEffect(() => { if (state.reviewSnapshot) setReviewOpen(true) }, [state.reviewSnapshot])
  const [reviewState, setReviewState] = useState<ReviewPanelState>(emptyReviewPanelState)
  useSyncExternalStore(subscribeReviewForms, reviewFormMemoryVersion, reviewFormMemoryVersion)
  const formScope = `edit:${block.block_ref.id}`
  const heldForms = pendingReviewForms(workspace, formScope)
  const activeReview = reviewState.dirty && !reviewState.isolated
  const protectedPublication = pendingEditPublicationMemory(workspace, block.block_ref) || pendingReviewMemory(workspace)
  const safe = state.safe && reviewState.safe && !protectedPublication, dirty = heldForms || state.dirty || state.pendingMemory || activeReview || protectedPublication
  useEffect(() => { callback.current?.({ dirty, safe: state.pendingMemory || protectedPublication || safe, closeSafe: safe }) }, [dirty, safe, state.pendingMemory, protectedPublication])
  useEffect(() => () => { const pending = pendingReviewForms(workspace, `edit:${block.block_ref.id}`) || pendingEditMemory(workspace, block.block_ref) || pendingEditPublicationMemory(workspace, block.block_ref) || pendingReviewMemory(workspace); callback.current?.({ dirty: pending, safe: true, closeSafe: !pending }) }, [workspace, block.block_ref.id, block.block_ref.revision, block.block_ref.sha256])
  useEffect(() => {
    const guard = (event: BeforeUnloadEvent) => { if (!safe) { event.preventDefault(); event.returnValue = '' } }
    window.addEventListener('beforeunload', guard); return () => window.removeEventListener('beforeunload', guard)
  }, [safe])
  const supported = block.block.kind === 'text' && !block.block.body_path.startsWith('private/')
  if (!supported) return null
  const close = () => { if (dirty || !safe) setClosing(true); else setOpen(false) }
  const conflict = state.conflict
  const editorDisabled = activeReview || !reviewState.safe || state.busy || !!conflict || state.buffer?.baseline.state !== 'draft'
  return <section className="draft-editor" aria-label="文本块编辑与恢复">
    <button aria-expanded={open} onClick={() => open ? close() : setOpen(true)}>{open ? '收起文本编辑' : '编辑此精确文本块'}</button>
    {open && <div><h3>编辑未发布草稿</h3><p>基于此块修订 {block.block_ref.revision} · <code>{block.block_ref.sha256}</code>。本机编辑只保存标题和正文。准确服务端修订须另行进入审核，再明确发布为原块下一修订。</p>
      {state.busy && <p role="status">正在核对原记录…</p>}{state.error && <p role="alert">{state.error}</p>}
      {state.pendingMemory && <><p role="alert">有尚未落盘的文字隔离保留在本页内存中，刷新或关闭浏览器仍可能丢失。恢复原会话的作者权限后，需重新核验准确基准并明确保存。</p><button disabled={state.busy || state.saving} onClick={() => setDiscarding(true)}>放弃此块未落盘的隔离内存</button></>}
      {!state.ready ? <p>需要当前作者角色，且当前测试策略允许读取学科材料。</p> : <>
        {!!block.block.concepts?.length && <section aria-label="保留的原概念 ID"><p>以下原概念 ID 及顺序会完整保留；本次只能修改标题和正文。</p><pre aria-label="原概念 ID 只读记录">{JSON.stringify(block.block.concepts, null, 2)}</pre></section>}
        {!!block.block.depends_on?.length && <section aria-label="保留的原精确依赖"><p>以下原依赖及顺序会完整保留；本次只能修改标题和正文。</p><pre aria-label="原精确依赖只读记录">{JSON.stringify(block.block.depends_on, null, 2)}</pre></section>}
        {state.pendingMemory && <button disabled={!state.canRecoverMemory || state.busy || state.saving} onClick={() => void state.recoverMemory()}>核验原会话与精确基准，恢复内存副本</button>}
        <button disabled={!safe || activeReview} onClick={() => void state.create(block.block.title)}>从此准确修订明确创建编辑稿</button>
        <label>读取已有编辑稿 ID<input value={draftId} onChange={e => setDraftId(e.target.value)} /></label><button disabled={!safe || activeReview || !draftId.trim()} onClick={() => void state.read(draftId)}>另行读取服务端草稿头</button>
        {state.buffers.length > 0 && <section aria-label="本机工作副本"><h4>本机工作副本</h4><p>恢复会复制原副本；重新核验原精确草稿修订，不自动采用服务端新头。</p>{state.buffers.map(b => <button key={b.id} disabled={!safe || activeReview} onClick={() => void state.restore(b)}>恢复本机副本 {b.id} · {b.local.title} · 草稿 r{b.baseline.candidate.draft_revision}</button>)}</section>}
        {state.buffer && <section aria-label="当前本机编辑"><h4>当前本机编辑</h4><p><code>{state.buffer.baseline.candidate.draft_id}</code> · 基准草稿 r{state.buffer.baseline.candidate.draft_revision} · <code>{state.buffer.baseline.candidate.candidate_sha256}</code></p>
          <p>{state.buffer.baseline.state === 'published' ? '该精确草稿已发布，只读保留。' : '未取得数学、来源或教学批准。'}</p>
          <fieldset disabled={editorDisabled}><label>本机标题<input value={state.buffer.local.title} onChange={e => state.update({ ...state.buffer!.local, title: e.target.value })} /></label><MarkdownSourceEditor label="本机正文" sourceIdentity={JSON.stringify([workspace, block.block_ref, state.buffer.id, state.buffer.baseline.candidate])} disabled={editorDisabled} value={state.buffer.local.body_markdown} onChange={body_markdown => state.update({ ...state.buffer!.local, body_markdown })} /></fieldset>
          <p role="status">{state.saving ? '正在保存本机工作副本…' : state.safe ? '本机工作副本已保存；不代表已同步到服务端。' : '本机保存尚未确认，请保持页面打开。'}</p>
          {!state.safe && !state.busy && !state.saving && <button onClick={() => void state.retrySave()}>重试保存本机工作副本</button>}
          <button disabled={!safe || activeReview || !!conflict || !state.dirty || state.buffer.baseline.state !== 'draft'} onClick={() => void state.submit()}>明确提交本机标题与正文</button>
          <button disabled={!safe || activeReview || state.dirty || !!conflict || state.buffer.baseline.state !== 'draft'} onClick={() => void state.selectReview()}>核验已保存精确编辑稿并进入审核</button>
          <p>仅提交过的服务端修订可进入审核。本机未同步文字、旧 ACK 和三方冲突不会作为审核候选。</p>
        </section>}
        {conflict && <section aria-label="三方冲突恢复"><h4>三方冲突恢复</h4><p>原命令 {conflict.command.key} 返回 412，仍完整保留。以下服务端状态来自独立 GET；未自动变基。</p><div className="edit-three-columns">
          {[{ name: '基准', text: { title: conflict.base.payload.title, body_markdown: conflict.base.payload.body_markdown }, revision: conflict.base.candidate.draft_revision }, { name: '本地待同步', text: conflict.local, revision: conflict.base.candidate.draft_revision }, { name: '服务端当前', text: { title: conflict.server.payload.title, body_markdown: conflict.server.payload.body_markdown }, revision: conflict.server.candidate.draft_revision }].map(side => <section key={side.name} aria-label={side.name}><h5>{side.name} · 草稿 r{side.revision}</h5><label>{side.name}标题<input readOnly value={side.text.title} /></label><label>{side.name}正文<textarea aria-label={`${side.name}正文`} readOnly rows={8} value={side.text.body_markdown} /></label></section>)}
        </div>{conflict.server.state === 'published' ? <p>服务端此草稿已发布；不能新增 PATCH 修订，原本机候选保留。</p> : <ConflictResolution key={conflict.command.key + conflict.server.candidate.candidate_sha256} base={conflict.base.payload} local={conflict.local} server={conflict.server.payload} disabled={!safe || activeReview} resolve={state.resolve} />}</section>}
        <section aria-label="编辑原命令历史"><h4>编辑原命令历史</h4>{state.commands.map(c => <div key={c.key}><p><code>{c.key}</code> · {c.operation.kind === 'create' ? '创建' : '提交编辑'} · {c.ack ? `历史 ACK：草稿 ${c.ack.draft_id} r${c.ack.revision}（不是当前状态）` : c.rejection ? `原请求被拒绝：${c.rejection}` : '结果未知，完整原命令保留'}</p>
          {!state.canReplay(c) && <p>原操作者不能由旧页面记录确认，此命令只读保留。</p>}
          <button disabled={!safe || activeReview || !state.canReplay(c) || c.rejection !== null} onClick={() => void state.execute(c)}>显式回放原编辑命令 {c.key}</button>
          {c.ack && <button disabled={!safe || activeReview} onClick={() => void state.read(c.ack!.draft_id)}>另行读取草稿头 {c.ack.draft_id}</button>}
          {c.operation.kind === 'patch' && c.rejection === 412 && <button disabled={!safe || activeReview} onClick={() => void state.readConflict(c)}>读取原冲突三方内容 {c.key}</button>}
        </div>)}</section>
      </>}
      <button disabled={!state.safe} onClick={() => setReviewOpen(true)}>打开编辑审核与发布恢复</button>
      {reviewOpen && <ReviewPanel formScope={formScope} workspace={workspace} paused={paused || !state.ready} candidate={state.reviewSnapshot?.candidate ?? null}
        candidateState={state.reviewSnapshot?.state ?? '尚未明确核验编辑候选'} editDraft={state.reviewSnapshot} onState={setReviewState} />}
      <button disabled={!safe || activeReview} onClick={() => void state.refresh()}>重新核对编辑权限与本机记录</button>
    </div>}
    {closing && <div role="dialog" aria-label="保留本机编辑"><p>本机副本与已保存原命令会保留；未提交审核表单和发布确认将丢弃。关闭不会提交、批准或发布。</p><button disabled={!safe} onClick={() => { reviewState.discardForms(); discardReviewForms(workspace, formScope); setClosing(false); setOpen(false) }}>保留本机编辑并收起</button><button onClick={() => setClosing(false)}>返回编辑</button></div>}
    {discarding && <div role="dialog" aria-label="放弃尚未落盘的内存副本"><p>明确放弃此精确块尚未落盘的隔离文字，无法恢复。已保存的本机副本、原命令和服务端内容不受影响。</p><button disabled={state.busy || state.saving} onClick={() => { state.discardMemory(); setDiscarding(false) }}>确认放弃隔离文字</button><button onClick={() => setDiscarding(false)}>取消放弃</button></div>}
  </section>
}
function ConflictResolution({ base, local, server, disabled, resolve }: { base: EditText; local: EditText; server: EditText; disabled: boolean; resolve: (value: EditText) => Promise<void> }) {
  const [title, setTitle] = useState(''), [body, setBody] = useState(''), [custom, setCustom] = useState<EditText>({ title: '', body_markdown: '' }), [confirmed, setConfirmed] = useState(false)
  const choices: Record<string, EditText> = { base, local, server, custom }
  return <fieldset disabled={disabled}><legend>明确选择解决结果</legend>
    {(['title', 'body_markdown'] as const).map(field => <div key={field}><label>{field === 'title' ? '标题解决方式' : '正文解决方式'}<select aria-label={field === 'title' ? '标题解决方式' : '正文解决方式'} value={field === 'title' ? title : body} onChange={e => { (field === 'title' ? setTitle : setBody)(e.target.value); setConfirmed(false) }}><option value="">请选择</option><option value="base">采用基准</option><option value="local">采用本地待同步</option><option value="server">采用服务端当前</option><option value="custom">手动合并</option></select></label>{(field === 'title' ? title : body) === 'custom' && (field === 'body_markdown' ? <MarkdownSourceEditor label="手动解决正文" sourceIdentity="conflict-body" value={custom.body_markdown} disabled={disabled} onChange={body_markdown => { setCustom({ ...custom, body_markdown }); setConfirmed(false) }} /> : <label>手动解决标题<textarea aria-label="手动解决标题" value={custom.title} onChange={e => { setCustom({ ...custom, title: e.target.value }); setConfirmed(false) }} /></label>)}</div>)}
    <label><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />我已核对三方标题和正文，明确以本次服务端修订作为新基准。</label>
    <button disabled={!title || !body || !confirmed} onClick={() => void resolve({ title: choices[title].title, body_markdown: choices[body].body_markdown })}>保存解决结果到本机，暂不提交</button>
  </fieldset>
}
