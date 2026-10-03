"""Immutable group inputs and owner records, PRODUCT_DESIGN 3.0.7 appendix D."""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json
from .. import authoring_group_dto as g
from ..authoring_dto import (
    AuthoringInputMaterial,
    AuthoringModel,
    NonBlank,
    NumericCheckResult,
    NumericPlan,
    NumericRuntimeProfile,
    _check_assertions,
)
from .authoring_group_validation import plan_sha256, validate_group_candidate, validate_group_context


class AuthoringGroupJobInput(AuthoringModel):
    version: Literal["authoring-group-job-v1"]
    workspace_id: dm.Id
    job_id: dm.Id
    request: g.AuthoringGroupPrepareWrite


class PreparedAuthoringGroupContext(AuthoringModel):
    version: Literal["authoring-group-context-v1"]
    job_id: dm.Id
    snapshot: dm.ContextSnapshot
    template_version: NonBlank
    messages: Annotated[list[dm.GenerationMessage], Field(min_length=2, max_length=2)]
    evidence: Annotated[list[dm.EvidenceChunk], Field(max_length=8)]
    materials: Annotated[list[AuthoringInputMaterial], Field(max_length=8)]
    targets: Annotated[list[g.AuthoringTargetMaterial], Field(max_length=33)]
    warnings: list[dm.Warning]

    @model_validator(mode="after")
    def complete_preparation(self) -> Self:
        if self.snapshot.policy != "authoring" or [x.role for x in self.messages] != ["system", "user"]:
            raise ValueError("group context needs authoring Policy and the system/user message pair")
        if any(not item.content.strip() for item in self.messages):
            raise ValueError("group template and exact request wrapper cannot be blank")
        wrapper = strict_json(self.messages[1].content)
        if not isinstance(wrapper, dict) or set(wrapper) != {"request", "targets"}:
            raise ValueError("group user message must contain only the exact request and target metadata")
        request = g.AuthoringGroupPrepareWrite.model_validate(wrapper["request"])
        if (
            wrapper["targets"] != [x.model_dump(mode="json") for x in self.targets]
            or self.messages[1].content.encode()
            != canonical_bytes(
                {
                    "request": request.model_dump(mode="json"),
                    "targets": [x.model_dump(mode="json") for x in self.targets],
                }
            )
            or self.snapshot.request_sha256 != sha256_bytes(canonical_bytes(request))
        ):
            raise ValueError("group user wrapper and snapshot must preserve the exact request and target bytes")
        validate_group_context(request, self.targets, self.materials)
        refs = [x.ref.model_dump() for x in self.materials]
        if refs != [x.model_dump() for x in self.snapshot.resolved_refs] or len(self.evidence) != len(self.materials):
            raise ValueError("snapshot references and Provider evidence pair only with original source blocks")
        count = sum(len(item.content) for item in self.messages)
        for evidence, material in zip(self.evidence, self.materials, strict=True):
            body = evidence.text.encode("utf-8")
            if (
                evidence.ref.model_dump() != material.ref.model_dump()
                or len(body) != material.body_bytes
                or sha256_bytes(body) != material.body_sha256
                or "\r" in evidence.text
            ):
                raise ValueError("evidence must preserve original verified source body bytes")
            count += len("<reference>\n" + canonical_bytes(evidence).decode("utf-8") + "\n</reference>")
        if count != self.snapshot.character_count or not 1 <= count <= 12000:
            raise ValueError("group budget counts the entire messages and Provider evidence wrappers")
        return self


def group_context_sha256(context: PreparedAuthoringGroupContext) -> str:
    value = context.model_dump(mode="json")
    del value["snapshot"]["snapshot_sha256"]
    return sha256_bytes(canonical_bytes(value))


