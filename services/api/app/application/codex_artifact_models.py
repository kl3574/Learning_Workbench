"""Private artifact facts; public manifests are projections, never scan authority."""
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator
from packages.contracts import domain_models as dm
from ..codex_turn_dto import CodexArtifactManifestView, SafeCode


# Frozen descriptor of the original v1 scan contract. This identifies historical
# application checks, not a proof of physical runtime isolation/code closure.
# Future producers need their own version/decoder; never reinterpret old facts
# using a mutable current policy.
SCAN_PROFILE_V1_SHA256 = '7d17e2f9aa292425ad787453cfdf62772707c08add6c1f90dee08420cf9c836e'


class AnswerSource(dm.StrictModel):
    version: Literal['codex-checked-answer-source-v1']
    workspace_id: dm.Id
    session_id: dm.Id
    turn_id: dm.Id
    job_id: dm.Id
    execution_owner_id: dm.Id
    start_sha256: dm.Sha256
    model_result_sha256: dm.Sha256
    runtime_profile_sha256: dm.Sha256
    operation_result_sha256: Annotated[list[dm.Sha256], Field(max_length=32)]
    answer_sha256: dm.Sha256
    answer_bytes: Annotated[int, Field(strict=True, ge=0, le=16777216)]


class OutputFile(dm.StrictModel):
    logical_path: Literal['answer.md']
    size: Annotated[int, Field(strict=True, ge=0, le=16777216)]
    sha256: dm.Sha256
    media_type: Literal['text/markdown; charset=utf-8']
    import_kind: Literal['markdown']


class AnswerCollection(dm.StrictModel):
    version: Literal['codex-checked-answer-collection-v1']
    source: AnswerSource
    producer: Literal['codex-checked-answer-materializer-v1']
    scan_profile_sha256: dm.Sha256
    writer_stop: Literal['synchronous-owner-closed']
    files: Annotated[list[OutputFile], Field(min_length=1, max_length=1)]

    @model_validator(mode='after')
    def original_bytes(self) -> Self:
        if (self.scan_profile_sha256 != SCAN_PROFILE_V1_SHA256
                or self.files[0].sha256 != self.source.answer_sha256 or self.files[0].size != self.source.answer_bytes):
            raise ValueError('The real output must be the exact original answer UTF-8 bytes')
        return self


class ArtifactTerminalReceipt(dm.StrictModel):
    version: Literal['codex-artifact-terminal-receipt-v1']
    collection: AnswerCollection
    source_outcome: Literal['completed', 'failed', 'incomplete', 'cancelled', 'unknown']
    error_code: SafeCode | None


class ArtifactRecord(dm.StrictModel):
    version: Literal['codex-artifact-record-v1']
    receipt: ArtifactTerminalReceipt
    manifest: CodexArtifactManifestView

    @model_validator(mode='after')
    def receipt_binding(self) -> Self:
        from ..serialization import content_sha256
        value, receipt = self.manifest.manifest, self.receipt
        source = receipt.collection.source
        if (value.terminal_receipt_sha256 != content_sha256(receipt)
                or value.session_id != source.session_id or value.turn_id != source.turn_id
                or value.source_job_id != source.job_id or value.source_outcome != receipt.source_outcome
                or value.runtime_profile_sha256 != source.runtime_profile_sha256
                or value.scan_profile_sha256 != receipt.collection.scan_profile_sha256
                or value.excluded or len(value.entries) != len(receipt.collection.files)):
            raise ValueError('Manifest must bind the complete original collection receipt')
        for entry, file in zip(value.entries, receipt.collection.files, strict=True):
            if entry.model_dump(exclude={'artifact_id', 'scan'}) != file.model_dump():
                raise ValueError('Manifest membership differs from the actual scanned bytes')
        return self


class TurnManifestReady(dm.StrictModel):
    kind: Literal['manifest_ready']
    turn_id: dm.Id
    receipt_sha256: dm.Sha256
    manifest: CodexArtifactManifestView


class ArtifactControlEnvelope(dm.StrictModel):
    version: Literal['codex-turn-event-v6']
    workspace_id: dm.Id
    session_id: dm.Id
    seq: dm.Revision
    previous_sha256: dm.Sha256 | None
    occurred_at: dm.UTC
    event: TurnManifestReady
