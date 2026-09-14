"""Strict assessment application projections; private answer pins never cross HTTP."""

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from packages.contracts import domain_models as dm

from .application.eligibility_models import EligibilityReason
from .application.question_qualification import ReviewMaterial

QuestionKind = Literal["single_choice", "text_blank", "numeric", "expression", "calculation"]
AttemptStatus = Literal["active", "submitted", "grading", "graded", "needs_review", "abandoned"]
AssessmentMode = Literal["independent", "assisted", "open_book"]
ReasonCode = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_]+$")]


class QuestionKindCount(dm.StrictModel):
    kind: QuestionKind
    count: int = Field(ge=1)


class GradingReadiness(dm.StrictModel):
    status: Literal["reviewed", "unreviewed", "unavailable"]
    approved_count: int = Field(ge=0)
    draft_count: int = Field(ge=0)
    needs_review_count: int = Field(ge=0)
    missing_count: int = Field(ge=0)
    damaged_count: int = Field(ge=0)
    reason_codes: list[ReasonCode]

    @model_validator(mode="after")
    def matching_status(self):
        expected = "unavailable" if self.missing_count or self.damaged_count else "unreviewed" if self.draft_count or self.needs_review_count else "reviewed"
        if self.status != expected:
            raise ValueError("grading readiness must match actual answer review counts")
        return self


class PriorSeenQuestion(dm.StrictModel):
    question_ref: dm.ContentRef
    state: Literal["unseen", "seen", "unknown"]
    reason_codes: list[ReasonCode]

    @field_validator("question_ref")
    @classmethod
    def question_entity(cls, value: dm.ContentRef) -> dm.ContentRef:
        if value.entity != "question":
            raise ValueError("prior seen reference must be a question")
        return value


class PriorSeen(dm.StrictModel):
    status: Literal["known", "unknown"]
    questions: list[PriorSeenQuestion]

    @model_validator(mode="after")
    def consistent(self):
        ids = [item.question_ref.id for item in self.questions]
        if len(ids) != len(set(ids)) or (self.status == "unknown") != any(item.state == "unknown" for item in self.questions):
            raise ValueError("prior seen summary must describe unique questions and actual uncertainty")
        return self


class AssessmentPreflight(dm.StrictModel):
    course_refs: list[dm.ContentRef]
    question_kinds: list[QuestionKindCount]
    target_concept_refs: list[dm.ContentRef]
    grading: GradingReadiness
    prior_seen: PriorSeen
    startable: bool
    start_block_reason_codes: list[ReasonCode]

    @model_validator(mode="after")
    def references_and_counts(self):
        if any(ref.entity != "course" for ref in self.course_refs) or any(ref.entity != "concept" for ref in self.target_concept_refs):
            raise ValueError("preflight references must have the declared entity")
        for refs in (self.course_refs, self.target_concept_refs):
            keys = [(ref.id, ref.revision, ref.sha256) for ref in refs]
            if len(keys) != len(set(keys)):
                raise ValueError("duplicate preflight reference")
        kinds = [item.kind for item in self.question_kinds]
        total = sum(item.count for item in self.question_kinds)
        grading_total = sum((self.grading.approved_count, self.grading.draft_count, self.grading.needs_review_count, self.grading.missing_count, self.grading.damaged_count))
        if not total or len(kinds) != len(set(kinds)) or total != grading_total or total != len(self.prior_seen.questions):
            raise ValueError("preflight counts must describe every assigned question")
        if self.startable != (not self.start_block_reason_codes) or self.startable and self.grading.status == "unavailable":
            raise ValueError("startability must describe actual blockers")
        return self


class RecentAttempt(dm.StrictModel):
    id: dm.Id
    revision: dm.Revision
    status: AttemptStatus
    mode: AssessmentMode
    created_at: dm.UTC
    submitted_at: dm.UTC | None


class AssessmentSummary(dm.StrictModel):
    ref: dm.ContentRef
    title: str
    question_count: int = Field(ge=1)
    allowed_modes: list[AssessmentMode] = Field(min_length=1)
    time_limit_seconds: int | None = Field(gt=0)
    preflight: AssessmentPreflight
    recent_attempts: list[RecentAttempt] = Field(max_length=10)
    recent_attempts_truncated: bool

    @model_validator(mode="after")
    def exact_summary(self):
        if self.ref.entity != "assessment" or self.question_count != len(self.preflight.prior_seen.questions):
            raise ValueError("assessment summary must describe its complete question allocation")
        if len(self.allowed_modes) != len(set(self.allowed_modes)):
            raise ValueError("duplicate allowed modes")
        return self


