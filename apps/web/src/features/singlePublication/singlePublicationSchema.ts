import type { AuthoringDraftView, AuthoringJobView, ContentRef, DraftCandidate, NumericCheckView, StoredReviewReceipt, Warning } from '../../../../../packages/contracts/generated/api-types'
import { checkedAuthoring } from '../authoring/authoringCommands'
import { checkedPublication, publicationRef } from '../draftPublication/publicationSchema'
import { exactObject, sameValue } from '../providers/providerSchema'
import { reviewReceipt } from '../draftReview/reviewSchema'
import { digest } from '../retrieval/retrievalModel'

export type SinglePublicationBasis = { owner: 'authoring_single'; snapshot: AuthoringDraftView; candidate: AuthoringDraftView['candidate'];
  generation: AuthoringJobView; target: { entity: 'block'; revision: 1; current: null }; review: StoredReviewReceipt; checks: NumericCheckView[]; warnings: Warning[] }
export class SinglePublicationUnavailable extends Error {}
const numericUnavailable = (verdict?: string): never => { throw new SinglePublicationUnavailable(verdict === 'BLOCKED'
  ? '当前最新数值结果为 BLOCKED，尚无本候选完整实际 PASS，不能准备发布。请读取实际运行结果；满足条件后须新的 Review 与明确人类决定。'
  : '当前最新数值检查尚无完整实际 PASS，不能准备发布；不能跳过较新检查选用历史 PASS。满足条件后须新的 Review 与明确人类决定。') }
const invalid = (): never => { throw new Error('单块生成例题的候选、原正文、数值记录或所选人工审核不一致。') }
export function singleSnapshot(raw: unknown, candidate?: DraftCandidate): AuthoringDraftView {
  const value = checkedAuthoring<AuthoringDraftView>('AuthoringDraftView', raw)
  if (value.owner !== 'authoring' || value.candidate.entity !== 'block' || value.candidate.draft_revision !== 1
      || value.body_sha256 !== digest(value.payload.body_markdown) || candidate && !sameValue(value.candidate, candidate)
      || new Set(value.numeric_check_ids).size !== value.numeric_check_ids.length) invalid()
  return value
}
export function singlePublishedRef(raw: unknown): ContentRef {
  const value = publicationRef(raw)
  if (value.revision !== 1) invalid()
  return value
}
function numeric(raw: unknown, id: string, snapshot: AuthoringDraftView): NumericCheckView {
  const value = checkedAuthoring<NumericCheckView>('NumericCheckView', raw)
  if (value.id !== id || !sameValue(value.candidate, snapshot.candidate) || !sameValue(value.plan, snapshot.payload.numeric_plan)
      || value.revision !== (value.decision === 'pending' ? 1 : 2)
      || (value.job !== null) !== (value.decision === 'approve_once') || (value.job_revision !== null) !== (value.job !== null)) invalid()
  return value
}
export function checkedSingleBasis(value: SinglePublicationBasis): SinglePublicationBasis {
  if (!exactObject(value, ['owner', 'snapshot', 'candidate', 'generation', 'target', 'review', 'checks', 'warnings']) || value.owner !== 'authoring_single'
      || !exactObject(value.target, ['entity', 'revision', 'current']) || !sameValue(value.target, { entity: 'block', revision: 1, current: null })) invalid()
  const snapshot = singleSnapshot(value.snapshot, value.candidate)
  const generation = checkedAuthoring<AuthoringJobView>('AuthoringJobView', value.generation)
  if (generation.summary.id !== snapshot.source_job_id || generation.summary.status !== 'completed'
      || !sameValue(generation.summary.candidate, snapshot.candidate)) invalid()
  if (snapshot.state !== 'draft' || snapshot.published_ref !== null || !Array.isArray(value.checks)
      || value.checks.length !== snapshot.numeric_check_ids.length) invalid()
  if (!value.checks.length) numericUnavailable()
  const checks = value.checks.map((check, index) => numeric(check, snapshot.numeric_check_ids[index], snapshot))
  const latest = checks.at(-1)!, result = latest.result
  if (latest.decision !== 'approve_once' || latest.job?.status !== 'completed' || !result || result.job_id !== latest.job.id
      || result.operation_sha256 !== latest.operation_sha256 || result.outcome !== 'passed' || result.verdict !== 'PASS'
      || !result.started_at || result.exit_code !== 0 || !result.output_sha256
      || !sameValue(result.assertions.map(item => item.id), latest.plan.assertions.map(item => item.id))
      || result.assertions.some(item => !item.passed || item.error_code !== null || item.actual === null)) numericUnavailable(result?.verdict)
  const review = reviewReceipt(value.review, value.review?.id, snapshot.candidate)
  if (review.structural !== 'PASS' || review.mathematical !== 'APPROVED'
      || !['APPROVED', 'NOT_APPLICABLE'].includes(review.sources) || review.sources === 'NOT_APPLICABLE' && (snapshot.payload.declared_source_refs.length || generation.preparation.materials.length)
      || !review.decision_reason.trim() || review.revision! < 2) invalid()
  // Draft warnings describe the old generation stage. Admission consumes the
  // original context warnings plus numerical records, not that display message.
  const warnings = [...generation.preparation.warnings, ...checks.flatMap(check => check.warnings)]
  if (!sameValue(value.warnings, warnings)) invalid()
  warnings.forEach(warning => checkedPublication('Warning', warning))
  return structuredClone(value)
}
export function prepareSingleBasis(snapshot: AuthoringDraftView, generation: AuthoringJobView, review: StoredReviewReceipt, checks: NumericCheckView[]): SinglePublicationBasis {
  return checkedSingleBasis({ owner: 'authoring_single', snapshot, generation, candidate: snapshot.candidate, target: { entity: 'block', revision: 1, current: null },
    review, checks, warnings: [...generation.preparation.warnings, ...checks.flatMap(check => check.warnings)] })
}
export function singleAcknowledgedCodes(basis: SinglePublicationBasis, selected: number[]): string[] {
  if (new Set(selected).size !== selected.length || selected.some(index => !Number.isSafeInteger(index) || basis.warnings[index]?.severity !== 'warning')
      || basis.warnings.some((warning, index) => warning.severity === 'error' || warning.severity === 'warning' && !selected.includes(index))) invalid()
  return [...new Set(basis.warnings.filter(warning => warning.severity === 'warning').map(warning => warning.code))]
}
export const matchesSingleCandidate = (draft: AuthoringDraftView, candidate: DraftCandidate) => sameValue(draft.candidate, candidate)
