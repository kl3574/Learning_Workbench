import { useEffect, useRef, useState } from 'react'
import type { ImportDraftSnapshot, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
import { matchesPublicationCandidate } from './publicationSchema'
import type { PublicationPort } from './publicationClient'
import { usePublication } from './usePublication'

export function PublicationPanel({ workspace, paused, blocked, draft, receipt, port, onState }: {
  workspace: string; paused: boolean; blocked: boolean; draft: ImportDraftSnapshot | null; receipt: StoredReviewReceipt | null; port?: PublicationPort
  onState?: (value: { dirty: boolean; safe: boolean }) => void
}) {
  const selection = JSON.stringify([draft && { id: draft.id, revision: draft.revision, sha256: draft.candidate_sha256, warnings: draft.warnings }, receipt])
  const state = usePublication(workspace, paused, selection, port)
  const key = `${selection}:${state.preparedAt}`
  const [form, setForm] = useState({ key: '', selected: [] as number[], confirmed: false })
  const value = state.basis && form.key === key ? form : { key, selected: [] as number[], confirmed: false }
  const callback = useRef(onState); callback.current = onState
  const dirty = state.ready && (!!value.selected.length || value.confirmed || state.commands.some(command => !command.ack && !command.rejection))
  const safe = !state.busy
  useEffect(() => { if (!state.ready) setForm({ key: '', selected: [], confirmed: false }) }, [state.ready])
  useEffect(() => { callback.current?.({ dirty, safe }) }, [dirty, safe])
  useEffect(() => () => callback.current?.({ dirty: false, safe: true }), [])
  const busy = blocked || state.busy, basis = state.basis
  const matches = draft && receipt && matchesPublicationCandidate(draft, receipt.candidate)
  const eligible = !!draft && draft.kind === 'block' && draft.state === 'draft' && !!matches && receipt?.structural === 'PASS'
    && receipt.mathematical === 'NOT_APPLICABLE' && receipt.sources === 'APPROVED' && !!receipt.decision_reason.trim()
  const warningsConfirmed = basis && basis.warnings.every((warning, index) => warning.severity !== 'error' && (warning.severity !== 'warning' || value.selected.includes(index)))
  return <section className="publication-panel" aria-label="Import 文本块发布与恢复"><h4>发布这一 Import 文本块</h4>
    <p>当前仅支持待确认导入中无依赖的公开纯文本块。须已有明确的数学“不适用”及理由、来源批准；服务端仍会核验原件、审核与完整证据。这里不会替你填写人工判断。</p>
    <p>发布只生成此块的不可变修订，不确认整份导入。随后整份导入会遇到该对象 ID 冲突；如继续导入，需要明确映射冲突 ID。复制内容不会继承本次审核批准。</p>
    {state.error && <p role="status">{state.error}</p>}
    {!state.ready ? <p>正在核验或当前权限不允许发布；本机原命令保留，保护内容已收起。</p> : <>
      {receipt && <p>待选择审核：{receipt.id} · 页面已读回执 r{receipt.revision}。创建时间不代表全局唯一审批；只使用你明确选择的这份审核。</p>}
      <button disabled={busy || !eligible} onClick={() => { if (draft && receipt) void state.prepare(draft, receipt) }}>选择此审核并重新读取发布基准</button>
      {!eligible && <p>请先明确读取匹配的 Import 文本块及其当前人工审核回执。机器 NOT_RUN、拒绝或不匹配的回执不能用于本次发布。</p>}
      {basis && <section aria-label="本次发布基准"><h5>本次实际重新读取的基准</h5>
        <p>候选 {basis.candidate.draft_id} · r{basis.candidate.draft_revision}</p><code>{basis.candidate.candidate_sha256}</code>
        <p>目标对象 {basis.target.object_id} · r{basis.target.object_revision}（尚不作为发布回执）</p>
        <p>所选审核 {basis.review.id} · 本页读取 r{basis.review.revision}；结构 {basis.review.structural}；数学 {basis.review.mathematical}；来源 {basis.review.sources}；独立教学 NOT_RUN。</p>
        <p>记录操作者：{basis.review.reviewer}；已保存理由：{basis.review.decision_reason}</p>
        <p>提交会重新核验所选审核的当前决定；本页读取的回执版本不作为另一个写入字段，也不预先保证发布成功。</p>
        <fieldset disabled={busy}><legend>逐条确认此块警告</legend>{basis.warnings.map((warning, index) => <div key={index}>
          {warning.severity === 'warning' ? <label><input type="checkbox" checked={value.selected.includes(index)} onChange={event => setForm({ ...value, selected: event.target.checked ? [...value.selected, index] : value.selected.filter(item => item !== index) })} />{warning.code} · {warning.message} · {warning.locator ?? '无定位'}</label>
            : <p>{warning.severity} · {warning.code} · {warning.message} · {warning.locator ?? '无定位'}</p>}
        </div>)}{!basis.warnings.length && <p>此候选没有返回警告。</p>}</fieldset>
        <label><input type="checkbox" checked={value.confirmed} disabled={busy} onChange={event => setForm({ ...value, confirmed: event.target.checked })} />我已核对这份发布候选、所选人工审核与逐条警告，明确发布这一文本块。</label>
        <button disabled={busy || !warningsConfirmed || !value.confirmed} onClick={() => void state.publish(value.selected)}>明确发布这一文本块</button>
      </section>}
      <section aria-label="原发布命令"><h5>本机原发布命令与历史引用</h5>{state.commands.map(command => <article key={command.command_id}>
        <p>{command.ack ? '原发布 ACK 已保存' : command.rejection ? '服务端拒绝，原发布基准保留' : '发布结果未知，原 key 与完整命令保留'}</p>
        <details><summary>核对原发布命令与基准</summary><p>{command.command_id}</p><pre>{JSON.stringify(command.body, null, 2)}</pre><pre>{JSON.stringify(command.basis, null, 2)}</pre></details>
        {!state.canReplay(command) && <p>无法核对原操作者；旧页面或旧访问代次的命令只读保留，不能用当前会话冒充原 key 回放。</p>}
        <button disabled={busy || !state.canReplay(command)} onClick={() => void state.execute(command)}>显式回放原发布命令 {command.command_id}</button>
        {command.ack && <><p>原发布历史引用：{command.ack.entity} · {command.ack.id} · r{command.ack.revision}</p><code>{command.ack.sha256}</code>
          <button disabled={busy} onClick={() => void state.readCurrent(command)}>另行读取当前引用 {command.ack.id}</button>
          {state.currentRead?.command_id === command.command_id ? <section aria-label="另行读取的当前引用"><p>本次 GET current 的实际结果：{state.currentRead.ref.id} · r{state.currentRead.ref.revision}</p><code>{state.currentRead.ref.sha256}</code><p>此结果独立于原发布 ACK，后续变更需再次读取。</p></section>
            : <p>当前指针尚未在本面板另行读取；原 ACK 不代表对象现在的 current。</p>}</>}
      </article>)}</section>
    </>}
    <button disabled={busy || dirty} onClick={() => void state.refresh()}>重新核验发布权限与本机记录</button>
    <p>网络中断不等于服务端回滚。结果未知时只显式恢复原命令，不自动重发；关闭前保留本页确认选择和已保存的原命令。</p>
  </section>
}
