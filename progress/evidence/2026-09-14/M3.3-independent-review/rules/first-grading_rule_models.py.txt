"""Internal deterministic-grading records. Private traces must never be API projections."""

from dataclasses import dataclass
from typing import Literal

from pydantic import ConfigDict, Field

from packages.contracts import domain_models as dm

from .assessment_content import FrozenAnswer

RULES_VERSION = "deterministic-v1"
TEXT_RULE = "NFC; strip Unicode edge whitespace; case-sensitive; preserve internal whitespace; explicit synonyms only"
UNIT_RULE = "units-v1; explicit compatible unit or bare value in declared target unit; exact base-unit comparison"
Outcome = Literal["correct", "incorrect", "unanswered", "invalid_input", "needs_review"]
ReasonCode = Literal[
    "answer_unreviewed", "manual_review_required", "grading_kind_mismatch", "steps_review_required",
    "standard_answer_limit", "standard_answer_invalid", "unanswered", "invalid_choice",
    "choice_match", "choice_mismatch", "text_match", "text_mismatch", "unit_unsupported",
    "input_invalid_numeric", "unit_incompatible", "numeric_precision_limit", "numeric_match", "numeric_mismatch",
]


@dataclass(frozen=True)
class RuleSet:
    """Only this named implementation is supported; callers cannot silently tune its meaning."""

    version: Literal["deterministic-v1"] = "deterministic-v1"

    @property
    def rules_version(self) -> str:
        return self.version


RULES_V1 = RuleSet()


class NumericComparison(dm.StrictModel):
    expected: str
    expected_in_base_unit: str
    absolute_difference: str
    allowed_difference: str
    matched: bool


class NumericTrace(dm.StrictModel):
    parsed_user: str
    user_in_base_unit: str
    supplied_unit: str | None
    target_unit: str | None
    comparison_unit: str | None
    user_to_base_factor: str
    target_to_base_factor: str
    absolute_tolerance: str
    relative_tolerance: str
    comparisons: list[NumericComparison]


class PrivateGradeTrace(dm.StrictModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True, frozen=True)

    rules_version: Literal["deterministic-v1"] = "deterministic-v1"
    question_ref: dm.ContentRef
    private_pin: FrozenAnswer
    response: dm.ResponseDraft | None
    outcome: Outcome
    reason_codes: list[ReasonCode]
    text_rule: str = TEXT_RULE
    unit_rule: str = UNIT_RULE
    normalized_answer: str | None = None
    normalized_accepted: list[str] = Field(default_factory=list)
    numeric: NumericTrace | None = None
    steps_assessment: Literal["not_assessed", "review_required"] = "not_assessed"


class RuleDecision(dm.StrictModel):
    item_grade: dm.ItemGrade
    private_trace: PrivateGradeTrace


class GradingBindingError(ValueError):
    """An invalid trusted assignment is a storage/integrity failure, never a zero score."""

    code = "GRADING_BINDING_INVALID"

    def __init__(self) -> None:
        super().__init__("评分输入与冻结题目或私有解答不一致。")
