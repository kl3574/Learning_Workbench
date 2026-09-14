import { useEffect, useRef, useState } from 'react'
import { ApiError, getSessionGeneration, request } from '../../api/client'
import type { AssessmentGradingResult, RegradeRequest } from '../../../../../packages/contracts/generated/api-types'
import type { ContentRef, JobRef } from '../../../../../packages/contracts/generated/types'
import { sameRef } from '../reader/target'
import { decodeReview, newReview, reviewBaseline, reviewDirty, reviewKey, useReviewJournal, type ReviewBaseline, type ReviewEnvelope, type ReviewField } from './reviewDrafts'
export function reviewRequest(value: ReviewEnvelope): RegradeRequest {
  if (!value.reason.trim() || Array.from(value.reason).length > 4000) throw new Error('请填写 1–4000 字的人工复核理由。')
  const items = value.items.filter(item => item.selected)
  if (!items.length) throw new Error('请明确选择至少一道需要人工复核的题目。')
  return { expected_grading_revision: value.base.grading_revision, reason: value.reason, item_reviews: items.map(item => {
    const text = item.score.trim(), score = Number(text), maximum = value.base.items.find(base => base.question_ref.id === item.question_id)?.max_score
    if (!/^[+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$/.test(text) || !Number.isFinite(score) || score < 0 || maximum == null || score > maximum) throw new Error('每道已选题须填写有限分数，范围为 0 到该题满分；空白不是零分。')
    if (!item.feedback_markdown.trim() || Array.from(item.feedback_markdown).length > 20000) throw new Error('请为每道已选题填写 1–20000 字的复核依据。')
    return { question_id: item.question_id, score, feedback_markdown: item.feedback_markdown }
  }) }
}
export function useGradingReview(workspace: string, assessment: ContentRef, attempt: string, result: AssessmentGradingResult | null, authorized: boolean, onJob: (job: JobRef) => void, fallback: ReviewBaseline | null = null, revalidate: () => void = () => {}) {
  const journal = useReviewJournal(workspace), journalRef = useRef(journal); journalRef.current = journal
  const [editor, setEditor] = useState<ReviewEnvelope | null>(null), [error, setError] = useState(''), [busy, setBusy] = useState(false), [selected, setSelected] = useState(false)
  const live = useRef(false), epoch = useRef(0), current = useRef(editor); current.current = editor
  const callback = useRef(onJob); callback.current = onJob
  useEffect(() => { live.current = true; ++epoch.current; setEditor(null); setSelected(false); setError(''); return () => { live.current = false; ++epoch.current } }, [workspace, attempt, JSON.stringify(assessment)])
  const own = (value: ReviewEnvelope) => {
    if (value.attempt_id !== attempt || !sameRef(value.assessment_ref, assessment)) throw new Error('这份复核草稿的测试实例或修订不同，未替换当前草稿。')
    if (result && (value.base.items.length !== result.items.length || value.base.items.some(item => !result.items.some(remote => sameRef(remote.question_ref, item.question_ref) && remote.max_score === item.max_score)))) throw new Error('复核草稿的冻结题目集合不同，原记录保留。')
    return value
  }
  const records = Object.values(journal.records).filter(record => record.objectId.startsWith(`review:${attempt}:`))
  const candidates: { key: string; text: string; value: ReviewEnvelope }[] = []
  let decodeError = ''
  for (const record of records) for (const text of new Set([record.text, ...record.conflicts.map(item => item.text)])) {
    try { const value = own(decodeReview(text, workspace)); if (reviewDirty(value)) candidates.push({ key: record.objectId, text, value }) }
    catch (reason) { decodeError = reason instanceof Error ? reason.message : '复核草稿无法恢复，原记录保留。' }
  }
  const needsRecovery = !selected && candidates.length > 0
  const key = editor ? reviewKey(attempt, editor.base.grading_revision) : null
  const conflicts = key ? journal.records[key]?.conflicts ?? [] : []
  const persist = (value: ReviewEnvelope) => { current.current = value; setEditor(value); journalRef.current.save(value) }
  const begin = () => { const base = result ?? fallback; if (base && authorized && journal.ready && !needsRecovery && !decodeError) { setSelected(true); setEditor(newReview(workspace, assessment, base)) } }
  const edit = (change: Partial<Pick<ReviewEnvelope, 'reason' | 'items'>>) => { if (!current.current || busy || !authorized) return; persist({ ...current.current, ...change, command_id: `review_command_${crypto.randomUUID()}`, submitted_job: null }); setError('') }
  const item = (id: string, change: Partial<Omit<ReviewField, 'question_id'>>) => { if (current.current) edit({ items: current.current.items.map(value => value.question_id === id ? { ...value, ...change } : value) }) }
  const restore = async (candidate: typeof candidates[number]) => {
    const owner = epoch.current; setBusy(true); setError('')
    try { const value = own(await journalRef.current.resolve(candidate.key, candidate.text)); if (live.current && owner === epoch.current) { current.current = value; setEditor(value); setSelected(true) } }
    catch (reason) { if (live.current && owner === epoch.current) setError(reason instanceof Error ? reason.message : '复核草稿恢复失败，原记录保留。') }
    finally { if (live.current && owner === epoch.current) setBusy(false) }
  }
  const changed = !!editor && !editor.submitted_job && !!result && editor.base.grading_revision !== result.grading_revision
  const rebase = () => { if (!result || !current.current || busy || !authorized) return; persist({ ...current.current, base: reviewBaseline(result), command_id: `review_command_${crypto.randomUUID()}`, submitted_job: null }); setError('已按您的选择采用当前评分版本；请再次核对后明确提交。') }
  const submit = async () => {
    const value = current.current
    if (!value || !authorized || busy || !journal.ready || journal.unsafe || journal.saving || conflicts.length || decodeError) return
    const owner = epoch.current, access = getSessionGeneration(); setBusy(true); setError('')
    try {
      const body = reviewRequest(value)
      const job = await request('POST /api/v1/attempts/{id}/regrade', body, { 'Idempotency-Key': value.command_id }, { path: { id: attempt } })
      if (!live.current || owner !== epoch.current || current.current !== value) return
      persist({ ...value, submitted_job: job })
      if (access === getSessionGeneration()) callback.current(job)
    } catch (reason) { if (live.current && owner === epoch.current) { setError(`人工复核尚未确认：${reason instanceof Error ? reason.message : '提交失败'}。草稿与原命令均保留，未自动重放。`); if (reason instanceof ApiError && [409, 412].includes(reason.status)) revalidate() } }
    finally { if (live.current && owner === epoch.current) setBusy(false) }
  }
  return { editor, error, busy, candidates, needsRecovery, conflicts, decodeError, changed, begin, edit, item, restore, rebase, submit, retryLocal: () => { if (current.current) journalRef.current.save(current.current) }, journal,
    dirty: !!editor && reviewDirty(editor) || needsRecovery || !!conflicts.length, safe: !journal.unsafe }
}
