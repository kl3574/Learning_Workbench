"""Artifacts-owned routing facts; these facts grant no permission to read bytes."""

from dataclasses import dataclass
import sqlite3

from packages.contracts.canonical import canonical_bytes, sha256_bytes
from ..import_dto import DownloadArtifact
from ..application.errors import ApiError
from .content_repository import ContentRepository, damaged, missing
from .blobs import BlobInfo
from .database import utc_now


@dataclass(frozen=True)
class ArtifactBinding:
    id: str
    workspace_id: str
    profile: str
    job_id: str


class ArtifactRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection, self.workspace_id = connection, workspace_id

    def register(self, *, identifier: str, job_id: str, profile: str,
                 info: BlobInfo, filename: str, media_type: str) -> None:
        """Register only a caller-owned descriptor for already verified Blob bytes."""
        if not self.connection.in_transaction:
            raise damaged()
        self.connection.execute('INSERT OR IGNORE INTO content_blobs(sha256,relative_path,size,created_at) VALUES(?,?,?,?)',
            (info.sha256, info.relative_path, info.size, utc_now()))
        blob = self.connection.execute('SELECT * FROM content_blobs WHERE sha256=?', (info.sha256,)).fetchone()
        if ContentRepository.decode_blob(blob) != info:
            raise damaged()
        descriptor = canonical_bytes(dict(version=1, filename=filename, media_type=media_type,
            size=info.size, sha256=info.sha256)).decode()
        self.connection.execute('INSERT INTO artifacts(id,workspace_id,job_id,blob_sha256,profile,visibility,manifest_json,created_at) VALUES(?,?,?,?,?,?,?,?)',
            (identifier, self.workspace_id, job_id, info.sha256, profile, 'author_private', descriptor, utc_now()))

    def binding(self, identifier: str) -> ArtifactBinding:
        if not self.connection.in_transaction:
            raise ApiError(409, 'TRANSACTION_REQUIRED', '附件归属核验需要当前事务。')
        row = self.connection.execute(
            'SELECT id,workspace_id,profile,job_id FROM artifacts WHERE id=? AND workspace_id=?',
            (identifier, self.workspace_id)).fetchone()
        if row is None:
            raise missing()
        if not isinstance(row['job_id'], str) or not row['job_id'] or not row['profile']:
            raise damaged()
        return ArtifactBinding(row['id'], row['workspace_id'], row['profile'], row['job_id'])

    def manifest_sha256(self, identifier: str, artifact: DownloadArtifact) -> str:
        """Bind a reader's checked descriptor to the actual complete manifest.

        This validates storage metadata, not current access or physical bytes;
        callers still need the exact registered reader in this same transaction.
        """
        self.binding(identifier)
        try:
            artifact = DownloadArtifact.model_validate(artifact.model_dump(mode='python', warnings='error'))
            row = self.connection.execute('SELECT * FROM artifacts WHERE id=? AND workspace_id=?',
                (identifier, self.workspace_id)).fetchone()
            blob = self.connection.execute('SELECT * FROM content_blobs WHERE sha256=?', (row['blob_sha256'],)).fetchone()
            if blob is None:
                raise damaged()
            info = ContentRepository.decode_blob(blob)
            raw = canonical_bytes(dict(version=1, filename=artifact.filename, media_type=artifact.media_type,
                                       size=artifact.size, sha256=artifact.sha256)).decode()
            if (artifact.artifact_id != identifier or info.sha256 != artifact.sha256 or info.size != artifact.size
                    or row['manifest_json'] != raw):
                raise damaged()
            return sha256_bytes(raw.encode())
        except (ValueError, TypeError, AttributeError):
            raise damaged() from None
