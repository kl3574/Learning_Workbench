import type { DraftCandidate, StoredReviewReceipt } from '../../../../../packages/contracts/generated/api-types'
import type { CreateFormValue, DecisionFormValue } from './ReviewForms'

export type ReviewFormOwner = 'import' | 'authoring_single' | 'authoring_group' | 'edit' | 'restore'
export type ReviewPanelState = { dirty: boolean; safe: boolean; isolated: boolean; discardForms: () => void }
export const emptyReviewPanelState: ReviewPanelState = { dirty: false, safe: true, isolated: false, discardForms: () => {} }
export const reviewCandidateKey = (candidate: DraftCandidate) => `${candidate.entity}:${candidate.draft_id}:${candidate.draft_revision}:${candidate.candidate_sha256}`
export const reviewDecisionKey = (receipt: StoredReviewReceipt) => `${receipt.id}:${receipt.revision}:${reviewCandidateKey(receipt.candidate)}`
export type ReviewForm = { workspace: string; scope: string; actor: string; owner: ReviewFormOwner; candidate: DraftCandidate } & (
  { kind: 'create'; value: CreateFormValue } | { kind: 'decision'; value: DecisionFormValue; receipt: StoredReviewReceipt })
export type VerifiedReviewForm = { form: ReviewForm; currentCandidate: DraftCandidate; currentReceipt: StoredReviewReceipt | null }
const held = new Map<string, ReviewForm>(), listeners = new Set<() => void>()
let version = 0
const changed = () => { ++version; listeners.forEach(listener => listener()) }
const key = (form: ReviewForm) => JSON.stringify([form.workspace, form.scope, form.actor, form.kind, form.owner,
  reviewCandidateKey(form.candidate), form.kind === 'decision' ? reviewDecisionKey(form.receipt) : ''])
export const subscribeReviewForms = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }
export const reviewFormMemoryVersion = () => version
export const pendingReviewForms = (workspace: string, scope?: string) => [...held.values()].some(row => row.workspace === workspace && (scope === undefined || row.scope === scope))
export function retainReviewForm(form: ReviewForm, dirty: boolean) {
  if (!form.actor) throw new Error('Missing original Review form actor')
  if (dirty) held.set(key(form), structuredClone(form)); else held.delete(key(form))
  changed()
}
// Page memory only. This actor binding is not authority: recovery also requires
// a fresh session and real protected owner/Review reads in useReview.
export const originalReviewForms = (workspace: string, scope: string, actor: string) => [...held.values()]
  .filter(row => row.workspace === workspace && row.scope === scope && row.actor === actor).map(row => structuredClone(row))
export function discardReviewForms(workspace: string, scope: string) {
  for (const [id, row] of held) if (row.workspace === workspace && row.scope === scope) held.delete(id)
  changed()
}
if (typeof window !== 'undefined') window.addEventListener('beforeunload', event => {
  if (held.size) { event.preventDefault(); event.returnValue = '' }
})
