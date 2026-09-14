"""Append-only user actions and atomic workspace progress projections."""

import sqlite3
from typing import Literal
from uuid import uuid4

from pydantic import ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, strict_json

from ..application.errors import ApiError
from ..learning_dto import BookmarkState, LearningActionRequest, LearningActionResponse, LearningProgress, ReadingState
from .database import utc_now


class StoredUserAction(dm.StrictModel):
    event_id: dm.Id
    workspace_id: dm.Id
    actor: Literal["learner"] = "learner"
    origin: Literal["native"] = "native"
    kind: Literal["read_marked", "bookmark_set"]
    ref: dm.ContentRef
    value: bool
    occurred_at: dm.UTC


def ref_key(ref: dm.ContentRef) -> tuple[str, str, int, str]:
    return ref.entity, ref.id, ref.revision, ref.sha256


class LearningRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection = connection
        self.workspace_id = workspace_id

    def progress(self) -> LearningProgress:
        row = self.connection.execute("SELECT * FROM learning_progress WHERE workspace_id=?", (self.workspace_id,)).fetchone()
        if row is None:
            return LearningProgress(revision=1, readings=[], route_steps=[], bookmarks=[])
        try:
            value = LearningProgress.model_validate(strict_json(row["projection_json"]))
            if value.revision != row["revision"]:
                raise ValueError("revision mismatch")
            for identities in [[ref_key(item.ref) for item in value.readings], [ref_key(item.ref) for item in value.bookmarks]]:
                if len(identities) != len(set(identities)):
                    raise ValueError("duplicate projection ref")
            return value
        except (ValueError, TypeError, ValidationError):
            raise ApiError(409, "LEARNING_PROJECTION_INVALID", "学习记录完整性校验失败。") from None

    def append(self, event: StoredUserAction | dm.LearningEvent) -> None:
        self.connection.execute(
            "INSERT INTO learning_events(event_id,workspace_id,kind,origin,payload_json,occurred_at) VALUES(?,?,?,?,?,?)",
            (event.event_id, self.workspace_id, event.kind, event.origin, canonical_bytes(event).decode(), event.occurred_at),
        )

    def save(self, previous: LearningProgress, updated: LearningProgress, event_id: str) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO learning_progress(workspace_id,revision,projection_json,last_event_id) VALUES(?,1,?,NULL)",
            (self.workspace_id, canonical_bytes(LearningProgress(revision=1, readings=[], route_steps=[], bookmarks=[])).decode()),
        )
        result = self.connection.execute(
            "UPDATE learning_progress SET revision=?,projection_json=?,last_event_id=? WHERE workspace_id=? AND revision=?",
            (updated.revision, canonical_bytes(updated).decode(), event_id, self.workspace_id, previous.revision),
        )
        if result.rowcount != 1:
            raise ApiError(412, "REVISION_CONFLICT", "学习记录已更新，请读取最新版本后重试。")
        self.connection.execute("INSERT INTO outbox(id,event_type,payload_json) VALUES(?,?,?)", (
            f"outbox_{uuid4().hex}", "learning.action_recorded",
            canonical_bytes({"workspace_id": self.workspace_id, "event_id": event_id, "progress_revision": updated.revision}).decode(),
        ))

    def action(self, request: LearningActionRequest) -> LearningActionResponse:
        previous = self.progress()
        if request.expected_revision != previous.revision:
            raise ApiError(412, "REVISION_CONFLICT", "学习记录已更新，请读取最新版本后重试。")
        now = utc_now()
        event = StoredUserAction(event_id=f"event_{uuid4().hex}", workspace_id=self.workspace_id,
                                 kind=request.kind, ref=request.ref, value=request.value, occurred_at=now)
        readings = {ref_key(item.ref): item for item in previous.readings}
        bookmarks = {ref_key(item.ref): item for item in previous.bookmarks}
        if request.kind == "read_marked":
            readings[ref_key(request.ref)] = ReadingState(ref=request.ref, read=request.value, read_at=now if request.value else None)
        else:
            bookmarks[ref_key(request.ref)] = BookmarkState(ref=request.ref, value=request.value, updated_at=now)
        updated = LearningProgress(revision=previous.revision + 1, readings=[readings[key] for key in sorted(readings)],
                                   route_steps=previous.route_steps, bookmarks=[bookmarks[key] for key in sorted(bookmarks)])
        self.append(event)
        self.save(previous, updated, event.event_id)
        return LearningActionResponse(event_id=event.event_id, progress_revision=updated.revision)

    def note_created(self, ref: dm.ContentRef) -> str:
        previous = self.progress()
        event = dm.LearningEvent(event_id=f"event_{uuid4().hex}", workspace_id=self.workspace_id, actor="learner",
                                 origin="native", kind="note_created", ref=ref, occurred_at=utc_now())
        updated = LearningProgress(revision=previous.revision + 1, readings=previous.readings,
                                   route_steps=previous.route_steps, bookmarks=previous.bookmarks)
        self.append(event)
        self.save(previous, updated, event.event_id)
        return event.event_id

    def practice_event(self, kind: Literal["hint_revealed", "solution_revealed", "practice_submitted"],
                       ref: dm.ContentRef, practice_session_id: str) -> str:
        previous = self.progress()
        event = dm.LearningEvent(event_id=f"event_{uuid4().hex}", workspace_id=self.workspace_id, actor="server",
            origin="native", kind=kind, ref=ref, occurred_at=utc_now(), attempt_id=practice_session_id)
        updated = LearningProgress(revision=previous.revision + 1, readings=previous.readings,
                                   route_steps=previous.route_steps, bookmarks=previous.bookmarks)
        self.append(event)
        self.save(previous, updated, event.event_id)
        return event.event_id

    def validate_practice_event(self, event_id: str,
                                kind: Literal["hint_revealed", "solution_revealed", "practice_submitted"],
                                ref: dm.ContentRef, practice_session_id: str) -> None:
        row = self.connection.execute("SELECT * FROM learning_events WHERE event_id=? AND workspace_id=?",
                                      (event_id, self.workspace_id)).fetchone()
        try:
            if row is None:
                raise ValueError("missing event")
            event = dm.LearningEvent.model_validate(strict_json(row["payload_json"]))
            if (event.event_id != event_id or event.workspace_id != self.workspace_id or event.actor != "server"
                    or event.origin != "native" or row["origin"] != event.origin
                    or event.kind != kind or row["kind"] != event.kind
                    or event.ref != ref or event.attempt_id != practice_session_id
                    or event.occurred_at != row["occurred_at"]):
                raise ValueError("event association mismatch")
        except (ValueError, TypeError, KeyError):
            raise ApiError(409, "PRACTICE_SNAPSHOT_INVALID", "练习关联的学习事件完整性校验失败。") from None
