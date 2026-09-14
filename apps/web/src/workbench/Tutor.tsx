import { useState } from 'react'
import type { ViewContext } from './model'
export function Tutor({ context, title, draft, onDraft }: { context: ViewContext | null; title: string; draft: string; onDraft: (text: string) => void }) {
  const [intent, setIntent] = useState('讲解')
  return <div className="tutor"><header className="tutor-heading"><h2>Agent</h2><span className="connection-state">未配置模型</span></header>
    <details className="context-preview" open><summary>当前上下文</summary><p>{context ? title : '尚未选择学习对象'}</p>{context && <><small>修订 {context.active_ref.revision} · 合成示例引用</small><details><summary>查看引用范围</summary><code>{context.active_ref.id}<br />SHA-256 {context.active_ref.sha256}</code><p>只附加当前对象；附加材料 {(context.attached_refs ?? []).length} 项。</p></details>{context.selection && <blockquote>选文：{context.selection.exact_quote}</blockquote>}</>}</details>
    <div className="tutor-messages"><div className="assistant-mark" aria-hidden="true">✦</div><h3>围绕当前内容，一起思考</h3><p>模型尚未配置。配置提供商并明确授权后，可以围绕选中的教材提问。</p><p className="muted">现在可以浏览内容、调整工作台并保留问题草稿。尚未调用模型，也未联网检索。</p></div>
    <form className="composer" onSubmit={event => event.preventDefault()}><div className="intent-tabs" aria-label="教学意图">{['讲解', '提示', '推导', '拓展'].map(name => <button type="button" key={name} aria-pressed={intent === name} onClick={() => setIntent(name)}>{name}</button>)}</div><label className="sr-only" htmlFor="question-draft">问题草稿</label><textarea id="question-draft" value={draft} onChange={event => onDraft(event.target.value)} placeholder="写下问题，草稿按当前对象保留…" rows={4} /><div className="composer-footer"><span>联网：未授权</span><button className="primary-button" disabled title="需要配置模型并授权后才能发送">发送 ↑</button></div><small>草稿仅存本机浏览器，尚未发送。</small></form>
  </div>
}
