"""Permission-checked immutable notes with exact Markdown codepoint anchors."""

import base64
from collections.abc import Iterator
from contextlib import contextmanager
import hashlib
import hmac
import re
import secrets
import sqlite3
import time

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, strict_json

from ..infrastructure.blobs import BlobStore
from ..infrastructure.content_repository import damaged, reference
from ..infrastructure.database import Database
from ..infrastructure.idempotency import execute_idempotent
from ..infrastructure.notes_repository import NotesRepository
from ..infrastructure.security import SessionIdentity, guard_subject_access
from ..learning_dto import NoteDeleted, PageNote
from .errors import ApiError
from .learning import record_note_created, validated_ref


def invalid_anchor() -> ApiError:
    return ApiError(422, "ANCHOR_INVALID", "笔记选区与精确修订的正文不匹配。")


class NotesService:
    def __init__(self, database: Database):
        self.database = database
        self._cursor_key = secrets.token_bytes(32)

    @contextmanager
    def _access(self, workspace_id: str) -> Iterator[NotesRepository]:
        try:
            with self.database.transaction() as connection:
                repository = NotesRepository(connection, workspace_id)
                repository.require_workspace()
                guard_subject_access(connection, workspace_id)
                yield repository
        except sqlite3.Error:
            raise ApiError(503, "NOTES_STORAGE_UNAVAILABLE", "笔记存储暂不可用。", True) from None

    def _anchor(self, repository: NotesRepository, anchor: dm.Selection) -> None:
        validated_ref(repository, anchor.ref)
        value = repository.load(anchor.ref.entity, anchor.ref.id, anchor.ref.revision).value
        if isinstance(value, dm.ContentBlock):
            info = repository.body_info(value)
            try:
                body = BlobStore(self.database.settings.data_dir, max_bytes=max(1, info.size)).read(info.sha256, expected_size=info.size).decode("utf-8")
            except UnicodeError:
                raise damaged() from None
        else:
            raise ApiError(422, "ANCHOR_BODY_UNAVAILABLE", "此类对象没有可验证的 Markdown 正文，请选择具体内容块。")
        start, end = anchor.start_codepoint, anchor.end_codepoint
        if (not 0 <= start <= end <= len(body) or body[start:end] != anchor.exact_quote
                or len(anchor.prefix) > start or body[start - len(anchor.prefix):start] != anchor.prefix
                or body[end:end + len(anchor.suffix)] != anchor.suffix):
            raise invalid_anchor()

    @staticmethod
    def _identity(note: dm.Note, workspace_id: str, id: str | None = None) -> dm.Note:
        value = dm.Note.model_validate(note.model_dump(mode="python"))
        if value.workspace_id != workspace_id or id is not None and value.id != id:
            raise ApiError(422, "SCHEMA_INVALID", "笔记标识或工作区与请求不一致。")
        return value

    @staticmethod
    def _match(old: dm.Note, expected_sha256: str) -> None:
        if not isinstance(expected_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", expected_sha256) is None:
            raise ApiError(422, "SCHEMA_INVALID", "笔记版本条件无效。")
        if reference(old).sha256 != expected_sha256:
            raise ApiError(412, "REVISION_CONFLICT", "笔记已有新修订，请比较最新版本后重试。")

    def list(self, workspace_id: str, ref_id: str | None = None, limit: int = 20, cursor: str | None = None) -> PageNote:
        if type(limit) is not int or not 1 <= limit <= 100 or ref_id is not None and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,79}", ref_id) is None:
            raise ApiError(422, "SCHEMA_INVALID", "笔记查询参数无效。")
        scope = [workspace_id, ref_id, limit]
        position = ""
        if cursor is not None:
            try:
                if not 1 <= len(cursor) <= 1024 or re.fullmatch(r"[A-Za-z0-9_-]+", cursor) is None:
                    raise ValueError("cursor")
                decoded = base64.b64decode(cursor + "=" * (-len(cursor) % 4), altchars=b"-_", validate=True)
                data, signature = decoded[:-32], decoded[-32:]
                if not hmac.compare_digest(hmac.new(self._cursor_key, data, hashlib.sha256).digest(), signature):
                    raise ValueError("signature")
                value = strict_json(data)
                if (not isinstance(value, dict) or set(value) != {"scope", "position", "expires"} or value["scope"] != scope
                        or not isinstance(value["position"], str) or type(value["expires"]) is not int or value["expires"] < time.time()):
                    raise ValueError("scope")
                position = value["position"]
            except (ValueError, TypeError, KeyError):
                raise ApiError(422, "SCHEMA_INVALID", "笔记分页游标无效或已过期。") from None
        with self._access(workspace_id) as repository:
            rows = repository.connection.execute(
                "SELECT o.id FROM objects o JOIN notes_index n ON n.note_id=o.id AND n.note_revision=o.current_revision "
                "WHERE o.workspace_id=? AND o.kind='note' AND o.lifecycle='active' AND o.id>? "
                "AND (? IS NULL OR n.anchor_id=?) ORDER BY o.id LIMIT ?",
                (workspace_id, position, ref_id, ref_id, limit + 1),
            ).fetchall()
            items = [repository.note(row["id"]) for row in rows[:limit]]
            next_cursor = None
            if len(rows) > limit:
                data = canonical_bytes({"scope": scope, "position": items[-1].id, "expires": int(time.time()) + 3600})
                next_cursor = base64.urlsafe_b64encode(data + hmac.new(self._cursor_key, data, hashlib.sha256).digest()).decode().rstrip("=")
            return PageNote(items=items, next_cursor=next_cursor)

    def create(self, identity: SessionIdentity, note: dm.Note, key: str | None) -> dm.ContentRef:
        value = self._identity(note, identity.workspace_id)
        with self._access(identity.workspace_id) as repository:
            def operation():
                if value.revision != 1 or value.anchor_state != "exact":
                    raise ApiError(422, "SCHEMA_INVALID", "新笔记必须从修订 1 和已验证选区开始。")
                if value.anchor.ref.id == value.id:
                    raise invalid_anchor()
                self._anchor(repository, value.anchor)
                ref = repository.save_note(value)
                record_note_created(repository.connection, identity.workspace_id, ref)
                return ref.model_dump(mode="json")

            return dm.ContentRef.model_validate(execute_idempotent(repository.connection, actor=identity.workspace_id,
                route="POST /notes", key=key, payload=value.model_dump(mode="json"), operation=operation))

    def update(self, identity: SessionIdentity, id: str, note: dm.Note, expected_sha256: str, key: str | None) -> dm.ContentRef:
        value = self._identity(note, identity.workspace_id, id)
        with self._access(identity.workspace_id) as repository:
            def operation():
                old = repository.note(id)
                self._match(old, expected_sha256)
                if value.revision != old.revision + 1:
                    raise ApiError(422, "SCHEMA_INVALID", "笔记候选修订必须正好递增 1。")
                if value.anchor.ref.id == value.id:
                    raise invalid_anchor()
                if value.anchor != old.anchor or value.anchor_state != old.anchor_state:
                    if value.anchor_state != "exact" or old.anchor_state != "exact" and value.anchor == old.anchor:
                        raise invalid_anchor()
                    self._anchor(repository, value.anchor)
                elif value.anchor_state == "exact":
                    self._anchor(repository, value.anchor)
                return repository.save_note(value).model_dump(mode="json")

            return dm.ContentRef.model_validate(execute_idempotent(repository.connection, actor=identity.workspace_id,
                route=f"PATCH /notes/{id}", key=key, payload={"note": value.model_dump(mode="json"), "if_match": expected_sha256}, operation=operation))

    def delete(self, identity: SessionIdentity, id: str, expected_sha256: str, key: str | None) -> NoteDeleted:
        with self._access(identity.workspace_id) as repository:
            def operation():
                old = repository.note(id, active=False)
                self._match(old, expected_sha256)
                if repository.object_row(id)["lifecycle"] == "active":
                    repository.delete(id)
                return NoteDeleted(id=id).model_dump(mode="json")

            return NoteDeleted.model_validate(execute_idempotent(repository.connection, actor=identity.workspace_id,
                route=f"DELETE /notes/{id}", key=key, payload={"id": id, "if_match": expected_sha256}, operation=operation))
