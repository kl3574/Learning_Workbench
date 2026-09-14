"""Original algorithm fixtures; approved inputs are not human content-review evidence."""

from typing import get_args

import pytest
from pydantic import ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, strict_json
from services.api.app.application.eligibility import (
    EligibilityBindingError, evidence_reason, finalize_eligibility,
    prerequisite_reasons, validate_prerequisites,
)
from services.api.app.application.eligibility_models import (
    EligibilityDecision, EligibilityReason, ItemPrerequisites,
)


def sample(**updates):
    concept = dm.Concept(id="concept_eligibility", revision=2, title="Original synthetic concept")
    question = dm.QuestionPublic(id="question_eligibility", revision=3, kind="numeric",
        stem_markdown="Original synthetic quantity case, not approved teaching content.",
        concept_ids=[concept.id], skill="compute", exposure_group="exposure_eligibility",
        max_score=2.5, input_instructions="Synthetic test input")
    ref = dm.ContentRef(entity="question", id=question.id, revision=question.revision, sha256=metadata_sha256(question))
    value = dict(question_ref=ref, required_concept_ids=[concept.id],
        concept_refs=[dm.ContentRef(entity="concept", id=concept.id, revision=concept.revision, sha256=metadata_sha256(concept))],
        skill=question.skill, exposure_group=question.exposure_group, max_score=question.max_score,
        solution_revision=4, solution_sha256="a" * 64, answer_review_status="approved",
        prior_seen="unseen", pre_submission_help_state="none", in_attempt_help_state="none", source_trusted=True)
    value.update(updates)
    return ItemPrerequisites.model_validate(value)


def grade(value, score=2.5):
    return dm.ItemGrade(question_ref=value.question_ref, score=score, max_score=value.max_score,
        status="needs_review" if score is None else "graded",
        feedback_markdown="SYNTHETIC_PRIVATE_FEEDBACK", solution_markdown="SYNTHETIC_PRIVATE_SOLUTION")


def decide(value, *, score=2.5, mode="independent", basis="submission_frozen"):
    return finalize_eligibility(prerequisites=value, grade=grade(value, score), mode=mode, basis=basis)


@pytest.mark.parametrize("score,normalized", [(0.0, 0.0), (1.25, .5), (2.5, 1.0)])
def test_eligibility_does_not_depend_on_correctness_and_preserves_true_wrong_evidence(score, normalized):
    value = sample()
    before = canonical_bytes(value)
    assert prerequisite_reasons(prerequisites=value, mode="independent", basis="submission_frozen") == []
    actual = decide(value, score=score)
    assert actual.eligible and actual.normalized_score == normalized
    assert actual.independence == "independent" and actual.freshness == "novel"
    assert evidence_reason(actual) == "ELIGIBLE_INDEPENDENT_NOVEL"
    assert canonical_bytes(value) == before


def test_prerequisites_cannot_store_score_or_resolved_and_do_not_finalize_an_unresolved_grade():
    value = sample()
    assert not {"score", "eligible", "resolved", "normalized_score", "grading_revision"} & value.model_dump().keys()
    for field in ["score", "eligible", "resolved"]:
        with pytest.raises(ValidationError):
            ItemPrerequisites.model_validate({**value.model_dump(), field: True})
    assert prerequisite_reasons(prerequisites=value, mode="independent", basis="submission_frozen") == []
    decision = decide(value, score=None)
    assert not decision.eligible and decision.normalized_score is None
    assert decision.reason_codes == ["GRADE_UNRESOLVED"]


@pytest.mark.parametrize("review", ["draft", "needs_review"])
def test_human_resolved_score_cannot_upgrade_the_original_unreviewed_answer(review):
    value = sample(answer_review_status=review)
    decision = decide(value)
    assert decision.normalized_score == 1.0 and not decision.eligible
    assert decision.reason_codes == ["ANSWER_UNREVIEWED"]
    assert value.answer_review_status == review


