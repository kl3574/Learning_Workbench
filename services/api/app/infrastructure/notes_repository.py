"""Immutable note revisions, soft deletion and transaction-local anchor invalidation."""

from collections.abc import Iterable
import sqlite3
from uuid import uuid4

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes

from ..application.errors import ApiError
from .content_repository import ContentRepository, damaged, missing, reference
from .security import guard_subject_access


class NotesRepository(ContentRepository):
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        super().__init__(connection, workspace_id, allow_notes=True)

    def note(self, id: str, *, active: bool = True) -> dm.Note:
        stored = self.current(id)
        if not isinstance(stored.value, dm.Note):
            raise missing()
        index = self.connection.execute("SELECT * FROM notes_index WHERE note_id=? AND note_revision=?",
                                        (id, stored.value.revision)).fetchone()
        if (index is None or stored.value.workspace_id != self.workspace_id or index["workspace_id"] != self.workspace_id
                or index["anchor_id"] != stored.value.anchor.ref.id or index["anchor_revision"] != stored.value.anchor.ref.revision
                or index["anchor_state"] != stored.value.anchor_state):
            raise damaged()
        if active and stored.lifecycle != "active":
            raise ApiError(409, "NOTE_ARCHIVED", "笔记已删除，历史修订仍保留。")
        return stored.value

    def save_note(self, note: dm.Note, *, invalidated: bool = False) -> dm.ContentRef:
        self.ensure_new([note])
        self.insert_revisions([note], {})
        self.insert_dependencies(note, [(note.anchor.ref, "anchor")])
        self.connection.execute(
            "INSERT INTO notes_index(note_id,note_revision,workspace_id,anchor_id,anchor_revision,anchor_state) VALUES(?,?,?,?,?,?)",
            (note.id, note.revision, self.workspace_id, note.anchor.ref.id, note.anchor.ref.revision, note.anchor_state),
        )
        # Notes do not recursively advance the content dependency graph.
        self.connection.execute("UPDATE objects SET current_revision=? WHERE id=? AND workspace_id=?",
                                (note.revision, note.id, self.workspace_id))
        ref = reference(note)
        self.connection.execute("INSERT INTO outbox(id,event_type,payload_json) VALUES(?,?,?)", (
            f"outbox_{uuid4().hex}", "note.anchor_stale" if invalidated else "note.saved",
            canonical_bytes({"workspace_id": self.workspace_id, "ref": ref.model_dump(mode="json")}).decode(),
        ))
        return ref

    def delete(self, id: str) -> None:
        self.connection.execute("UPDATE objects SET lifecycle='archived' WHERE id=? AND workspace_id=?", (id, self.workspace_id))
        self.connection.execute("INSERT INTO outbox(id,event_type,payload_json) VALUES(?,?,?)", (
            f"outbox_{uuid4().hex}", "note.deleted", canonical_bytes({"workspace_id": self.workspace_id, "id": id}).decode(),
        ))


def mark_stale_notes(connection: sqlite3.Connection, workspace_id: str, previous_refs: Iterable[dm.ContentRef]) -> list[dm.ContentRef]:
    """Run once after all publication pointers advance, within their transaction.

    The caller freezes pre-publication current refs. Only exact anchors on those
    changed refs are affected; old revisions and explicit new anchors stay intact.
    """
    if not connection.in_transaction:
        raise ApiError(409, "TRANSACTION_REQUIRED", "笔记失效更新需要有效事务。")
    guard_subject_access(connection, workspace_id)
    repository = NotesRepository(connection, workspace_id)
    repository.require_workspace()
    changed: dict[tuple[str, int], dm.ContentRef] = {}
    for ref in previous_refs:
        if ref.entity == "note":
            continue
        old = repository.load(ref.entity, ref.id, ref.revision).value
        if reference(old) != ref:
            raise damaged()
        if reference(repository.current(ref.id).value) != ref:
            changed[(ref.id, ref.revision)] = ref
    if not changed:
        return []
    rows = connection.execute(
        "SELECT o.id FROM objects o JOIN notes_index n ON n.note_id=o.id AND n.note_revision=o.current_revision "
        "WHERE o.workspace_id=? AND o.kind='note' AND o.lifecycle='active' AND n.anchor_state='exact' ORDER BY o.id",
        (workspace_id,),
    ).fetchall()
    output = []
    for row in rows:
        note = repository.note(row["id"])
        ref = note.anchor.ref
        if note.anchor_state == "exact" and changed.get((ref.id, ref.revision)) == ref:
            updated = dm.Note.model_validate({**note.model_dump(mode="python"), "revision": note.revision + 1, "anchor_state": "stale"})
            output.append(repository.save_note(updated, invalidated=True))
    return output
