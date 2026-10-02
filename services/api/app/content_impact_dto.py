"""Closed Content impact application contract, PRODUCT_DESIGN v3.0.9 §20.11."""
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator
from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from .authoring_dto import AuthoringModel, NonBlank

ImpactClassification = Literal['exact_ref', 'id_only_candidate']
ImpactDecision = Literal['no_revision_needed', 'new_revision_required']
ImpactReason = Annotated[NonBlank, Field(max_length=2000)]


class ImpactArtifact(AuthoringModel):
    id: dm.Id
    sha256: dm.Sha256


class ImpactObjectDecisionWrite(AuthoringModel):
    target_id: dm.Id
    observed_ref: dm.ContentRef
    expected_event_snapshot_sha256: dm.Sha256
    expected_decision_revision: Annotated[int, Field(ge=0)]
    decision: ImpactDecision
    reason: ImpactReason
    evidence_artifact_ids: Annotated[list[dm.Id], Field(max_length=32)]

    @model_validator(mode='after')
    def distinct_evidence(self) -> Self:
        if len(self.evidence_artifact_ids) != len(set(self.evidence_artifact_ids)):
            raise ValueError('Evidence IDs must be unique')
        return self


class ImpactObjectDecisionReceipt(AuthoringModel):
    event_id: dm.Id
    target_id: dm.Id
    decision_revision: dm.Revision
    classification: ImpactClassification
    observed_ref: dm.ContentRef
    target_metadata_sha256: dm.Sha256
    target_body_sha256: dm.Sha256 | None
    event_snapshot_sha256: dm.Sha256
    decision: ImpactDecision
    reason: ImpactReason
    evidence_artifacts: Annotated[list[ImpactArtifact], Field(max_length=32)]
    actor_session_id: dm.Id
    decided_at: dm.UTC
    request_sha256: dm.Sha256
    receipt_sha256: dm.Sha256

    @model_validator(mode='after')
    def complete_identity(self) -> Self:
        if (self.observed_ref.id != self.target_id or self.observed_ref.entity == 'note'
                or self.target_metadata_sha256 != self.observed_ref.sha256
                or (self.observed_ref.entity == 'block') != (self.target_body_sha256 is not None)
                or len({x.id for x in self.evidence_artifacts}) != len(self.evidence_artifacts)
                or self.receipt_sha256 != sha256_bytes(canonical_bytes(self.model_dump(exclude={'receipt_sha256'})))):
            raise ValueError('Receipt identity or digest mismatch')
        return self


class ContentImpactView(AuthoringModel):
    event_id: dm.Id
    old_ref: dm.ContentRef
    new_ref: dm.ContentRef
    reason: Literal['content_revision_published']
    evidence_version: Literal['owner_frozen_v1', 'legacy_unverified']
    event_snapshot_sha256: dm.Sha256 | None
    affected_ids: list[dm.Id]
    exact_dependency_refs: list[dm.ContentRef]
    conservative_only_ids: list[dm.Id]
    pending_target_ids: list[dm.Id]
    action_required_target_ids: list[dm.Id]
    target_decision_head: Annotated[int, Field(ge=0)] | None
    decisions: list[ImpactObjectDecisionReceipt]
    next_cursor: str | None
