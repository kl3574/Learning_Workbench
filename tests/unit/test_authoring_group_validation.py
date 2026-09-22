"""Synthetic unpublished groups: byte/shape checks, no actual owner or model claims."""

import copy

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes
from services.api.app import authoring_group_dto as g
from services.api.app.authoring_dto import NumericCheckResult, NumericRuntimeProfile, numeric_result_sha256
from services.api.app.application.authoring_group_models import (
    AuthoringContentPlanRecord,
    AuthoringGroupCandidateRecord,
    AuthoringGroupJobInput,
    AuthoringGroupNumericJobInput,
    PreparedAuthoringGroupContext,
    group_context_sha256,
    group_numeric_operation_sha256,
    validate_group_context_binding,
    validate_group_numeric_result,
)
from services.api.app.application.authoring_group_validation import (
    build_group_candidate_payload,
    group_candidate_sha256,
    group_draft_view,
    group_numeric_plan,
    group_private_solution_view,
    group_target_refs,
    member_ref,
    parse_group_generated,
    parse_group_plan,
    plan_sha256,
    validate_group_context,
)

NOW = "2026-09-22T03:00:00Z"


def numeric_plan():
    return {
        "version": "finite-arithmetic-v1",
        "variables": [{"name": "x", "value": 3.0, "unit": "1"}],
        "assertions": [
            {"id": "check_double", "expression": "2*x", "expected": 6.0, "atol": 0.0, "rtol": 0.0, "unit": "1"}
        ],
        "seed": None,
    }


def symbols():
    return [{"name": "x", "tex": "x", "domain": "real", "dimension": "1"}]


