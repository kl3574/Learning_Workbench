import { useEffect, useRef, useState } from 'react'
import { getSessionGeneration, request } from '../../api/client'
import type { AssessmentGradingResult, AttemptSnapshot } from '../../../../../packages/contracts/generated/api-types'
import { useGradingResult } from './useGradingResult'
import { GradingSummary } from './GradingSummary'
import { AssessmentReview } from './AssessmentReview'
import type { ReviewBaseline } from './reviewDrafts'
import './grading.css'
const jobLabels = { queued: '评分任务排队中', running: '评分任务进行中', awaiting_approval: '评分任务等待明确批准', completed: '评分任务完成，正在回读结果', failed: '评分任务失败', cancelled: '评分任务已取消' }
export function AssessmentResult({ workspace, snapshot, changed, onState }: { workspace: string; snapshot: AttemptSnapshot; changed: () => void; onState: (state: { dirty: boolean; safe: boolean }) => void }) {
  const grading = useGradingResult(workspace, snapshot, changed)
  const live = useRef(false); useEffect(() => { live.current = true; return () => { live.current = false } }, [])
  const [roleError, setRoleError] = useState(''), [roleBusy, setRoleBusy] = useState(false)
  const history = useRef<{ access: number; attempt: string; results: AssessmentGradingResult[] }>({ access: getSessionGeneration(), attempt: snapshot.id, results: [] })
  if (history.current.access !== getSessionGeneration() || history.current.attempt !== snapshot.id) history.current = { access: getSessionGeneration(), attempt: snapshot.id, results: [] }
  if (grading.result?.attempt_id === snapshot.id && !history.current.results.some(value => value.grading_revision === grading.result!.grading_revision)) history.current.results = [...history.current.results, grading.result]
  const author = async () => { setRoleBusy(true); setRoleError(''); try { await request('POST /api/v1/session/role', { role: 'author' }, { 'Idempotency-Key': crypto.randomUUID() }) } catch (reason) { if (live.current) setRoleError(`作者角色尚未确认：${reason instanceof Error ? reason.message : '操作失败'}`) } finally { if (live.current) setRoleBusy(false) } }
  const fallback: ReviewBaseline | null = !grading.result && ['failed', 'cancelled'].includes(grading.job?.status ?? '') ? { attempt_id: snapshot.id, grading_revision: snapshot.grading_revision ?? 0, status: 'needs_review', items: snapshot.preflight.prior_seen.questions.map(item => ({ question_ref: item.question_ref, max_score: snapshot.questions.find(question => question.id === item.question_ref.id)?.max_score ?? 1, score: null, status: 'needs_review', feedback_markdown: '' })) } : null
  return <section className="assessment-result" aria-label="测试评分与复核"><div className="reader-actions"><button disabled={grading.loading || roleBusy} onClick={grading.refresh}>重新读取评分结果</button></div>{grading.loading && <p role="status">正在读取真实评分状态…</p>}{grading.error && <p role="alert">{grading.error}</p>}{grading.job && <section className="grading-job"><h2>{jobLabels[grading.job.status]}</h2><p>{grading.job.progress.label}；已完成 {grading.job.progress.completed}{grading.job.progress.total == null ? '，总量未知' : ` / ${grading.job.progress.total}`}。</p>{grading.job.error && <p>{grading.job.error.code}：{grading.job.error.message}</p>}<details><summary>核对评分任务</summary><code>{grading.job.id}</code><p>任务修订 {grading.job.revision}；最近更新 {grading.job.updated_at}</p></details><p>任务状态不是分数；未完成项不会显示为零分。</p></section>}{grading.result && <GradingSummary result={grading.result} />}
    {history.current.results.filter(value => value.grading_revision !== grading.result?.grading_revision).map(value => <details key={value.grading_revision}><summary>本页先前读到的评分版本 {value.grading_revision}（非当前结果）</summary><GradingSummary result={value} previous /></details>)}
    {roleError && <p role="alert">{roleError}</p>}{grading.role === 'learner' && <button disabled={roleBusy} onClick={() => void author()}>切换为作者角色以人工复核</button>}
    <AssessmentReview workspace={workspace} assessment={snapshot.assessment_ref} attempt={snapshot.id} result={grading.result} fallback={(snapshot.grading_revision ?? 0) === 0 ? fallback : null} authorized={grading.role === 'author'} onJob={grading.watch} revalidate={grading.refresh} onState={onState} />
  </section>
}
