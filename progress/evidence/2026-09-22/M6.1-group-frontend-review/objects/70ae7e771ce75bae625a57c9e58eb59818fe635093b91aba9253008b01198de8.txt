import { useEffect, useMemo, useRef, useState } from 'react'
import type { AuthoringJobReadView, ConsentProposalView, ProviderConfigView } from '../../../../../packages/contracts/generated/api-types'
import { providerClient, type ProviderPort } from '../providers/providerClient'
import { ConsentPreview } from '../providers/ConsentPreview'
import { ProposalDisplay } from '../providers/ConsentSummary'
import { ProviderCommandPanel } from '../providers/ProviderCommandPanel'
import { useProviderCommands } from '../providers/useProviderCommands'
import type { ProviderCommand } from '../providers/providerDrafts'
const commandJob = (command: ProviderCommand) => command.kind === 'preview' ? command.body.job_id : command.kind === 'grant' ? command.proposal.summary.job_id : null
export function AuthoringConsent({ workspace, value, refresh, denied, onState, port = providerClient }: { workspace: string; value: AuthoringJobReadView; refresh: () => void; denied: (reason: unknown) => void; onState: (state: { dirty: boolean; safe: boolean }) => void; port?: ProviderPort }) {
  const callbacks = useRef({ denied, onState, refresh }); callbacks.current = { denied, onState, refresh }
  const wrapped = useMemo<ProviderPort>(() => {
    const guarded = async <T,>(promise: Promise<T>) => { try { return await promise } catch (reason) { callbacks.current.denied(reason); throw reason } }
    return { ...port, config: id => guarded(port.config(id)), preview: (body, key) => guarded(port.preview(body, key)), proposal: id => guarded(port.proposal(id)), grant: (body, key) => guarded(port.grant(body, key)), consents: query => guarded(port.consents(query)) }
  }, [port])
  const commands = useProviderCommands(workspace, false, wrapped)
  const [config, setConfig] = useState<ProviderConfigView | null>(null), [proposal, setProposal] = useState<ConsentProposalView | null>(null), [dirty, setDirty] = useState(false), [confirmed, setConfirmed] = useState(false), [error, setError] = useState(''), [generation, setGeneration] = useState(0)
  const job = value.summary.id, provider = value.request.provider_id
  useEffect(() => {
    let live = true; setConfig(null); setProposal(null); setConfirmed(false); setError('')
    void wrapped.config(provider).then(v => { if (v.id !== provider) throw new Error('配置身份不一致。'); if (live) setConfig(v) }).catch(() => { if (live) setError('当前配置尚未读回，未猜测可调用能力。') })
    if (value.proposal_id) void wrapped.proposal(value.proposal_id).then(v => { if (v.id !== value.proposal_id || v.summary.job_id !== job || v.summary.purpose !== 'authoring' || v.summary.provider_id !== provider) throw new Error('提案与当前例题任务不一致。'); if (live) setProposal(v) }).catch(() => { if (live) setError('授权提案尚未按本次任务核实。') })
    return () => { live = false }
  }, [wrapped, job, provider, value.proposal_id, value.consent_id, generation])
  const editor = commands.editor && commandJob(commands.editor) === job ? commands.editor : null
  const candidates = commands.candidates.filter(v => commandJob(v.value) === job)
  const scoped = { ...commands, editor, candidates, remote: editor ? commands.remote : null, competing: editor ? commands.competing : [] }
  const previousAck = useRef<unknown>(null)
  useEffect(() => { if (editor?.ack && editor.ack !== previousAck.current) { previousAck.current = editor.ack; callbacks.current.refresh() } }, [editor?.ack])
  useEffect(() => { callbacks.current.onState({ dirty: dirty || !!editor && !editor.ack || candidates.length > 0, safe: commands.closeSafe }); return () => callbacks.current.onState({ dirty: false, safe: true }) }, [dirty, editor, candidates.length, commands.closeSafe])
  const group = 'variant' in value
  const awaiting = value.summary.status === 'awaiting_approval' && !value.consent_id
  return <section aria-label={group ? '本次组合草稿模型授权' : '本次例题模型授权'}><h3>另行批准本次模型调用</h3><p>本次 Provider 授权绑定此创作任务；数值运行需要单独批准，草稿仍需审查。</p><button disabled={commands.busy} onClick={() => { setGeneration(v => v + 1); refresh() }}>刷新配置与本任务授权</button>{error && <p role="alert">{error}</p>}
    {awaiting && !proposal && <ConsentPreview task={{ job_id: job, expected_job_revision: value.summary.job_revision }} config={config} paused={false} disabled={!commands.safe || commands.busy || !!editor && !editor.ack} prepare={commands.begin} onDirty={setDirty} />}
    {proposal && <><ProposalDisplay value={proposal} />{awaiting && !proposal.consent_id && proposal.validity === 'current' && <><label><input type="checkbox" checked={confirmed} onChange={e => setConfirmed(e.target.checked)} />{group ? '我已核对本次组合草稿的冻结范围、提供商、预算与到期时间' : '我已核对本次例题的冻结范围、提供商、预算与到期时间'}</label><button disabled={!confirmed || !commands.safe || commands.busy || !!editor && !editor.ack} onClick={() => commands.begin({ kind: 'grant', proposal, body: { proposal_id: proposal.id, proposal_sha256: proposal.proposal_sha256 } })}>{group ? '准备批准组合草稿模型调用' : '准备批准例题模型调用'}</button></>}</>}
    {value.consent_id && <p>此任务已有授权，继续读取同一任务；不要再次创建来继续。</p>}
    <ProviderCommandPanel state={scoped} />
  </section>
}
