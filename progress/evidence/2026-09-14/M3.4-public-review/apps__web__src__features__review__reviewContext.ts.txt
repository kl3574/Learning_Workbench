import type { CurrentReviewPolicy, GradeHistoryEntry, QuestionReviewMaterials } from '../../../../../packages/contracts/generated/api-types'
import type { ContentRef, ResponseDraft } from '../../../../../packages/contracts/generated/types'
export type ReviewTutorContext = {
  attempt: string; assessment: ContentRef; question: ContentRef; questionText: string;
  submitted: ResponseDraft | null; gradingRevision: number; historyItem: GradeHistoryEntry['items'][number];
  feedback: string | null; solution: string | null; solutionReview: 'draft' | 'needs_review' | 'approved' | null;
  materials: QuestionReviewMaterials['materials'];
}
export type ReviewAccess = { access: number; policy: CurrentReviewPolicy | null; context: ReviewTutorContext | null }
