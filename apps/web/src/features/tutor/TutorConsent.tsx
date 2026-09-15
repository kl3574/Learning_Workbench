import { useEffect, useRef, useState } from 'react'
import type { ConsentProposalView, ProviderConfigView, TutorRunView } from '../../../../../packages/contracts/generated/api-types'
import { providerClient, type ProviderPort } from '../providers/providerClient'
import { useProviderCommands } from '../providers/useProviderCommands'
import { ConsentPreview } from '../providers/ConsentPreview'
import { ProposalDisplay } from '../providers/ConsentSummary'
import { ProviderCommandPanel } from '../providers/ProviderCommandPanel'
import type { ProviderCommand } from '../providers/providerDrafts'
import { getSessionGeneration, subscribeSessionAccess } from '../../api/client'
import { useSyncExternalStore } from 'react'

const job = (value: ProviderCommand) => value.kind === 'preview' ? value.body.job_id : value.kind === 'grant' ? value.proposal.summary.job_id : null
export function TutorConsent({ workspace, run, refresh, settings, port = providerClient }: { workspace: string; run: TutorRunView; refresh: () => void; settings: () => void; port?: ProviderPort }) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  const owner = `${workspace}:${access}:${run.run.id}`, current = useRef(owner); current.current = owner
  const commands = useProviderCommands(workspace, false, port)
  const [configs, setConfigs] = useState<ProviderConfigView[]>([]), [selected, setSelected] = useState(''), [error, setError] = useState(''), [proposal, setProposal] = useState<ConsentProposalView | null>(null)
  const [dirty, setDirty] = useState(false), [confirmed, setConfirmed] = useState(false)
  const [generation, setGeneration] = useState(0)
  const config = configs.find(value => value.id === selected) ?? null
  useEffect(() => {
    let live = true
    void (async () => { try {
      const capabilities = await port.capabilities()
      const values = await Promise.all(capabilities.items.filter(value => value.configured).map(value => port.config(value.provider_id)))
      if (live && current.current === owner && getSessionGeneration() === access) { setConfigs(values); setSelected(old => values.some(value => value.id === old) ? old : values.length === 1 ? values[0].id : ''); setError('') }
    } catch (reason) { if (live && current.current === owner) setError(reason instanceof Error ? reason.message : '提供商配置尚未读回。') } })()
    return () => { live = false }
  }, [owner, port, generation])
  useEffect(() => {
    let live = true; setProposal(null); setConfirmed(false)
    if (run.latest_proposal_id) void port.proposal(run.latest_proposal_id).then(value => {
      if (value.id !== run.latest_proposal_id || value.summary.job_id !== run.run.id) throw new Error('提案与当前任务不匹配。')
      if (live && current.current === owner && getSessionGeneration() === access) setProposal(value)
    }).catch(reason => { if (live && current.current === owner) setError(reason instanceof Error ? reason.message : '授权提案尚未读回。') })
    return () => { live = false }
  }, [owner, run.latest_proposal_id, run.consent_id, port, generation])
  const editor = commands.editor && job(commands.editor) === run.run.id ? commands.editor : null
  const candidates = commands.candidates.filter(value => job(value.value) === run.run.id)
  const ack = editor?.ack
  const observedAck = useRef<unknown>(null)
  useEffect(() => { if (ack && ack !== observedAck.current) { observedAck.current = ack; refresh(); setGeneration(value => value + 1) } }, [ack, refresh])
  const scoped = { ...commands, editor, candidates, remote: editor ? commands.remote : null, competing: editor ? commands.competing : [] }
  return <section className="tutor-consent" aria-label="本次问答授权"><h3>本次问答的明确授权</h3>
    <p>先本地冻结输入，再核对服务端预览；只有明确批准后才允许派发。配置存在不代表模型具备完整输入计量证明。</p>
    <button onClick={settings}>打开提供商设置</button><button disabled={commands.busy} onClick={() => { setGeneration(value => value + 1); refresh() }}>刷新配置与授权状态</button>
    {error && <p role="alert">{error}</p>}
    {!configs.length ? <p>尚未读到配置。可以保存提供商配置后返回刷新；当前任务仍可取消。</p> : <label>本次选择的提供商<select value={selected} disabled={commands.busy || !!editor && !editor.ack || dirty} onChange={event => setSelected(event.target.value)}><option value="">请选择</option>{configs.map(value => <option key={value.id} value={value.id}>{value.id} · {value.model} · r{value.revision}</option>)}</select></label>}
    {!run.consent_id && run.run.status === 'awaiting_approval' && !proposal && <ConsentPreview key={`${run.run.id}:${config?.id ?? ''}:${config?.revision ?? ''}`} task={{ job_id: run.run.id, expected_job_revision: run.job_revision }} config={config} paused={false} disabled={commands.busy || !commands.safe || !!editor && !editor.ack} prepare={commands.begin} onDirty={setDirty} />}
    {proposal && <><ProposalDisplay value={proposal} />{!run.consent_id && !proposal.consent_id && proposal.validity === 'current' && run.latest_proposal_id === proposal.id && <><label><input type="checkbox" checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />我已核对本次冻结范围、目的地、预算与到期时间</label><button disabled={!confirmed || commands.busy || !commands.safe || !!editor && !editor.ack} onClick={() => commands.begin({ kind: 'grant', proposal, body: { proposal_id: proposal.id, proposal_sha256: proposal.proposal_sha256 } })}>准备批准本次授权命令</button></>}</>}
    {run.consent_id && <p>此 Run 已关联授权 {run.consent_id}。继续观察原任务，不重新创建问题或再次授权。</p>}
    <ProviderCommandPanel state={scoped} />
  </section>
}
