"""Durable import/job records and lease transitions in caller-owned transactions."""

import sqlite3
from typing import Any
from uuid import uuid4

from packages.contracts.canonical import canonical_bytes, strict_json

from ..application.errors import ApiError
from .blobs import BlobInfo
from .content_repository import ContentRepository, damaged, missing
from .database import utc_now


def identifier(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def json_text(value: Any) -> str:
    return canonical_bytes(value).decode("utf-8")


def json_object(value: str) -> dict[str, Any]:
    try:
        result = strict_json(value)
        if not isinstance(result, dict):
            raise damaged()
        return result
    except (ValueError, TypeError):
        raise damaged() from None


class ImportRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection = connection
        self.workspace_id = workspace_id

    def load(self, import_id: str) -> sqlite3.Row:
        row = self.connection.execute(
            "SELECT i.*,j.status AS job_status,j.revision AS job_revision,j.lease_owner,j.lease_until,"
            "j.input_json,j.result_json,s.metadata_json AS source_metadata,s.blob_sha256,s.media_type,s.title,s.rights,"
            "s.parser_version FROM ingestion_imports i JOIN jobs j ON j.id=i.job_id JOIN sources s ON s.id=i.source_id "
            "WHERE i.id=? AND i.workspace_id=?", (import_id, self.workspace_id),
        ).fetchone()
        if row is None:
            raise missing()
        return row

    def from_job(self, job_id: str) -> sqlite3.Row:
        row = self.connection.execute("SELECT id FROM ingestion_imports WHERE job_id=? AND workspace_id=?",
                                      (job_id, self.workspace_id)).fetchone()
        if row is None:
            raise missing()
        return self.load(row["id"])

    def add_blob(self, info: BlobInfo) -> None:
        existing = self.connection.execute("SELECT * FROM content_blobs WHERE sha256=?", (info.sha256,)).fetchone()
        if existing is not None and ContentRepository.decode_blob(existing) != info:
            raise damaged()
        self.connection.execute("INSERT OR IGNORE INTO content_blobs(sha256,relative_path,size,created_at) VALUES(?,?,?,?)",
                                (info.sha256, info.relative_path, info.size, utc_now()))

    def blob(self, digest: str) -> BlobInfo:
        row = self.connection.execute("SELECT * FROM content_blobs WHERE sha256=?", (digest,)).fetchone()
        if row is None:
            raise damaged()
        return ContentRepository.decode_blob(row)

    def event(self, job_id: str, kind: str, payload: dict[str, Any]) -> None:
        self.connection.execute(
            "INSERT INTO job_events(job_id,seq,type,payload_json,occurred_at) "
            "VALUES(?,COALESCE((SELECT MAX(seq)+1 FROM job_events WHERE job_id=?),1),?,?,?)",
            (job_id, job_id, kind, json_text(payload), utc_now()),
        )

    def transition(self, row: sqlite3.Row, *, job_status: str, import_status: str,
                   result: dict[str, Any] | None = None, lease_owner: str | None = None) -> None:
        changed = self.connection.execute(
            "UPDATE jobs SET status=?,revision=revision+1,result_json=?,lease_owner=NULL,lease_until=NULL,updated_at=? "
            "WHERE id=? AND workspace_id=? AND revision=? AND (? IS NULL OR lease_owner=?)",
            (job_status, json_text(result) if result is not None else row["result_json"], utc_now(), row["job_id"],
             self.workspace_id, row["job_revision"], lease_owner, lease_owner),
        )
        if changed.rowcount != 1:
            raise ApiError(409, "REVISION_CONFLICT", "导入任务状态已改变。", True)
        self.connection.execute("UPDATE ingestion_imports SET status=? WHERE id=? AND workspace_id=?",
                                (import_status, row["id"], self.workspace_id))
        self.event(row["job_id"], job_status, {"status": job_status, "revision": row["job_revision"] + 1})

    def artifact(self, *, info: BlobInfo, filename: str, media_type: str, visibility: str,
                 profile: str, job_id: str, artifact_id: str | None = None) -> str:
        artifact_id = artifact_id or identifier("artifact")
        self.add_blob(info)
        self.connection.execute(
            "INSERT INTO artifacts(id,workspace_id,job_id,blob_sha256,profile,manifest_json,visibility,created_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (artifact_id, self.workspace_id, job_id, info.sha256, profile,
             json_text({"version": 1, "filename": filename, "media_type": media_type, "size": info.size,
                        "sha256": info.sha256}), visibility, utc_now()),
        )
        return artifact_id
