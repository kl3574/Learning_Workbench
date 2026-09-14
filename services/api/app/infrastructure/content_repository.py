"""SQLite persistence for exact public revisions; no HTTP or answer projections."""

from dataclasses import dataclass
import sqlite3
from uuid import uuid4
from typing import Literal

from pydantic import ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.canonical import CANONICAL_VERSION, canonical_bytes, metadata_sha256, strict_json
from packages.contracts.validation import ENTITY_MODELS, PublishedModel

from ..application.errors import ApiError
from .blobs import BlobInfo
from .database import utc_now


@dataclass(frozen=True)
class StoredRevision:
    value: PublishedModel
    created_at: str
    lifecycle: Literal["active", "archived"]


def reference(value: PublishedModel) -> dm.ContentRef:
    return dm.ContentRef(entity=value.entity, id=value.id, revision=value.revision, sha256=metadata_sha256(value))


def missing() -> ApiError:
    return ApiError(404, "REFERENCE_MISSING", "指定内容修订不存在或不可访问。")


def damaged() -> ApiError:
    return ApiError(409, "CONTENT_HASH_MISMATCH", "存储的内容完整性校验失败。")


class ContentRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str, *, allow_notes: bool = False):
        self.connection = connection
        self.workspace_id = workspace_id
        self.allow_notes = allow_notes

    def require_workspace(self) -> None:
        if self.connection.execute("SELECT 1 FROM workspace WHERE id=?", (self.workspace_id,)).fetchone() is None:
            raise missing()

    def object_row(self, object_id: str) -> sqlite3.Row:
        row = self.connection.execute(
            "SELECT * FROM objects WHERE id=? AND workspace_id=?", (object_id, self.workspace_id),
        ).fetchone()
        if row is None or row["kind"] == "note" and not self.allow_notes:
            # Notes have their own permission and anchor lifecycle, outside M2.1.
            raise missing()
        return row

    def load(self, entity: str, object_id: str, revision: int) -> StoredRevision:
        if entity not in ENTITY_MODELS or entity == "note" and not self.allow_notes:
            raise missing()
        row = self.connection.execute(
            "SELECT r.*,o.kind,o.lifecycle FROM revisions r JOIN objects o ON o.id=r.object_id "
            "WHERE o.workspace_id=? AND o.id=? AND o.kind=? AND r.revision=?",
            (self.workspace_id, object_id, entity, revision),
        ).fetchone()
        if row is None:
            raise missing()
        return self.decode(row)

    @staticmethod
    def decode(row: sqlite3.Row) -> StoredRevision:
        try:
            model = ENTITY_MODELS[row["kind"]].model_validate(strict_json(row["metadata_json"]))
            if (model.id != row["object_id"] or model.entity != row["kind"]
                    or model.revision != row["revision"] or metadata_sha256(model) != row["sha256"]
                    or row["status"] != "published" or row["lifecycle"] not in {"active", "archived"}):
                raise damaged()
            return StoredRevision(model, row["created_at"], row["lifecycle"])
        except (KeyError, ValueError, TypeError, ValidationError):
            raise damaged() from None

    def current(self, object_id: str) -> StoredRevision:
        row = self.object_row(object_id)
        if row["current_revision"] is None:
            raise missing()
        return self.load(row["kind"], object_id, row["current_revision"])

    def body_info(self, value: dm.ContentBlock) -> BlobInfo:
        row = self.connection.execute(
            "SELECT b.* FROM content_blobs b JOIN block_bodies bb ON bb.body_sha256=b.sha256 "
            "JOIN objects o ON o.id=bb.block_id WHERE o.workspace_id=? AND o.kind='block' "
            "AND bb.block_id=? AND bb.block_revision=?",
            (self.workspace_id, value.id, value.revision),
        ).fetchone()
        if row is None or row["sha256"] != value.body_sha256:
            raise damaged()
        return self.decode_blob(row)

    @staticmethod
    def decode_blob(row: sqlite3.Row) -> BlobInfo:
        digest = row["sha256"]
        if row["relative_path"] != f"blobs/{digest[:2]}/{digest}" or type(row["size"]) is not int or row["size"] < 0:
            raise damaged()
        return BlobInfo(digest, row["relative_path"], row["size"])

    def public_body(self, digest: str) -> BlobInfo:
        row = self.connection.execute(
            "SELECT b.* FROM content_blobs b JOIN block_bodies bb ON bb.body_sha256=b.sha256 "
            "JOIN objects o ON o.id=bb.block_id WHERE o.workspace_id=? AND o.kind='block' AND b.sha256=? LIMIT 1",
            (self.workspace_id, digest),
        ).fetchone()
        if row is None:
            raise missing()
        return self.decode_blob(row)

    def concept_dependency(self, owner: PublishedModel, identifier: str) -> dm.Concept:
        rows = self.connection.execute(
            "SELECT d.target_revision FROM object_dependencies d JOIN objects o ON o.id=d.target_id "
            "WHERE d.owner_id=? AND d.owner_revision=? AND d.target_id=? AND d.relation='concept' "
            "AND o.workspace_id=? AND o.kind='concept'",
            (owner.id, owner.revision, identifier, self.workspace_id),
        ).fetchall()
        if len(rows) != 1:
            raise damaged()
        value = self.load("concept", identifier, rows[0]["target_revision"]).value
        if not isinstance(value, dm.Concept):
            raise damaged()
        return value

    def ensure_new(self, values: list[PublishedModel]) -> None:
        for value in values:
            row = self.connection.execute("SELECT * FROM objects WHERE id=?", (value.id,)).fetchone()
            if row is None:
                continue
            if row["workspace_id"] != self.workspace_id or row["kind"] != value.entity:
                raise missing()
            maximum = self.connection.execute(
                "SELECT MAX(revision) FROM revisions WHERE object_id=?", (value.id,),
            ).fetchone()[0]
            if maximum is not None and value.revision <= maximum:
                raise ApiError(409, "REVISION_CONFLICT", "发布必须使用尚未存在的递增修订。")

    def insert_revisions(self, values: list[PublishedModel], blobs: dict[str, BlobInfo]) -> None:
        now = utc_now()
        for info in blobs.values():
            existing = self.connection.execute("SELECT * FROM content_blobs WHERE sha256=?", (info.sha256,)).fetchone()
            if existing is not None and self.decode_blob(existing) != info:
                raise damaged()
            self.connection.execute(
                "INSERT OR IGNORE INTO content_blobs(sha256,relative_path,size,created_at) VALUES(?,?,?,?)",
                (info.sha256, info.relative_path, info.size, now),
            )
        for value in values:
            self.connection.execute(
                "INSERT OR IGNORE INTO objects(id,workspace_id,kind,current_revision) VALUES(?,?,?,NULL)",
                (value.id, self.workspace_id, value.entity),
            )
            self.connection.execute(
                "INSERT INTO revisions(object_id,revision,sha256,metadata_json,created_at) VALUES(?,?,?,?,?)",
                (value.id, value.revision, metadata_sha256(value), canonical_bytes(value).decode(), now),
            )
            if isinstance(value, dm.ContentBlock):
                self.connection.execute(
                    "INSERT INTO block_bodies(block_id,block_revision,body_sha256) VALUES(?,?,?)",
                    (value.id, value.revision, value.body_sha256),
                )

    def insert_dependencies(self, value: PublishedModel, targets: list[tuple[dm.ContentRef, str]]) -> None:
        for target, relation in targets:
            self.connection.execute(
                "INSERT OR IGNORE INTO object_dependencies(owner_id,owner_revision,target_id,target_revision,relation) "
                "VALUES(?,?,?,?,?)", (value.id, value.revision, target.id, target.revision, relation),
            )
        if isinstance(value, dm.Route):
            for position, step in enumerate(value.steps):
                self.connection.execute(
                    "INSERT INTO route_steps(route_id,route_revision,step_id,position,target_id,target_revision,requires_json) "
                    "VALUES(?,?,?,?,?,?,?)",
                    (value.id, value.revision, step.id, position, step.target.id, step.target.revision,
                     canonical_bytes(step.requires_steps).decode()),
                )

    def insert_concept_edges(self, course: dm.Course, concepts: dict[str, dm.Concept]) -> None:
        for concept in concepts.values():
            for prerequisite in concept.prerequisite_ids:
                self.connection.execute(
                    "INSERT INTO concept_edges(course_id,course_revision,prerequisite_id,dependent_id) VALUES(?,?,?,?)",
                    (course.id, course.revision, prerequisite, concept.id),
                )

    def advance(self, value: PublishedModel) -> None:
        old_row = self.object_row(value.id)
        old = self.load(value.entity, value.id, old_row["current_revision"]).value if old_row["current_revision"] else None
        affected = self.connection.execute(
            "WITH RECURSIVE affected(id) AS (SELECT ? UNION SELECT d.owner_id FROM object_dependencies d "
            "JOIN affected a ON d.target_id=a.id JOIN objects o ON o.id=d.owner_id WHERE o.workspace_id=?) "
            "SELECT id FROM affected ORDER BY id", (value.id, self.workspace_id),
        ).fetchall()
        self.connection.execute("UPDATE objects SET current_revision=? WHERE id=? AND workspace_id=?",
                                (value.revision, value.id, self.workspace_id))
        payload = {
            "workspace_id": self.workspace_id, "canonical_version": CANONICAL_VERSION,
            "old_ref": reference(old).model_dump(mode="json") if old else None,
            "new_ref": reference(value).model_dump(mode="json"),
            "affected_ids": [row["id"] for row in affected], "reason": "content_revision_published",
        }
        # Durable invalidation intent; no worker/index rebuild or downstream completion is claimed.
        self.connection.execute("INSERT INTO outbox(id,event_type,payload_json) VALUES(?,?,?)",
                                (f"outbox_{uuid4().hex}", "content.published", canonical_bytes(payload).decode()))
        if old is not None:
            self.connection.execute("INSERT INTO outbox(id,event_type,payload_json) VALUES(?,?,?)",
                                    (f"outbox_{uuid4().hex}", "content.dependencies_invalidated", canonical_bytes(payload).decode()))