@pytest.mark.parametrize("mode,independence,reason", [
    ("open_book", "unknown", "MODE_OPEN_BOOK"), ("assisted", "assisted", "MODE_ASSISTED"),
])
def test_mode_capability_is_separate_from_actually_received_help(mode, independence, reason):
    decision = decide(sample(), mode=mode)
    assert not decision.eligible and decision.independence == independence
    assert decision.reason_codes == [reason] and decision.freshness == "novel"
    assert "HELP_BEFORE_SUBMIT" not in decision.reason_codes


@pytest.mark.parametrize("score", [None, 0.0, 2.5])
def test_legacy_basis_permanently_excludes_every_regrade_even_if_other_facts_look_valid(score):
    decision = decide(sample(), score=score, basis="history_not_frozen")
    assert not decision.eligible
    assert "HISTORY_PREREQUISITES_NOT_FROZEN" in decision.reason_codes
    assert ("GRADE_UNRESOLVED" in decision.reason_codes) == (score is None)


def test_all_known_exclusions_are_retained_as_finite_safe_codes():
    value = sample(concept_refs=[], source_trusted=False, answer_review_status="needs_review",
        prior_seen="unknown", pre_submission_help_state="unknown", in_attempt_help_state="present")
    decision = decide(value, score=None, mode="open_book", basis="history_not_frozen")
    assert set(decision.reason_codes) == {"HISTORY_PREREQUISITES_NOT_FROZEN", "MODE_OPEN_BOOK",
        "SOURCE_NOT_TRUSTED", "ANSWER_UNREVIEWED", "CONCEPT_MAPPING_UNRESOLVED", "PRIOR_SEEN_UNKNOWN",
        "HELP_BEFORE_SUBMIT", "HELP_HISTORY_UNKNOWN", "GRADE_UNRESOLVED"}
    assert set(decision.reason_codes) <= set(get_args(EligibilityReason))
    assert decision.reason_codes == sorted(decision.reason_codes)
    assert decision.independence == decision.freshness == "unknown"


@pytest.mark.parametrize("prior,pre,in_attempt,freshness,independence,reasons", [
    ("seen", "none", "none", "repeated", "independent", {"PREVIOUSLY_SEEN"}),
    ("unknown", "none", "none", "unknown", "independent", {"PRIOR_SEEN_UNKNOWN"}),
    ("unseen", "present", "none", "repeated", "independent", {"HELP_BEFORE_SUBMIT"}),
    ("unseen", "present", "present", "repeated", "assisted", {"HELP_BEFORE_SUBMIT"}),
    ("unseen", "unknown", "none", "unknown", "independent", {"HELP_HISTORY_UNKNOWN"}),
    ("unseen", "unknown", "unknown", "unknown", "unknown", {"HELP_HISTORY_UNKNOWN"}),
    ("seen", "unknown", "none", "repeated", "independent", {"PREVIOUSLY_SEEN", "HELP_HISTORY_UNKNOWN"}),
])
def test_prior_snapshot_and_help_windows_separate_freshness_from_this_attempt_independence(
        prior, pre, in_attempt, freshness, independence, reasons):
    value = sample(prior_seen=prior, pre_submission_help_state=pre, in_attempt_help_state=in_attempt)
    decision = decide(value)
    assert not decision.eligible and decision.freshness == freshness
    assert decision.independence == independence and set(decision.reason_codes) == reasons
    assert value.prior_seen == prior  # Output never rewrites the actual start snapshot.


def test_post_submit_help_is_not_an_input_to_the_frozen_pure_decision():
    value = sample()
    stored = canonical_bytes(value)
    expected = canonical_bytes(decide(value))
    # A later projection can differ; repeat evaluation uses the original persisted bytes.
    later = sample(prior_seen="seen", pre_submission_help_state="present", in_attempt_help_state="none")
    assert not decide(later).eligible
    restored = ItemPrerequisites.model_validate(strict_json(stored))
    assert canonical_bytes(decide(restored)) == expected


def test_missing_concept_mapping_is_excluded_without_an_invented_concept():
    value = sample(required_concept_ids=["concept_eligibility", "concept_unresolved"])
    assert not value.mapping_complete
    decision = decide(value)
    assert decision.reason_codes == ["CONCEPT_MAPPING_UNRESOLVED"]
    assert [ref.id for ref in decision.concept_refs] == ["concept_eligibility"]
    empty = decide(sample(concept_refs=[]))
    assert empty.concept_refs == [] and not empty.eligible


