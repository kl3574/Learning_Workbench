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
