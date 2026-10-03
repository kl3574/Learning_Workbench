"""Explicit artifact readers: routing is not an authorization or blob-read grant.

Only application composition supplies the registry. A future Quality reader must
be implemented and registered explicitly; it cannot use Import's trusted legacy
download method as a substitute for current-session, same-transaction admission.
"""

from collections.abc import Mapping
import sqlite3
from types import MappingProxyType
from typing import Protocol

from ..import_dto import DownloadArtifact
from ..infrastructure.artifact_repository import ArtifactRepository
from ..infrastructure.content_repository import ContentRepository
from ..infrastructure.database import Database
from ..infrastructure.security import SessionIdentity, current_session_identity, guard_subject_access
from .errors import ApiError
from .jobs import artifact_job_kind


class ArtifactReader(Protocol):
    def read_artifact(self, connection: sqlite3.Connection, identity: SessionIdentity,
                      identifier: str) -> tuple[bytes, DownloadArtifact]: ...


def unavailable_owner() -> ApiError:
    return ApiError(409, 'ARTIFACT_OWNER_UNAVAILABLE', '此附件没有已实现的受控读取所有者。')


class ArtifactsService:
    def __init__(self, database: Database, readers: Mapping[tuple[str, str], ArtifactReader]):
        self.database, self.readers = database, MappingProxyType(dict(readers))

    def download(self, identity: SessionIdentity, identifier: str) -> tuple[bytes, DownloadArtifact]:
        try:
            with self.database.transaction() as connection:
                current = current_session_identity(connection, identity)
                ContentRepository(connection, current.workspace_id).require_workspace()
                guard_subject_access(connection, current.workspace_id)
                binding = ArtifactRepository(connection, current.workspace_id).binding(identifier)
                kind = artifact_job_kind(connection, current.workspace_id, binding.job_id)
                owner = self.readers.get((binding.profile, kind))
                if owner is None:
                    raise unavailable_owner()
                return owner.read_artifact(connection, current, identifier)
        except sqlite3.Error:
            # Preserve the existing download endpoint's storage error contract.
            raise ApiError(503, 'IMPORT_STORAGE_UNAVAILABLE', '导入存储暂不可用。', True) from None
