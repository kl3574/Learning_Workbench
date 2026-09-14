import { useEffect, useRef, useState, useSyncExternalStore } from 'react'
import { getSessionGeneration, request, subscribeSessionAccess } from '../../api/client'
import type { AssessmentGradingResult, AttemptSnapshot, JobSnapshot, GradeHistoryEntry, CurrentReviewPolicy } from '../../../../../packages/contracts/generated/api-types'
import type { JobRef } from '../../../../../packages/contracts/generated/types'
import { validateGrading } from './gradingModel'
import { validateHistory, validateReviewResult } from '../review/reviewModel'
type Reading = { identity: string; access: number; history: GradeHistoryEntry[]; reviewPolicy: CurrentReviewPolicy | null; result: AssessmentGradingResult | null; lastCompletedResult: AssessmentGradingResult | null; job: JobSnapshot | null; role: 'learner' | 'author' | null; error: string; loading: boolean }
export function useGradingResult(workspace: string, snapshot: AttemptSnapshot, completed: () => void) {
  const access = useSyncExternalStore(subscribeSessionAccess, getSessionGeneration, getSessionGeneration)
  const refs = JSON.stringify(snapshot.preflight.prior_seen.questions.map(item => item.question_ref))
  const identity = JSON.stringify([workspace, snapshot.id, snapshot.assessment_ref, refs, snapshot.questions.map(question => [question.id, question.revision, question.max_score ?? 1])])
  const [reading, setReading] = useState<Reading>({ identity, access, history: [], reviewPolicy: null, result: null, lastCompletedResult: null, job: null, role: null, error: '', loading: false })
  const [retry, setRetry] = useState(0), [requestedJob, setRequestedJob] = useState<JobRef | null>(null)
  const epoch = useRef(0), callback = useRef(completed), notified = useRef(''); callback.current = completed
  const eligible = snapshot.status !== 'active' && snapshot.status !== 'abandoned'
  useEffect(() => {
    const owner = ++epoch.current
    let stopped = false, completedReads = 0, timer: ReturnType<typeof setTimeout> | undefined
    const current = () => !stopped && owner === epoch.current && access === getSessionGeneration()
    setReading({ identity, access, history: [], reviewPolicy: null, result: null, lastCompletedResult: null, job: null, role: null, error: '', loading: eligible })
    const checked = (value: AssessmentGradingResult) => {
      const result = validateGrading(value, snapshot.id, snapshot.preflight.prior_seen.questions.map(item => item.question_ref))
      if (result.items.some(item => item.max_score !== (snapshot.questions.find(question => question.id === item.question_ref.id)?.max_score ?? 1))) throw new Error('评分满分与冻结题目不匹配，未显示结果')
      const released = result.items.filter(item => item.solution_markdown != null).map(item => item.question_ref.id)
      if (JSON.stringify(released) !== JSON.stringify(result.solution_reviews.map(item => item.question_id))) throw new Error('已释放解答缺少匹配的原审核状态，未推测审核结论')
      return validateReviewResult(result, snapshot)
    }
    const poll = async () => {
      try {
        const auth = await request('GET /api/v1/session', undefined)
        if (auth.workspace_id !== workspace) throw new Error('工作区已变化，未显示其他工作区的评分。')
        if (!current()) return
        setReading(old => ({ ...old, role: auth.role }))
        const value = await request('GET /api/v1/attempts/{id}/result', undefined, undefined, { path: { id: snapshot.id } })
        if (!current()) return
        if ('grading_revision' in value) {
          const result = checked(value)
          setReading({ identity, access, history: result.history, reviewPolicy: result.current_review_policy, role: auth.role, result, lastCompletedResult: null, job: null, error: '', loading: false })
          const completedIdentity = `${snapshot.id}:${result.grading_revision}`
          if (notified.current !== completedIdentity) { notified.current = completedIdentity; callback.current() }
          return
        }
        const history = validateHistory(value.history, snapshot)
        const lastCompletedResult = value.last_completed_result == null ? null : checked(value.last_completed_result)
        if (JSON.stringify(lastCompletedResult?.history ?? []) !== JSON.stringify(history)) throw new Error('评分任务与最近完成结果的历史不一致。')
        const job = await request('GET /api/v1/jobs/{id}', undefined, undefined, { path: { id: value.id } })
        if (!current()) return
        if (job.id !== value.id || job.workspace_id !== workspace) throw new Error('评分任务不属于当前工作区，未采用这份任务状态。')
        if (job.status === 'completed' && ++completedReads > 2) throw new Error('任务已完成，但对应结果尚不可读；未推测评分成功')
        setReading({ identity, access, history, reviewPolicy: value.current_review_policy, role: auth.role, result: null, lastCompletedResult, job, loading: false, error: job.status === 'failed' ? `评分任务失败：${job.error?.message ?? '请查看任务诊断并明确重试。'}` : job.status === 'cancelled' ? '评分任务已取消，尚无本次评分结果。' : '' })
        if (job.status !== 'failed' && job.status !== 'cancelled' && job.status !== 'awaiting_approval') timer = setTimeout(() => void poll(), 750)
      } catch (reason) { if (current()) setReading(old => ({ ...old, loading: false, error: `评分尚未确认：${reason instanceof Error ? reason.message : '读取失败'}。请重新读取。` })) }
    }
    if (eligible) void poll()
    return () => { stopped = true; ++epoch.current; clearTimeout(timer) }
  }, [identity, eligible, access, retry, requestedJob?.id])
  const visible = reading.identity === identity && reading.access === access && eligible ? reading : { identity, access, history: [], reviewPolicy: null, result: null, lastCompletedResult: null, job: null, role: null, error: '', loading: true }
  return { ...visible, refresh: () => setRetry(value => value + 1), watch: (job: JobRef) => setRequestedJob(job) }
}
