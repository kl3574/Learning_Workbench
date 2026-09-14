"""Strict eligibility facts and decisions; no persistence or public answer projection."""

from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from packages.contracts import domain_models as dm

ELIGIBILITY_VERSION = "eligibility-v1"
AssessmentMode = Literal["independent", "open_book", "assisted"]
QualificationBasis = Literal["submission_frozen", "history_not_frozen"]
HelpState = Literal["none", "present", "unknown"]
Skill = Literal["recall", "explain", "compute", "derive", "transfer"]
Independence = Literal["independent", "assisted", "unknown"]
Freshness = Literal["novel", "repeated", "unknown"]
EligibilityReason = Literal[
    "MODE_OPEN_BOOK", "MODE_ASSISTED", "HELP_BEFORE_SUBMIT", "ANSWER_UNREVIEWED",
    "GRADE_UNRESOLVED", "CONCEPT_MAPPING_UNRESOLVED", "PREVIOUSLY_SEEN",
    "PRIOR_SEEN_UNKNOWN", "HELP_HISTORY_UNKNOWN", "SOURCE_NOT_TRUSTED",
    "HISTORY_PREREQUISITES_NOT_FROZEN",
]


class ItemPrerequisites(dm.StrictModel):
    """Non-score facts supplied by validated module-owned ports.

    This value alone does not prove persistence, native origin, or provenance.
    The Learning boundary stores the original witnesses and freezes their hash.
    Legacy reconstruction uses the explicit history_not_frozen basis forever.
    """

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True, frozen=True)

    question_ref: dm.ContentRef
    required_concept_ids: list[dm.Id] = Field(min_length=1)
    concept_refs: list[dm.ContentRef]
    skill: Skill
    exposure_group: dm.Id
    max_score: float = Field(gt=0, le=100)
    solution_revision: dm.Revision
    solution_sha256: dm.Sha256
    answer_review_status: Literal["approved", "draft", "needs_review"]
    prior_seen: Literal["unseen", "seen", "unknown"]
    pre_submission_help_state: HelpState
    in_attempt_help_state: HelpState
    source_trusted: bool

    @model_validator(mode="after")
    def consistent_facts(self):
        if self.question_ref.entity != "question":
            raise ValueError("eligibility must identify an exact question")
        required = self.required_concept_ids
        actual = [ref.id for ref in self.concept_refs]
        if (len(set(required)) != len(required) or len(set(actual)) != len(actual)
                or not set(actual) <= set(required)
                or any(ref.entity != "concept" for ref in self.concept_refs)):
            raise ValueError("concept mapping must be a unique subset of the question dependencies")
        if self.pre_submission_help_state == "none" and self.in_attempt_help_state != "none":
            raise ValueError("known absent pre-submission help cannot contain uncertain or present attempt help")
        return self

    @property
    def mapping_complete(self) -> bool:
        return set(self.required_concept_ids) == {ref.id for ref in self.concept_refs}


class EligibilityDecision(dm.StrictModel):
    """No answers, private pins, raw responses, or inferred mastery probabilities."""

    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True, frozen=True)

    question_ref: dm.ContentRef
    concept_refs: list[dm.ContentRef]
    skill: Skill
    eligible: bool
    reason_codes: list[EligibilityReason]
    normalized_score: float | None = Field(ge=0, le=1)
    independence: Independence
    freshness: Freshness

    @model_validator(mode="after")
    def consistent_decision(self):
        ids = [ref.id for ref in self.concept_refs]
        if (self.question_ref.entity != "question" or any(ref.entity != "concept" for ref in self.concept_refs)
                or len(ids) != len(set(ids)) or len(self.reason_codes) != len(set(self.reason_codes))):
            raise ValueError("eligibility decision has duplicate or invalid references/reasons")
        if self.eligible != (not self.reason_codes):
            raise ValueError("eligibility must preserve every exclusion")
        if self.eligible and (not self.concept_refs or self.normalized_score is None
                              or self.independence != "independent" or self.freshness != "novel"):
            raise ValueError("eligible evidence requires resolved, mapped, independent and novel facts")
        if ("GRADE_UNRESOLVED" in self.reason_codes) != (self.normalized_score is None):
            raise ValueError("unresolved evidence retains a null score")
        return self


class EligibilityBindingError(ValueError):
    """A damaged trusted input cannot be converted to a zero or an eligible result."""

    code = "ELIGIBILITY_BINDING_INVALID"

    def __init__(self) -> None:
        super().__init__("证据输入与冻结题目或评分项不一致。")
