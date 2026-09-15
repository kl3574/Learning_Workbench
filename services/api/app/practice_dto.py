"""Strict public practice projections from PRODUCT_DESIGN Appendix A.

Frozen private solution identities belong to application storage, never these
session views. A solution body is returned only by the explicit reveal command.
"""

from typing import Literal

from pydantic import Field, StrictBool, field_validator, model_validator

from packages.contracts import domain_models as dm

PracticeStatus = Literal["active", "submitted", "abandoned"]
HintLevel = Literal[1, 2, 3]
SolutionReviewStatus = Literal["draft", "needs_review", "approved"]


def integer_hint(value: object) -> object:
    if type(value) is not int:
        raise ValueError("hint levels must be JSON integers")
    return value


def practice_reference(ref: dm.ContentRef) -> dm.ContentRef:
    if ref.entity != "practice_set":
        raise ValueError("practice_ref must identify a practice set")
    return ref


def lesson_reference(ref: dm.ContentRef) -> dm.ContentRef:
    if ref.entity != "lesson":
        raise ValueError("lesson_ref must identify a lesson")
    return ref


class PracticeSetSummary(dm.StrictModel):
    ref: dm.ContentRef
    title: str
    lesson_ref: dm.ContentRef
    question_count: int = Field(ge=1)

    _practice_ref = field_validator("ref")(practice_reference)
    _lesson_ref = field_validator("lesson_ref")(lesson_reference)


class PagePracticeSet(dm.StrictModel):
    items: list[PracticeSetSummary]
    next_cursor: str | None


class PracticeSessionCreate(dm.StrictModel):
    practice_ref: dm.ContentRef

    _practice_ref = field_validator("practice_ref")(practice_reference)


class PracticeAssistance(dm.StrictModel):
    question_id: dm.Id
    highest_hint_level: Literal[0, 1, 2, 3]
    solution_revealed: bool

    _level_type = field_validator("highest_hint_level", mode="before")(integer_hint)


class PracticeAssistanceView(PracticeAssistance):
    # Omission is only legacy receipt compatibility; current projections emit it.
    model_help_received: StrictBool = False


class PracticeSession(dm.StrictModel):
    id: dm.Id
    revision: dm.Revision
    practice_ref: dm.ContentRef
    lesson_ref: dm.ContentRef
    questions: list[dm.QuestionPublic] = Field(min_length=1)
    responses: list[dm.ResponseDraft]
    status: PracticeStatus
    exposure_event_ids: list[dm.Id]
    assisted: bool
    assistance: list[PracticeAssistanceView]
    results: list[dm.ItemGrade] | None

    _practice_ref = field_validator("practice_ref")(practice_reference)
    _lesson_ref = field_validator("lesson_ref")(lesson_reference)

    @model_validator(mode="after")
    def assigned_public_state(self) -> "PracticeSession":
        assigned = [question.id for question in self.questions]
        responses = [response.question_id for response in self.responses]
        assistance = [item.question_id for item in self.assistance]
        if len(assigned) != len(set(assigned)):
            raise ValueError("question IDs must identify one assigned revision")
        if len(responses) != len(set(responses)) or not set(responses) <= set(assigned):
            raise ValueError("responses must be unique assigned questions")
        if len(assistance) != len(set(assistance)) or set(assistance) != set(assigned):
            raise ValueError("assistance must describe every assigned question exactly once")
        if self.assisted != any(item.highest_hint_level > 0 or item.solution_revealed or item.model_help_received for item in self.assistance):
            raise ValueError("assisted must reflect recorded assistance")
        if len(self.exposure_event_ids) != len(set(self.exposure_event_ids)):
            raise ValueError("duplicate exposure event IDs")
        if (self.status == "submitted") != (self.results is not None):
            raise ValueError("only submitted sessions have submission results")
        if self.results is not None:
            result_ids = [item.question_ref.id for item in self.results]
            if len(result_ids) != len(set(result_ids)) or set(result_ids) != set(assigned):
                raise ValueError("submission results must match assigned questions")
            if any(item.solution_markdown is not None for item in self.results):
                raise ValueError("session results cannot release private solutions")
        return self


class PracticeSessionCreated(PracticeSession):
    status: Literal["active"]


class PracticeResponsesSaved(dm.StrictModel):
    id: dm.Id
    revision: dm.Revision
    saved_at: dm.UTC


class PracticeSubmitRequest(dm.StrictModel):
    expected_revision: dm.Revision


class PracticeSubmitted(dm.StrictModel):
    id: dm.Id
    revision: dm.Revision
    results: list[dm.ItemGrade] = Field(min_length=1)
    evidence_label: Literal["practice"]
    exposure_event_ids: list[dm.Id]
    assisted: bool
    assistance: list[PracticeAssistanceView]

    @model_validator(mode="after")
    def public_submission(self) -> "PracticeSubmitted":
        if any(item.solution_markdown is not None for item in self.results):
            raise ValueError("submit does not release private solutions")
        return self


class PracticeHintRequest(dm.StrictModel):
    question_id: dm.Id
    expected_revision: dm.Revision
    level: HintLevel

    _level_type = field_validator("level", mode="before")(integer_hint)


class PracticeHint(dm.StrictModel):
    markdown: dm.Text
    exposure_event_id: dm.Id
    revision: dm.Revision
    level: HintLevel
    rule_version: str = Field(min_length=1, max_length=80)
    source: Literal["rules"]

    _level_type = field_validator("level", mode="before")(integer_hint)


class PracticeSolutionRequest(dm.StrictModel):
    question_id: dm.Id
    expected_revision: dm.Revision


class PracticeSolution(dm.StrictModel):
    solution_markdown: dm.Text
    exposure_event_id: dm.Id
    revision: dm.Revision
    review_status: SolutionReviewStatus