def group_case(kind="practice_set", question_kind="numeric"):
    concept = dm.Concept(
        id="concept_synthetic", revision=1, title="合成概念", prerequisite_ids=[], skill_dimensions=["compute"]
    )
    concept_ref = dm.ContentRef(entity="concept", id=concept.id, revision=1, sha256=metadata_sha256(concept))
    selected = [] if kind == "lesson" else [concept_ref.model_dump()]
    request = {
        "topic": "合成生成测试",
        "prerequisites": [],
        "objectives": ["解释并计算"],
        "proof_policy": "full",
        "output_kind": kind,
        "source_refs": [],
        "provider_id": "provider_synthetic",
        "target_concept_refs": selected,
    }
    targets = [] if kind == "lesson" else [g.AuthoringTargetMaterial(ref=concept_ref, metadata=concept)]
    if kind == "practice_set":
        # Synthetic published metadata fixture; no lookup or draft ContentRef is implied.
        lesson = dm.Lesson(
            id="lesson_synthetic",
            revision=1,
            title="合成已有小节",
            objectives=["计算"],
            block_refs=[dm.ContentRef(entity="block", id="block_fixture", revision=1, sha256="a" * 64)],
        )
        lesson_ref = dm.ContentRef(entity="lesson", id=lesson.id, revision=1, sha256=metadata_sha256(lesson))
        request["lesson_ref"] = lesson_ref.model_dump()
        targets.insert(0, g.AuthoringTargetMaterial(ref=lesson_ref, metadata=lesson))
    if kind == "assessment":
        request.update(allowed_modes=["independent", "open_book"], time_limit_seconds=None)
    plan = {
        "version": "authoring-content-plan-v1",
        **{key: request[key] for key in ("topic", "prerequisites", "objectives", "proof_policy", "output_kind")},
        "entries": [],
    }
    if kind == "lesson":
        blocks = [
            {
                "member_key": "intro",
                "depends_on_keys": [],
                "payload": {
                    "version": "content-block-candidate-v1",
                    "kind": "definition",
                    "title": "合成定义",
                    "body_markdown": "定义正文。",
                    "symbols": [],
                    "declared_source_refs": [],
                },
            },
            {
                "member_key": "example",
                "depends_on_keys": ["intro"],
                "payload": {
                    "version": "worked-example-candidate-v1",
                    "kind": "worked_example",
                    "title": "合成例题",
                    "body_markdown": "令 x=3，计算 2x=6。",
                    "symbols": symbols(),
                    "declared_source_refs": [],
                    "numeric_plan": numeric_plan(),
                },
            },
        ]
        plan["entries"] = [
            {
                "member_key": x["member_key"],
                "entity": "block",
                "kind": x["payload"]["kind"],
                "title": x["payload"]["title"],
                "objective_indexes": [0],
                "prerequisite_indexes": [],
                "depends_on_keys": x["depends_on_keys"],
            }
            for x in blocks
        ]
        draft = {"output_kind": kind, "title": "合成小节草稿", "blocks": blocks}
    else:
        choices = (
            [{"id": "option_a", "text_markdown": "六"}, {"id": "option_b", "text_markdown": "七"}]
            if question_kind == "single_choice"
            else []
        )
        question = {
            "member_key": "question_one",
            "kind": question_kind,
            "stem_markdown": "合成题：计算两倍。",
            "choices": choices,
            "concept_refs": selected,
            "skill": "compute",
            "exposure_family_key": "family_local",
            "max_score": 1.0,
            "input_instructions": "",
            "declared_source_refs": [],
            "depends_on_keys": [],
        }
        graders = {
            "single_choice": "choice_exact",
            "text_blank": "text_normalized",
            "numeric": "numeric_tolerance",
            "expression": "symbolic_review",
            "calculation": "rubric_review",
        }
        answers = (
            ["option_a", "option_b"]
            if choices
            else ["6", "6.0"]
            if question_kind == "numeric"
            else ["", " original ", " original "]
        )
        answer = {
            "question_key": "question_one",
            "grading_kind": graders[question_kind],
            "accepted_answers": answers,
            "absolute_tolerance": 0.0,
            "relative_tolerance": 0.0,
            "unit": None,
            "domain_assumptions": [],
            "solution_markdown": "PRIVATE_SYNTHETIC_ANSWER",
            "rubric_markdown": "",
            "symbols": symbols(),
            "numeric_plan": numeric_plan() if question_kind == "numeric" else None,
        }
        plan["entries"] = [
            {
                "member_key": question["member_key"],
                "entity": "question",
                "kind": question_kind,
                "objective_indexes": [0],
                "prerequisite_indexes": [],
                "depends_on_keys": [],
            }
        ]
        draft = {"output_kind": kind, "title": "合成题目草稿", "questions": [question], "solutions": [answer]}
    return (
        g.AuthoringGroupPrepareWrite.model_validate(request),
        targets,
        {"version": "authoring-group-generated-v1", "content_plan": plan, "draft": draft},
    )


def built(kind="practice_set", question_kind="numeric"):
    request, targets, body = group_case(kind, question_kind)
    generated = parse_group_generated(canonical_bytes(body), request, targets, [])
    payload, validation = build_group_candidate_payload(generated, request, targets, [])
    candidate = g.AuthoringGroupCandidate(
        draft_id="group_synthetic", draft_revision=1, entity=kind, candidate_sha256=group_candidate_sha256(payload)
    )
    record = AuthoringGroupCandidateRecord(
        version="authoring-group-record-v1",
        workspace_id="workspace_synthetic",
        candidate=candidate,
        source_job_id="job_synthetic",
        provider_receipt_id="receipt_synthetic",
        plan_ref=g.AuthoringContentPlanRef(
            source_job_id="job_synthetic", plan_sha256=plan_sha256(payload.content_plan)
        ),
        payload=payload,
        validation=validation,
        created_at=NOW,
    )
    return request, targets, body, record


