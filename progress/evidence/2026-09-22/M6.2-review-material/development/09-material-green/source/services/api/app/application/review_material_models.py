"""Complete immutable review inputs; hashes describe bytes, never grant approval.

Only a real owner may return these after checking current access and original
history in the caller's transaction. Numeric observations and workflow state
belong to separate ports and cannot change this material descriptor.
"""
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes
from ..authoring_dto import AuthoringModel
from ..import_dto import BlockDraftPayload, DraftPayload
from .authoring_models import AuthoringCandidateRecord, AuthoringJobInput, PreparedAuthoringContext, context_sha256
from .authoring_group_models import (
    AuthoringContentPlanRecord, AuthoringGroupCandidateRecord, AuthoringGroupJobInput,
    PreparedAuthoringGroupContext, group_context_sha256, validate_group_context_binding,
)
from .draft_candidate_models import DraftOwner, DraftSourceKind, ResolvedDraftCandidate


class ImportReviewMaterial(AuthoringModel):
    version: Literal['import-review-material-v1']
    candidate: dm.DraftCandidate
    import_id: dm.Id
    source_id: dm.Id
    original_input_sha256: dm.Sha256
    payload: DraftPayload
    warnings: list[dm.Warning]
    private_solution_coverage: Literal['excluded']

    @model_validator(mode='after')
    def exact_payload(self) -> Self:
        metadata = self.payload.metadata if isinstance(self.payload, BlockDraftPayload) else self.payload
        if self.candidate.entity != metadata.entity or self.candidate.candidate_sha256 != metadata_sha256(metadata):
            raise ValueError('Import review scope is the exact public candidate metadata')
        if isinstance(self.payload, BlockDraftPayload):
            if (self.payload.source_id != self.source_id
                    or sha256_bytes(self.payload.body_markdown.encode()) != self.payload.metadata.body_sha256):
                raise ValueError('Import block review requires its complete original body')
        return self


class SingleReviewMaterial(AuthoringModel):
    version: Literal['authoring-single-review-material-v1']
    record: AuthoringCandidateRecord
    input: AuthoringJobInput
    context: PreparedAuthoringContext

    @model_validator(mode='after')
    def exact_history(self) -> Self:
        if (self.record.workspace_id != self.input.workspace_id
                or self.record.source_job_id != self.input.job_id or self.context.job_id != self.input.job_id
                or self.context.snapshot.request_sha256 != metadata_sha256(self.input.request)
                or self.context.snapshot.snapshot_sha256 != context_sha256(self.context)):
            raise ValueError('Single material must preserve its original candidate/input/context binding')
        return self


class GroupReviewMaterial(AuthoringModel):
    version: Literal['authoring-group-review-material-v1']
    record: AuthoringGroupCandidateRecord
    input: AuthoringGroupJobInput
    context: PreparedAuthoringGroupContext
    plan: AuthoringContentPlanRecord
    private_solution_coverage: Literal['included_in_complete_root_sha']

    @model_validator(mode='after')
    def exact_history(self) -> Self:
        validate_group_context_binding(self.input, self.context)
        if (self.record.workspace_id != self.input.workspace_id or self.plan.workspace_id != self.input.workspace_id
                or self.record.source_job_id != self.input.job_id or self.plan.source_job_id != self.input.job_id
                or self.plan.provider_receipt_id != self.record.provider_receipt_id
                or self.plan.job_input_sha256 != metadata_sha256(self.input)
                or self.plan.plan_ref != self.record.plan_ref or self.plan.plan != self.record.payload.content_plan
                or self.context.snapshot.snapshot_sha256 != group_context_sha256(self.context)):
            raise ValueError('Group material must preserve the complete original plan and candidate history')
        return self


ReviewPayload = Annotated[ImportReviewMaterial | SingleReviewMaterial | GroupReviewMaterial,
                          Field(discriminator='version')]


class CheckedReviewMaterial(AuthoringModel):
    version: Literal['checked-review-material-v1']
    workspace_id: dm.Id
    owner: DraftOwner
    source_kind: DraftSourceKind
    candidate: dm.DraftCandidate
    payload: ReviewPayload
    owner_record_sha256: dm.Sha256
    descriptor_sha256: dm.Sha256
    source_refs: list[dm.ContentRef]
    warnings: list[dm.Warning]

    @model_validator(mode='after')
    def complete_descriptor(self) -> Self:
        if isinstance(self.payload, ImportReviewMaterial):
            expected_owner, expected_kind = 'import', 'import'
            candidate = self.payload.candidate
            record_sha = metadata_sha256(self.payload)
            refs: list[dm.ContentRef] = []
        else:
            expected_owner = 'authoring'
            expected_kind = 'authoring_single' if isinstance(self.payload, SingleReviewMaterial) else 'authoring_group'
            candidate = self.payload.record.candidate
            record_sha = metadata_sha256(self.payload.record)
            refs = self.payload.context.snapshot.resolved_refs
            if self.workspace_id != self.payload.record.workspace_id:
                raise ValueError('Review material belongs to another workspace')
        if (self.owner != expected_owner or self.source_kind != expected_kind
                or self.candidate.model_dump() != candidate.model_dump()
                or self.owner_record_sha256 != record_sha or self.source_refs != refs):
            raise ValueError('Review descriptor must bind the exact owner record and complete source order')
        raw = self.model_dump(mode='json', exclude={'descriptor_sha256'})
        if self.descriptor_sha256 != sha256_bytes(canonical_bytes(raw)):
            raise ValueError('Review descriptor hash must cover every immutable material field')
        return self


def checked_material(identity: ResolvedDraftCandidate, payload: ReviewPayload) -> CheckedReviewMaterial:
    """Package already checked owner bytes; this function performs no authorization."""
    if isinstance(payload, ImportReviewMaterial):
        record_sha = metadata_sha256(payload)
        refs: list[dm.ContentRef] = []
        warnings = payload.warnings
    else:
        record_sha = metadata_sha256(payload.record)
        refs = payload.context.snapshot.resolved_refs
        warnings = payload.context.warnings
    raw = dict(version='checked-review-material-v1', workspace_id=identity.workspace_id,
        owner=identity.owner, source_kind=identity.source_kind, candidate=identity.candidate.model_dump(mode='json'),
        payload=payload.model_dump(mode='json'), owner_record_sha256=record_sha,
        source_refs=[ref.model_dump(mode='json') for ref in refs],
        warnings=[warning.model_dump(mode='json') for warning in warnings])
    raw['descriptor_sha256'] = sha256_bytes(canonical_bytes(raw))
    return CheckedReviewMaterial.model_validate(raw)
