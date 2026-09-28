"""Artifacts-owned routing facts; these facts grant no permission to read bytes."""

from dataclasses import dataclass
import sqlite3

from ..application.errors import ApiError
from .content_repository import damaged, missing


@dataclass(frozen=True)
class ArtifactBinding:
    id: str
    workspace_id: str
    profile: str
    job_id: str


class ArtifactRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection, self.workspace_id = connection, workspace_id

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
