import { useEffect, useRef } from 'react'
import type { DraftStore } from '../../workbench/DraftStore'
import type { TurnOutboundPort } from './turnOutboundClient'
import type { TurnPanelState } from './CodexTurnPanel'
import type { OutboundFields } from './turnOutboundForms'
import { useCodexOutbound } from './useCodexOutbound'
export function CodexTurnOutboundPanel({ workspace, writeAdmitted, port, store, formStore, onState }: {
 workspace: string; writeAdmitted: boolean; port?: TurnOutboundPort; store?: DraftStore; formStore?: DraftStore; onState?: (state: TurnPanelState) => void
}) {
 const state = useCodexOutbound(workspace, writeAdmitted, port, store, formStore), callback = useRef(onState); callback.current = onState
 useEffect(() => { callback.current?.({ dirty: state.dirty, safe: state.safe, isolated: state.isolated }) }, [state.dirty, state.safe, state.isolated])
 const field = (key: keyof OutboundFields, label: string) => <label>{label}<input value={state.fields[key]} disabled={!state.ready} onChange={e => state.edit({ [key]: e.target.value })} /></label>
 const disabled = !state.ready || state.busy
 return <section aria-label="Codex 外发许可与回合结果"><h3>Codex 外发许可与回合结果</h3>
  <p>先读取真实基准，逐次明确预览、批准和开始。批准不会自动开始；开始 ACK 仅表示排队。默认完整证明或执行器不可用时保持 BLOCKED。</p>
  <button disabled={!workspace || state.busy} onClick={() => void state.refresh()}>读取外发记录与权限</button>
  {state.error && <p role="status">{state.error}</p>}{state.message && <p role="status">{state.message}</p>}
  {state.busy && <p role="status">正在处理本次明确外发操作；新的表单编辑独立保存，不改变原命令。</p>}
  {state.retained > 0 && <p>存在未落盘的外发原事实或表单，已隔离保留。</p>}
  {state.canSave && <button disabled={state.busy} onClick={() => void state.saveMemory()}>仅保存外发本机事实</button>}
  {state.ready && !state.allowed && <p>当前仅开放安全许可撤销。学科摘要、原批准记录和结果已收起，原记录仍保留。</p>}
  {state.ready && <section aria-label="安全许可撤销">
   {field('turn_id', '外发回合 ID')}
   <button disabled={disabled || !state.fields.turn_id} onClick={() => void state.read('control')}>读取外发安全控制</button>
   {state.control && <><pre aria-label="外发安全控制原基准">{JSON.stringify(state.control, null, 2)}</pre>
    <button disabled={!state.can('revoke')} onClick={() => void state.submit('revoke')}>明确撤销本回合外发许可</button>
    <p>撤销只使用安全 control 中真实许可 ID 与 revision。撤销不退款，也不证明已发生的外发停止。</p></>}
  </section>}
  {state.allowed && <section aria-label="外发预算与学科读口">
   {field('preparation_id', '原准备 ID')}{field('session_id', '外发 session ID')}{field('proposal_id', '外发 proposal ID')}{field('consent_id', '外发 consent ID')}
   {field('max_input_tokens', '完整输入 token 硬上限')}{field('max_output_tokens', '输出 token 硬上限')}{field('max_cost_usd', '最高费用 USD（空表示未知上限）')}{field('expires_at', '明确到期 UTC（未来十分钟内）')}
   <p>模型请求固定最多 1 次；搜索固定 0 次。费用为空不会显示成零。必须明确填写两个正整数 token 上限和到期时间，例如 UTC 的 …Z 格式。</p>
   <button disabled={disabled || !state.fields.preparation_id} onClick={() => void state.read('basis')}>读取准备、Job 与 Provider 基准</button>
   {state.basis && <section aria-label="外发准备只读基准"><pre>{JSON.stringify(state.basis, null, 2)}</pre>
    {state.basis.preparation.validity === 'unavailable' && <p>BLOCKED：CODEX_INPUT_PROOF_UNAVAILABLE。当前没有完整输入证明，不能以字符数或 bootstrap ready 代替。</p>}
   </section>}
   <button disabled={!state.can('preview')} onClick={() => void state.submit('preview')}>明确创建完整外发预览</button>
   <button disabled={disabled || !state.fields.proposal_id} onClick={() => void state.read('proposal')}>独立读取当前外发提案</button>
   {state.proposal && <section aria-label="当前外发提案"><p>{state.proposal.id} · {state.proposal.validity}</p><pre>{JSON.stringify(state.proposal, null, 2)}</pre>
    <p>请核对 endpoint、模型、完整请求的计量保证、预算、引用与历史摘要、工具与 runtime、费用估算及 warnings。摘要不替代服务端私有证明。</p></section>}
   <button disabled={!state.can('grant')} onClick={() => void state.submit('grant')}>明确批准当前完整外发提案</button>
   <button disabled={disabled || !state.fields.consent_id} onClick={() => void state.read('consent')}>独立读取当前外发许可</button>
   {state.consent && <section aria-label="当前外发许可"><pre>{JSON.stringify(state.consent, null, 2)}</pre><p>active 不表示尚未消费；dispatch 是独立真实事实。原批准 ACK 保持不变。</p></section>}
   <button disabled={disabled || !state.fields.session_id} onClick={() => void state.read('current')}>独立读取开始 session 基准</button>
   {state.current && <pre aria-label="开始 session 原基准">{JSON.stringify(state.current, null, 2)}</pre>}
   <button disabled={!state.can('start')} onClick={() => void state.submit('start')}>明确开始本回合</button>
   <p>预算、提案过期或证明变化时，先明确取消原未开始 Job，再新准备。不会自动换 key、重试、借用 bootstrap 或普通 Provider 许可。</p>
   <button disabled={disabled || !state.basis || state.basis.preparation.turn_id !== state.fields.turn_id} onClick={() => void state.read('result')}>独立读取本回合结果</button>
   {state.result && <section aria-label="当前未审回合结果"><p>输出 {state.result.output_state} · {state.result.control.execution} · {state.result.control.outcome ?? '尚无终态'}</p>
    {state.result.control.outcome !== 'completed' && <p>回合尚未记为 completed。输出状态仅描述保留的原响应，不表示回合成功或执行可以重试。</p>}
    <pre aria-label="原始未审回答">{state.result.answer_markdown}</pre><pre>{JSON.stringify({ output_sha256: state.result.output_sha256, usage: state.result.usage }, null, 2)}</pre>
    <p>数学审查 NOT_RUN · 来源审查 NOT_RUN · 独立教学审查 NOT_RUN。partial 是部分结果，HTTP 200 或空文本不表示完成；未自动发布或回导。</p></section>}
   {state.forms.map(f => <button key={f.snapshot_id} disabled={state.busy} onClick={() => void state.restore(f)}>恢复外发表单 {f.draft_id} · {f.sequence}</button>)}
  </section>}
  <section aria-label="外发原命令与历史 ACK"><h4>外发原命令与历史 ACK</h4>
   {state.commands.map(c => <article key={c.command_id}><p>{c.kind} · {c.ack ? '原 ACK 已保存，不是当前 GET' : c.error ? `安全错误 ${c.error.status} ${c.error.code ?? ''}；原基准保持` : '结果未知；仅显式原 key 回放'}</p>
    {c.actor_session_id !== state.actor && <p>其他 actor 的安全撤销记录只读，不能接管回放。</p>}
    <details><summary>核对外发原命令 {c.command_id}</summary><pre>{JSON.stringify(c, null, 2)}</pre></details>
    <button disabled={state.busy || !state.canReplay(c)} onClick={() => void state.execute(c)}>显式回放外发原 key {c.command_id}</button>
   </article>)}
  </section>
 </section>
}
