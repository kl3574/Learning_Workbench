"""Closed internal persistence values; construction authenticates no owner or human.

Current Policy and physical artifact validation belong to the calling owners.
These values retain the bytes those owners supplied, never session credentials.
"""
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator
from pydantic_core import PydanticSerializationError
from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256
from ..authoring_dto import AuthoringModel, NonBlank
from ..import_dto import DownloadArtifact, JobCancelRequest, JobSnapshot
from ..review_dto import DraftReviewWrite, ReviewDecisionWrite
from .draft_candidate_models import DraftOwner
from .errors import ApiError
from .review_models import ReviewJobInput
from .review_checks import StructuralReviewReport
from .review_material_models import CheckedReviewMaterial
from .review_numeric_models import ReviewNumericObservation
from .restore_review_numeric import RestoreReviewNumericObservation


def instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace('Z', '+00:00'))


class StoredReviewReceipt(AuthoringModel, dm.ReviewReceipt):
    """The unchanged core receipt shape with private diagnostic behavior."""


class ReviewJobAck(AuthoringModel, dm.JobRef):
    pass


class ReviewCancelRequest(AuthoringModel, JobCancelRequest):
    pass


class ReviewCancelAck(AuthoringModel, JobSnapshot):
    pass


class ReviewArtifactBinding(AuthoringModel):
    version: Literal['review-artifact-binding-v1']
    workspace_id: dm.Id
    candidate: dm.DraftCandidate
    artifact: DownloadArtifact
    artifact_owner: Literal['import', 'quality']
    source_job_id: dm.Id
    profile: NonBlank
    manifest_sha256: dm.Sha256
    purpose: Literal['machine_report', 'human_decision_evidence']
    bound_at: dm.UTC


class ReviewCommandIdentity(AuthoringModel):
    workspace_id: dm.Id
    actor_id: dm.Id
    route: NonBlank
    command_key: NonBlank
    review_id: dm.Id
    basis_revision: dm.Revision
    resulting_revision: dm.Revision
    recorded_at: dm.UTC


class ReviewCreateCommand(ReviewCommandIdentity):
    command_kind: Literal['create']
    request: DraftReviewWrite
    ack: ReviewJobAck

    @model_validator(mode='after')
    def original_creation(self) -> Self:
        if (self.resulting_revision != 1 or self.basis_revision != self.request.expected_revision
                or self.ack.id != self.review_id or self.ack.status != 'queued'):
            raise ValueError('Creation retains the original candidate basis and queued Job ACK')
        return self


class ReviewDecisionCommand(ReviewCommandIdentity):
    command_kind: Literal['decision']
    request: ReviewDecisionWrite
    ack: StoredReviewReceipt

    @model_validator(mode='after')
    def original_decision(self) -> Self:
        if (self.route != f'POST /reviews/{self.review_id}/decision'
                or self.basis_revision != self.request.expected_revision
                or self.resulting_revision != self.basis_revision + 1
                or self.ack.id != self.review_id or self.ack.revision != self.resulting_revision):
            raise ValueError('Decision retains its exact review route and adjacent revision ACK')
        return self


class ReviewCancelCommand(ReviewCommandIdentity):
    command_kind: Literal['cancel']
    request: ReviewCancelRequest
    ack: ReviewCancelAck

    @model_validator(mode='after')
    def original_cancellation(self) -> Self:
        if (self.route != f'POST /jobs/{self.review_id}/cancel' or self.ack.id != self.review_id
                or self.ack.workspace_id != self.workspace_id or self.ack.kind != 'draft_review'
                or self.ack.revision != self.resulting_revision
                or self.resulting_revision not in (self.basis_revision, self.basis_revision + 1)):
            raise ValueError('Cancellation retains its exact Job route and revision ACK')
        return self


ReviewCommand = Annotated[ReviewCreateCommand | ReviewDecisionCommand | ReviewCancelCommand,
                          Field(discriminator='command_kind')]


class ReviewBinding(AuthoringModel):
    input: ReviewJobInput
    owner: DraftOwner
    job: ReviewCancelAck


MACHINE_REASON = 'Machine checks recorded; human decisions remain NOT_RUN.'


