"""Original synthetic algorithm cases; approved fixtures are not human-review evidence."""

from decimal import getcontext, localcontext
import json

import pytest
from pydantic import ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, strict_json
from services.api.app.application.assessment_content import FrozenAnswer
from services.api.app.application.grading_rules import (
    RULES_V1, RULES_VERSION, GradingBindingError, PrivateGradeTrace, RuleDecision, RuleSet, grade_item,
)


def inputs(*, kind="numeric", grading_kind=None, answer="1", expected=None, unit=None,
           atol=0.0, rtol=0.0, review="approved", skill="compute", steps="", rubric=""):
    question = dm.QuestionPublic(id="question_rule_synthetic", revision=1, kind=kind,
        stem_markdown="Original synthetic grading-rule case, not reviewed teaching material.",
        choices=[dm.Choice(id="option_a", text_markdown="Option A"), dm.Choice(id="option_b", text_markdown="Option B")]
        if kind == "single_choice" else [], concept_ids=["concept_rule_synthetic"], skill=skill,
        exposure_group="group_rule_synthetic", max_score=2.5, input_instructions="Use declared deterministic-v1 rules.")
    ref = dm.ContentRef(entity="question", id=question.id, revision=question.revision, sha256=metadata_sha256(question))
    algorithm = grading_kind or {"single_choice": "choice_exact", "text_blank": "text_normalized", "numeric": "numeric_tolerance",
        "calculation": "numeric_tolerance", "expression": "symbolic_review"}[kind]
    solution = dm.SolutionPrivate(id="solution_rule_synthetic", revision=2, question_ref=ref,
        grading_kind=algorithm, accepted_answers=expected if expected is not None else ["1"],
        absolute_tolerance=atol, relative_tolerance=rtol, unit=unit, review_status=review,
        solution_markdown="SYNTHETIC_PRIVATE_EXPLANATION", rubric_markdown=rubric)
    pin = FrozenAnswer(question_ref=ref, solution_revision=solution.revision,
                       sha256=metadata_sha256(solution), review_status=solution.review_status)
    response = dm.ResponseDraft(question_id=question.id, answer=answer, steps_markdown=steps) if answer is not None else None
    return dict(question_ref=ref, question=question, pin=pin, solution=solution, response=response)


def assert_review(value, code, *, invalid=False):
    assert value.item_grade.status == "needs_review"
    assert value.item_grade.score is None
    assert value.private_trace.reason_codes == [code]
    assert value.private_trace.outcome == ("invalid_input" if invalid else "needs_review")


@pytest.mark.parametrize("answer,score,outcome", [("option_a", 2.5, "correct"), ("option_b", 0, "incorrect"), ("", 0, "unanswered"), (None, 0, "unanswered")])
def test_choice_uses_frozen_option_identity_and_keeps_missing_answer(answer, score, outcome):
    decision = grade_item(**inputs(kind="single_choice", answer=answer, expected=["option_a"]))
    assert decision.item_grade.score == score
    assert decision.private_trace.outcome == outcome
    assert decision.item_grade.solution_markdown is None
    assert decision.private_trace.response is None if answer is None else decision.private_trace.response.answer == answer


@pytest.mark.parametrize("answer", ["Option A", "OPTION_A", " option_a", "option_a,option_b", "other"])
def test_choice_does_not_infer_an_option_from_text_or_trim_id(answer):
    assert_review(grade_item(**inputs(kind="single_choice", answer=answer, expected=["option_a"])), "invalid_choice", invalid=True)


@pytest.mark.parametrize("answer,expected,score", [
    ("  cafe\u0301 \n", ["café"], 2.5), ("second synonym", ["first", "second synonym"], 2.5),
    ("ALPHA", ["alpha"], 0), ("a  b", ["a b"], 0), ("Ａ", ["A"], 0),
    ("word.", ["word"], 0), ("\u00a0\t", ["word"], 0),
])
def test_text_rules_are_declared_nfc_case_sensitive_and_only_explicit_synonyms(answer, expected, score):
    value = grade_item(**inputs(kind="text_blank", answer=answer, expected=expected))
    assert value.item_grade.score == score
    assert value.private_trace.response.answer == answer
    assert "case-sensitive" in value.private_trace.text_rule
    assert "preserve internal whitespace" in value.private_trace.text_rule


