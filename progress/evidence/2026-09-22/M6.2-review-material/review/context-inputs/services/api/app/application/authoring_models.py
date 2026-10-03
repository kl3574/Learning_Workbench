"""Immutable M6.1 owner collaboration models, sole spec appendix D.

These byte relationships supplement owner history/Policy checks; neither a
self-consistent hash nor these shapes establish a real source or authorization.
"""
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes

from ..authoring_dto import (
    AuthoringCandidate, AuthoringInputMaterial, AuthoringModel, AuthoringPrepareWrite,
    AuthoringValidation, NonBlank, NumericPlan, NumericRuntimeProfile, WorkedExamplePayload,
    validate_candidate,
)


class AuthoringJobInput(AuthoringModel):
    version: Literal['authoring-job-v1']
    workspace_id: dm.Id
    job_id: dm.Id
    request: AuthoringPrepareWrite


class PreparedAuthoringContext(AuthoringModel):
    version: Literal['authoring-context-v1']
    job_id: dm.Id
    snapshot: dm.ContextSnapshot
    template_version: NonBlank
    messages: Annotated[list[dm.GenerationMessage], Field(min_length=2, max_length=2)]
    evidence: Annotated[list[dm.EvidenceChunk], Field(max_length=8)]
    materials: Annotated[list[AuthoringInputMaterial], Field(max_length=8)]
    warnings: list[dm.Warning]

    @model_validator(mode='after')
    def exact_preparation(self) -> Self:
        if self.snapshot.policy != 'authoring':
            raise ValueError('authoring preparation requires its authoring policy')
        if [item.role for item in self.messages] != ['system', 'user']:
            raise ValueError('preparation requires one trusted template and original user constraints')
        if any(not item.content.strip() for item in self.messages):
            raise ValueError('the original template and constraints cannot be empty')
        refs = [item.ref for item in self.materials]
        if [ref.model_dump() for ref in refs] != [ref.model_dump() for ref in self.snapshot.resolved_refs]:
            raise ValueError('snapshot references must match actual complete materials in order')
        if (len({(ref.id, ref.revision) for ref in refs}) != len(refs)
                or len(self.evidence) != len(self.materials)):
            raise ValueError('each selected exact material needs exactly one evidence item')
        count = sum(len(message.content) for message in self.messages)
        for evidence, material in zip(self.evidence, self.materials, strict=True):
            body = evidence.text.encode('utf-8')
            if (evidence.ref.model_dump() != material.ref.model_dump()
                    or len(body) != material.body_bytes
                    or sha256_bytes(body) != material.body_sha256 or '\r' in evidence.text):
                raise ValueError('evidence must preserve actual verified UTF-8/LF body bytes')
            count += len('<reference>\n' + canonical_bytes(evidence).decode('utf-8') + '\n</reference>')
        if self.snapshot.character_count != count or not 1 <= count <= 12000:
            raise ValueError('count must include all messages and complete provider reference envelopes')
        return self


def context_sha256(context: PreparedAuthoringContext) -> str:
    value = context.model_dump(mode='json')
    del value['snapshot']['snapshot_sha256']
    return sha256_bytes(canonical_bytes(value))


class AuthoringCandidateRecord(AuthoringModel):
    version: Literal['authoring-candidate-v1']
    workspace_id: dm.Id
    candidate: AuthoringCandidate
    source_job_id: dm.Id
    provider_receipt_id: dm.Id
    payload: WorkedExamplePayload
    body_sha256: dm.Sha256
    validation: AuthoringValidation
    created_at: dm.UTC

    @model_validator(mode='after')
    def actual_candidate(self) -> Self:
        validate_candidate(self.candidate, self.payload, self.body_sha256, self.validation)
        return self


def numeric_operation_sha256(workspace_id: str, check_id: str, candidate: dm.DraftCandidate,
                             plan: NumericPlan, runtime: NumericRuntimeProfile) -> str:
    return sha256_bytes(canonical_bytes({
        'version': 'numeric-operation-v1', 'workspace_id': workspace_id, 'check_id': check_id,
        'candidate': candidate.model_dump(mode='json'), 'plan': plan.model_dump(mode='json'),
        'runtime': runtime.model_dump(mode='json'),
    }))


class NumericJobInput(AuthoringModel):
    version: Literal['authoring-numeric-job-v1']
    workspace_id: dm.Id
    job_id: dm.Id
    check_id: dm.Id
    operation_sha256: dm.Sha256
    candidate: AuthoringCandidate
    plan: NumericPlan
    runtime: NumericRuntimeProfile

    @model_validator(mode='after')
    def approved_operation(self) -> Self:
        expected = numeric_operation_sha256(self.workspace_id, self.check_id, self.candidate, self.plan, self.runtime)
        if self.operation_sha256 != expected:
            raise ValueError('numeric job input must preserve the original entire approved operation')
        return self
