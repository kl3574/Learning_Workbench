"""Restore numeric shape checks are not source proof or execution approval."""

from copy import deepcopy
import json

import pytest
from pydantic import ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from services.api.app import restore_numeric_dto as dto
from services.api.app.content_restore_dto import ContentRestoreDraftCreateWrite, ContentRestoreDraftSnapshot


def material():
    return {
        "version": "restore-numeric-material-v1",
        "symbols": [{"name": "x", "tex": "x", "domain": "finite real", "dimension": "unitless"}],
        "plan": {
            "version": "finite-arithmetic-v1",
            "variables": [{"name": "x", "value": 2.0, "unit": "1"}],
            "assertions": [
                {"id": "assert_sum", "expression": "x+1", "expected": 3.0, "atol": 0.0, "rtol": 0.0, "unit": "1"}
            ],
            "seed": None,
        },
        "variable_bindings": [
            {"variable_name": "x", "value_source": {"start_codepoint": 2, "end_codepoint": 3, "quote": "2"}}
        ],
        "assertion_bindings": [
            {
                "assertion_id": "assert_sum",
                "expression_source": {"start_codepoint": 5, "end_codepoint": 8, "quote": "x+1"},
                "expected_source": {"start_codepoint": 9, "end_codepoint": 10, "quote": "3"},
            }
        ],
        "reason": "Synthetic explicit body-to-plan mapping; not academic approval.",
    }


def candidate():
    return {"draft_id": "restore_synthetic", "draft_revision": 1, "entity": "block", "candidate_sha256": "a" * 64}


def material_view():
    return {
        "owner": "authoring_restore",
        "candidate": candidate(),
        "restore_record_sha256": "b" * 64,
        "source_ref": {"entity": "block", "id": "synthetic_block", "revision": 1, "sha256": "c" * 64},
        "source_material_sha256": "d" * 64,
        "body_sha256": sha256_bytes(b"x=2; x+1=3.\n"),
        "material": material(),
        "numeric_material_sha256": "e" * 64,
    }


def check_view():
    return {
        "owner": "authoring_restore",
        "id": "numeric_synthetic",
        "revision": 1,
        "candidate": candidate(),
        "numeric_material_sha256": "e" * 64,
        "plan": material()["plan"],
        "runtime": {
            "evaluator_version": "finite-arithmetic-v1",
            "evaluator_sha256": "f" * 64,
            "runtime_manifest_sha256": "1" * 64,
            "python_version": "3.12.13",
            "sandbox_version": "synthetic-nonexecuted",
            "wall_seconds": 5,
            "cpu_seconds": 2,
            "memory_bytes": 268435456,
            "output_bytes": 65536,
            "evaluator_process_limit": 1,
        },
        "operation_sha256": "2" * 64,
        "decision": "pending",
        "created_at": "2026-10-02T00:00:00Z",
        "expires_at": "2026-10-02T00:10:00Z",
        "expired": False,
        "job": None,
        "job_revision": None,
        "result": None,
        "warnings": [],
    }


def snapshot(bound=True):
    view = material_view()
    block = dm.ContentBlock(
        id="synthetic_block",
        revision=3,
        kind="worked_example",
        title="Synthetic material",
        body_path="content/synthetic.md",
        body_sha256=view["body_sha256"],
        concepts=[],
        citations=[],
        depends_on=[],
    )
    return {
        "owner": "authoring_restore",
        "candidate": candidate(),
        "source_ref": view["source_ref"],
        "base_ref": {**view["source_ref"], "revision": 2, "sha256": "3" * 64},
        "reason": "Explicit restoration.",
        "proposed_block": block.model_dump(mode="json"),
        "body_markdown": "x=2; x+1=3.\n",
        "source_material_sha256": view["source_material_sha256"],
        "warnings": [],
        "state": "draft",
        "published_ref": None,
        "numeric_material": view if bound else None,
        "numeric_check_ids": ["numeric_synthetic"] if bound else [],
    }


def samples():
    value = material()
    return [
        (dto.RestoreNumericSourceSpan, value["variable_bindings"][0]["value_source"]),
        (dto.RestoreNumericVariableBinding, value["variable_bindings"][0]),
        (dto.RestoreNumericAssertionBinding, value["assertion_bindings"][0]),
        (dto.RestoreNumericMaterialWrite, value),
        (dto.RestoreNumericMaterialView, material_view()),
        (dto.RestoreNumericCheckPreviewWrite, {"candidate": candidate(), "material": value}),
        (dto.RestoreNumericCheckView, check_view()),
        (ContentRestoreDraftSnapshot, snapshot()),
    ]


@pytest.mark.parametrize(("model", "value"), samples(), ids=lambda v: v.__name__ if isinstance(v, type) else "")
def test_each_named_model_is_closed_all_required_and_hides_payload(model, value):
    parsed = model.model_validate_json(json.dumps(value))
    assert parsed.model_dump(mode="json") == value
    assert repr(parsed) == model.__name__ + "()"
    schema = model.model_json_schema()
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])
    for field in value:
        missing = deepcopy(value)
        missing.pop(field)
        with pytest.raises(ValidationError):
            model.model_validate(missing)
    for name in ("runtime_claim", "actor_session_id", "provider_receipt", "path"):
        with pytest.raises(ValidationError):
            model.model_validate({**value, name: "untrusted"})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("start_codepoint", True),
        ("start_codepoint", 1.0),
        ("start_codepoint", -1),
        ("end_codepoint", False),
        ("end_codepoint", 400001),
        ("end_codepoint", 2),
        ("end_codepoint", 516),
        ("quote", ""),
        ("quote", " \n"),
        ("quote", "a" * 513),
        ("quote", "\ud800"),
    ],
)
def test_span_codepoint_boundaries_are_strict(field, value):
    span = {"start_codepoint": 2, "end_codepoint": 3, "quote": "2", field: value}
    with pytest.raises(ValidationError):
        dto.RestoreNumericSourceSpan.model_validate(span)


