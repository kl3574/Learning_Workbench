import { useCallback, useEffect, useRef, useState } from 'react'
import type { AuthoringDraftView, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
import { Dialog } from '../../workbench/Controls'
import type { SinglePublicationPort } from './singlePublicationClient'
import { matchesSingleCandidate } from './singlePublicationSchema'
import { discardSinglePublicationForms, discardSinglePublicationMemory, pendingSinglePublicationForms, pendingSinglePublicationMemory } from './singlePublicationMemory'
import { useSinglePublication } from './useSinglePublication'

export function SinglePublicationPanel({ workspace, paused, blocked, draft, receipt, port, onState, onDraftRead }: {
  workspace: string; paused: boolean; blocked: boolean; draft: AuthoringDraftView | null; receipt: StoredReviewReceipt | null; port?: SinglePublicationPort
  onState?: (value: { dirty: boolean; safe: boolean; discardForms?: () => void }) => void; onDraftRead?: () => void
}) {
  const selection = JSON.stringify([draft && { candidate: draft.candidate, state: draft.state, numeric_check_ids: draft.numeric_check_ids }, receipt])
  const state = useSinglePublication(workspace, paused, selection, port, draft?.candidate.draft_id)
  const key = `${selection}:${state.preparedAt}`
  const [form, setForm] = useState({ key: '', selected: [] as number[], confirmed: false })
  const value = state.basis && form.key === key ? form : { key, selected: [] as number[], confirmed: false }
  const [discardMemory, setDiscardMemory] = useState(false), [discardForm, setDiscardForm] = useState(false)
  const callback = useRef(onState); callback.current = onState
  const discardForms = useCallback(() => { discardSinglePublicationForms(workspace); setForm({ key: '', selected: [], confirmed: false }); setDiscardForm(false) }, [workspace])
  const dirty = state.pendingMemory || state.pendingForms || state.ready && state.commands.some(command => !command.ack && !command.rejection)
  const safe = !state.busy && !state.pendingMemory
  const latestSafe = useRef(safe); latestSafe.current = safe
  useEffect(() => { if (!state.ready) setForm({ key: '', selected: [], confirmed: false }) }, [state.ready])
  useEffect(() => { callback.current?.({ dirty, safe, discardForms }) }, [dirty, safe, discardForms])
  useEffect(() => () => callback.current?.({ dirty: pendingSinglePublicationForms(workspace) || pendingSinglePublicationMemory(workspace), safe: latestSafe.current && !pendingSinglePublicationMemory(workspace), discardForms }), [workspace, discardForms])
  const busy = blocked || state.busy || state.pendingMemory, basis = state.basis
  const eligible = !!draft && draft.state === 'draft' && !!receipt && matchesSingleCandidate(draft, receipt.candidate)
    && receipt.structural === 'PASS' && receipt.mathematical === 'APPROVED' && ['APPROVED', 'NOT_APPLICABLE'].includes(receipt.sources) && !!receipt.decision_reason.trim()
  const warningsConfirmed = basis && basis.warnings.every((warning, index) => warning.severity !== 'error' && (warning.severity !== 'warning' || value.selected.includes(index)))
  const change = (next: typeof value) => { setForm(next); state.retainForm(next.selected, next.confirmed) }
  const readPublished = async (candidate: AuthoringDraftView['candidate'], ack?: Parameters<typeof state.readPublication>[1]) => {
    if (await state.readPublication(candidate, ack)) onDraftRead?.()
  }
  return <section className="publication-panel" aria-label="生成例题发布与恢复"><h4>发布这一单块生成例题</h4>
    <p>发布保留原候选正文、标题和声明来源顺序，新建一个公开例题块 r1。新对象 ID 由服务端分配，首次发布要求 current 为空；候选 SHA 不是公开块 SHA。</p>
    <p>只发布这个块，不调整章节或课程引用。生成来源保留 unresolved 提示，不因人审或发布变成已验证原件。</p>
    {state.error && <p role="status">{state.error}</p>}
    {state.pendingForms && <p role="status">未提交的发布确认保留在原会话的本页隔离内存。重新进入不会自动恢复确认或发送；可明确核验原候选、审核和数值基准后继续。</p>}
    {state.pendingForms && <button disabled={blocked || state.busy} onClick={() => setDiscardForm(true)}>放弃临时生成发布确认</button>}
    {discardForm && <Dialog title="放弃临时生成发布确认" close={() => setDiscardForm(false)}><p>明确放弃本工作区保留的临时发布选择。已保存的原命令、审核理由和服务端事实不变。</p><button disabled={blocked || state.busy} onClick={discardForms}>确认放弃临时生成发布确认</button></Dialog>}
    {state.pendingMemory && <><p role="alert">原发布命令或回执尚未落盘，已隔离保留在本页内存。请保持页面打开；权限恢复后只保存原记录，不自动发送。</p><button disabled={blocked || state.busy} onClick={() => setDiscardMemory(true)}>放弃未落盘生成发布记录</button></>}
    {discardMemory && <Dialog title="放弃未落盘生成发布记录" close={() => setDiscardMemory(false)}><p>明确放弃尚未落盘的原命令或回执；已经保存的记录不变。此内存无法恢复。</p><button disabled={blocked || state.busy} onClick={() => { discardSinglePublicationMemory(workspace); setDiscardMemory(false) }}>确认放弃未落盘生成发布记录</button></Dialog>}
    {state.canSaveMemory && <button disabled={blocked || state.busy} onClick={() => void state.saveMemory()}>保存原会话的生成发布内存记录</button>}
    {!state.ready ? <p>正在核验或当前权限不允许读取发布资料；原记录保留，保护内容已收起。</p> : <>
      {draft && <button disabled={busy} onClick={() => void readPublished(draft.candidate)}>独立读取生成候选的发布状态</button>}
      {state.publicationRead && <section aria-label="独立读取的生成发布状态"><p>本次 GET 候选状态：{state.publicationRead.state}</p>{state.publicationRead.published_ref && <p>原实际发布引用：{state.publicationRead.published_ref.id} · r{state.publicationRead.published_ref.revision} · <code>{state.publicationRead.published_ref.sha256}</code></p>}</section>}
      {state.forms.map(held => <section key={held.key} aria-label="保留的生成发布确认"><p>原候选 {held.basis.candidate.draft_id}；所选审核 {held.basis.review.id} r{held.basis.review.revision}；保留 {held.selected.length} 条警告选择。</p>
        <button disabled={busy || !!draft && !matchesSingleCandidate(draft, held.basis.candidate)} onClick={() => { void state.recoverForm(held).then(recovered => { if (recovered) setForm({ key: `${selection}:${recovered.key}`, selected: recovered.selected, confirmed: false }) }) }}>核验并恢复原生成发布表单</button>
        <p>重新核验不提交，最终发布确认必须重新勾选；基准已变化时原选择只读保留。</p></section>)}
      <button disabled={busy || !eligible} onClick={() => { if (draft && receipt) void state.prepare(draft, receipt) }}>选择此审核并重新读取生成发布基准</button>
      {!eligible && <p>先读取准确的未发布单块候选及其明确数学、来源决定和理由。数学 NOT_APPLICABLE、旧数值 PASS 或其他候选的审核不能代替本次准入。</p>}
      {basis && <section aria-label="本次生成发布基准"><h5>本次重新读取的完整基准</h5>
        <p>候选 {basis.candidate.draft_id} · r{basis.candidate.draft_revision} · <code>{basis.candidate.candidate_sha256}</code></p>
        <p>新公开块 r1；首次 current = null。具体 ID、路径和 ContentRef 由首次成功事务固定，不在浏览器猜测。</p>
        <pre aria-label="发布的原候选正文">{basis.snapshot.payload.body_markdown}</pre>
        <details><summary>原教学要求与全部来源材料</summary><pre>{JSON.stringify({ request: basis.generation.request, materials: basis.generation.preparation.materials, declared_source_refs: basis.snapshot.payload.declared_source_refs }, null, 2)}</pre></details>
        <p>所选审核 {basis.review.id} · r{basis.review.revision}；结构 {basis.review.structural}；数学 {basis.review.mathematical}；来源 {basis.review.sources}；独立教学 NOT_RUN。</p>
        <p>记录操作者：{basis.review.reviewer}；已保存理由：{basis.review.decision_reason}</p>
        <p>本次读取 {basis.checks.length} 份有序数值记录；最新检查 {basis.checks.at(-1)!.id} 显示实际 PASS。服务端仍会原子核验完整执行及所选 Review 的当前账本端点；新增事实须新 Review 和人类决定。</p>
        <fieldset disabled={busy}><legend>逐条确认真实来源与数值警告</legend>{basis.warnings.map((warning, index) => <div key={index}>{warning.severity === 'warning'
          ? <label><input type="checkbox" checked={value.selected.includes(index)} onChange={event => change({ ...value, selected: event.target.checked ? [...value.selected, index] : value.selected.filter(item => item !== index) })} />{warning.code} · {warning.message} · {warning.locator ?? '无定位'}</label>
          : <p>{warning.severity} · {warning.code} · {warning.message}</p>}</div>)}{!basis.warnings.length && <p>当前受检来源与数值记录没有警告。</p>}</fieldset>
        <label><input type="checkbox" checked={value.confirmed} disabled={busy} onChange={event => change({ ...value, confirmed: event.target.checked })} />我已核对原候选、来源、数值记录和所选人工审核，明确新建这一个公开例题块。</label>
        <button disabled={busy || !warningsConfirmed || !value.confirmed} onClick={() => void state.publish(value.selected)}>明确发布这一生成例题</button>
      </section>}
      <section aria-label="原生成发布命令"><h5>原命令与历史发布引用</h5>{state.commands.map(command => <article key={command.command_id}>
        <p>{command.ack ? '原生成发布 ACK 已保存' : command.rejection ? '服务端拒绝，原完整命令保留' : '发布结果未知，原 key 与完整命令保留'}</p>
        <details><summary>核对原生成发布命令</summary><p>{command.command_id}</p><pre>{JSON.stringify(command.body, null, 2)}</pre><pre>{JSON.stringify(command.basis, null, 2)}</pre></details>
        {!state.canReplay(command) && <p>旧页面或旧访问代次只读保留，不能用当前会话冒充原 key 回放。</p>}
        <button disabled={busy || !state.canReplay(command)} onClick={() => void state.execute(command)}>显式回放原生成发布命令 {command.command_id}</button>
        <button disabled={busy} onClick={() => void readPublished(command.basis.candidate, command.ack ?? undefined)}>另行读取该候选发布状态 {command.basis.candidate.draft_id}</button>
        {command.ack && <><p>原不可变发布引用：{command.ack.id} · r{command.ack.revision} · <code>{command.ack.sha256}</code></p><button disabled={busy} onClick={() => void state.readCurrent(command)}>另行读取当前引用 {command.ack.id}</button>
          {state.currentRead?.command_id === command.command_id && <p>本次 GET current：{state.currentRead.ref.id} · r{state.currentRead.ref.revision} · <code>{state.currentRead.ref.sha256}</code></p>}<p>原 ACK 不代表对象现在的 current；父章节和课程仍保留原引用。</p></>}
      </article>)}</section>
    </>}
    <button disabled={busy || dirty} onClick={() => void state.refresh()}>重新核验生成发布权限与本机记录</button>
  </section>
}
