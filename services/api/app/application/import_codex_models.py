"""Private Import-owned Codex source bindings and checked artifact read port."""
from dataclasses import dataclass
import sqlite3
from typing import Annotated, Literal, Protocol

from pydantic import Field
from packages.contracts import domain_models as dm

from ..codex_turn_dto import CodexArtifactImportWrite
from ..import_dto import ImportStatus
from ..infrastructure.security import SessionIdentity


class CodexImportBinding(dm.StrictModel):
    version: Literal['codex-import-binding-v1']
    workspace_id: dm.Id
    actor_session_id: dm.Id
    session_id: dm.Id
    turn_id: dm.Id
    source_job_id: dm.Id
    terminal_receipt_sha256: dm.Sha256
    manifest_id: dm.Id
    manifest_sha256: dm.Sha256
    artifact_id: dm.Id
    artifact_sha256: dm.Sha256
    artifact_size: Annotated[int, Field(strict=True, ge=1, le=16777216)]
    aggregate_job_id: dm.Id
    import_id: dm.Id
    import_job_id: dm.Id
    source_id: dm.Id


@dataclass(frozen=True)
class CheckedCodexArtifactSource:
    """Returned only by the configured Artifact owner after an actual byte read."""
    workspace_id: str
    actor_session_id: str
    session_id: str
    turn_id: str
    source_job_id: str
    terminal_receipt_sha256: str
    manifest_id: str
    manifest_sha256: str
    artifact_id: str
    artifact_sha256: str
    artifact_size: int
    import_kind: Literal['markdown', 'html', 'learnpack']
    filename: str
    media_type: str
    data: bytes


class CodexArtifactSourcePort(Protocol):
    def read_selected_artifacts(self, conn: sqlite3.Connection, identity: SessionIdentity,
                                session_id: str, body: CodexArtifactImportWrite
                                ) -> tuple[CheckedCodexArtifactSource, ...]: ...


@dataclass(frozen=True)
class CheckedCodexImportStage:
    binding: CodexImportBinding
    status: ImportStatus
    job: dm.JobRef
    preview_reached: bool
    preview_receipt_sha256: str | None


class CodexImportRecord(dm.StrictModel):
    version: Literal['codex-import-record-v1']
    binding: CodexImportBinding
    original_artifact_id: dm.Id
    filename: str
    media_type: str
    job_input_json: str
    created_at: dm.UTC


class CodexImportBatch(dm.StrictModel):
    version: Literal['codex-import-batch-v1']
    workspace_id: dm.Id
    aggregate_job_id: dm.Id
    records: Annotated[list[CodexImportRecord], Field(min_length=1, max_length=32)]


class CodexImportPreviewReceipt(dm.StrictModel):
    version: Literal['codex-import-preview-v1']
    workspace_id: dm.Id
    import_id: dm.Id
    binding_sha256: dm.Sha256
    job_revision: dm.Revision
    preview_json: str
    event_prefix_json: str


CODEX_SOURCE_RIGHTS = 'user_selected_model_output; unreviewed; rights_not_verified'


def codex_source_warning() -> dm.Warning:
    return dm.Warning(code='CODEX_IMPORTED_MATERIAL_UNREVIEWED', severity='warning',
        message='这是用户选择回导的未审模型材料；不代表人类原作、已核引用或数学、来源、教学审核通过。')