@pytest.mark.parametrize(
    "fault",
    [
        "extra_symbol",
        "missing_symbol",
        "no_symbols",
        "missing_variable",
        "extra_variable",
        "duplicate_variable",
        "missing_assertion",
        "extra_assertion",
        "duplicate_assertion",
        "reason_empty",
        "reason_long",
        "bool_number",
        "infinite",
        "bool_tolerance",
        "seed",
        "runtime",
    ],
)
def test_complete_material_rejects_shape_or_structural_mismatch(fault):
    value = material()
    if fault == "extra_symbol":
        value["symbols"].append(deepcopy(value["symbols"][0]))
    elif fault == "missing_symbol":
        value["symbols"][0]["name"] = "y"
    elif fault == "no_symbols":
        value["symbols"] = []
    elif fault == "missing_variable":
        value["variable_bindings"] = []
    elif fault == "extra_variable":
        value["variable_bindings"][0]["variable_name"] = "y"
    elif fault == "duplicate_variable":
        value["variable_bindings"].append(deepcopy(value["variable_bindings"][0]))
    elif fault == "missing_assertion":
        value["assertion_bindings"] = []
    elif fault == "extra_assertion":
        value["assertion_bindings"][0]["assertion_id"] = "foreign_assertion"
    elif fault == "duplicate_assertion":
        value["assertion_bindings"].append(deepcopy(value["assertion_bindings"][0]))
    elif fault == "reason_empty":
        value["reason"] = "  "
    elif fault == "reason_long":
        value["reason"] = "α" * 2001
    elif fault == "bool_number":
        value["plan"]["variables"][0]["value"] = True
    elif fault == "infinite":
        value["plan"]["assertions"][0]["expected"] = float("inf")
    elif fault == "bool_tolerance":
        value["plan"]["assertions"][0]["atol"] = False
    elif fault == "seed":
        value["plan"]["seed"] = 0
    elif fault == "runtime":
        value["runtime"] = check_view()["runtime"]
    with pytest.raises(ValidationError):
        dto.RestoreNumericMaterialWrite.model_validate(value)


def test_shape_does_not_claim_original_body_or_decimal_semantics():
    value = material()
    value["variable_bindings"][0]["value_source"]["quote"] = "π"
    assert dto.RestoreNumericMaterialWrite.model_validate(value).variable_bindings[0].value_source.quote == "π"
    # The owner must reject this relation with 409 NUMERIC_PLAN_UNSUPPORTED,
    # after reading actual source bytes. A DTO alone cannot invent that proof.


@pytest.mark.parametrize("fault", ["owner", "entity", "revision", "duration", "job", "limits"])
def test_restore_view_preserves_existing_approval_execution_invariants(fault):
    view = check_view()
    if fault == "owner":
        view["owner"] = "authoring_single"
    elif fault == "entity":
        view["candidate"]["entity"] = "lesson"
    elif fault == "revision":
        view["revision"] = 2
    elif fault == "duration":
        view["expires_at"] = "2026-10-02T00:11:00Z"
    elif fault == "job":
        view["job"] = {"id": "job_unapproved", "status": "queued"}
    elif fault == "limits":
        view["runtime"]["evaluator_process_limit"] = True
    with pytest.raises(ValidationError):
        dto.RestoreNumericCheckView.model_validate(view)


@pytest.mark.parametrize(
    "fault",
    [
        "missing_material",
        "missing_ids",
        "duplicate_ids",
        "foreign_candidate",
        "foreign_source",
        "wrong_hash",
        "wrong_body",
        "wrong_kind",
        "orphan_ids",
        "orphan_material",
    ],
)
def test_required_restore_discovery_cannot_hide_missing_or_foreign_binding(fault):
    value = snapshot()
    if fault == "missing_material":
        value.pop("numeric_material")
    elif fault == "missing_ids":
        value.pop("numeric_check_ids")
    elif fault == "duplicate_ids":
        value["numeric_check_ids"] *= 2
    elif fault == "foreign_candidate":
        value["numeric_material"]["candidate"]["draft_id"] = "restore_other"
    elif fault == "foreign_source":
        value["numeric_material"]["source_ref"]["sha256"] = "4" * 64
        value["source_ref"] = {**value["source_ref"], "sha256": "c" * 64}
    elif fault == "wrong_hash":
        value["numeric_material"]["source_material_sha256"] = "5" * 64
    elif fault == "wrong_body":
        value["numeric_material"]["body_sha256"] = "6" * 64
    elif fault == "wrong_kind":
        value["proposed_block"]["kind"] = "text"
    elif fault == "orphan_ids":
        value["numeric_material"] = None
    elif fault == "orphan_material":
        value["numeric_check_ids"] = []
    with pytest.raises(ValidationError):
        ContentRestoreDraftSnapshot.model_validate(value)


def test_legacy_and_other_kinds_explicitly_project_null_and_empty_ids():
    for kind in ("worked_example", "text", "proof"):
        value = snapshot(False)
        value["proposed_block"]["kind"] = kind
        parsed = ContentRestoreDraftSnapshot.model_validate(value)
        assert parsed.numeric_material is None and parsed.numeric_check_ids == []


def test_original_create_cannot_accept_numeric_material_or_plan():
    view = snapshot(False)
    create = {"source_ref": view["source_ref"], "expected_current_ref": view["base_ref"], "reason": "Explicit restore."}
    for extra in ("numeric_plan", "numeric_material", "material"):
        with pytest.raises(ValidationError):
            ContentRestoreDraftCreateWrite.model_validate({**create, extra: material()})