@pytest.mark.parametrize("change", [
    {"required_concept_ids": []}, {"required_concept_ids": ["concept_eligibility", "concept_eligibility"]},
    {"source_trusted": "true"}, {"prior_seen": "current"}, {"max_score": float("inf")},
    {"max_score": 101.0}, {"solution_revision": True}, {"solution_sha256": "bad"},
    {"pre_submission_help_state": "none", "in_attempt_help_state": "present"},
    {"pre_submission_help_state": "none", "in_attempt_help_state": "unknown"},
])
def test_strict_invalid_prerequisites_cannot_be_built(change):
    with pytest.raises(ValidationError):
        sample(**change)


def test_duplicate_or_wrong_entity_concept_refs_cannot_claim_complete_mapping():
    value = sample()
    for refs in [[value.concept_refs[0], value.concept_refs[0]], [value.question_ref],
                 [value.concept_refs[0].model_copy(update={"id": "concept_foreign"})]]:
        with pytest.raises(ValidationError):
            sample(concept_refs=refs)


@pytest.mark.parametrize("field,new_value", [("revision", 2), ("sha256", "b" * 64), ("id", "question_other")])
def test_item_grade_must_match_the_full_frozen_question_reference(field, new_value):
    value = sample()
    wrong = grade(value).model_copy(update={"question_ref": value.question_ref.model_copy(update={field: new_value})})
    with pytest.raises(EligibilityBindingError):
        finalize_eligibility(prerequisites=value, grade=wrong, mode="independent", basis="submission_frozen")


@pytest.mark.parametrize("update", [{"score": float("nan")}, {"score": float("inf")}, {"score": 3.0},
    {"score": True}, {"max_score": 3.0}, {"status": "needs_review"}, {"extra_authority": True}])
def test_model_copy_does_not_bypass_grade_integrity(update):
    value = sample()
    with pytest.raises(EligibilityBindingError):
        finalize_eligibility(prerequisites=value, grade=grade(value).model_copy(update=update),
            mode="independent", basis="submission_frozen")


def test_nested_model_copy_and_mutated_lists_are_revalidated_and_outputs_detached():
    value = sample()
    malformed = value.model_copy(update={"question_ref": value.question_ref.model_copy(update={"revision": True})})
    for invalid in [malformed, value.model_copy(update={"score": 2.5}), value.model_copy(update={"source_trusted": "yes"})]:
        with pytest.raises(EligibilityBindingError):
            validate_prerequisites(invalid)
    valid_copy = validate_prerequisites(value)
    decision = decide(value)
    expected = canonical_bytes(decision)
    value.concept_refs[0].sha256 = "c" * 64
    value.required_concept_ids.append("concept_added_later")
    assert canonical_bytes(decision) == expected
    assert valid_copy.mapping_complete


@pytest.mark.parametrize("mode,basis", [("practice", "submission_frozen"), ("independent", "latest"), (True, "submission_frozen")])
def test_undeclared_mode_or_forged_basis_cannot_silently_fall_back(mode, basis):
    with pytest.raises(EligibilityBindingError):
        decide(sample(), mode=mode, basis=basis)


def test_decision_json_roundtrip_is_strict_and_never_projects_private_text_or_pins():
    decision = decide(sample())
    payload = canonical_bytes(decision)
    assert EligibilityDecision.model_validate(strict_json(payload)) == decision
    assert b"SYNTHETIC_PRIVATE" not in payload
    assert not {"solution_revision", "solution_sha256", "response", "feedback_markdown", "solution_markdown"} & decision.model_dump().keys()
    with pytest.raises(ValidationError):
        EligibilityDecision.model_validate({**decision.model_dump(), "reason_codes": ["ARBITRARY_SECRET"]})
    with pytest.raises(EligibilityBindingError):
        evidence_reason(decision.model_copy(update={"eligible": False}))


def test_positive_tiny_score_is_not_silently_normalized_to_a_false_zero():
    value = sample(max_score=100.0)
    with pytest.raises(EligibilityBindingError):
        decide(value, score=5e-324)
