import { useEffect, useRef, useState } from 'react'
import type { ProviderConfigView } from '../../../../../packages/contracts/generated/api-types'
import { getSessionGeneration } from '../../api/client'
import type { ProviderPort } from './providerClient'
import { configFields, configWrite, ProviderConfigFields, type ConfigFields } from './ProviderConfigFields'
import { ProviderSecretPanel } from './ProviderSecretPanel'
import { ProviderCommandPanel } from './ProviderCommandPanel'
import { ConsentPreview, type PreparedTaskIdentity } from './ConsentPreview'
import { ConsentHistoryEntry, ProposalDisplay } from './ConsentSummary'
import { useProviderCommands } from './useProviderCommands'
import { useProviderReads } from './useProviderReads'
import { validIdentity } from './providerSchema'
import './providers.css'

export function ProviderSettings({ workspace, paused, port, onState, task = null }: { workspace: string; paused: boolean; port: ProviderPort; onState: (state: { dirty: boolean; safe: boolean }) => void; task?: PreparedTaskIdentity | null }) {
  const [idInput, setIdInput] = useState(''), [activeId, setActiveId] = useState(''), [error, setError] = useState('')
  const [form, setForm] = useState<{ owner: string; id: string; base: ProviderConfigView | null; fields: ConfigFields } | null>(null)
  const [secretState, setSecretState] = useState({ dirty: false, busy: false }), [previewDirty, setPreviewDirty] = useState(false)
  const reads = useProviderReads(workspace, paused, activeId, port), commands = useProviderCommands(workspace, paused, port)
  const callback = useRef(onState); callback.current = onState
  const config = reads.config?.value ?? null, visibleForm = form?.owner === reads.owner && form.id === activeId ? form : null
  const dirty = commands.dirty || !!visibleForm || secretState.dirty || previewDirty
  const safe = commands.closeSafe && !secretState.busy
  const ackId = commands.editor?.ack?.id, notified = useRef<string | null>(null)
  useEffect(() => { callback.current({ dirty, safe }) }, [dirty, safe])
  useEffect(() => {
    const identity = commands.editor?.ack ? `${commands.editor.command_id}:${ackId}` : null
    if (identity && notified.current !== identity) { notified.current = identity; reads.refresh(); if (!paused) reads.refreshHistory() }
  }, [ackId, commands.editor?.command_id, paused])
  useEffect(() => { setForm(null); setIdInput(''); setActiveId(''); setError(''); setSecretState({ dirty: false, busy: false }); setPreviewDirty(false) }, [workspace])
  useEffect(() => {
    const guard = (event: BeforeUnloadEvent) => { if (visibleForm || previewDirty || !safe) { event.preventDefault(); event.returnValue = '' } }
    addEventListener('beforeunload', guard); return () => removeEventListener('beforeunload', guard)
  }, [visibleForm, previewDirty, safe])
  const switchingBlocked = !!visibleForm || secretState.dirty || secretState.busy || commands.busy
  const select = (id: string) => { if (switchingBlocked) { setError('请先准备或明确丢弃当前临时输入，再切换配置。'); return }; if (!validIdentity(id)) { setError('提供商标识须以字母开头，只含字母、数字、下划线或短横线，最多80字符。'); return }; setActiveId(id); setIdInput(id); setError('') }
  const change = (fields: ConfigFields) => { if (reads.config && !secretState.busy) setForm({ owner: reads.owner, id: activeId, base: visibleForm ? visibleForm.base : config, fields }) }
  const prepareConfig = () => {
    if (!visibleForm || secretState.busy || reads.owner !== JSON.stringify([workspace, getSessionGeneration()])) return
    try { if (commands.begin({ kind: 'config', provider_id: activeId, base: visibleForm.base, body: configWrite(visibleForm.fields, visibleForm.base) })) { setForm(null); setError('') } }
    catch (reason) { setError(reason instanceof Error ? reason.message : '配置输入无效。') }
  }
  const proposal = !paused && commands.remote?.kind === 'proposal' ? commands.remote.value : null
  return <section className="provider-settings" aria-label="提供商与授权设置"><h3>提供商与授权</h3><p>设置操作只访问本机服务，不连接、验证密钥或调用模型。配置存在与模型可调度分别显示。</p>
    <section aria-label="提供商能力"><h4>当前能力</h4><button onClick={reads.refresh} disabled={secretState.busy}>重新读取配置与能力</button>{reads.controlError && <p role="alert">{reads.controlError}</p>}{reads.capabilities ? reads.capabilities.items.length ? <ul>{reads.capabilities.items.map(item => <li key={item.provider_id}><button disabled={switchingBlocked} onClick={() => select(item.provider_id)}>{item.provider_id}</button> · 已配置 {item.configured ? '是' : '否'} · 文本 {item.chat ? '可调度' : '不可调度'} · 流 {item.streaming ? '已实现且满足计量准入' : '不可调度'} · 搜索 {item.web_search ? '支持' : '不支持'} · 工具 {item.tool_calls ? '支持' : '不支持'} · 结构化 {item.structured_output ? '支持' : '不支持'}<p>{item.version_evidence}</p></li>)}</ul> : <p>本工作区尚无提供商配置。</p> : <p>能力尚待读回。</p>}</section>
    <div className="provider-actions"><label>提供商标识<input value={idInput} onChange={event => setIdInput(event.target.value)} disabled={switchingBlocked} autoComplete="off" /></label><button disabled={switchingBlocked || !idInput} onClick={() => select(idInput)}>读取或准备新配置</button></div>{error && <p role="alert">{error}</p>}
    {activeId && reads.config && <><p>提供商 {activeId}：{config ? `当前读回 r${config.revision}，${config.secret_present ? '有秘密引用' : '无秘密引用'}` : '本工作区未读到此配置；创建仍由服务端校验身份占用和版本'}</p><ProviderConfigFields value={visibleForm?.fields ?? configFields(config)} change={change} disabled={secretState.busy || commands.busy} /><div className="provider-actions"><button disabled={!visibleForm || !commands.safe || commands.busy || secretState.busy} onClick={prepareConfig}>准备配置保存命令</button>{visibleForm && <button onClick={() => { setForm(null); setError('临时配置输入已明确丢弃。') }}>明确丢弃临时配置输入</button>}</div><ProviderSecretPanel workspace={workspace} config={config} port={port} changed={reads.refresh} onState={setSecretState} /></>}
    {activeId && !reads.config && <p>正在核对配置身份；尚不能编辑或猜测基准。</p>}
    {task ? <ConsentPreview key={`${workspace}:${task.job_id}:${task.expected_job_revision}`} task={task} config={config} paused={paused} disabled={commands.busy || !commands.safe} prepare={commands.begin} onDirty={setPreviewDirty} /> : <section aria-label="授权任务"><h4>发起授权</h4><p>本阶段尚无可发起授权的生成任务。后续由真实生成任务提供准备好的输入；这里不创建任意提示词任务。</p></section>}
    <ProviderCommandPanel state={commands} />
    {proposal && <><ProposalDisplay value={proposal} /><button disabled={commands.busy || !commands.safe || proposal.validity !== 'current' || !!proposal.consent_id || Date.parse(proposal.summary.expires_at) <= Date.now()} onClick={() => commands.begin({ kind: 'grant', proposal, body: { proposal_id: proposal.id, proposal_sha256: proposal.proposal_sha256 } })}>核对范围后准备批准命令</button></>}
    <section aria-label="授权历史"><h3>授权历史与停止控制</h3><p>撤销阻止新的派发，并请求停止在途处理；无法保证撤回内容或退款。</p>{paused ? <p>当前正在核验权限或处于独立测试。授权摘要隐藏，已停止新的摘要读取；此前安全取得的授权标识仍可用于撤销。</p> : <><button disabled={reads.historyBusy} onClick={reads.refreshHistory}>重新读取授权历史</button>{reads.historyError && <p role="alert">{reads.historyError}</p>}{reads.history ? reads.history.items.length ? reads.history.items.map(value => <ConsentHistoryEntry key={value.id} value={value} />) : <p>本工作区尚无授权记录。</p> : <p>授权历史尚待读回。</p>}{reads.history?.next_cursor && <button disabled={reads.historyBusy} onClick={() => void reads.more()}>读取下一页授权</button>}</>}
      {reads.controlRefs.map(value => <div className="provider-actions" key={value.id}><span>停止控制：{value.id} · 已取得基准 r{value.revision}</span><button disabled={commands.busy || !commands.safe} onClick={() => commands.begin({ kind: 'revoke', consent_id: value.id, body: { expected_revision: value.revision } })}>准备撤销 {value.id}</button></div>)}
      {!reads.controlRefs.length && paused && <p>当前页面没有已取得的授权控制标识；不会读取受限摘要来寻找它们。</p>}
    </section>
  </section>
}