@pytest.mark.parametrize("expected,answer,atol,rtol,score", [
    ("1", "1.1", .1, 0., 2.5), ("1", "1.1000000000000000000000000000001", .1, 0., 0),
    ("1", "1.0999999999999999999999999999999", .1, 0., 2.5),
    ("-100", "-98.9", .1, .01, 2.5), ("-100", "-98.89999999999999999999999999999", .1, .01, 0),
    ("0", "0.000000000000000000000000000000001", 0., .5, 0),
    ("0", "-0", 0., 0., 2.5), ("1", "1.000000000000000000000000000000001", 0., 0., 0),
    ("1e-1000", "0", 0., 0., 0), ("1e1000", "1e1000", 0., 0., 2.5),
])
def test_decimal_comparison_preserves_exact_boundary_and_relative_expected_magnitude(expected, answer, atol, rtol, score):
    value = grade_item(**inputs(answer=answer, expected=[expected], atol=atol, rtol=rtol))
    assert value.item_grade.score == score
    assert value.private_trace.numeric is not None
    assert value.private_trace.numeric.comparisons[0].matched == (score > 0)


@pytest.mark.parametrize("target,answer,expected,score", [
    ("m", "100cm", "1", 2.5), ("cm", "1 m", "100", 2.5),
    ("kg", "1000 g", "1", 2.5), ("L", "250mL", ".25", 2.5),
    ("min", "1s", "0.016666666666666666666666666666666666", 0),
    ("min", "60s", "1", 2.5), ("h", "60min", "1", 2.5),
    ("m", "1", "1", 2.5), (None, "1", "1", 2.5),
    ("m/s", "100cm/s", "1", 2.5), ("m²", "10000cm^2", "1", 2.5),
    ("m^2", "1000000mm²", "1", 2.5),
])
def test_unit_conversion_uses_exact_base_units_without_repeating_decimal_division(target, answer, expected, score):
    value = grade_item(**inputs(unit=target, answer=answer, expected=[expected]))
    assert value.item_grade.score == score
    assert value.private_trace.numeric.target_unit == target
    assert "bare value" in value.private_trace.unit_rule


def test_absolute_tolerance_is_scaled_from_declared_target_unit_before_base_comparison():
    correct = grade_item(**inputs(unit="cm", answer="1.01 m", expected=["100"], atol=1.))
    incorrect = grade_item(**inputs(unit="cm", answer="1.010000000000000000000001 m", expected=["100"], atol=1.))
    assert correct.item_grade.score == 2.5 and incorrect.item_grade.score == 0
    assert correct.private_trace.numeric.comparisons[0].allowed_difference == "0.010"


@pytest.mark.parametrize("target,answer,code", [("m", "1s", "unit_incompatible"), (None, "1m", "unit_incompatible"),
    ("m", "1M", "unit_unsupported"), ("m", "1furlong", "unit_unsupported"), ("m", "1m/s", "unit_incompatible")])
def test_unknown_case_or_incompatible_units_do_not_produce_fake_zero(target, answer, code):
    assert_review(grade_item(**inputs(unit=target, answer=answer)), code, invalid=True)


@pytest.mark.parametrize("answer", ["NaN", "sNaN", "Infinity", "-Infinity", "1e1001", "1e-1001", "1e999999999",
    "__import__('os').system('false')", "sqrt(2)", "1/2", "2+2", "1,000", "0x10", "١", "1\n2"])
def test_invalid_numeric_inputs_are_retained_but_not_executed_or_scored(answer):
    value = grade_item(**inputs(answer=answer))
    assert_review(value, "input_invalid_numeric", invalid=True)
    assert value.private_trace.response.answer == answer
    assert answer not in value.item_grade.feedback_markdown


def test_accepted_numeric_set_is_all_validated_before_any_match():
    assert grade_item(**inputs(answer="2", expected=["1", "2"])).item_grade.score == 2.5
    assert_review(grade_item(**inputs(answer="1", expected=["1", "NaN"])), "standard_answer_invalid")
    assert_review(grade_item(**inputs(answer="1", expected=["1", "1/2"])), "standard_answer_invalid")


@pytest.mark.parametrize("kind,expected,unit", [("text_blank", [""], None), ("single_choice", ["missing"], None), ("numeric", ["1"], "°C")])
def test_invalid_standard_answers_never_award_or_deduct_even_for_empty_response(kind, expected, unit):
    value = grade_item(**inputs(kind=kind, expected=expected, answer="", unit=unit))
    assert_review(value, "unit_unsupported" if unit else "standard_answer_invalid")


@pytest.mark.parametrize("review", ["draft", "needs_review"])
@pytest.mark.parametrize("answer", ["1", "0", "", None])
def test_unreviewed_private_answer_is_not_normal_grading_even_when_correct_or_empty(review, answer):
    assert_review(grade_item(**inputs(review=review, answer=answer)), "answer_unreviewed")


@pytest.mark.parametrize("kind,algorithm", [("expression", "symbolic_review"), ("calculation", "symbolic_review"), ("calculation", "rubric_review")])
def test_symbolic_and_rubric_cases_remain_explicit_human_review(kind, algorithm):
    result = grade_item(**inputs(kind=kind, grading_kind=algorithm, steps="A plausible-looking synthetic proof."))
    assert_review(result, "manual_review_required")
    assert result.private_trace.steps_assessment == "review_required"


