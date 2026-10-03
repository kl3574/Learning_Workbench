"""Pure construction and exact relationships for unpublished Authoring groups.

The caller owns current Policy, real Content/Provider records and transactions.
No helper resolves a ref, publishes content, assigns permission or calls a model.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, overload

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, strict_json
from .. import authoring_group_dto as g
from ..authoring_dto import AuthoringInputMaterial, NumericPlan, WorkedExamplePayload
from .question_solution_validation import validate_grading_structure

if TYPE_CHECKING:
    from .authoring_group_models import AuthoringGroupCandidateRecord


def same(left: object, right: object) -> bool:
    return canonical_bytes(left) == canonical_bytes(right)


def group_target_refs(request: g.AuthoringGroupPrepareWrite) -> list[dm.ContentRef]:
    request = g.AuthoringGroupPrepareWrite.model_validate(request.model_dump(mode="python"))
    values: list[dm.ContentRef] = []
    if isinstance(request.root, g.AuthoringPracticePrepareWrite):
        values.append(dm.ContentRef.model_validate(request.root.lesson_ref.model_dump()))
    values.extend(dm.ContentRef.model_validate(ref.model_dump()) for ref in request.target_concept_refs)
    return values


def validate_group_context(
    request: g.AuthoringGroupPrepareWrite,
    targets: Sequence[g.AuthoringTargetMaterial],
    materials: Sequence[AuthoringInputMaterial],
) -> None:
    request = g.AuthoringGroupPrepareWrite.model_validate(request.model_dump(mode="python"))
    checked_targets = [g.AuthoringTargetMaterial.model_validate(x.model_dump(mode="python")) for x in targets]
    checked_materials = [AuthoringInputMaterial.model_validate(x.model_dump(mode="python")) for x in materials]
    if (
        len(targets) > 33
        or len(materials) > 8
        or [canonical_bytes(x.ref) for x in checked_targets] != [canonical_bytes(x) for x in group_target_refs(request)]
        or [canonical_bytes(x.ref) for x in checked_materials] != [canonical_bytes(x) for x in request.source_refs]
    ):
        raise ValueError("preparation must preserve exactly every requested target and source in original order")


def validate_plan_request(plan: g.AuthoringContentPlan, request: g.AuthoringGroupPrepareWrite) -> None:
    plan = g.AuthoringContentPlan.model_validate(plan.model_dump(mode="python"))
    request = g.AuthoringGroupPrepareWrite.model_validate(request.model_dump(mode="python"))
    for field in ("output_kind", "topic", "prerequisites", "objectives", "proof_policy"):
        if getattr(plan, field) != getattr(request, field):
            raise ValueError("the plan must preserve the complete original request constraints")


def plan_sha256(plan: g.AuthoringContentPlan) -> str:
    return metadata_sha256(g.AuthoringContentPlan.model_validate(plan.model_dump(mode="python")))


@overload
def member_ref(member: g.AuthoringGeneratedBlock) -> g.AuthoringBlockMemberRef: ...


@overload
def member_ref(member: g.QuestionDraftPublic) -> g.AuthoringQuestionMemberRef: ...


def member_ref(member: g.AuthoringGeneratedBlock | g.QuestionDraftPublic) -> g.AuthoringDraftMemberRef:
    if isinstance(member, g.AuthoringGeneratedBlock):
        block = g.AuthoringGeneratedBlock.model_validate(member.model_dump(mode="python"))
        return g.AuthoringBlockMemberRef(
            member_key=block.member_key, entity="block", member_sha256=metadata_sha256(block)
        )
    question = g.QuestionDraftPublic.model_validate(member.model_dump(mode="python"))
    return g.AuthoringQuestionMemberRef(
        member_key=question.member_key, entity="question", member_sha256=metadata_sha256(question)
    )


def solution_sha256(solution: g.SolutionDraftPrivate) -> str:
    return metadata_sha256(g.SolutionDraftPrivate.model_validate(solution.model_dump(mode="python")))


def _answer_rules(question: g.QuestionDraftPublic, answer: g.GeneratedSolutionAnswer) -> None:
    if question.member_key != answer.question_key:
        raise ValueError("private answer has another question member key")
    validate_grading_structure(
        question_kind=question.kind,
        grading_kind=answer.grading_kind,
        choice_ids=[choice.id for choice in question.choices],
        accepted_answers=answer.accepted_answers,
    )


def _plan_members(
    plan: g.AuthoringContentPlan,
    blocks: Sequence[g.AuthoringGeneratedBlock],
    questions: Sequence[g.QuestionDraftPublic],
) -> None:
    members: list[g.AuthoringGeneratedBlock | g.QuestionDraftPublic]
    members = list(blocks) if plan.output_kind == "lesson" else list(questions)
    if (
        plan.output_kind == "lesson"
        and questions
        or plan.output_kind != "lesson"
        and blocks
        or [x.member_key for x in plan.entries] != [x.member_key for x in members]
    ):
        raise ValueError("plan and ordered members must match exactly without missing or extra members")
    for entry, member in zip(plan.entries, members, strict=True):
        if isinstance(member, g.AuthoringGeneratedBlock):
            if (
                not isinstance(entry, g.AuthoringBlockPlanEntry)
                or entry.kind != member.payload.kind
                or entry.title != member.payload.title
            ):
                raise ValueError("block kind and exact title must match the authoritative plan entry")
        elif not isinstance(entry, g.AuthoringQuestionPlanEntry) or entry.kind != member.kind:
            raise ValueError("question kind must match its authoritative plan entry")
        if entry.depends_on_keys != member.depends_on_keys:
            raise ValueError("member dependencies must preserve the plan exact earlier-member edges")


def validate_generated_members(generated: g.AuthoringGroupGenerated) -> None:
    draft, plan = generated.draft, generated.content_plan
    if draft.output_kind != plan.output_kind:
        raise ValueError("generated root kind must match its content plan")
    if isinstance(draft, g.AuthoringLessonGenerated):
        _plan_members(plan, draft.blocks, [])
    else:
        _plan_members(plan, [], draft.questions)
        keys = [x.question_key for x in draft.solutions]
        if len(keys) != len(set(keys)) or set(keys) != {x.member_key for x in draft.questions}:
            raise ValueError("each generated question needs exactly one separate private answer")
        answers = {x.question_key: x for x in draft.solutions}
        for question in draft.questions:
            _answer_rules(question, answers[question.member_key])


def _envelope(raw: str | bytes) -> dict:
    data = raw.encode("utf-8") if isinstance(raw, str) else raw
    if not isinstance(data, bytes) or len(data) > g.MAX_GROUP_OUTPUT_BYTES:
        raise ValueError("group response exceeds the complete four MiB byte budget")
    value = strict_json(data)
    if (
        not isinstance(value, dict)
        or set(value) != {"version", "content_plan", "draft"}
        or value["version"] != "authoring-group-generated-v1"
    ):
        raise ValueError("expected the entire closed group response envelope")
    return value


def parse_group_plan(raw: str | bytes, request: g.AuthoringGroupPrepareWrite) -> g.AuthoringContentPlan:
    """Retain a valid request-bound plan even if the separate draft is invalid."""
    plan = g.AuthoringContentPlan.model_validate(_envelope(raw)["content_plan"])
    validate_plan_request(plan, request)
    return plan


def parse_group_generated(
    raw: str | bytes,
    request: g.AuthoringGroupPrepareWrite,
    targets: Sequence[g.AuthoringTargetMaterial],
    materials: Sequence[AuthoringInputMaterial],
) -> g.AuthoringGroupGenerated:
    value = g.AuthoringGroupGenerated.model_validate(_envelope(raw))
    _validate_generation_inputs(value, request, targets, materials)
    return value


def _validate_generation_inputs(
    generated: g.AuthoringGroupGenerated,
    request: g.AuthoringGroupPrepareWrite,
    targets: Sequence[g.AuthoringTargetMaterial],
    materials: Sequence[AuthoringInputMaterial],
) -> None:
    validate_group_context(request, targets, materials)
    validate_plan_request(generated.content_plan, request)
    validate_generated_members(generated)
    allowed_sources = {canonical_bytes(x.ref) for x in materials}
    allowed_concepts = {canonical_bytes(x) for x in request.target_concept_refs}
    if isinstance(generated.draft, g.AuthoringLessonGenerated):
        source_lists = [x.payload.declared_source_refs for x in generated.draft.blocks]
    else:
        source_lists = [x.declared_source_refs for x in generated.draft.questions]
        for question in generated.draft.questions:
            if any(canonical_bytes(ref) not in allowed_concepts for ref in question.concept_refs):
                raise ValueError("question concepts must be actual explicitly prepared exact Concept targets")
    if any(canonical_bytes(ref) not in allowed_sources for refs in source_lists for ref in refs):
        raise ValueError("declared sources must be actual explicitly prepared exact source blocks")


def _quality(question: g.QuestionDraftPublic) -> g.AuthoringQuestionQuality:
    return g.AuthoringQuestionQuality(
        question=member_ref(question),
        grading_compatibility="PASS",
        accepted_answer_membership="PASS",
        answer_uniqueness="NOT_RUN",
        distractor_reasonableness="NOT_RUN",
        condition_sufficiency="NOT_RUN",
        unit_semantics="NOT_RUN",
        solution_grading_semantics="NOT_RUN",
        objective_alignment="NOT_RUN",
        prerequisite_sufficiency="NOT_RUN",
    )


def group_not_run() -> g.AuthoringGroupValidation:
    return g.AuthoringGroupValidation.model_validate(
        {
            "schema": "NOT_RUN",
            "references": "NOT_RUN",
            "symbol_declarations": "NOT_RUN",
            "issues": [],
            "mathematical": "NOT_RUN",
            "sources": "NOT_RUN",
            "independent_pedagogy": "NOT_RUN",
            "plan_membership": "NOT_RUN",
            "private_bindings": "NOT_RUN",
            "question_checks": [],
        }
    )


def build_group_candidate_payload(
    generated: g.AuthoringGroupGenerated,
    request: g.AuthoringGroupPrepareWrite,
    targets: Sequence[g.AuthoringTargetMaterial],
    materials: Sequence[AuthoringInputMaterial],
) -> tuple[g.AuthoringGroupCandidatePayload, g.AuthoringGroupValidation]:
    generated = g.AuthoringGroupGenerated.model_validate(generated.model_dump(mode="python"))
    request = g.AuthoringGroupPrepareWrite.model_validate(request.model_dump(mode="python"))
    _validate_generation_inputs(generated, request, targets, materials)
    draft = generated.draft
    blocks: list[g.AuthoringGeneratedBlock] = []
    questions: list[g.QuestionDraftPublic] = []
    private: list[g.SolutionDraftPrivate] = []
    root: g.LessonCandidateRoot | g.PracticeSetCandidateRoot | g.AssessmentCandidateRoot
    if isinstance(draft, g.AuthoringLessonGenerated):
        blocks = draft.blocks
        root = g.LessonCandidateRoot(
            entity="lesson",
            title=draft.title,
            objectives=request.objectives,
            prerequisites=request.prerequisites,
            proof_policy=request.proof_policy,
            blocks=[member_ref(x) for x in blocks],
        )
    else:
        questions = draft.questions
        answers = {x.question_key: x for x in draft.solutions}
        private = [
            g.SolutionDraftPrivate(question=member_ref(q), answer=answers[q.member_key], review_status="needs_review")
            for q in questions
        ]
        if isinstance(request.root, g.AuthoringPracticePrepareWrite):
            root = g.PracticeSetCandidateRoot(
                entity="practice_set",
                title=draft.title,
                lesson_ref=request.root.lesson_ref,
                questions=[member_ref(x) for x in questions],
                feedback_policy="on_submit_or_reveal",
            )
        elif isinstance(request.root, g.AuthoringAssessmentPrepareWrite):
            root = g.AssessmentCandidateRoot(
                entity="assessment",
                title=draft.title,
                questions=[member_ref(x) for x in questions],
                allowed_modes=request.root.allowed_modes,
                time_limit_seconds=request.root.time_limit_seconds,
            )
        else:
            raise ValueError("question root must match its exact request variant")
    payload = g.AuthoringGroupCandidatePayload(
        version="authoring-group-candidate-v1",
        content_plan=generated.content_plan,
        root=root,
        blocks=blocks,
        questions=questions,
        private_solutions=private,
    )
    validation = g.AuthoringGroupValidation.model_validate(
        {
            "schema": "PASS",
            "references": "PASS",
            "symbol_declarations": "PASS",
            "issues": [],
            "mathematical": "NOT_RUN",
            "sources": "NOT_RUN",
            "independent_pedagogy": "NOT_RUN",
            "plan_membership": "PASS",
            "private_bindings": "PASS",
            "question_checks": [_quality(q).model_dump() for q in questions],
        }
    )
    return payload, validation


def _root_members(
    plan: g.AuthoringContentPlan,
    root: g.LessonCandidateRoot | g.PracticeSetCandidateRoot | g.AssessmentCandidateRoot,
    blocks: Sequence[g.AuthoringGeneratedBlock],
    questions: Sequence[g.QuestionDraftPublic],
) -> None:
    if root.entity != plan.output_kind:
        raise ValueError("candidate root and plan kinds must agree")
    _plan_members(plan, blocks, questions)
    if isinstance(root, g.LessonCandidateRoot):
        if (
            root.objectives != plan.objectives
            or root.prerequisites != plan.prerequisites
            or root.proof_policy != plan.proof_policy
            or [canonical_bytes(x) for x in root.blocks] != [canonical_bytes(member_ref(x)) for x in blocks]
        ):
            raise ValueError("lesson root must bind the complete ordered blocks and original plan constraints")
    elif [canonical_bytes(x) for x in root.questions] != [canonical_bytes(member_ref(x)) for x in questions]:
        raise ValueError("question root must bind every exact ordered question member")


def validate_group_payload(payload: g.AuthoringGroupCandidatePayload) -> None:
    _root_members(payload.content_plan, payload.root, payload.blocks, payload.questions)
    if isinstance(payload.root, g.LessonCandidateRoot):
        if payload.private_solutions:
            raise ValueError("lesson groups cannot contain private question answers")
    else:
        if [x.question.member_key for x in payload.private_solutions] != [x.member_key for x in payload.questions]:
            raise ValueError("group private answers must cover every question once in root order")
        for question, private in zip(payload.questions, payload.private_solutions, strict=True):
            if not same(member_ref(question), private.question):
                raise ValueError("private answer must bind the exact complete public question payload")
            _answer_rules(question, private.answer)


def group_candidate_sha256(payload: g.AuthoringGroupCandidatePayload) -> str:
    return metadata_sha256(g.AuthoringGroupCandidatePayload.model_validate(payload.model_dump(mode="python")))


def validate_group_candidate(
    candidate: g.AuthoringGroupCandidate,
    payload: g.AuthoringGroupCandidatePayload,
    validation: g.AuthoringGroupValidation,
) -> None:
    candidate = g.AuthoringGroupCandidate.model_validate(candidate.model_dump())
    validation = g.AuthoringGroupValidation.model_validate(validation.model_dump())
    if (
        candidate.draft_revision != 1
        or candidate.entity != payload.root.entity
        or candidate.candidate_sha256 != group_candidate_sha256(payload)
    ):
        raise ValueError("group identity must bind its entire immutable plan, members and private answers")
    if not validation.structure_passed() or [canonical_bytes(x.question) for x in validation.question_checks] != [
        canonical_bytes(member_ref(x)) for x in payload.questions
    ]:
        raise ValueError("structural checks must cover all and only the exact group questions")


def validate_group_draft_projection(view: g.AuthoringGroupDraftView) -> None:
    """Validate visible membership; the owner must separately verify the private full group hash."""
    _root_members(view.content_plan, view.root, view.blocks, view.questions)
    if (
        view.candidate.entity != view.root.entity
        or view.candidate.draft_revision != 1
        or view.plan_ref.source_job_id != view.source_job_id
        or view.plan_ref.plan_sha256 != plan_sha256(view.content_plan)
        or not view.validation.structure_passed()
    ):
        raise ValueError("draft projection must preserve its root, source plan and structural facts")
    expected = [canonical_bytes(member_ref(x)) for x in view.questions]
    if [canonical_bytes(x.question) for x in view.private_solution_refs] != expected or [
        canonical_bytes(x.question) for x in view.validation.question_checks
    ] != expected:
        raise ValueError("public draft projection needs exact private hash references and per-question checks")
    g.unique(view.numeric_check_ids, "numeric preview identities must be distinct")


def _checked_record(record: AuthoringGroupCandidateRecord) -> AuthoringGroupCandidateRecord:
    from .authoring_group_models import AuthoringGroupCandidateRecord

    return AuthoringGroupCandidateRecord.model_validate(record.model_dump(mode="python"))


def group_draft_view(
    record: AuthoringGroupCandidateRecord, numeric_check_ids: list[str], warnings: list[dm.Warning]
) -> g.AuthoringGroupDraftView:
    record = _checked_record(record)
    payload = record.payload
    return g.AuthoringGroupDraftView(
        owner="authoring",
        candidate=record.candidate,
        source_job_id=record.source_job_id,
        state="draft",
        base_ref=None,
        plan_ref=record.plan_ref,
        content_plan=payload.content_plan,
        root=payload.root,
        blocks=payload.blocks,
        questions=payload.questions,
        private_solution_refs=[
            g.AuthoringPrivateSolutionRef(question=x.question, solution_sha256=solution_sha256(x))
            for x in payload.private_solutions
        ],
        validation=record.validation,
        numeric_check_ids=numeric_check_ids,
        warnings=warnings,
    )


def group_private_solution_view(
    record: AuthoringGroupCandidateRecord, member_key: str
) -> g.AuthoringPrivateSolutionView:
    record = _checked_record(record)
    selected = next((x for x in record.payload.private_solutions if x.question.member_key == member_key), None)
    if selected is None:
        raise ValueError("private solution is not a member of this group")
    return g.AuthoringPrivateSolutionView(
        candidate=record.candidate,
        ref=g.AuthoringPrivateSolutionRef(question=selected.question, solution_sha256=solution_sha256(selected)),
        payload=selected,
    )


def group_numeric_plan(payload: g.AuthoringGroupCandidatePayload, target: g.AuthoringDraftMemberRef) -> NumericPlan:
    payload = g.AuthoringGroupCandidatePayload.model_validate(payload.model_dump(mode="python"))
    target = g.AuthoringDraftMemberRef.model_validate(target.model_dump())
    plan = None
    if target.entity == "block":
        block = next((x for x in payload.blocks if same(member_ref(x), target)), None)
        if block is None:
            raise ValueError("numeric target is not an exact member of this group")
        if isinstance(block.payload, WorkedExamplePayload):
            plan = block.payload.numeric_plan
    else:
        private = next((x for x in payload.private_solutions if same(x.question, target)), None)
        if private is None:
            raise ValueError("numeric target is not an exact member of this group")
        plan = private.answer.numeric_plan
    if plan is None:
        raise ValueError("NUMERIC_PLAN_UNSUPPORTED")
    return NumericPlan.model_validate(plan.model_dump(mode="python"))
