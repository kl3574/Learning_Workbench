import type { AssessmentGradingResult, AttemptSnapshot, GradeHistoryEntry, GradeHistoryItem } from '../../../../../packages/contracts/generated/api-types'
import { sameRef, refKey } from '../reader/target'

export const eligibilityReasons: Record<GradeHistoryItem['reason_codes'][number], string> = {
  MODE_OPEN_BOOK: '开卷模式：保留学习记录，不作为独立测试证据。',
  MODE_ASSISTED: '辅助模式允许学科帮助；模式标签不表示实际使用过帮助。',
  HELP_BEFORE_SUBMIT: '交卷前存在相关帮助记录，不作为未经帮助的新颖证据。',
  ANSWER_UNREVIEWED: '冻结的参考答案尚未审核；人工给分不会自动批准参考答案。',
  GRADE_UNRESOLVED: '本题尚待复核，分数为空，不记作零分。',
  CONCEPT_MAPPING_UNRESOLVED: '尚未核验完整的精确概念映射。',
  PREVIOUSLY_SEEN: '此前见过相关题目或答案，不能作为首次未见题的证据。',
  PRIOR_SEEN_UNKNOWN: '此前是否见过的记录不完整，不能推断为首次未见。',
  HELP_HISTORY_UNKNOWN: '帮助记录不足以确认独立完成条件。',
  SOURCE_NOT_TRUSTED: '证据来源尚未通过所需的可信性校验。',
  HISTORY_PREREQUISITES_NOT_FROZEN: '历史交卷没有事前冻结资格条件；保留成绩，但后续复核不能补造当时的条件。',
}
export function validateHistory(history: GradeHistoryEntry[], snapshot: AttemptSnapshot) {
  const refs = snapshot.preflight.prior_seen.questions.map(item => item.question_ref)
  let previous = 0
  for (const entry of history) {
    if (!Number.isSafeInteger(entry.grading_revision) || entry.grading_revision <= previous || entry.items.length !== refs.length) throw new Error('评分历史版本或完整题序不一致，未显示混合历史。')
    previous = entry.grading_revision
    for (const [index, item] of entry.items.entries()) {
      if (!sameRef(item.question_ref, refs[index]) || item.max_score !== (snapshot.questions[index]?.max_score ?? 1) || !Number.isFinite(item.max_score) || item.max_score <= 0 || item.status === 'needs_review' && item.score !== null || item.status === 'graded' && (item.score === null || !Number.isFinite(item.score) || item.score < 0 || item.score > item.max_score)) throw new Error('历史分数与冻结题目不一致，未采用这份摘要。')
      if (item.concept_refs.some(ref => ref.entity !== 'concept' || !snapshot.preflight.target_concept_refs.some(frozen => sameRef(frozen, ref))) || new Set(item.concept_refs.map(refKey)).size !== item.concept_refs.length) throw new Error('历史概念不属于本次冻结范围，未猜测映射。')
      if (item.reason_codes.some(code => !(code in eligibilityReasons)) || new Set(item.evidence_ids).size !== item.evidence_ids.length || item.eligible && (item.status !== 'graded' || !item.concept_refs.length || item.reason_codes.length || item.independence !== 'independent' || item.freshness !== 'novel')) throw new Error('证据资格摘要内部不一致，未推断资格。')
      if (entry.qualification_basis === 'history_not_frozen' && (item.eligible || !item.reason_codes.includes('HISTORY_PREREQUISITES_NOT_FROZEN'))) throw new Error('历史成绩缺少原始资格条件标识，未采用这份摘要。')
    }
    if ((entry.items.some(item => item.status === 'needs_review') ? 'needs_review' : 'graded') !== entry.status) throw new Error('历史汇总与逐题状态不一致。')
  }
  return history
}
export function validateReviewResult(value: AssessmentGradingResult, snapshot: AttemptSnapshot) {
  const history = validateHistory(value.history, snapshot), last = history.at(-1)
  if (!last || last.grading_revision !== value.grading_revision || last.status !== value.status || last.finalized_at !== value.finalized_at || last.grading_rules_version !== value.grading_rules_version || last.items.some((item, index) => !sameRef(item.question_ref, value.items[index]?.question_ref) || item.score !== value.items[index]?.score || item.max_score !== value.items[index]?.max_score || item.status !== value.items[index]?.status)) throw new Error('最新评分与服务端历史摘要不匹配，未替换当前结果。')
  if (value.review_materials.length !== value.items.length) throw new Error('对应教材没有完整绑定到冻结题目。')
  for (const [index, group] of value.review_materials.entries()) {
    if (!sameRef(group.question_ref, value.items[index]?.question_ref)) throw new Error('对应教材指向其他题目，未显示这些链接。')
    const concepts = last.items[index].concept_refs
    for (const item of group.materials) {
      if (item.course_ref.entity !== 'course' || !snapshot.preflight.course_refs.some(ref => sameRef(ref, item.course_ref)) || item.lesson_ref.entity !== 'lesson' || item.block_ref.entity !== 'block' || !item.concept_refs.length || item.concept_refs.some(ref => !concepts.some(concept => sameRef(ref, concept)))) throw new Error('教材链接与冻结课程或概念不匹配，未猜测当前版本。')
    }
  }
  return value
}
export const scoreText = (item: Pick<GradeHistoryItem, 'score' | 'max_score' | 'status'>) => item.status === 'needs_review' ? '待复核 · 分数为空' : `${item.score} / ${item.max_score}`