def test_numeric_calculation_does_not_claim_steps_correct_or_infer_rubric_points():
    answer = grade_item(**inputs(kind="calculation", steps="This synthetic step is deliberately wrong."))
    assert answer.item_grade.score == 2.5
    assert "计算步骤未评分" in answer.item_grade.feedback_markdown
    assert answer.private_trace.steps_assessment == "not_assessed"
    for extra in [{"skill": "derive"}, {"rubric": "Only check the final value; review steps separately."}]:
        declared = grade_item(**inputs(kind="calculation", **extra))
        assert declared.item_grade.score == 2.5
        assert "计算步骤未评分" in declared.item_grade.feedback_markdown
    assert_review(grade_item(**inputs(kind="numeric", grading_kind="choice_exact")), "grading_kind_mismatch")


@pytest.mark.parametrize("field,change", [
    ("question_ref", {"sha256": "0" * 64}), ("question", {"revision": 2}),
    ("pin", {"sha256": "0" * 64}), ("pin", {"solution_revision": 3}),
    ("pin", {"review_status": "needs_review"}), ("solution", {"accepted_answers": ["2"]}),
    ("response", {"question_id": "question_other"}), ("response", {"answer": "x" * 4001}),
    ("solution", {"absolute_tolerance": float("nan")}), ("question", {"max_score": float("inf")}),
    ("solution", {"accepted_answers": []}),
])
def test_exact_reference_and_strict_models_reject_mutated_or_cross_question_inputs(field, change):
    arguments = inputs()
    arguments[field] = arguments[field].model_copy(update=change)
    with pytest.raises(GradingBindingError) as error:
        grade_item(**arguments)
    assert error.value.code == "GRADING_BINDING_INVALID"
    assert "SYNTHETIC_PRIVATE" not in str(error.value)


def test_strict_private_trace_roundtrip_is_separate_from_safe_item_projection():
    value = grade_item(**inputs(answer="42", expected=["42"]))
    assert RuleDecision.model_validate(strict_json(canonical_bytes(value))) == value
    assert PrivateGradeTrace.model_validate(strict_json(canonical_bytes(value.private_trace))) == value.private_trace
    public = value.item_grade.model_dump(mode="json")
    assert public["solution_markdown"] is None
    assert not {"private_pin", "numeric", "accepted_answers", "response"} & public.keys()
    assert "42" not in public["feedback_markdown"]
    tampered = strict_json(canonical_bytes(value.private_trace))
    tampered["unrecognized"] = True
    with pytest.raises(ValidationError):
        PrivateGradeTrace.model_validate(tampered)
    tampered.pop("unrecognized")
    tampered["reason_codes"] = ["untrusted arbitrary content"]
    with pytest.raises(ValidationError):
        PrivateGradeTrace.model_validate(tampered)


def test_resource_limits_do_not_partial_grade_a_large_standard_answer_set():
    assert_review(grade_item(**inputs(expected=["1"] * 1001)), "standard_answer_limit")
    assert_review(grade_item(**inputs(kind="text_blank", expected=["a" * 400001])), "standard_answer_limit")


def test_long_finite_numeric_input_is_exact_and_independent_of_callers_decimal_context():
    literal = "0." + "0" * 3996 + "1"
    arguments = inputs(answer=literal, expected=["0"])
    original = canonical_bytes(arguments["solution"])
    with localcontext() as context:
        context.prec = 2
        before = getcontext().copy()
        value = grade_item(**arguments)
        assert getcontext().prec == before.prec
    assert value.item_grade.score == 0
    assert canonical_bytes(arguments["solution"]) == original
    assert canonical_bytes(grade_item(**arguments)) == canonical_bytes(value)


def test_ruleset_version_is_explicit_and_cannot_silently_change_algorithm():
    assert RULES_V1.rules_version == RULES_VERSION == "deterministic-v1"
    with pytest.raises(ValueError, match="Unsupported"):
        grade_item(**inputs(), rules=RuleSet(version="unknown"))
    assert json.loads(canonical_bytes(grade_item(**inputs()).private_trace))["rules_version"] == RULES_VERSION


def test_default_float_fields_keep_exact_canonical_binding_after_strict_revalidation():
    arguments = inputs()
    data = arguments["question"].model_dump(mode="python")
    data.pop("max_score")
    question = dm.QuestionPublic.model_validate(data)
    ref = dm.ContentRef(entity="question", id=question.id, revision=question.revision, sha256=metadata_sha256(question))
    solution = arguments["solution"].model_copy(update={"question_ref": ref})
    pin = FrozenAnswer(question_ref=ref, solution_revision=solution.revision, sha256=metadata_sha256(solution), review_status=solution.review_status)
    result = grade_item(question_ref=ref, question=question, pin=pin, solution=solution, response=arguments["response"])
    assert result.item_grade.score == result.item_grade.max_score == 1
