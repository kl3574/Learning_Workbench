import { useEffect, useRef, useState } from 'react'
import { getSessionGeneration } from '../../api/client'
import { readBlock } from '../reader/contentClient'
import type { TutorInputMaterial, TutorMessage, TutorRunView } from '../../../../../packages/contracts/generated/api-types'
export function TutorEvidence({ value, messages }: { value: TutorRunView | null; messages: TutorMessage[] }) {
  return <section className="tutor-evidence" aria-label="问答原文与证据边界">
    {messages.length > 0 && <details><summary>真实线程消息（{messages.length} 条）</summary>{messages.map(message => <article key={message.id}><h4>{message.role === 'user' ? '你的原问题' : `模型${message.channel === 'refusal' ? '拒答' : '输出'} · ${message.status}`}</h4>{message.role === 'assistant' && <p>模型输出／推导尝试，未逐项核验</p>}<pre className="tutor-original">{message.content_markdown}</pre><small>{message.created_at} · {message.id} · 顺序 {message.seq}</small></article>)}</details>}
    {value && <><h3>模型输出／推导尝试，未逐项核验</h3><p>保留模型原文；其中的链接、引用标记与自行声称不代表已核验来源。</p><pre className="tutor-original" aria-label="本次模型回答原文">{value.run.answer_markdown || '尚未收到回答原文。'}</pre>{value.result.refusal_markdown && <><h4>单独保留的拒答原文</h4><pre className="tutor-original">{value.result.refusal_markdown}</pre></>}
      <h3>教材已给出的材料：本次实际输入记录</h3><p>这些记录仅证明输入了什么，不证明答案或推导受到这些材料支持。</p>
      {!value.context ? <p>上下文尚未冻结。</p> : <><p>实际消息总字符 {value.context.snapshot.character_count}（不是 token 计数）；真实纳入历史 {value.context.history_message_ids.length} 条。</p>{value.context.included.length ? value.context.included.map((material, index) => <details key={index}><summary>{material.reference.title} · {material.material_review === 'unreviewed' ? '材料未审' : '真实交互材料，不属于已审教材'}</summary><p>{material.reference.locator}</p><p>{material.reference.ref.entity}/{material.reference.ref.id} · r{material.reference.ref.revision}</p><p>对象 SHA <code>{material.reference.ref.sha256}</code></p><p>正文 SHA <code>{material.body_sha256 ?? '不适用'}</code></p><p>摘录 SHA <code>{material.reference.excerpt_sha256}</code> · {material.reference.character_count} 字符</p><InputOriginal value={material} /></details>) : <p>本次没有纳入教材内容块。</p>}{value.context.omissions.map((item, index) => <p key={index}>未纳入：{item.message}（{item.reason}）</p>)}{value.context.warnings.map((warning, index) => <p key={index}>{warning.message}</p>)}</>}
      <h3>外部来源陈述</h3><p>尚未外部搜索，没有受检外部来源；模型自报链接不作为已核引文。</p>
      <h3>暂时无法核验</h3><p>本阶段没有逐项数学或事实核验。任务完成只表示本机接受了完整非拒答输出；不代表答案正确。</p>
      <details><summary>实际用量与提供商终态</summary><p>输入 token：{value.result.usage.input_tokens ?? '未知'}；输出 token：{value.result.usage.output_tokens ?? '未知'}。累计用量不会把未知写成零。</p>{value.result.provider ? <><p>本地受检结果 {value.result.provider.outcome}；远端事实 {value.result.provider.provider_outcome}；原文状态 {value.result.provider.output_state}。</p><p>回执 {value.result.provider.receipt_id} · <code>{value.result.provider.receipt_sha256}</code></p></> : <p>尚无提供商终态回执，不能推断已调用或远端已停止。</p>}</details>
    </>}
  </section>
}

function InputOriginal({ value }: { value: TutorInputMaterial }) {
  const [text, setText] = useState<string | null>(null), [error, setError] = useState(''), [busy, setBusy] = useState(false)
  const live = useRef(true), identity = JSON.stringify(value), current = useRef(identity); current.current = identity
  useEffect(() => { live.current = true; setText(null); setError(''); return () => { live.current = false } }, [identity])
  const load = async () => {
    if (busy || value.reference.ref.entity !== 'block' || !value.body_sha256) return
    const access = getSessionGeneration(); setBusy(true)
    try {
      const block = await readBlock(value.reference.ref)
      if (block.block.body_sha256 !== value.body_sha256 || block.block.body_sha256 !== value.reference.excerpt_sha256 || Array.from(block.body).length !== value.reference.character_count) throw new Error('当前可读原文未匹配本次输入摘要，未把它显示为输入原文。')
      if (live.current && current.current === identity && getSessionGeneration() === access) setText(block.body)
    } catch (reason) { if (live.current && current.current === identity && getSessionGeneration() === access) setError(reason instanceof Error ? reason.message : '本次输入原文尚未核验。') }
    finally { if (live.current && current.current === identity && getSessionGeneration() === access) setBusy(false) }
  }
  return value.reference.ref.entity === 'block' && value.body_sha256 ? <><button disabled={busy} onClick={() => void load()}>核对本次输入的完整块原文</button>{error && <p role="alert">{error}</p>}{text !== null && <pre className="tutor-original">{text}</pre>}</> : <p>此项为 owner 冻结的交互材料；这里只显示安全摘要，不从其他接口猜测私有正文。</p>
}
