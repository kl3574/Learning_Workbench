import { useEffect, useRef, useState } from 'react'
import type { AssessmentSummary } from '../../../../../packages/contracts/generated/api-types'
import type { PolicySnapshot, ContentRef } from '../../../../../packages/contracts/generated/types'
import { request } from '../../api/client'
import { readLocal, writeLocal, removeLocal } from '../../workbench/uiCache'
import { readAssessment, validateAttempt } from './assessmentClient'
import { modeLabels, PreflightFacts } from './PreflightFacts'
import type { AssessmentTarget } from './target'
export function AssessmentPreview({ workspace, target, open, loaded, course }: { workspace: string; target: AssessmentTarget; open: (target: AssessmentTarget, pinned?: boolean) => void; loaded: (title: string, resolved: boolean) => void; course: (ref: ContentRef) => void }) {
  const [summary, setSummary] = useState<AssessmentSummary | null>(null), [error, setError] = useState(''), [busy, setBusy] = useState(false), [retry, setRetry] = useState(0)
  const [mode, setMode] = useState<PolicySnapshot['mode']>('independent'), [acknowledged, setAcknowledged] = useState(false)
  const epoch = useRef(0), live = useRef(false), callbacks = useRef({ open, loaded }); callbacks.current = { open, loaded }
  useEffect(() => { live.current = true; const owner = ++epoch.current; setSummary(null); setError(''); callbacks.current.loaded('', false); void readAssessment(target).then(value => { if (live.current && owner === epoch.current) { setSummary(value); setMode(value.allowed_modes[0]); callbacks.current.loaded(value.title, true) } }).catch(reason => { if (live.current && owner === epoch.current) setError((reason as Error).message) }); return () => { live.current = false; ++epoch.current } }, [workspace, JSON.stringify(target), retry])
  const start = async () => {
    if (!summary || !summary.preflight.startable || !acknowledged || busy || summary.time_limit_seconds !== null) return
    const owner = epoch.current; setBusy(true); setError('')
    const storageKey = `learning-workbench.${workspace}.assessment-create.${target.assessment_ref.id}.${target.assessment_ref.revision}.${target.assessment_ref.sha256}.${mode}`
    let key = readLocal(storageKey)
    if (!key) { key = crypto.randomUUID(); if (!writeLocal(storageKey, key)) { setError('创建命令尚未安全保留，未开始测试。请恢复本机缓存后重试。'); setBusy(false); return } }
    try {
      const snapshot = validateAttempt(await request('POST /api/v1/assessments/{id}/attempts', { assessment_ref: target.assessment_ref, mode }, { 'Idempotency-Key': key }, { path: { id: target.assessment_ref.id } }), target, workspace)
      if (live.current && owner === epoch.current) { callbacks.current.open({ ...target, attempt_id: snapshot.id }, true); removeLocal(storageKey) }
    } catch (reason) { if (live.current && owner === epoch.current) setError(`开始测试未确认：${(reason as Error).message}。保留同一命令，重试不会另建实例。`) }
    finally { if (live.current && owner === epoch.current) setBusy(false) }
  }
  return <div className="reader-scroll"><article className="reader-content assessment-content"><div className="eyebrow">测试 · 开始前核对</div><h1>{summary?.title ?? '精确测试引用'}</h1>{error && <p role="alert">{error}</p>}{!summary && <button onClick={() => setRetry(value => value + 1)}>重试测试预览</button>}{summary && <><PreflightFacts facts={summary.preflight} course={course} /><fieldset disabled={busy}><legend>本次测试模式</legend>{summary.allowed_modes.map(value => <label className="assessment-mode" key={value}><input type="radio" name="assessment-mode" checked={mode === value} onChange={() => { setMode(value); setAcknowledged(false) }} />{modeLabels[value]}</label>)}</fieldset><p>{mode === 'independent' ? '进行中将限制本工作区的教材、笔记、学科帮助、联网与答案访问。Agent 只提供固定操作帮助；随时可明确放弃。' : mode === 'open_book' ? '可以阅读获准材料；Agent 仅提供操作帮助，禁止联网与提前查看答案。' : '可以使用获准材料和学科帮助；联网仍须授权，标准答案不会在提交前自动释放。'}</p><p>这些是应用内限制，无法阻止使用应用外的文件或工具。目前仅支持不计时测试；提交后执行评分，待复核项没有确定分数。独立模式本身不等于已通过独立能力验证。</p>{summary.time_limit_seconds !== null && <p role="alert">此测试要求时限 {summary.time_limit_seconds} 秒。目前仅支持不计时测试，因此不能开始此计时测试。</p>}<label className="assessment-ack"><input type="checkbox" checked={acknowledged} onChange={event => setAcknowledged(event.target.checked)} />我已核对内容状态与模式，确认开始未评分测试</label><button className="primary-button" disabled={busy || !acknowledged || !summary.preflight.startable || summary.time_limit_seconds !== null} onClick={() => void start()}>{busy ? '正在创建冻结测试…' : '明确开始本次测试'}</button><details><summary>准确测试引用</summary><code>{target.assessment_ref.id} · r{target.assessment_ref.revision}<br />SHA-256 {target.assessment_ref.sha256}</code></details></>}</article></div>
}
