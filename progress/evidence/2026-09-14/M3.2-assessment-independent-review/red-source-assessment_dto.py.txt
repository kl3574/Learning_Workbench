"""Strict assessment application projections; private answer pins never cross HTTP."""

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from packages.contracts import domain_models as dm

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
    grading_status: Literal["not_graded"]

    @model_validator(mode="after")
    def frozen_public_facts(self):
        if self.assessment_ref.entity != "assessment" or self.status not in {"active", "submitted", "abandoned"}:
            raise ValueError("M3.2 has no completed grading or grading worker projection")
        ids = [question.id for question in self.questions]
        if len(ids) != len(set(ids)) or ids != [item.question_ref.id for item in self.preflight.prior_seen.questions]:
            raise ValueError("public preflight must match ordered assigned questions")
        if self.status == "submitted" and self.submitted_at is None or self.status != "submitted" and self.submitted_at is not None:
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