@pytest.mark.parametrize("kind", ["lesson", "practice_set", "assessment"])
def test_complete_group_projection_and_root_configuration(kind):
    request, _, _, record = built(kind)
    view = group_draft_view(record, [], [])
    assert view.candidate == record.candidate and view.state == "draft"
    assert b"PRIVATE_SYNTHETIC_ANSWER" not in canonical_bytes(view)
    assert "private_solutions" not in view.model_dump() and "accepted_answers" not in str(view.model_dump())
    assert (
        record.validation.mathematical
        == record.validation.sources
        == record.validation.independent_pedagogy
        == "NOT_RUN"
    )
    assert record.validation.structure_passed()
    if kind != "lesson":
        private = group_private_solution_view(record, "question_one")
        assert private.payload.review_status == "needs_review"
        assert private.payload.answer.accepted_answers == ["6", "6.0"]
        assert record.validation.question_checks[0].answer_uniqueness == "NOT_RUN"
    if kind == "practice_set":
        assert record.payload.root.lesson_ref == request.root.lesson_ref
        assert record.payload.root.feedback_policy == "on_submit_or_reveal"
    if kind == "assessment":
        assert record.payload.root.allowed_modes == request.root.allowed_modes
        assert record.payload.root.time_limit_seconds is None


@pytest.mark.parametrize("kind", ["single_choice", "text_blank", "numeric", "expression", "calculation"])
def test_all_existing_question_kinds_preserve_full_answers(kind):
    _, _, body, record = built(question_kind=kind)
    assert (
        record.payload.private_solutions[0].answer.accepted_answers == body["draft"]["solutions"][0]["accepted_answers"]
    )
    assert all(
        getattr(record.validation.question_checks[0], field) == "NOT_RUN"
        for field in (
            "answer_uniqueness",
            "distractor_reasonableness",
            "condition_sufficiency",
            "unit_semantics",
            "solution_grading_semantics",
            "objective_alignment",
            "prerequisite_sufficiency",
        )
    )


@pytest.mark.parametrize(
    "mutation", ["private_in_public", "missing_solution", "extra_solution", "wrong_key", "wrong_grader", "nonfinite"]
)
def test_valid_plan_survives_separate_invalid_draft(mutation):
    request, targets, body = group_case()
    if mutation == "private_in_public":
        body["draft"]["questions"][0]["answer"] = "secret"
    if mutation == "missing_solution":
        body["draft"]["solutions"] = []
    if mutation == "extra_solution":
        body["draft"]["solutions"] *= 2
    if mutation == "wrong_key":
        body["draft"]["solutions"][0]["question_key"] = "other_question"
    if mutation == "wrong_grader":
        body["draft"]["solutions"][0]["grading_kind"] = "choice_exact"
    if mutation == "nonfinite":
        body["draft"]["solutions"][0]["accepted_answers"] = ["Infinity"]
    raw = canonical_bytes(body)
    plan = parse_group_plan(raw, request)
    assert plan.output_kind == request.output_kind
    with pytest.raises(ValueError):
        parse_group_generated(raw, request, targets, [])


@pytest.mark.parametrize("mutation", ["proof", "objective", "index", "duplicate", "cycle", "root_kind", "title"])
def test_plan_request_membership_and_order_fail_closed(mutation):
    request, targets, body = group_case("lesson")
    if mutation == "proof":
        body["content_plan"]["proof_policy"] = "declared_dependencies"
    if mutation == "objective":
        body["content_plan"]["objectives"] = ["另外目标"]
    if mutation == "index":
        body["content_plan"]["entries"][0]["objective_indexes"] = [1]
    if mutation == "duplicate":
        body["content_plan"]["entries"][1]["member_key"] = "intro"
    if mutation == "cycle":
        body["content_plan"]["entries"][0]["depends_on_keys"] = ["example"]
    if mutation == "root_kind":
        body["draft"]["output_kind"] = "assessment"
    if mutation == "title":
        body["draft"]["blocks"][0]["payload"]["title"] = "替换计划标题"
    with pytest.raises(ValueError):
        parse_group_generated(canonical_bytes(body), request, targets, [])


@pytest.mark.parametrize("mutation", ["extra", "duplicate", "fence", "over_budget"])
def test_entire_response_is_strict_and_bounded(mutation):
    request, _, body = group_case()
    raw = canonical_bytes(body)
    if mutation == "extra":
        raw = raw[:-1] + b',"unexpected":true}'
    if mutation == "duplicate":
        raw = raw[:-1] + b',"version":"authoring-group-generated-v1"}'
    if mutation == "fence":
        raw = b"```json\n" + raw + b"\n```"
    if mutation == "over_budget":
        raw = b" " * (g.MAX_GROUP_OUTPUT_BYTES + 1)
    with pytest.raises(ValueError):
        parse_group_plan(raw, request)