class ReviewMachineRecord(AuthoringModel):
    version: Literal['review-machine-record-v1']
    workspace_id: dm.Id
    review_id: dm.Id
    job_revision: dm.Revision
    input_sha256: dm.Sha256
    material: CheckedReviewMaterial
    numeric: ReviewNumericObservation | RestoreReviewNumericObservation
    structural_report: StructuralReviewReport
    report: ReviewArtifactBinding
    receipt: StoredReviewReceipt
    checked_at: dm.UTC

    @model_validator(mode='after')
    def complete_machine_binding(self) -> Self:
        candidate = self.material.candidate
        if (self.workspace_id != self.material.workspace_id or self.workspace_id != self.numeric.workspace_id
                or self.numeric.source_kind != self.material.source_kind or self.numeric.candidate != candidate
                or self.structural_report.candidate != candidate
                or self.structural_report.material_descriptor_sha256 != self.material.descriptor_sha256
                or self.report.workspace_id != self.workspace_id or self.report.candidate != candidate
                or self.report.source_job_id != self.review_id or self.report.artifact_owner != 'quality'
                or self.report.purpose != 'machine_report'
                or self.receipt.id != self.review_id or self.receipt.revision != 1
                or self.receipt.candidate != candidate or self.receipt.structural != self.structural_report.structural
                or any(getattr(self.receipt, field) != 'NOT_RUN' for field in
                       ('mathematical', 'sources', 'independent_pedagogy'))
                or self.receipt.reviewer != 'system:draft-review-rules-v1'
                or self.receipt.decision_reason != MACHINE_REASON
                or self.receipt.evidence_paths != [self.report.artifact.download_path]
                or any(instant(value) > instant(self.checked_at) for value in
                       (self.numeric.observed_at, self.report.bound_at, self.receipt.created_at))):
            raise ValueError('Machine history must preserve its complete bound inputs and unreviewed human fields')
        return self


class ReviewDecisionRecord(AuthoringModel):
    version: Literal['review-decision-record-v1']
    workspace_id: dm.Id
    review_id: dm.Id
    candidate: dm.DraftCandidate
    previous_receipt_sha256: dm.Sha256
    machine_record_sha256: dm.Sha256
    material_descriptor_sha256: dm.Sha256
    request: ReviewDecisionWrite
    request_sha256: dm.Sha256
    actor_session_id: dm.Id
    actor_role_at_decision: Literal['author']
    evidence: list[ReviewArtifactBinding]
    receipt: StoredReviewReceipt
    decided_at: dm.UTC

    @model_validator(mode='after')
    def complete_human_binding(self) -> Self:
        if (self.request_sha256 != metadata_sha256(self.request)
                or self.request.candidate_sha256 != self.candidate.candidate_sha256
                or self.receipt.id != self.review_id or self.receipt.candidate != self.candidate
                or self.receipt.revision != self.request.expected_revision + 1
                or self.receipt.reviewer != self.actor_session_id
                or self.receipt.mathematical != self.request.mathematical or self.receipt.sources != self.request.sources
                or self.receipt.decision_reason != self.request.reason
                or self.receipt.independent_pedagogy != 'NOT_RUN'
                or [item.artifact.artifact_id for item in self.evidence] != self.request.evidence_artifact_ids
                or instant(self.receipt.created_at) > instant(self.decided_at)):
            raise ValueError('Human history must retain the exact original decision and actor')
        for item in self.evidence:
            if (item.workspace_id != self.workspace_id or item.candidate != self.candidate
                    or item.purpose != 'human_decision_evidence' or instant(item.bound_at) > instant(self.decided_at)):
                raise ValueError('Decision evidence must retain its original candidate and ordered attachment binding')
        return self


ReviewRecord = Annotated[ReviewMachineRecord | ReviewDecisionRecord, Field(discriminator='version')]


class ReviewHistory(AuthoringModel):
    state: Literal['pending', 'ready']
    binding: ReviewBinding
    records: list[ReviewRecord]
    receipt: StoredReviewReceipt | None

    @model_validator(mode='after')
    def no_invented_pending_receipt(self) -> Self:
        if self.state == 'pending':
            if self.records or self.receipt is not None:
                raise ValueError('Pending review has no machine receipt')
        elif (not self.records or not isinstance(self.records[0], ReviewMachineRecord)
              or self.receipt != self.records[-1].receipt):
            raise ValueError('Ready projection must retain its original machine history and last receipt')
        return self


def machine_job_result(record: ReviewMachineRecord) -> dict[str, str]:
    """Exact terminal reference for the caller's real Jobs transition, not execution."""
    try:
        record = ReviewMachineRecord.model_validate(record.model_dump(mode='python', warnings='error'))
    except (ValueError, TypeError, AttributeError, PydanticSerializationError):
        raise ApiError(409, 'REVIEW_INTEGRITY_ERROR', '审核持久历史未通过完整性校验。') from None
    return {'review_id': record.review_id, 'receipt_sha256': metadata_sha256(record.receipt),
            'machine_record_sha256': metadata_sha256(record)}
