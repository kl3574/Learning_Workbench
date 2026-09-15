import type { ContentRef, RecommendationPage, RecommendationView } from '../../../../../packages/contracts/generated/api-types'
import { exactRef, assessmentHref, type AssessmentTarget } from '../assessment/target'
import { practiceHref, type PracticeTarget } from '../practice/target'
import { readerHref, refKey, sameRef, type ReaderTarget } from '../reader/target'
export type RecommendationNavigation = RecommendationView['navigation_options'][number]
export type RecommendationReason = RecommendationView['reason_codes'][number]
export const reasonLabels: Record<RecommendationReason, string> = { prerequisite_gap: '先修概念缺少证据', assessment_error: '确定性评分中的错误', review_due: '到达复习提醒时间', next_route_step: '路线中的下一任务', user_goal: '与你记录的目标有关', read_without_practice: '已有阅读记录，尚缺练习', practice_without_independent: '已有练习参与，尚缺独立证据' }
export const actionLabels: Record<RecommendationView['action'], string> = { read: '阅读', practice: '练习', test: '测试', review: '复习', inspect_source: '查看来源' }
export const decisionLabels: Record<RecommendationView['decision'], string> = { pending: '尚未决定', accepted: '已接受', dismissed: '已拒绝' }
export const projectionLabels: Record<RecommendationPage['projection_state'], string> = { missing: '尚无已生成的本地推荐', pending_refresh: '已登记更新，尚未完成', ready: '本批推荐依据已核验', stale: '历史推荐依据已过期', failed: '推荐投影处理失败' }
export type RecommendationTarget = { kind: 'reader'; value: ReaderTarget } | { kind: 'practice'; value: PracticeTarget } | { kind: 'assessment'; value: AssessmentTarget }
export function navigationTarget(option: RecommendationNavigation): RecommendationTarget {
  if (option.kind === 'reader') return { kind: 'reader', value: { course: option.course_ref, lesson: option.lesson_ref, ...(option.block_ref ? { block: option.block_ref } : {}) } }
  if (option.kind === 'practice') return { kind: 'practice', value: { course_ref: option.course_ref, lesson_ref: option.lesson_ref, practice_ref: option.practice_ref } }
  return { kind: 'assessment', value: { assessment_ref: option.assessment_ref, ...(option.course_ref ? { course_ref: option.course_ref } : {}) } }
}
export function navigationHref(option: RecommendationNavigation): string {
  const target = navigationTarget(option)
  return target.kind === 'reader' ? readerHref(target.value) : target.kind === 'practice' ? practiceHref(target.value) : assessmentHref(target.value)
}
export function navigationLabel(option: RecommendationNavigation): string {
  return option.course_ref ? `从教材 ${option.course_ref.id} · r${option.course_ref.revision}${option.kind === 'assessment' ? '' : ` / 小节 ${option.lesson_ref.id} · r${option.lesson_ref.revision}`} 打开${option.kind === 'reader' ? '材料' : option.kind === 'practice' ? '练习' : '测试'}` : '打开此精确测试（没有父教材）'
}
export function navigationRefs(option: RecommendationNavigation): ContentRef[] {
  return option.kind === 'reader' ? [option.course_ref, option.lesson_ref, ...(option.block_ref ? [option.block_ref] : [])] : option.kind === 'practice' ? [option.course_ref, option.lesson_ref, option.practice_ref] : [...(option.course_ref ? [option.course_ref] : []), option.assessment_ref]
}
export function validateNavigation(item: RecommendationView): RecommendationView {
  if (!item.navigation_options.length) throw new Error('推荐没有真实导航父链，未构造可点击链接。')
  const seen = new Set<string>()
  for (const option of item.navigation_options) {
    let target: ContentRef
    if (option.kind === 'reader') {
      if (!exactRef(option.course_ref, 'course') || !exactRef(option.lesson_ref, 'lesson') || option.block_ref !== null && !exactRef(option.block_ref, 'block')) throw new Error('推荐教材导航的精确引用无效。')
      target = option.block_ref ?? option.lesson_ref
    } else if (option.kind === 'practice') {
      if (!exactRef(option.course_ref, 'course') || !exactRef(option.lesson_ref, 'lesson') || !exactRef(option.practice_ref, 'practice_set')) throw new Error('推荐练习导航的精确引用无效。')
      target = option.practice_ref
    } else {
      if (option.kind !== 'assessment' || !exactRef(option.assessment_ref, 'assessment') || option.course_ref !== null && !exactRef(option.course_ref, 'course')) throw new Error('推荐测试导航的精确引用无效。')
      target = option.assessment_ref
    }
    if (!sameRef(target, item.target_ref)) throw new Error('推荐导航与原精确目标不同，未猜测最新版本。')
    const key = navigationRefs(option).map(refKey).join('|')
    if (seen.has(key)) throw new Error('推荐返回重复父链，未合并来源身份。')
    seen.add(key)
  }
  if (!item.reason_codes.length || new Set(item.reason_codes).size !== item.reason_codes.length || item.reason_codes.some(code => !(code in reasonLabels))) throw new Error('推荐原因不符合当前闭合契约。')
  return item
}
export function validatePage(page: RecommendationPage): RecommendationPage {
  if (page.snapshot_id === null && (page.items.length || page.generated_at !== null) || page.projection_state !== 'ready' && page.items.some(item => item.staleness !== 'stale')) throw new Error('推荐批次状态与实际快照不一致。')
  if (new Set(page.items.map(item => item.id)).size !== page.items.length) throw new Error('推荐批次包含重复身份。')
  page.items.forEach(validateNavigation)
  return page
}
