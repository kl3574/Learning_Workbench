"""Closed internal persistence values; construction authenticates no owner or human.

Current Policy and physical artifact validation belong to the calling owners.
These values retain the bytes those owners supplied, never session credentials.
"""
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator
from packages.contracts import domain_models as dm
from ..authoring_dto import AuthoringModel, NonBlank
from ..import_dto import DownloadArtifact, JobCancelRequest, JobSnapshot
from ..review_dto import DraftReviewWrite, ReviewDecisionWrite
from .draft_candidate_models import DraftOwner
from .review_models import ReviewJobInput


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
