"""Closed group Authoring DTOs, PRODUCT_DESIGN 3.0.7 appendix A.

These models validate shape and byte relationships, never actual ownership,
permission, Provider authorization, publication or mathematical correctness.
"""

from datetime import timedelta
from typing import Annotated, Literal, Self

from pydantic import Field, RootModel, model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256
from .authoring_dto import (
    AuthoringJobView,
    AuthoringModel,
    AuthoringPreparationSummary,
    AuthoringValidation,
    BlockRefs,
    FiniteNumber,
    NonBlank,
    NonNegativeNumber,
    NumericCheckResult,
    NumericPlan,
    NumericRuntimeProfile,
    WorkedExamplePayload,
    WorkedExampleSymbol,
    _check_assertions,
    _time,
)
from .application.provider_models import UsageSnapshot

MAX_GROUP_OUTPUT_BYTES = 4 * 1024 * 1024
BlockKind = Literal[
    "orientation",
    "definition",
    "theorem",
    "proof",
    "intuition",
    "worked_example",
    "boundary",
    "summary",
    "text",
    "code",
    "figure",
]
TextBlockKind = Literal[
    "orientation", "definition", "theorem", "proof", "intuition", "boundary", "summary", "text", "code", "figure"
]
QuestionKind = Literal["single_choice", "text_blank", "numeric", "expression", "calculation"]
GroupKind = Literal["lesson", "practice_set", "assessment"]
Mode = Literal["independent", "assisted", "open_book"]
BoundedText = Annotated[NonBlank, Field(max_length=400000)]
Constraint = Annotated[NonBlank, Field(max_length=2000)]
MemberKeys = Annotated[list[dm.Id], Field(max_length=32)]