def validate_group_context_binding(value: AuthoringGroupJobInput, context: PreparedAuthoringGroupContext) -> None:
    value = AuthoringGroupJobInput.model_validate(value.model_dump(mode="python"))
    context = PreparedAuthoringGroupContext.model_validate(context.model_dump(mode="python"))
    wrapper = strict_json(context.messages[1].content)
    if (
        context.job_id != value.job_id
        or wrapper["request"] != value.request.model_dump(mode="json")
        or context.snapshot.snapshot_sha256 != group_context_sha256(context)
    ):
        raise ValueError("prepared group context must bind the real original job and complete context hash")


class AuthoringContentPlanRecord(AuthoringModel):
    version: Literal["authoring-content-plan-record-v1"]
    workspace_id: dm.Id
    source_job_id: dm.Id
    provider_receipt_id: dm.Id
    job_input_sha256: dm.Sha256
    plan_ref: g.AuthoringContentPlanRef
    plan: g.AuthoringContentPlan
    created_at: dm.UTC

    @model_validator(mode="after")
    def exact_plan(self) -> Self:
        if self.plan_ref.source_job_id != self.source_job_id or self.plan_ref.plan_sha256 != plan_sha256(self.plan):
            raise ValueError("plan record must preserve its original job and complete plan hash")
        return self


class AuthoringGroupCandidateRecord(AuthoringModel):
    version: Literal["authoring-group-record-v1"]
    workspace_id: dm.Id
    candidate: g.AuthoringGroupCandidate
    source_job_id: dm.Id
    provider_receipt_id: dm.Id
    plan_ref: g.AuthoringContentPlanRef
    payload: g.AuthoringGroupCandidatePayload
    validation: g.AuthoringGroupValidation
    created_at: dm.UTC

    @model_validator(mode="after")
    def exact_candidate(self) -> Self:
        validate_group_candidate(self.candidate, self.payload, self.validation)
        if self.plan_ref.source_job_id != self.source_job_id or self.plan_ref.plan_sha256 != plan_sha256(
            self.payload.content_plan
        ):
            raise ValueError("candidate must retain its exact source job plan identity")
        return self


def group_numeric_operation_sha256(
    workspace_id: str,
    check_id: str,
    candidate: g.AuthoringGroupCandidate,
    target: g.AuthoringDraftMemberRef,
    plan: NumericPlan,
    runtime: NumericRuntimeProfile,
) -> str:
    return sha256_bytes(
        canonical_bytes(
            {
                "version": "group-numeric-operation-v1",
                "workspace_id": workspace_id,
                "check_id": check_id,
                "candidate": candidate.model_dump(mode="json"),
                "target": target.model_dump(mode="json"),
                "plan": plan.model_dump(mode="json"),
                "runtime": runtime.model_dump(mode="json"),
            }
        )
    )


class AuthoringGroupNumericJobInput(AuthoringModel):
    version: Literal["authoring-group-numeric-job-v1"]
    workspace_id: dm.Id
    job_id: dm.Id
    check_id: dm.Id
    operation_sha256: dm.Sha256
    candidate: g.AuthoringGroupCandidate
    target: g.AuthoringDraftMemberRef
    plan: NumericPlan
    runtime: NumericRuntimeProfile

    @model_validator(mode="after")
    def exact_operation(self) -> Self:
        g.AuthoringGroupNumericPreviewWrite(candidate=self.candidate, target=self.target)
        expected = group_numeric_operation_sha256(
            self.workspace_id, self.check_id, self.candidate, self.target, self.plan, self.runtime
        )
        if self.operation_sha256 != expected:
            raise ValueError("group numeric input must preserve its full group/member/plan/runtime operation")
        return self


def validate_group_numeric_result(value: AuthoringGroupNumericJobInput, result: NumericCheckResult) -> None:
    value = AuthoringGroupNumericJobInput.model_validate(value.model_dump(mode="python"))
    result = NumericCheckResult.model_validate(result.model_dump(mode="python"))
    if (
        result.input_sha256 != sha256_bytes(canonical_bytes(value))
        or result.job_id != value.job_id
        or result.operation_sha256 != value.operation_sha256
    ):
        raise ValueError("numeric result must hash this actual GroupNumericJobInput and name its exact job/operation")
    _check_assertions(value.plan, result)
