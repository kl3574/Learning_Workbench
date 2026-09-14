import { useEffect, useRef, useState } from 'react'
import { request } from '../../api/client'
import type { AttemptSnapshot, GradeHistoryEntry } from '../../../../../packages/contracts/generated/api-types'
import { useGradingResult } from './useGradingResult'
import { GradingSummary } from './GradingSummary'
import { AssessmentReview } from './AssessmentReview'
import type { ReviewBaseline } from './reviewDrafts'
import './grading.css'
import '../review/review.css'
import { GradingHistory } from '../review/GradingHistory'
import { ReviewMaterialLinks } from '../review/ReviewMaterialLinks'
import type { ReaderTarget } from '../reader/target'
import type { ResponseDraft } from '../../../../../packages/contracts/generated/types'
import type { ReviewAccess } from '../review/reviewContext'
const jobLabels = { queued: '评分任务排队中', running: '评分任务进行中', awaiting_approval: '评分任务等待明确批准', completed: '评分任务完成，正在回读结果', failed: '评分任务失败', cancelled: '评分任务已取消' }
export function AssessmentResult({ workspace, snapshot, changed, onState, review, tabId, questionId, submitted = [], onReviewAccess, reader }: { workspace: string; snapshot: AttemptSnapshot; changed: () => void; onState: (state: { dirty: boolean; safe: boolean }) => void; review?: boolean; tabId?: string; questionId?: string; submitted?: ResponseDraft[]; onReviewAccess?: (value: ReviewAccess) => void; reader?: (target: ReaderTarget, pinned?: boolean) => void }) {
  const grading = useGradingResult(workspace, snapshot, changed)
  const live = useRef(false); useEffect(() => { live.current = true; return () => { live.current = false } }, [])
  const [roleError, setRoleError] = useState(''), [roleBusy, setRoleBusy] = useState(false)
  const [selected, setSelected] = useState<GradeHistoryEntry | null>(null)
  const contextCallback = useRef(onReviewAccess); contextCallback.current = onReviewAccess
  const current = grading.result ?? grading.lastCompletedResult
  const selectedEntry = selected && grading.history.find(value => value.grading_revision === selected.grading_revision)
  const materialGroup = current?.review_materials.find(group => group.question_ref.id === questionId) ?? null
  useEffect(() => {
    const item = selectedEntry?.items.find(value => value.question_ref.id === questionId)
    const question = snapshot.questions.find(value => value.id === questionId)
    const released = grading.result?.grading_revision === selectedEntry?.grading_revision ? grading.result?.items.find(value => value.question_ref.id === questionId) : null
    contextCallback.current?.({ access: grading.access, policy: grading.reviewPolicy, context: review && item && question && selectedEntry ? {
      attempt: snapshot.id, assessment: snapshot.assessment_ref, question: item.question_ref, questionText: question.stem_markdown,
      submitted: submitted.find(value => value.question_id === questionId) ?? null, gradingRevision: selectedEntry.grading_revision,
      historyItem: item, feedback: released?.feedback_markdown ?? null, solution: released?.solution_markdown ?? null,
      solutionReview: grading.result?.solution_reviews.find(value => value.question_id === questionId)?.review_status ?? null,
      materials: grading.reviewPolicy?.allow_materials ? materialGroup?.materials ?? [] : [],
    } : null })
  }, [grading.access, grading.reviewPolicy, grading.result, selectedEntry, questionId, snapshot, submitted, review, materialGroup])
  const author = async () => { setRoleBusy(true); setRoleError(''); try { await request('POST /api/v1/session/role', { role: 'author' }, { 'Idempotency-Key': crypto.randomUUID() }) } catch (reason) { if (live.current) setRoleError(`作者角色尚未确认：${reason instanceof Error ? reason.message : '操作失败'}`) } finally { if (live.current) setRoleBusy(false) } }
  const fallback: ReviewBaseline | null = !grading.result && !grading.lastCompletedResult && ['failed', 'cancelled'].includes(grading.job?.status ?? '') ? { attempt_id: snapshot.id, grading_revision: snapshot.grading_revision ?? 0, status: 'needs_review', items: snapshot.preflight.prior_seen.questions.map(item => ({ question_ref: item.question_ref, max_score: snapshot.questions.find(question => question.id === item.question_ref.id)?.max_score ?? 1, score: null, status: 'needs_review', feedback_markdown: '' })) } : null
  return <section className="assessment-result" aria-label="测试评分与复核"><div className="reader-actions"><button disabled={grading.loading || roleBusy} onClick={grading.refresh}>重新读取评分结果</button></div>{grading.loading && <p role="status">正在读取真实评分状态…</p>}{grading.error && <p role="alert">{grading.error}</p>}{grading.job && <section className="grading-job"><h2>{jobLabels[grading.job.status]}</h2><p>{grading.job.progress.label}；已完成 {grading.job.progress.completed}{grading.job.progress.total == null ? '，总量未知' : ` / ${grading.job.progress.total}`}。</p>{grading.job.error && <p>{grading.job.error.code}：{grading.job.error.message}</p>}<details><summary>核对评分任务</summary><code>{grading.job.id}</code><p>任务修订 {grading.job.revision}；最近更新 {grading.job.updated_at}</p></details><p>任务状态不是分数；未完成项不会显示为零分。</p></section>}{grading.result && <GradingSummary result={grading.result} questionId={review ? questionId : undefined} summaryOnly={review && selectedEntry?.grading_revision !== grading.result.grading_revision} />}{grading.lastCompletedResult && <GradingSummary result={grading.lastCompletedResult} pending questionId={review ? questionId : undefined} summaryOnly={review && selectedEntry?.grading_revision !== grading.lastCompletedResult.grading_revision} />}
    {review && tabId && <><GradingHistory key={`${workspace}:${tabId}:${grading.access}`} workspace={workspace} tabId={tabId} history={grading.history} questionId={questionId ?? null} selected={setSelected} /><ReviewMaterialLinks group={materialGroup} allowed={!!grading.reviewPolicy?.allow_materials} open={reader} /></>}
    {review && <p>人工复核始终基于最近完成的实际评分版本，生成新的评分记录；不会修改上方选中的历史版本。</p>}
    {roleError && <p role="alert">{roleError}</p>}{grading.role === 'learner' && <button disabled={roleBusy} onClick={() => void author()}>切换为作者角色以人工复核</button>}
    <AssessmentReview workspace={workspace} assessment={snapshot.assessment_ref} attempt={snapshot.id} result={grading.result ?? grading.lastCompletedResult} pendingJob={!!grading.job && !['failed', 'cancelled'].includes(grading.job.status)} fallback={(snapshot.grading_revision ?? 0) === 0 ? fallback : null} authorized={grading.role === 'author'} onJob={grading.watch} revalidate={grading.refresh} onState={onState} />
  </section>
}
