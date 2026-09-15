import { ConsentSummary } from './ConsentSummary'
import type { useProviderCommands } from './useProviderCommands'
import { ConfigSnapshot } from './ProviderConfigFields'
const labels = { config: '配置保存', preview: '授权预览', grant: '批准授权', revoke: '撤销授权' }
export function ProviderCommandPanel({ state }: { state: ReturnType<typeof useProviderCommands> }) {
  const command = state.editor, blocked = state.busy || !state.safe || !!state.competing.length || state.journal.saving
  return <section aria-label="配置与授权命令"><h3>配置与授权命令</h3><p role="status">{state.busy ? '正在核对本机服务…' : state.journal.saving ? '原命令本机保存中…' : state.closeSafe ? '无秘密候选已安全保留在本机' : '本机候选尚未安全保存，请保持本页打开'}</p>
    {[state.error, state.decodeError, state.journal.error].filter(Boolean).map((message, index) => <p role="alert" key={index}>{message}</p>)}
    {state.journal.error && <button onClick={state.retryLocal}>重试本机命令保存</button>}
    {state.candidates.length > 0 && <details open><summary>本机未确认候选</summary>{state.candidates.map((candidate, index) => <div key={candidate.text}><span>{labels[candidate.value.kind]}候选 {index + 1}</span><button disabled={state.busy || !state.safe || state.journal.saving} onClick={() => void state.restore(candidate)}>恢复原命令 {index + 1}</button></div>)}</details>}
    {command && <section aria-label="当前原命令"><h4>{labels[command.kind]}</h4><p>原 key：<code>{command.command_id}</code></p>
      {command.kind === 'config' && <section aria-label="配置三方比较" className="provider-comparison"><article><h5>原始基准 · r{command.base?.revision ?? 0}</h5>{command.base ? <ConfigSnapshot value={command.base} /> : <p>新配置尚不存在</p>}</article><article><h5>本页候选</h5><ConfigSnapshot value={command.body} /></article><article><h5>当前服务端</h5>{state.remote?.kind === 'config' ? <><p>r{state.remote.value.revision}</p><ConfigSnapshot value={state.remote.value} /></> : <p>尚未另行读回</p>}</article></section>}
      {command.kind === 'preview' && <p>真实任务 {command.body.job_id} · 原修订 {command.body.expected_job_revision}；提供商 {command.body.provider_id} · 原修订 {command.body.expected_provider_revision}；到期 {command.body.expires_at}。尚未批准，也不会外发。</p>}
      {command.kind === 'grant' && <><p>仅批准原提案 {command.body.proposal_id} / <code>{command.body.proposal_sha256}</code>；批准不同步调用模型。</p><ConsentSummary value={command.proposal.summary} /></>}
      {command.kind === 'revoke' && <p>授权 {command.consent_id} · 原始基准 r{command.body.expected_revision}；本页候选：撤销。{state.remote?.kind === 'consent' ? `当前服务端 r${state.remote.value.revision} / ${state.remote.value.status}` : '当前摘要未读回或受策略限制；不会猜测当前版本。'}</p>}
      {command.ack && <p role="status">原命令已确认{command.kind === 'preview' ? ` · 提案 ${command.ack.id}` : ` · 修订 ${command.ack.revision}`}。此回执保留当时事实，不替代当前状态。</p>}
      {state.remote?.kind === 'proposal' && <p>当前提案 {state.remote.value.validity}{state.remote.value.consent_id ? ` · 已关联授权 ${state.remote.value.consent_id}` : ''}。</p>}
      <div className="provider-actions"><button disabled={blocked || !!command.ack || state.rejected} onClick={() => void state.send()}>{state.sealed ? '重试原配置或授权命令' : `确认发送${labels[command.kind]}`}</button><button disabled={state.busy} onClick={() => void state.refresh()}>另行读取当前状态</button>{(state.rejected || command.ack) && ['config', 'revoke'].includes(command.kind) && <button disabled={blocked || !state.remote} onClick={state.correct}>比较后采用当前版本，准备更正</button>}<button disabled={!state.closeSafe} onClick={state.retain}>保留候选，返回设置</button></div>
      {!!state.competing.length && <p role="alert">其他页面也保留了此对象的候选。请先从本机候选中明确选择，不会静默覆盖。</p>}
    </section>}
  </section>
}
