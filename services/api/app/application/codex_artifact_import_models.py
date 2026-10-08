"""Permanent aggregate commands; Import remains the child/source authority."""
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator
from packages.contracts import domain_models as dm
from ..codex_turn_dto import CodexArtifactImportWrite
from ..import_dto import JobCancelRequest, JobSnapshot
from .import_codex_models import CodexImportBinding


class ArtifactImportInput(dm.StrictModel):
    version: Literal['codex-artifact-import-input-v1']
    workspace_id: dm.Id
    actor_session_id: dm.Id
    session_id: dm.Id
    request: CodexArtifactImportWrite


class ArtifactImportCreated(dm.StrictModel):
    kind: Literal['created']
    input: ArtifactImportInput
    key: Annotated[str, Field(pattern=r'^[A-Za-z0-9_-]{1,128}$')]
    ack: dm.JobRef
    bindings: Annotated[list[CodexImportBinding], Field(min_length=1, max_length=32)]

    @model_validator(mode='after')
    def complete_membership(self) -> Self:
        if self.ack.status != 'queued' or [item.artifact_id for item in self.bindings] != self.input.request.artifact_ids:
            raise ValueError('The original aggregate ACK and complete ordered selection must agree')
        if len({item.import_id for item in self.bindings}) != len(self.bindings):
            raise ValueError('Import members must be unique')
        for item in self.bindings:
            if (item.aggregate_job_id != self.ack.id or item.workspace_id != self.input.workspace_id
                    or item.actor_session_id != self.input.actor_session_id or item.session_id != self.input.session_id
                    or item.turn_id != self.input.request.turn_id or item.manifest_sha256 != self.input.request.expected_manifest_sha256):
                raise ValueError('All members must belong to this exact original command')
        return self


class ArtifactImportCancelled(dm.StrictModel):
    kind: Literal['cancelled']
    actor_session_id: dm.Id
    key: Annotated[str, Field(pattern=r'^[A-Za-z0-9_-]{1,128}$')]
    body: JobCancelRequest
    basis_revision: dm.Revision
    ack: JobSnapshot


class ArtifactImportEnvelope(dm.StrictModel):
    version: Literal['codex-artifact-import-event-v1']
    workspace_id: dm.Id
    job_id: dm.Id
    seq: dm.Revision
    previous_sha256: dm.Sha256 | None
    event: Annotated[ArtifactImportCreated | ArtifactImportCancelled, Field(discriminator='kind')]


class ArtifactImportResult(dm.StrictModel):
    version: Literal['codex-artifact-import-result-v1']
    outcome: Literal['completed', 'failed', 'cancelled']
    preview_receipts: list[dm.Sha256]
    failed_import_ids: list[dm.Id]
    cancel_request_sha256: dm.Sha256 | None

    @model_validator(mode='after')
    def original_terminal(self) -> Self:
        if ((self.outcome == 'completed') != bool(self.preview_receipts)
                or (self.outcome == 'failed') != bool(self.failed_import_ids)
                or (self.outcome == 'cancelled') != (self.cancel_request_sha256 is not None)):
            raise ValueError('Terminal outcome must have exactly its actual supporting facts')
        return self
