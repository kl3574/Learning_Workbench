import type { TutorContextBinding, TutorRunView, TutorThreadView } from '../../../../../packages/contracts/generated/api-types'
import type { ViewContext } from '../../../../../packages/contracts/generated/types'
import type { TutorSSEEvent } from '../../../../../packages/contracts/generated/tutor-sse'
import { sameValue } from '../providers/providerSchema'

export const terminalRun = (value: TutorRunView) => ['completed', 'failed', 'cancelled'].includes(value.run.status)
export const contextIdentity = (scope: ViewContext, binding: TutorContextBinding) => JSON.stringify([scope.view_kind, [scope.active_ref.entity, scope.active_ref.id, scope.active_ref.revision, scope.active_ref.sha256], scope.attempt_id ?? null, binding.practice?.session_id ?? null])
export function threadMatches(thread: TutorThreadView, scope: ViewContext, binding: TutorContextBinding): boolean {
  return thread.scope.view_kind === scope.view_kind && sameValue(thread.scope.active_ref, scope.active_ref)
    && (thread.scope.attempt_id ?? null) === (scope.attempt_id ?? null)
    && (thread.binding.practice?.session_id ?? null) === (binding.practice?.session_id ?? null)
}
function usage(previous: number | null, next: number | null) {
  if (previous !== null && (next === null || next < previous)) throw new Error('任务累计计量倒退，未采用响应。')
}
export function acceptRun(previous: TutorRunView | null, next: TutorRunView, threadId: string): TutorRunView {
  if (next.run.thread_id !== threadId || previous && (previous.run.id !== next.run.id || next.run.last_seq < previous.run.last_seq)) throw new Error('任务或事件水位不匹配，未采用响应。')
  if (previous) {
    if (!(next.run.answer_markdown ?? '').startsWith(previous.run.answer_markdown ?? '') || !next.result.refusal_markdown.startsWith(previous.result.refusal_markdown)) throw new Error('已接收原文不一致，未以新响应覆盖。')
    if (previous.run.context_snapshot_id && next.run.context_snapshot_id !== previous.run.context_snapshot_id) throw new Error('任务冻结上下文身份改变。')
    if (terminalRun(previous) && (!sameValue(previous.run, next.run) || !sameValue(previous.context, next.context) || !sameValue(previous.result, next.result))) throw new Error('已终结任务发生变化，停止采用响应。')
    usage(previous.result.usage.input_tokens, next.result.usage.input_tokens); usage(previous.result.usage.output_tokens, next.result.usage.output_tokens)
  }
  return next
}
/** Events update only observed text/watermark. A terminal event requires GET;
 * it cannot establish the owner's committed result, receipt or current version. */
export function observeEvent(value: TutorRunView, event: TutorSSEEvent): TutorRunView {
  if (event.run_id !== value.run.id) throw new Error('事件属于另一任务。')
  if (event.seq <= value.run.last_seq) return value
  if (event.seq !== value.run.last_seq + 1 || terminalRun(value)) throw new Error('事件顺序不连续或出现在终态之后。')
  const next = structuredClone(value); next.run.last_seq = event.seq
  if (event.type === 'answer_delta') next.run.answer_markdown = (next.run.answer_markdown ?? '') + event.text
  if (event.type === 'usage') {
    usage(value.result.usage.input_tokens, event.input_tokens); usage(value.result.usage.output_tokens, event.output_tokens)
    next.result.usage.input_tokens = event.input_tokens; next.result.usage.output_tokens = event.output_tokens
  }
  return next
}
