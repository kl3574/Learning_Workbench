"""Explicit artifact readers: routing is not an authorization or blob-read grant.

Only application composition supplies the registry. A future Quality reader must
be implemented and registered explicitly; it cannot use Import's trusted legacy
download method as a substitute for current-session, same-transaction admission.
"""

from collections.abc import Callable, Mapping
import sqlite3
from types import MappingProxyType
from typing import Protocol

from packages.contracts.canonical import sha256_bytes

from ..import_dto import DownloadArtifact
from ..infrastructure.artifact_repository import ArtifactRepository
from ..infrastructure.content_repository import ContentRepository, damaged
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
    def __init__(self, database: Database, readers: Mapping[tuple[str, str], ArtifactReader], *,
                 download_guards: Mapping[tuple[str, str], Callable[[SessionIdentity], None]] | None = None):
        self.database, self.readers = database, MappingProxyType(dict(readers))
        self.download_guards = MappingProxyType(dict(download_guards or {}))
        if not self.download_guards.keys() <= self.readers.keys():
            raise ValueError('An artifact delivery guard requires its registered reader')

    def read_in_transaction(self, connection: sqlite3.Connection, identity: SessionIdentity,
                            identifier: str) -> tuple[bytes, DownloadArtifact]:
        """Authenticate registered owner and physical bytes in the caller's transaction.

        This is a read port for hash-bound evidence decisions, not an arbitrary
        blob capability. Unregistered profiles and missing owner history fail closed.
        """
        current = current_session_identity(connection, identity)
        ContentRepository(connection, current.workspace_id).require_workspace()
        guard_subject_access(connection, current.workspace_id)
        repository = ArtifactRepository(connection, current.workspace_id)
        binding = repository.binding(identifier)
        kind = artifact_job_kind(connection, current.workspace_id, binding.job_id)
        owner = self.readers.get((binding.profile, kind))
        if owner is None:
            raise unavailable_owner()
        raw, artifact = owner.read_artifact(connection, current, identifier)
        if (artifact.artifact_id != identifier or artifact.sha256 != sha256_bytes(raw)
                or artifact.size != len(raw)):
            raise damaged()
        repository.manifest_sha256(identifier, artifact)
        return raw, artifact

    def download(self, identity: SessionIdentity, identifier: str) -> tuple[bytes, DownloadArtifact]:
        try:
            with self.database.transaction() as connection:
                value = self.read_in_transaction(connection, identity, identifier)
                # Capture the checked owner in the same original transaction.
                # Its dedicated delivery guard runs only after that snapshot closes.
                binding = ArtifactRepository(connection, identity.workspace_id).binding(identifier)
                kind = artifact_job_kind(connection, identity.workspace_id, binding.job_id)
                guard = self.download_guards.get((binding.profile, kind))
            if guard is not None:
                guard(identity)
            return value
        except sqlite3.Error:
            # Preserve the existing download endpoint's storage error contract.
            raise ApiError(503, 'IMPORT_STORAGE_UNAVAILABLE', '导入存储暂不可用。', True) from None