class PageAssessment(dm.StrictModel):
    items: list[AssessmentSummary]
    next_cursor: str | None


class AssessmentAttemptCreate(dm.AttemptCreate):
    @field_validator("assessment_ref")
    @classmethod
    def assessment_entity(cls, value: dm.ContentRef) -> dm.ContentRef:
        if value.entity != "assessment":
            raise ValueError("attempt must refer to an assessment")
        return value


class AttemptSnapshot(dm.AttemptPublic):
    preflight: AssessmentPreflight
    grading_revision: int = Field(default=0, ge=0)
    grading_status: Literal["not_graded", "pending", "graded", "needs_review", "failed", "cancelled"]

    @model_validator(mode="after")
    def frozen_public_facts(self):
        if self.assessment_ref.entity != "assessment":
            raise ValueError("assessment projection must retain its exact blueprint")
        ids = [question.id for question in self.questions]
        if len(ids) != len(set(ids)) or ids != [item.question_ref.id for item in self.preflight.prior_seen.questions]:
            raise ValueError("public preflight must match ordered assigned questions")
        if (self.status not in {"active", "abandoned"}) != (self.submitted_at is not None):
            raise ValueError("submission timestamp must match state")
        return self


class AttemptResponses(dm.StrictModel):
    revision: dm.Revision
    responses: list[dm.ResponseDraft]
    saved_at: dm.UTC | None

    @model_validator(mode="after")
    def unique_responses(self):
        ids = [response.question_id for response in self.responses]
        if len(ids) != len(set(ids)):
            raise ValueError("responses must uniquely identify assigned questions")
        return self


class RegradeItemReview(dm.StrictModel):
    question_id: dm.Id
    score: float = Field(ge=0)
    feedback_markdown: str = Field(min_length=1, max_length=20000)


class RegradeRequest(dm.StrictModel):
    expected_grading_revision: int = Field(ge=0)
    reason: str = Field(min_length=1, max_length=4000)
    item_reviews: list[RegradeItemReview] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_items(self):
        if len({item.question_id for item in self.item_reviews}) != len(self.item_reviews):
            raise ValueError("manual review items must be unique")
        if not self.reason.strip() or any(not item.feedback_markdown.strip() for item in self.item_reviews):
            raise ValueError("human review requires a nonblank reason and feedback")
        return self


class ManualReviewReceipt(dm.StrictModel):
    id: dm.Id
    actor_role: Literal["author"]
    signed_at: dm.UTC
    reason: str
    question_ids: list[dm.Id]
    signature: dm.Sha256
    signature_algorithm: Literal["hmac-sha256-v1"]


class ReleasedSolutionReview(dm.StrictModel):
    question_id: dm.Id
    review_status: Literal["approved", "draft", "needs_review"]


class GradeHistoryItem(dm.StrictModel):
    question_ref: dm.ContentRef
    score: float | None = Field(ge=0)
    max_score: float = Field(gt=0)
    status: Literal["graded", "needs_review"]
    concept_refs: list[dm.ContentRef]
    eligible: bool
    reason_codes: list[EligibilityReason]
    evidence_ids: list[dm.Id]
    independence: Literal["independent", "assisted", "unknown"]
    freshness: Literal["novel", "repeated", "unknown"]

    @model_validator(mode="after")
    def checked_item(self):
        if (self.question_ref.entity != "question" or any(ref.entity != "concept" for ref in self.concept_refs)
                or len({(ref.id, ref.revision, ref.sha256) for ref in self.concept_refs}) != len(self.concept_refs)
                or len(set(self.reason_codes)) != len(self.reason_codes) or len(set(self.evidence_ids)) != len(self.evidence_ids)
                or (self.status == "needs_review") != (self.score is None)
                or self.score is not None and self.score > self.max_score):
            raise ValueError("history must retain exact references and real nullable grades")
        if self.eligible and (self.status != "graded" or not self.concept_refs or self.reason_codes
                              or self.independence != "independent" or self.freshness != "novel"):
            raise ValueError("eligible history requires resolved independent novel evidence")
        return self