def test_exact_targets_order_scope_and_source_references():
    request, targets, body = group_case()
    assert [x.entity for x in group_target_refs(request)] == ["lesson", "concept"]
    for wrong in (targets[::-1], targets[:1], targets + targets):
        with pytest.raises(ValueError):
            validate_group_context(request, wrong, [])
    body["draft"]["questions"][0]["concept_refs"][0]["sha256"] = "f" * 64
    with pytest.raises(ValueError):
        parse_group_generated(canonical_bytes(body), request, targets, [])
    request, targets, body = group_case("lesson")
    body["draft"]["blocks"][0]["payload"]["declared_source_refs"] = [
        {"entity": "block", "id": "unselected", "revision": 1, "sha256": "f" * 64}
    ]
    with pytest.raises(ValueError):
        parse_group_generated(canonical_bytes(body), request, targets, [])


def test_private_edit_changes_entire_group_identity_without_changing_public_question():
    request, targets, body, record = built()
    changed = copy.deepcopy(body)
    changed["draft"]["solutions"][0]["accepted_answers"] = ["7"]
    generated = parse_group_generated(canonical_bytes(changed), request, targets, [])
    payload, _ = build_group_candidate_payload(generated, request, targets, [])
    assert member_ref(payload.questions[0]) == member_ref(record.payload.questions[0])
    assert group_candidate_sha256(payload) != record.candidate.candidate_sha256
    bad = record.model_dump()
    bad["payload"] = payload.model_dump()
    with pytest.raises(ValueError):
        AuthoringGroupCandidateRecord.model_validate(bad)


@pytest.mark.parametrize("mutation", ["question_hash", "private_hash", "root_member", "missing_quality", "plan_job"])
def test_group_record_and_public_projection_reject_tampered_relationships(mutation):
    _, _, _, record = built()
    if mutation == "private_hash":
        view = group_private_solution_view(record, "question_one").model_dump()
        view["ref"]["solution_sha256"] = "0" * 64
        with pytest.raises(ValueError):
            g.AuthoringPrivateSolutionView.model_validate(view)
        return
    value = record.model_dump()
    if mutation == "question_hash":
        value["payload"]["private_solutions"][0]["question"]["member_sha256"] = "0" * 64
    if mutation == "root_member":
        value["payload"]["root"]["questions"][0]["member_key"] = "other"
    if mutation == "missing_quality":
        value["validation"]["question_checks"] = []
    if mutation == "plan_job":
        value["plan_ref"]["source_job_id"] = "other_job"
    with pytest.raises(ValueError):
        AuthoringGroupCandidateRecord.model_validate(value)


def runtime():
    return NumericRuntimeProfile(
        evaluator_version="finite-arithmetic-v1",
        evaluator_sha256="a" * 64,
        runtime_manifest_sha256="b" * 64,
        python_version="synthetic",
        sandbox_version="synthetic",
        wall_seconds=5,
        cpu_seconds=2,
        memory_bytes=268435456,
        output_bytes=65536,
        evaluator_process_limit=1,
    )


