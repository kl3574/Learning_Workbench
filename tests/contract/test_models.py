"""Model regression tests do not constitute end-to-end acceptance scenarios."""
import math

from jsonschema import Draft202012Validator
import pytest
from pydantic import ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, snapshot_sha256, strict_json


def question() -> dm.QuestionPublic:
    return dm.QuestionPublic(id="question_test", revision=1, kind="numeric", stem_markdown="求值",
                             concept_ids=["concept_test"], skill="compute", exposure_group="group_test",
                             input_instructions="输入有限实数")


def test_all_model_schemas_are_strict_2020_12():
    for model in dm.CONTRACTS.values():
        schema = model.model_json_schema()
        Draft202012Validator.check_schema(schema)
        assert schema["additionalProperties"] is False


@pytest.mark.parametrize("field", ["answer", "solution", "rubric_private", "solution_ref", "accepted_answers"])
def test_public_question_rejects_private_answer_fields(field):
    payload = question().model_dump(mode="json") | {field: "secret-canary"}
    with pytest.raises(ValidationError):
        dm.QuestionPublic.model_validate(payload)
    assert not Draft202012Validator(dm.QuestionPublic.model_json_schema()).is_valid(payload)


@pytest.mark.parametrize("revision", [0, -1, "1", True, 1.2])
def test_exact_reference_rejects_invalid_revision(revision):
    with pytest.raises(ValidationError):
        dm.ContentRef(entity="lesson", id="lesson_test", revision=revision, sha256="a" * 64)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_nonfinite_numbers_rejected(value):
    with pytest.raises(ValidationError):
        dm.QuestionPublic.model_validate(question().model_dump(mode="json") | {"max_score": value})
    with pytest.raises(ValueError):
        canonical_bytes({"x": value})


def test_default_float_roundtrip_hash_is_stable():
    original = question()
    validated = dm.QuestionPublic.model_validate(original.model_dump(mode="json"))
    assert original.model_dump(mode="json")["max_score"] == 1.0
    assert metadata_sha256(original) == metadata_sha256(validated)
    assert b'"max_score":1.0' in canonical_bytes(original)


def test_canonical_bytes_are_unicode_sorted_compact_utf8():
    assert canonical_bytes({"𐀀": 2, "": 1, "中文": "值"}) == '{"中文":"值","":1,"𐀀":2}'.encode()
    assert canonical_bytes({"a": 1}) != canonical_bytes({"a": 1.0})


@pytest.mark.parametrize("payload", ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'])
def test_strict_json_rejects_ambiguous_or_nonfinite_values(payload):
    with pytest.raises(ValueError):
        strict_json(payload)


def test_snapshot_hash_excludes_only_own_hash():
    snapshot = dm.ContextSnapshot(id="snapshot_test", created_at="2026-09-14T00:00:00Z",
                                  request_sha256="a" * 64, resolved_refs=[], policy="learning",
                                  character_count=0, snapshot_sha256="b" * 64)
    changed = snapshot.model_copy(update={"snapshot_sha256": "c" * 64})
    assert snapshot_sha256(snapshot) == snapshot_sha256(changed)
    assert snapshot_sha256(snapshot) != snapshot_sha256(snapshot.model_copy(update={"request_sha256": "d" * 64}))


@pytest.mark.parametrize("mode,scope,web,materials", [
    ("independent", "academic", False, False), ("independent", "operation_help_only", True, False),
    ("independent", "operation_help_only", False, True), ("open_book", "academic", False, True),
    ("open_book", "operation_help_only", True, True), ("assisted", "operation_help_only", False, True),
])
def test_policy_rejects_inconsistent_assistance(mode, scope, web, materials):
    with pytest.raises(ValidationError):
        dm.PolicySnapshot(mode=mode, tutor_scope=scope, allow_web=web, allow_materials=materials)


def test_grade_unknown_is_null_and_score_never_exceeds_max():
    reference = dm.ContentRef(entity="question", id="question_test", revision=1, sha256="a" * 64)
    valid = dm.ItemGrade(question_ref=reference, status="needs_review", max_score=1.0, feedback_markdown="待审")
    assert valid.score is None
    for status, score in [("needs_review", 0.0), ("graded", None), ("graded", 2.0)]:
        with pytest.raises(ValidationError):
            dm.ItemGrade(question_ref=reference, status=status, score=score, max_score=1.0, feedback_markdown="待审")


def test_utc_and_event_payload_are_semantically_checked():
    for time in ["2026-02-30T00:00:00Z", "2026-09-14T00:00:00+08:00"]:
        with pytest.raises(ValidationError):
            dm.RunEvent(run_id="run_test", seq=1, type="queued", occurred_at=time)
    with pytest.raises(ValidationError):
        dm.RunEvent(run_id="run_test", seq=1, type="answer_delta", occurred_at="2026-09-14T00:00:00Z")