class GradeHistoryEntry(dm.StrictModel):
    grading_revision: dm.Revision
    grading_rules_version: str = Field(min_length=1, max_length=120)
    status: Literal["graded", "needs_review"]
    finalized_at: dm.UTC
    qualification_basis: Literal["submission_frozen", "history_not_frozen"]
    qualification_recorded_at: dm.UTC
    items: list[GradeHistoryItem] = Field(min_length=1)

    @model_validator(mode="after")
    def checked_history(self):
        if (len({item.question_ref.id for item in self.items}) != len(self.items)
                or (self.status == "needs_review") != any(item.status == "needs_review" for item in self.items)):
            raise ValueError("history must retain every assigned item and unresolved status")
        if self.qualification_basis == "history_not_frozen" and any(
                item.eligible or "HISTORY_PREREQUISITES_NOT_FROZEN" not in item.reason_codes for item in self.items):
            raise ValueError("legacy qualification cannot be upgraded by a later grade")
        return self


class QuestionReviewMaterials(dm.StrictModel):
    question_ref: dm.ContentRef
    materials: list[ReviewMaterial]

    @field_validator("question_ref")
    @classmethod
    def question_entity(cls, value: dm.ContentRef) -> dm.ContentRef:
        if value.entity != "question":
            raise ValueError("review materials must bind an exact assigned question")
        return value


class CurrentReviewPolicy(dm.StrictModel):
    tutor_scope: Literal["operation_help_only", "academic"]
    allow_materials: bool
    allow_web: Literal[False]

    @field_validator("allow_web", mode="before")
    @classmethod
    def no_implicit_consent(cls, value: object) -> object:
        if type(value) is not bool:
            raise ValueError("web consent is a strict boolean")
        return value


class AssessmentGradingResult(dm.GradingResult):
    manual_reviews: list[ManualReviewReceipt]
    solution_reviews: list[ReleasedSolutionReview]
    eligibility_status: Literal["not_evaluated", "evaluated"]
    history: list[GradeHistoryEntry]
    current_review_policy: CurrentReviewPolicy
    review_materials: list[QuestionReviewMaterials]

    @model_validator(mode="after")
    def complete_result(self):
        ids = [item.question_ref.id for item in self.items]
        if not ids or len(set(ids)) != len(ids) or any(item.question_ref.entity != "question" for item in self.items):
            raise ValueError("result must retain every unique exact question")
        if (self.status == "needs_review") != any(item.status == "needs_review" for item in self.items):
            raise ValueError("overall grading status must preserve unresolved items")
        if [item.question_id for item in self.solution_reviews] != [item.question_ref.id for item in self.items if item.solution_markdown is not None]:
            raise ValueError("released answers must disclose their original review status")
        revisions = [entry.grading_revision for entry in self.history]
        if revisions != sorted(set(revisions)) or not revisions or revisions[-1] != self.grading_revision:
            raise ValueError("result must include its complete ordered history")
        for entry in self.history:
            if [item.question_ref for item in entry.items] != [item.question_ref for item in self.items]:
                raise ValueError("history belongs to another assignment")
        latest = self.history[-1]
        if (latest.status != self.status or latest.finalized_at != self.finalized_at
                or latest.grading_rules_version != self.grading_rules_version
                or [(item.score, item.max_score, item.status) for item in latest.items] != [(item.score, item.max_score, item.status) for item in self.items]
                or [item.question_ref for item in self.review_materials] != [item.question_ref for item in self.items]):
            raise ValueError("result history or material binding differs from current grade")
        return self


class AssessmentGradingJob(dm.JobRef):
    last_completed_result: AssessmentGradingResult | None
    history: list[GradeHistoryEntry]
    current_review_policy: CurrentReviewPolicy

    @model_validator(mode="after")
    def checked_previous(self):
        if self.last_completed_result is None:
            if self.history:
                raise ValueError("history requires the actual last completed result")
        elif (self.last_completed_result.history != self.history or self.last_completed_result.current_review_policy != self.current_review_policy
                or self.last_completed_result.solution_reviews
                or any(item.solution_markdown is not None for item in self.last_completed_result.items)):
            raise ValueError("pending-job history must retain the same safe previous result")
        return self
