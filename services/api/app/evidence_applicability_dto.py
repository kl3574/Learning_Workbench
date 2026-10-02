"""Closed Learning applicability contracts from PRODUCT_DESIGN v3.0.9 §20.11."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from packages.contracts import domain_models as dm
from .authoring_dto import AuthoringModel, NonBlank

Reason = Annotated[NonBlank, Field(max_length=2000)]
ExpectedDecisionRevision = Annotated[int, Field(ge=0)]


class EvidenceImpactArtifact(AuthoringModel):
    id: dm.Id
    sha256: dm.Sha256


class EvidenceImpactDecisionWrite(AuthoringModel):
    event_id: dm.Id
    expected_decision_revision: ExpectedDecisionRevision
    expected_current_basis_sha256: dm.Sha256
    decision: Literal['usable', 'confirmed_stale']
    reason: Reason
    evidence_artifact_ids: list[dm.Id] = Field(max_length=32)

    @model_validator(mode='after')
    def unique_artifacts(self):
        if len(self.evidence_artifact_ids) != len(set(self.evidence_artifact_ids)):
            raise ValueError('duplicate evidence artifact')
        return self


class EvidenceImpactDecisionReceipt(AuthoringModel):
    evidence_id: dm.Id
    event_id: dm.Id
    decision_revision: dm.Revision
    relevance: Literal['exact_ref', 'id_only_candidate']
    question_ref: dm.ContentRef
    concept_ref: dm.ContentRef
    attempt_id: dm.Id
    grading_revision: dm.Revision
    original_evidence_sha256: dm.Sha256
    current_basis_sha256: dm.Sha256
    decision: Literal['usable', 'confirmed_stale']
    reason: Reason
    evidence_artifacts: list[EvidenceImpactArtifact] = Field(max_length=32)
    actor_session_id: dm.Id
    decided_at: dm.UTC
    request_sha256: dm.Sha256
    receipt_sha256: dm.Sha256

    @model_validator(mode='after')
    def exact_types(self):
        if self.question_ref.entity != 'question' or self.concept_ref.entity != 'concept':
            raise ValueError('exact question and concept references required')
        if len({item.id for item in self.evidence_artifacts}) != len(self.evidence_artifacts):
            raise ValueError('duplicate evidence artifact')
        return self


class EvidenceApplicabilityDecisionView(AuthoringModel):
    evidence_id: dm.Id
    original_evidence: dm.Evidence
    question_ref: dm.ContentRef
    concept_ref: dm.ContentRef
    attempt_id: dm.Id
    grading_revision: dm.Revision
    original_evidence_sha256: dm.Sha256
    current_basis_sha256: dm.Sha256
    applicability: Literal['usable', 'pending_review', 'confirmed_stale']
    reason_codes: list[str]
    relevant_event_ids: list[dm.Id]
    event_decision_head: ExpectedDecisionRevision | None
    decisions: list[EvidenceImpactDecisionReceipt]
    next_cursor: str | None

    @model_validator(mode='after')
    def origin(self):
        if (self.evidence_id != self.original_evidence.id or self.question_ref.entity != 'question'
                or self.concept_ref.entity != 'concept' or self.concept_ref.id != self.original_evidence.concept_id
                or len(set(self.relevant_event_ids)) != len(self.relevant_event_ids)):
            raise ValueError('invalid original evidence identity')
        return self