def test_group_numeric_operation_binds_root_member_and_actual_input():
    _, _, _, record = built()
    target = member_ref(record.payload.questions[0])
    plan = group_numeric_plan(record.payload, target)
    operation = group_numeric_operation_sha256(
        record.workspace_id, "check_one", record.candidate, target, plan, runtime()
    )
    value = AuthoringGroupNumericJobInput(
        version="authoring-group-numeric-job-v1",
        workspace_id=record.workspace_id,
        job_id="numeric_job",
        check_id="check_one",
        operation_sha256=operation,
        candidate=record.candidate,
        target=target,
        plan=plan,
        runtime=runtime(),
    )
    altered = value.model_dump()
    altered["candidate"]["candidate_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        AuthoringGroupNumericJobInput.model_validate(altered)
    result_data = {
        "job_id": value.job_id,
        "input_sha256": sha256_bytes(canonical_bytes(value)),
        "operation_sha256": operation,
        "outcome": "environment_unavailable",
        "verdict": "BLOCKED",
        "started_at": None,
        "finished_at": NOW,
        "exit_code": 1,
        "assertions": [],
        "output_sha256": None,
        "result_sha256": "0" * 64,
    }
    result_data["result_sha256"] = numeric_result_sha256(result_data)
    result = NumericCheckResult.model_validate(result_data)
    validate_group_numeric_result(value, result)
    result_data["input_sha256"] = "0" * 64
    result_data["result_sha256"] = numeric_result_sha256(result_data)
    with pytest.raises(ValueError):
        validate_group_numeric_result(value, NumericCheckResult.model_validate(result_data))


def test_numeric_plan_is_selected_only_from_exact_group_member():
    _, _, _, record = built("lesson")
    with pytest.raises(ValueError, match="UNSUPPORTED"):
        group_numeric_plan(record.payload, member_ref(record.payload.blocks[0]))
    target = member_ref(record.payload.blocks[1])
    assert group_numeric_plan(record.payload, target).assertions[0].expected == 6
    with pytest.raises(ValueError):
        group_numeric_plan(record.payload, target.model_copy(update={"member_sha256": "0" * 64}))
    _, _, _, record = built(question_kind="text_blank")
    with pytest.raises(ValueError, match="UNSUPPORTED"):
        group_numeric_plan(record.payload, member_ref(record.payload.questions[0]))


def test_complete_prepared_context_hashes_target_metadata_without_provider_reference_expansion():
    request, targets, _, _ = built()
    value = AuthoringGroupJobInput(
        version="authoring-group-job-v1", workspace_id="workspace_synthetic", job_id="job_synthetic", request=request
    )
    user = canonical_bytes(
        {"request": request.model_dump(mode="json"), "targets": [x.model_dump(mode="json") for x in targets]}
    ).decode()
    messages = [
        dm.GenerationMessage(role="system", content="synthetic trusted template"),
        dm.GenerationMessage(role="user", content=user),
    ]
    snapshot = dm.ContextSnapshot(
        id="context_one",
        created_at=NOW,
        policy="authoring",
        request_sha256=sha256_bytes(canonical_bytes(request)),
        resolved_refs=[],
        character_count=sum(len(x.content) for x in messages),
        snapshot_sha256="0" * 64,
    )
    context = PreparedAuthoringGroupContext(
        version="authoring-group-context-v1",
        job_id=value.job_id,
        snapshot=snapshot,
        template_version="synthetic-v1",
        messages=messages,
        evidence=[],
        materials=[],
        targets=targets,
        warnings=[],
    )
    context.snapshot.snapshot_sha256 = group_context_sha256(context)
    validate_group_context_binding(value, context)
    forged = context.model_dump()
    forged["snapshot"]["resolved_refs"] = [targets[0].ref.model_dump()]
    with pytest.raises(ValueError):
        PreparedAuthoringGroupContext.model_validate(forged)
    changed = context.model_dump()
    changed["snapshot"]["snapshot_sha256"] = "a" * 64
    with pytest.raises(ValueError):
        validate_group_context_binding(value, PreparedAuthoringGroupContext.model_validate(changed))


def test_legitimate_plan_record_can_exist_without_a_successful_draft():
    request, _, body = group_case()
    body["draft"] = None
    plan = parse_group_plan(canonical_bytes(body), request)
    record = AuthoringContentPlanRecord(
        version="authoring-content-plan-record-v1",
        workspace_id="workspace_synthetic",
        source_job_id="job_synthetic",
        provider_receipt_id="receipt_synthetic",
        job_input_sha256="a" * 64,
        plan_ref=g.AuthoringContentPlanRef(source_job_id="job_synthetic", plan_sha256=plan_sha256(plan)),
        plan=plan,
        created_at=NOW,
    )
    assert record.plan == plan
    assert not hasattr(record, "candidate")
