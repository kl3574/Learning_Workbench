import { useEffect, useRef, useState } from 'react'
import type { ConsentPreviewWrite, ProviderConfigView } from '../../../../../packages/contracts/generated/api-types'
import { checkedProvider } from './providerSchema'
import type { CommandInput } from './providerDrafts'

export type PreparedTaskIdentity = Pick<ConsentPreviewWrite, 'job_id' | 'expected_job_revision'>
/** The source consumer supplies an existing durable identity. No prompt/job creator. */
export function ConsentPreview({ task, config, paused, disabled, prepare, onDirty }: { task: PreparedTaskIdentity; config: ProviderConfigView | null; paused: boolean; disabled: boolean; prepare: (value: CommandInput) => boolean; onDirty: (dirty: boolean) => void }) {
  const [input, setInput] = useState(''), [output, setOutput] = useState(''), [seconds, setSeconds] = useState('180'), [cost, setCost] = useState(''), [expiry, setExpiry] = useState(''), [error, setError] = useState('')
  const callback = useRef(onDirty); callback.current = onDirty
  useEffect(() => { callback.current(!!input || !!output || !!cost || !!expiry || seconds !== '180') }, [input, output, cost, expiry, seconds])
  const begin = () => {
    if (!config || paused || disabled) return
    try {
      const integer = (value: string) => { if (!/^[1-9][0-9]*$/.test(value) || !Number.isSafeInteger(Number(value))) throw new Error('预算需为正整数。'); return Number(value) }
      const body = checkedProvider<ConsentPreviewWrite>('ConsentPreviewWrite', { ...task, provider_id: config.id, expected_provider_revision: config.revision, budget: { max_input_tokens: integer(input), max_output_tokens: integer(output), max_provider_calls: 1, max_search_calls: 0, max_tool_calls: 0, timeout_seconds: integer(seconds), max_cost_usd: cost.trim() ? Number(cost) : null }, expires_at: expiry })
      if (!Number.isFinite(Date.parse(expiry)) || Date.parse(expiry) <= Date.now()) throw new Error('请填写未来的 UTC 到期时间；服务端仍会再次核验。')
      if (prepare({ kind: 'preview', body })) { setInput(''); setOutput(''); setCost(''); setExpiry(''); setSeconds('180'); setError('') }
    } catch (reason) { setError(reason instanceof Error ? reason.message : '预算或有效期无效。') }
  }
  if (paused) return <p>当前测试策略限制授权预览；未读取或发送任务摘要。</p>
  return <section aria-label="准备授权预览"><h3>为当前任务准备授权预览</h3><p>预览由服务端读取此任务的真实准备输入，当前不会外发。现有任务：{task.job_id} · r{task.expected_job_revision}。</p><fieldset disabled={disabled || !config} className="provider-fields"><legend>本次任务预算</legend><label>最大输入 token<input inputMode="numeric" value={input} onChange={event => setInput(event.target.value)} /></label><label>最大输出 token<input inputMode="numeric" value={output} onChange={event => setOutput(event.target.value)} /></label><label>总超时秒数<input inputMode="numeric" value={seconds} onChange={event => setSeconds(event.target.value)} /></label><label>金额上限 USD（可留空）<input inputMode="decimal" value={cost} onChange={event => setCost(event.target.value)} /></label><label>到期时间 UTC<input value={expiry} onChange={event => setExpiry(event.target.value)} placeholder="YYYY-MM-DDTHH:mm:ssZ" /></label><button onClick={begin}>准备服务端预览命令</button></fieldset>{error && <p role="alert">{error}</p>}</section>
}