def distinct_refs(refs: list[dm.ContentRef]) -> None:
    keys = [(ref.entity, ref.id, ref.revision) for ref in refs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate or conflicting exact references")


def unique(values: list, description: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(description)


class AuthoringConceptRef(dm.ContentRef):
    entity: Literal["concept"]

    @model_validator(mode="before")
    @classmethod
    def core_value(cls, value: object) -> object:
        return value.model_dump() if isinstance(value, dm.ContentRef) else value


class AuthoringLessonRef(dm.ContentRef):
    entity: Literal["lesson"]

    @model_validator(mode="before")
    @classmethod
    def core_value(cls, value: object) -> object:
        return value.model_dump() if isinstance(value, dm.ContentRef) else value


class AuthoringTargetRef(dm.ContentRef):
    entity: Literal["lesson", "concept"]

    @model_validator(mode="before")
    @classmethod
    def core_value(cls, value: object) -> object:
        return value.model_dump() if isinstance(value, dm.ContentRef) else value


class GroupCommon(AuthoringModel):
    topic: Annotated[NonBlank, Field(max_length=4000)]
    prerequisites: Annotated[list[Constraint], Field(max_length=32)]
    objectives: Annotated[list[Constraint], Field(min_length=1, max_length=32)]
    proof_policy: Literal["full", "declared_dependencies"]
    source_refs: BlockRefs
    provider_id: dm.Id
    target_concept_refs: Annotated[list[AuthoringConceptRef], Field(max_length=32)]

    @model_validator(mode="after")
    def exact_concepts(self) -> Self:
        distinct_refs(list(self.target_concept_refs))
        return self


class AuthoringLessonPrepareWrite(GroupCommon):
    output_kind: Literal["lesson"]


class AuthoringPracticePrepareWrite(GroupCommon):
    output_kind: Literal["practice_set"]
    lesson_ref: AuthoringLessonRef
    target_concept_refs: Annotated[list[AuthoringConceptRef], Field(min_length=1, max_length=32)]


class AuthoringAssessmentPrepareWrite(GroupCommon):
    output_kind: Literal["assessment"]
    target_concept_refs: Annotated[list[AuthoringConceptRef], Field(min_length=1, max_length=32)]
    allowed_modes: Annotated[list[Mode], Field(min_length=1, max_length=3)]
    time_limit_seconds: Annotated[int, Field(gt=0)] | None

    @model_validator(mode="after")
    def unique_modes(self) -> Self:
        unique(self.allowed_modes, "assessment modes cannot repeat")
        return self


GroupRequest = Annotated[
    AuthoringLessonPrepareWrite | AuthoringPracticePrepareWrite | AuthoringAssessmentPrepareWrite,
    Field(discriminator="output_kind"),
]


class AuthoringGroupPrepareWrite(RootModel[GroupRequest]):
    """Named union whose JSON is the original flat request, never a root wrapper."""

    model_config = {"strict": True, "hide_input_in_errors": True}

    def __repr_args__(self):
        return []

    @property
    def output_kind(self):
        return self.root.output_kind

    @property
    def topic(self):
        return self.root.topic

    @property
    def prerequisites(self):
        return self.root.prerequisites

    @property
    def objectives(self):
        return self.root.objectives

    @property
    def proof_policy(self):
        return self.root.proof_policy

    @property
    def source_refs(self):
        return self.root.source_refs

    @property
    def provider_id(self):
        return self.root.provider_id

    @property
    def target_concept_refs(self):
        return self.root.target_concept_refs


Indexes = Annotated[list[Annotated[int, Field(ge=0)]], Field(max_length=32)]
ObjectiveIndexes = Annotated[list[Annotated[int, Field(ge=0)]], Field(min_length=1, max_length=32)]


class AuthoringBlockPlanEntry(AuthoringModel):
    member_key: dm.Id
    entity: Literal["block"]
    kind: BlockKind
    title: Annotated[NonBlank, Field(max_length=300)]
    objective_indexes: ObjectiveIndexes
    prerequisite_indexes: Indexes
    depends_on_keys: MemberKeys


class AuthoringQuestionPlanEntry(AuthoringModel):
    member_key: dm.Id
    entity: Literal["question"]
    kind: QuestionKind
    objective_indexes: ObjectiveIndexes
    prerequisite_indexes: Indexes
    depends_on_keys: MemberKeys


PlanEntry = Annotated[AuthoringBlockPlanEntry | AuthoringQuestionPlanEntry, Field(discriminator="entity")]


class AuthoringContentPlan(AuthoringModel):
    version: Literal["authoring-content-plan-v1"]
    output_kind: GroupKind
    topic: Annotated[NonBlank, Field(max_length=4000)]
    prerequisites: Annotated[list[Constraint], Field(max_length=32)]
    objectives: Annotated[list[Constraint], Field(min_length=1, max_length=32)]
    proof_policy: Literal["full", "declared_dependencies"]
    entries: Annotated[list[PlanEntry], Field(min_length=1, max_length=32)]

    @model_validator(mode="after")
    def complete_plan(self) -> Self:
        seen: set[str] = set()
        covered: set[int] = set()
        expected = "block" if self.output_kind == "lesson" else "question"
        for item in self.entries:
            if item.member_key in seen or item.entity != expected:
                raise ValueError("plan members must be distinct and of the requested root kind")
            unique(item.objective_indexes, "plan objective indexes cannot repeat")
            unique(item.prerequisite_indexes, "plan prerequisite indexes cannot repeat")
            unique(item.depends_on_keys, "plan dependencies cannot repeat")
            if (
                any(i >= len(self.objectives) for i in item.objective_indexes)
                or any(i >= len(self.prerequisites) for i in item.prerequisite_indexes)
                or not set(item.depends_on_keys) <= seen
            ):
                raise ValueError("plan indexes and earlier-member dependencies must be in scope")
            covered.update(item.objective_indexes)
            seen.add(item.member_key)
        if covered != set(range(len(self.objectives))):
            raise ValueError("each requested objective needs declared structural coverage")
        return self


class AuthoringContentPlanRef(AuthoringModel):
    source_job_id: dm.Id
    plan_sha256: dm.Sha256


class AuthoringTextBlockPayload(AuthoringModel):
    version: Literal["content-block-candidate-v1"]
    kind: TextBlockKind
    title: Annotated[NonBlank, Field(max_length=300)]
    body_markdown: BoundedText
    symbols: Annotated[list[WorkedExampleSymbol], Field(max_length=64)]
    declared_source_refs: BlockRefs

    @model_validator(mode="after")
    def symbols_unique(self) -> Self:
        unique([x.name for x in self.symbols], "symbol names must be unique")
        return self


BlockPayload = Annotated[WorkedExamplePayload | AuthoringTextBlockPayload, Field(discriminator="kind")]


class AuthoringGeneratedBlock(AuthoringModel):
    member_key: dm.Id
    depends_on_keys: MemberKeys
    payload: BlockPayload


class QuestionDraftPublic(AuthoringModel):
    member_key: dm.Id
    kind: QuestionKind
    stem_markdown: BoundedText
    choices: Annotated[list[dm.Choice], Field(max_length=32)]
    concept_refs: Annotated[list[AuthoringConceptRef], Field(min_length=1, max_length=32)]
    skill: Literal["recall", "explain", "compute", "derive", "transfer"]
    exposure_family_key: dm.Id
    max_score: Annotated[FiniteNumber, Field(gt=0, le=100)]
    input_instructions: Annotated[str, Field(max_length=4000)]
    declared_source_refs: BlockRefs
    depends_on_keys: MemberKeys

    @model_validator(mode="after")
    def public_shape(self) -> Self:
        ids = [x.id for x in self.choices]
        unique(ids, "duplicate choice ID")
        distinct_refs(list(self.concept_refs))
        if self.kind == "single_choice" and len(ids) < 2 or self.kind != "single_choice" and ids:
            raise ValueError("choices must match the exact question kind")
        return self


class GeneratedSolutionAnswer(AuthoringModel):
    question_key: dm.Id
    grading_kind: Literal["choice_exact", "text_normalized", "numeric_tolerance", "symbolic_review", "rubric_review"]
    accepted_answers: Annotated[list[Annotated[str, Field(max_length=4000)]], Field(min_length=1, max_length=32)]
    absolute_tolerance: NonNegativeNumber
    relative_tolerance: NonNegativeNumber
    unit: Annotated[NonBlank, Field(max_length=64)] | None
    domain_assumptions: Annotated[list[Constraint], Field(max_length=32)]
    solution_markdown: BoundedText
    rubric_markdown: Annotated[str, Field(max_length=400000)]
    symbols: Annotated[list[WorkedExampleSymbol], Field(max_length=64)]
    numeric_plan: NumericPlan | None

    @model_validator(mode="after")
    def private_symbols(self) -> Self:
        names = [symbol.name for symbol in self.symbols]
        unique(names, "symbol names must be unique")
        if self.numeric_plan is not None and any(
            variable.name not in names for variable in self.numeric_plan.variables
        ):
            raise ValueError("each private numeric variable needs its same-name symbol")
        return self


class AuthoringLessonGenerated(AuthoringModel):
    output_kind: Literal["lesson"]
    title: Annotated[NonBlank, Field(max_length=300)]
    blocks: Annotated[list[AuthoringGeneratedBlock], Field(min_length=1, max_length=32)]


class AuthoringPracticeGenerated(AuthoringModel):
    output_kind: Literal["practice_set"]
    title: Annotated[NonBlank, Field(max_length=300)]
    questions: Annotated[list[QuestionDraftPublic], Field(min_length=1, max_length=32)]
    solutions: Annotated[list[GeneratedSolutionAnswer], Field(min_length=1, max_length=32)]


class AuthoringAssessmentGenerated(AuthoringModel):
    output_kind: Literal["assessment"]
    title: Annotated[NonBlank, Field(max_length=300)]
    questions: Annotated[list[QuestionDraftPublic], Field(min_length=1, max_length=32)]
    solutions: Annotated[list[GeneratedSolutionAnswer], Field(min_length=1, max_length=32)]


GeneratedDraft = Annotated[
    AuthoringLessonGenerated | AuthoringPracticeGenerated | AuthoringAssessmentGenerated,
    Field(discriminator="output_kind"),
]


class AuthoringGroupGenerated(AuthoringModel):
    version: Literal["authoring-group-generated-v1"]
    content_plan: AuthoringContentPlan
    draft: GeneratedDraft

    @model_validator(mode="after")
    def plan_members(self) -> Self:
        from .application.authoring_group_validation import validate_generated_members

        validate_generated_members(self)
        if len(canonical_bytes(self)) > MAX_GROUP_OUTPUT_BYTES:
            raise ValueError("complete generated group exceeds the four MiB byte budget")
        return self


class AuthoringDraftMemberRef(AuthoringModel):
    member_key: dm.Id
    entity: Literal["block", "question"]
    member_sha256: dm.Sha256


class AuthoringBlockMemberRef(AuthoringDraftMemberRef):
    entity: Literal["block"]


class AuthoringQuestionMemberRef(AuthoringDraftMemberRef):
    entity: Literal["question"]


class AuthoringGroupCandidate(dm.DraftCandidate):
    entity: GroupKind

    @model_validator(mode="before")
    @classmethod
    def core_value(cls, value: object) -> object:
        return value.model_dump() if isinstance(value, dm.DraftCandidate) else value


class LessonCandidateRoot(AuthoringModel):
    entity: Literal["lesson"]
    title: NonBlank
    objectives: Annotated[list[Constraint], Field(min_length=1, max_length=32)]
    prerequisites: Annotated[list[Constraint], Field(max_length=32)]
    proof_policy: Literal["full", "declared_dependencies"]
    blocks: Annotated[list[AuthoringBlockMemberRef], Field(min_length=1, max_length=32)]


class PracticeSetCandidateRoot(AuthoringModel):
    entity: Literal["practice_set"]
    title: NonBlank
    lesson_ref: AuthoringLessonRef
    questions: Annotated[list[AuthoringQuestionMemberRef], Field(min_length=1, max_length=32)]
    feedback_policy: Literal["on_submit_or_reveal"]


class AssessmentCandidateRoot(AuthoringModel):
    entity: Literal["assessment"]
    title: NonBlank
    questions: Annotated[list[AuthoringQuestionMemberRef], Field(min_length=1, max_length=32)]
    allowed_modes: Annotated[list[Mode], Field(min_length=1, max_length=3)]
    time_limit_seconds: Annotated[int, Field(gt=0)] | None

    @model_validator(mode="after")
    def unique_modes(self) -> Self:
        unique(self.allowed_modes, "assessment modes cannot repeat")
        return self


CandidateRoot = Annotated[
    LessonCandidateRoot | PracticeSetCandidateRoot | AssessmentCandidateRoot, Field(discriminator="entity")
]


class SolutionDraftPrivate(AuthoringModel):
    question: AuthoringQuestionMemberRef
    answer: GeneratedSolutionAnswer
    review_status: Literal["needs_review"]

    @model_validator(mode="after")
    def exact_key(self) -> Self:
        if self.question.member_key != self.answer.question_key:
            raise ValueError("private answer must name its exact question member")
        return self


class AuthoringPrivateSolutionRef(AuthoringModel):
    question: AuthoringQuestionMemberRef
    solution_sha256: dm.Sha256


class AuthoringGroupCandidatePayload(AuthoringModel):
    version: Literal["authoring-group-candidate-v1"]
    content_plan: AuthoringContentPlan
    root: CandidateRoot
    blocks: Annotated[list[AuthoringGeneratedBlock], Field(max_length=32)]
    questions: Annotated[list[QuestionDraftPublic], Field(max_length=32)]
    private_solutions: Annotated[list[SolutionDraftPrivate], Field(max_length=32)]

    @model_validator(mode="after")
    def complete_group(self) -> Self:
        from .application.authoring_group_validation import validate_group_payload

        validate_group_payload(self)
        return self


class AuthoringQuestionQuality(AuthoringModel):
    question: AuthoringQuestionMemberRef
    grading_compatibility: Literal["PASS", "FAIL", "NOT_RUN"]
    accepted_answer_membership: Literal["PASS", "FAIL", "NOT_RUN"]
    answer_uniqueness: Literal["NOT_RUN"]
    distractor_reasonableness: Literal["NOT_RUN"]
    condition_sufficiency: Literal["NOT_RUN"]
    unit_semantics: Literal["NOT_RUN"]
    solution_grading_semantics: Literal["NOT_RUN"]
    objective_alignment: Literal["NOT_RUN"]
    prerequisite_sufficiency: Literal["NOT_RUN"]


class AuthoringGroupValidation(AuthoringValidation):
    plan_membership: Literal["PASS", "FAIL", "NOT_RUN"]
    private_bindings: Literal["PASS", "FAIL", "NOT_RUN"]
    question_checks: Annotated[list[AuthoringQuestionQuality], Field(max_length=32)]

    def structure_passed(self) -> bool:
        return (
            super().structure_passed()
            and self.plan_membership == self.private_bindings == "PASS"
            and all(
                item.grading_compatibility == item.accepted_answer_membership == "PASS" for item in self.question_checks
            )
        )


class AuthoringTargetMaterial(AuthoringModel):
    ref: AuthoringTargetRef
    metadata: Annotated[dm.Lesson | dm.Concept, Field(discriminator="entity")]

    @model_validator(mode="after")
    def exact_target(self) -> Self:
        value = self.metadata
        if (self.ref.entity, self.ref.id, self.ref.revision) != (
            value.entity,
            value.id,
            value.revision,
        ) or self.ref.sha256 != metadata_sha256(value):
            raise ValueError("target reference must match its complete exact public metadata")
        return self


class AuthoringGroupPreparationSummary(AuthoringPreparationSummary):
    targets: Annotated[list[AuthoringTargetMaterial], Field(max_length=33)]

    @model_validator(mode="after")
    def target_uniqueness(self) -> Self:
        distinct_refs([item.ref for item in self.targets])
        return self


class AuthoringGroupJobSummary(AuthoringModel):
    id: dm.Id
    kind: Literal["authoring"]
    job_revision: dm.Revision
    status: Literal["queued", "running", "awaiting_approval", "completed", "failed", "cancelled"]
    title: NonBlank
    candidate: AuthoringGroupCandidate | None
    created_at: dm.UTC
    updated_at: dm.UTC

    @model_validator(mode="after")
    def persisted_candidate(self) -> Self:
        if (self.status == "completed") != (self.candidate is not None):
            raise ValueError("only actual completed generation has its group candidate")
        if self.candidate is not None and self.candidate.draft_revision != 1:
            raise ValueError("group generation creates an immutable first draft revision")
        if _time(self.updated_at) < _time(self.created_at):
            raise ValueError("job update cannot precede creation")
        return self


class AuthoringGroupJobView(AuthoringModel):
    variant: Literal["group"]
    summary: AuthoringGroupJobSummary
    request: AuthoringGroupPrepareWrite
    preparation: AuthoringGroupPreparationSummary
    proposal_id: dm.Id | None
    consent_id: dm.Id | None
    provider_receipt_id: dm.Id | None
    provider_outcome: Literal["completed", "failed", "incomplete", "cancelled", "unknown"] | None
    usage: UsageSnapshot
    raw_answer: str | None
    raw_refusal: str | None
    validation: AuthoringGroupValidation
    error_code: NonBlank | None
    plan_ref: AuthoringContentPlanRef | None
    content_plan: AuthoringContentPlan | None

    @model_validator(mode="after")
    def original_generation_facts(self) -> Self:
        from .application.authoring_group_validation import (
            build_group_candidate_payload,
            group_candidate_sha256,
            parse_group_generated,
            parse_group_plan,
            plan_sha256,
            validate_group_context,
            validate_plan_request,
        )

        validate_group_context(self.request, self.preparation.targets, self.preparation.materials)
        if self.summary.title != self.request.topic:
            raise ValueError("job title preserves its original topic")
        if self.consent_id is not None and self.proposal_id is None:
            raise ValueError("consent requires its actual proposal")
        receipt = self.provider_receipt_id is not None
        if receipt != (self.provider_outcome is not None) or receipt and self.consent_id is None:
            raise ValueError("checked receipt requires original consent and outcome")
        if not receipt and (self.raw_answer is not None or self.raw_refusal is not None):
            raise ValueError("raw output requires its actual checked receipt")
        if (self.plan_ref is None) != (self.content_plan is None):
            raise ValueError("plan content and exact identity must coexist")
        if self.content_plan is not None:
            if not receipt or self.provider_outcome != "completed" or self.raw_refusal or not self.raw_answer:
                raise ValueError("a plan needs complete non-refusal checked generation")
            assert self.plan_ref is not None
            validate_plan_request(self.content_plan, self.request)
            if canonical_bytes(parse_group_plan(self.raw_answer, self.request)) != canonical_bytes(self.content_plan):
                raise ValueError("saved plan must be the exact plan in the complete checked original response")
            if self.plan_ref.source_job_id != self.summary.id or self.plan_ref.plan_sha256 != plan_sha256(
                self.content_plan
            ):
                raise ValueError("plan identity must bind this actual job and exact plan bytes")
        completed = self.summary.status == "completed"
        if completed != self.validation.structure_passed():
            raise ValueError("completed group and all actual structural checks must agree")
        if completed:
            if (
                self.content_plan is None
                or self.provider_outcome != "completed"
                or self.raw_refusal
                or not self.raw_answer
                or self.error_code is not None
            ):
                raise ValueError("completed group needs a plan and complete checked result")
            assert self.summary.candidate is not None
            if self.summary.candidate.entity != self.request.output_kind:
                raise ValueError("candidate root kind must match original request")
            generated = parse_group_generated(
                self.raw_answer, self.request, self.preparation.targets, self.preparation.materials
            )
            payload, expected = build_group_candidate_payload(
                generated, self.request, self.preparation.targets, self.preparation.materials
            )
            if (
                self.summary.candidate.candidate_sha256 != group_candidate_sha256(payload)
                or self.validation.question_checks != expected.question_checks
            ):
                raise ValueError(
                    "completed summary must match the entire checked original group and its question checks"
                )
        if self.summary.status == "failed" and self.error_code is None:
            raise ValueError("failed generation needs its safe code")
        if self.summary.status not in {"failed", "cancelled"} and self.error_code is not None:
            raise ValueError("live or completed generation cannot carry terminal error")
        return self


class AuthoringJobReadView(RootModel[AuthoringJobView | AuthoringGroupJobView]):
    model_config = {"strict": True, "hide_input_in_errors": True}

    def __repr_args__(self):
        return []


class AuthoringGroupDraftView(AuthoringModel):
    owner: Literal["authoring"]
    candidate: AuthoringGroupCandidate
    source_job_id: dm.Id
    state: Literal["draft"]
    base_ref: None
    plan_ref: AuthoringContentPlanRef
    content_plan: AuthoringContentPlan
    root: CandidateRoot
    blocks: Annotated[list[AuthoringGeneratedBlock], Field(max_length=32)]
    questions: Annotated[list[QuestionDraftPublic], Field(max_length=32)]
    private_solution_refs: Annotated[list[AuthoringPrivateSolutionRef], Field(max_length=32)]
    validation: AuthoringGroupValidation
    numeric_check_ids: Annotated[list[dm.Id], Field(max_length=100)]
    warnings: list[dm.Warning]

    @model_validator(mode="after")
    def exact_visible_members(self) -> Self:
        from .application.authoring_group_validation import validate_group_draft_projection

        validate_group_draft_projection(self)
        return self


class AuthoringPrivateSolutionView(AuthoringModel):
    candidate: AuthoringGroupCandidate
    ref: AuthoringPrivateSolutionRef
    payload: SolutionDraftPrivate

    @model_validator(mode="after")
    def exact_solution(self) -> Self:
        from .application.authoring_group_validation import solution_sha256

        if (
            self.candidate.entity not in {"practice_set", "assessment"}
            or self.ref.question != self.payload.question
            or self.ref.solution_sha256 != solution_sha256(self.payload)
        ):
            raise ValueError("private solution view requires its exact group and solution identity")
        return self


class AuthoringGroupNumericPreviewWrite(AuthoringModel):
    candidate: AuthoringGroupCandidate
    target: AuthoringDraftMemberRef

    @model_validator(mode="after")
    def root_member_kind(self) -> Self:
        if (self.candidate.entity == "lesson") != (self.target.entity == "block"):
            raise ValueError("numeric target member kind must match the root group")
        return self


class AuthoringGroupNumericCheckView(AuthoringModel):
    id: dm.Id
    revision: dm.Revision
    candidate: AuthoringGroupCandidate
    target: AuthoringDraftMemberRef
    plan: NumericPlan
    runtime: NumericRuntimeProfile
    operation_sha256: dm.Sha256
    decision: Literal["pending", "approve_once", "decline"]
    created_at: dm.UTC
    expires_at: dm.UTC
    expired: bool
    job: dm.JobRef | None
    job_revision: dm.Revision | None
    result: NumericCheckResult | None
    warnings: list[dm.Warning]

    @model_validator(mode="after")
    def approval_and_execution(self) -> Self:
        AuthoringGroupNumericPreviewWrite(candidate=self.candidate, target=self.target)
        if _time(self.expires_at) != _time(self.created_at) + timedelta(minutes=10):
            raise ValueError("numeric preview expires exactly ten minutes after creation")
        if self.revision != (1 if self.decision == "pending" else 2):
            raise ValueError("one explicit decision advances the approval revision")
        approved = self.decision == "approve_once"
        if (self.job is not None) != approved or (self.job_revision is not None) != approved:
            raise ValueError("only explicit approval has a separate actual job and revision")
        if self.result is not None:
            if self.job is None or self.job.status not in {"completed", "failed", "cancelled"}:
                raise ValueError("numeric result needs an actual terminal job")
            expected = (
                "completed"
                if self.result.outcome in {"passed", "mismatch", "evaluation_error"}
                else "cancelled"
                if self.result.outcome == "cancelled"
                else "failed"
            )
            if (
                self.result.job_id != self.job.id
                or self.result.operation_sha256 != self.operation_sha256
                or self.job.status != expected
            ):
                raise ValueError("numeric result must match this exact operation and job")
            _check_assertions(self.plan, self.result)
        elif self.job is not None and self.job.status in {"completed", "failed", "cancelled"}:
            raise ValueError("terminal execution needs its saved real result")
        return self
