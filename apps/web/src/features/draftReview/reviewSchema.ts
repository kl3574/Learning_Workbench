import type { DraftCandidate, JobSnapshot, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
import { checkedProvider, sameValue } from '../providers/providerSchema'

export function checkedReview<T>(name: string, value: unknown): T {
  try { return checkedProvider<T>(name, value) }
  catch { throw new Error('审核记录不符合当前契约，原命令与候选保留。') }
}
export function reviewReceipt(value: unknown, id: string, candidate?: DraftCandidate): StoredReviewReceipt {
  const receipt = checkedReview<StoredReviewReceipt>('StoredReviewReceipt', value)
  if (receipt.id !== id || !Number.isSafeInteger(receipt.revision) || receipt.revision! < 1
      || receipt.independent_pedagogy !== 'NOT_RUN'
      || candidate && !sameValue(receipt.candidate, candidate)) throw new Error('审核回执与准确候选、修订或尚未执行的教学验收边界不一致。')
  return receipt
}
export function reviewJob(value: unknown, workspace: string, id: string): JobSnapshot {
  const job = checkedReview<JobSnapshot>('JobSnapshot', value)
  if (job.id !== id || job.workspace_id !== workspace || job.kind !== 'draft_review'
      || job.result_refs.length || job.warnings.length) throw new Error('审核任务控制记录身份不一致。')
  return job
}
