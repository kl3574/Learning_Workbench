"""Real SQLite transactions and authenticated HTTP for notes and explicit actions."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256
from services.api.app.application.content import ContentService
from services.api.app.application.errors import ApiError
from services.api.app.application.learning import LearningService, reading_states
from services.api.app.application.notes import NotesService
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.content_repository import ContentRepository, reference
from services.api.app.infrastructure.database import Database, utc_now
from services.api.app.infrastructure.notes_repository import mark_stale_notes
from services.api.app.infrastructure.security import SessionIdentity, issue_bootstrap_code
from services.api.app.interfaces.boundary import install_boundary
from services.api.app.interfaces.content_http import create_content_router
from services.api.app.interfaces.http import create_router
from services.api.app.interfaces.learning_http import create_learning_router
from services.api.app.learning_dto import LearningActionRequest


BODY = "首🧠字 e\u0301 中文\n\n$x^2$ 尾声"


def tree(suffix="", revision=1):
    data = (BODY + (f"\n新修订{revision}" if revision > 1 else "")).encode()
    block = dm.ContentBlock(id=f"block_notes{suffix}", revision=revision, kind="worked_example", title="合成例题",
        body_path=f"body/{suffix or 'main'}-{revision}.md", body_sha256=hashlib.sha256(data).hexdigest())
    lesson = dm.Lesson(id=f"lesson_notes{suffix}", revision=revision, title="合成小节", objectives=[], block_refs=[reference(block)])
    course = dm.Course(id=f"course_notes{suffix}", revision=revision, title="合成课程", audience="合成测试", lesson_refs=[reference(lesson)])
    return [block, lesson, course], {block.body_path: data}


def note_for(workspace, block, id="note_test", quote="e\u0301", text=BODY):
    start = text.index(quote)
    end = start + len(quote)
    return dm.Note(id=id, revision=1, workspace_id=workspace, markdown="合成笔记 $x^2$",
        anchor=dm.Selection(ref=reference(block), exact_quote=quote, prefix=text[max(0, start - 2):start],
                            suffix=text[end:end + 2], start_codepoint=start, end_codepoint=end))


@pytest.fixture
def storage(tmp_path):
    settings = Settings(data_dir=tmp_path / "data")
    database = Database(settings)
    workspace = database.initialize()
    identity = SessionIdentity("session_notes_test", workspace, "learner", "unused", "2099-01-01T00:00:00Z")
    objects, bodies = tree()
    ContentService(database).publish(workspace, objects, bodies)
    return database, workspace, identity, objects, bodies


def count(database, table):
    assert table in {"learning_events", "learning_progress", "notes_index", "revisions", "objects", "outbox", "idempotency", "evidence"}
    with database.connect() as connection:
        return connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def http_app(database):
    app = FastAPI()
    install_boundary(app, database.settings, database)
    app.include_router(create_router(database.settings, database))
    app.include_router(create_learning_router(database))
    app.include_router(create_content_router(database))
    return app


@pytest.fixture
def http(storage):
    database, workspace, identity, objects, bodies = storage
    with TestClient(http_app(database), base_url=database.settings.origin) as client:
        bootstrap = client.post("/api/v1/session/bootstrap", json={"one_time_code": issue_bootstrap_code(database)},
                                headers={"Origin": database.settings.origin})
        assert bootstrap.status_code == 200
        headers = {"Origin": database.settings.origin, "X-CSRF-Token": bootstrap.json()["csrf_token"], "Idempotency-Key": "note-create"}
        yield client, headers, storage


def test_note_create_patch_delete_replay_and_restart_preserve_exact_history(http):
    client, headers, (database, workspace, _, objects, _) = http
    note = note_for(workspace, objects[0])
    first = client.post("/api/v1/notes", json=note.model_dump(mode="json"), headers=headers)
    assert first.status_code == 201
    ref = first.json()
    assert ref == reference(note).model_dump(mode="json")
    assert first.headers["etag"] == f'"{ref["sha256"]}"'
    assert client.post("/api/v1/notes", json=note.model_dump(mode="json"), headers=headers).json() == ref
    assert count(database, "learning_events") == 1
    progress = client.get("/api/v1/learning/progress").json()
    assert progress == {"revision": 2, "readings": [], "route_steps": [], "bookmarks": []}
    assert client.get("/api/v1/notes?ref_id=block_notes").json()["items"] == [note.model_dump(mode="json")]
    updated = dm.Note.model_validate({**note.model_dump(), "revision": 2, "markdown": "编辑后合成笔记"})
    patch_headers = {**headers, "Idempotency-Key": "note-patch", "If-Match": first.headers["etag"]}
    patch = client.patch("/api/v1/notes/note_test", json=updated.model_dump(mode="json"), headers=patch_headers)
    assert patch.status_code == 200
    assert client.patch("/api/v1/notes/note_test", json=updated.model_dump(mode="json"), headers=patch_headers).json() == patch.json()
    stale = client.patch("/api/v1/notes/note_test", json=updated.model_dump(mode="json"), headers={**patch_headers, "Idempotency-Key": "note-stale"})
    assert stale.status_code == 412
    delete_headers = {**headers, "Idempotency-Key": "note-delete", "If-Match": patch.headers["etag"]}
    deleted = client.delete("/api/v1/notes/note_test", headers=delete_headers)
    assert deleted.json() == {"id": "note_test", "deleted": True}
    assert client.delete("/api/v1/notes/note_test", headers=delete_headers).json() == deleted.json()
    assert count(database, "learning_events") == 1
    assert client.get("/api/v1/notes").json()["items"] == []
    with database.connect() as connection:
        repository = ContentRepository(connection, workspace, allow_notes=True)
        assert repository.load("note", note.id, 1).value == note
        assert repository.load("note", note.id, 2).value == updated
        assert repository.current(note.id).lifecycle == "archived"
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    restarted = Database(database.settings)
    restarted.initialize()
    assert NotesService(restarted).list(workspace).items == []
    assert LearningService(restarted).progress(workspace).revision == 2


@pytest.mark.parametrize("change", [
    {"start_codepoint": 6, "end_codepoint": 8},  # UTF-16 position after a non-BMP character.
    {"start_codepoint": 10, "end_codepoint": 12},  # UTF-8 byte offsets are also invalid.
    {"exact_quote": "é"},  # No Unicode normalization.
    {"prefix": "wrong"}, {"suffix": "wrong"}, {"end_codepoint": 999},
    {"exact_quote": "PRIVATE_SYNTHETIC_CANARY"},
])
def test_native_anchor_rejects_wrong_units_text_bounds_and_context(http, change):
    client, headers, (database, workspace, _, objects, _) = http
    value = note_for(workspace, objects[0]).model_dump(mode="json")
    value["anchor"].update(change)
    response = client.post("/api/v1/notes", json=value, headers=headers)
    assert response.status_code == 422
    assert "PRIVATE_SYNTHETIC_CANARY" not in response.text
    assert count(database, "notes_index") == count(database, "learning_events") == 0


def test_full_reference_hash_and_workspace_are_required(http):
    client, headers, (database, workspace, _, objects, _) = http
    value = note_for(workspace, objects[0]).model_dump(mode="json")
    value["anchor"]["ref"]["sha256"] = "0" * 64
    assert client.post("/api/v1/notes", json=value, headers=headers).json()["error"]["code"] == "REFERENCE_HASH_MISMATCH"
    value = note_for(workspace, objects[0]).model_dump(mode="json")
    value["workspace_id"] = "workspace_other"
    assert client.post("/api/v1/notes", json=value, headers=headers).status_code == 422
    assert count(database, "learning_events") == 0


def test_note_create_and_event_are_atomic_on_real_sqlite_failure(storage):
    database, workspace, identity, objects, _ = storage
    before = {table: count(database, table) for table in ["objects", "revisions", "notes_index", "outbox", "idempotency"]}
    with database.transaction() as connection:
        connection.execute("CREATE TRIGGER fail_note_event BEFORE INSERT ON learning_events BEGIN SELECT RAISE(ABORT,'synthetic injected failure'); END")
    with pytest.raises(ApiError) as failure:
        NotesService(database).create(identity, note_for(workspace, objects[0]), "atomic-note")
    assert failure.value.code == "NOTES_STORAGE_UNAVAILABLE"
    assert {table: count(database, table) for table in before} == before
    assert count(database, "learning_events") == count(database, "learning_progress") == 0


def test_publication_hook_creates_one_immutable_stale_revision_and_explicit_reanchor(storage):
    database, workspace, identity, objects, _ = storage
    notes = NotesService(database)
    old_note = note_for(workspace, objects[0])
    notes.create(identity, old_note, "stale-note-create")
    other, bodies = tree("_unrelated")
    ContentService(database).publish(workspace, other, bodies)
    notes.create(identity, note_for(workspace, other[0], "note_unrelated"), "other-note-create")
    newer, new_bodies = tree(revision=2)
    with database.transaction() as connection:
        ContentService(database).publish_in_transaction(connection, workspace, newer, new_bodies)
        mark_stale_notes(connection, workspace, [reference(item) for item in objects])
        assert mark_stale_notes(connection, workspace, [reference(item) for item in objects]) == []
    current = {note.id: note for note in notes.list(workspace).items}
    stale = current[old_note.id]
    assert stale.revision == 2 and stale.anchor_state == "stale" and stale.anchor == old_note.anchor
    assert current["note_unrelated"].revision == 1 and current["note_unrelated"].anchor_state == "exact"
    with database.connect() as connection:
        old = ContentRepository(connection, workspace, allow_notes=True).load("note", old_note.id, 1).value
        assert old == old_note and metadata_sha256(old) == metadata_sha256(old_note)
    with pytest.raises(ApiError) as conflict:
        notes.update(identity, old_note.id, dm.Note.model_validate({**old_note.model_dump(), "revision": 2}), reference(old_note).sha256, "stale-edit")
    assert conflict.value.status == 412
    edit = dm.Note.model_validate({**stale.model_dump(), "revision": 3, "markdown": "只编辑正文，不自动重定位"})
    notes.update(identity, edit.id, edit, reference(stale).sha256, "stale-body-edit")
    exact = note_for(workspace, newer[0], text=next(iter(new_bodies.values())).decode())
    exact = dm.Note.model_validate({**exact.model_dump(), "revision": 4})
    notes.update(identity, exact.id, exact, reference(edit).sha256, "explicit-reanchor")
    assert {note.id: note for note in notes.list(workspace).items}[exact.id] == exact
    assert count(database, "learning_events") == 2  # Only two actual note creations.


def test_note_pagination_filter_signed_cursor_and_archived_view(storage):
    database, workspace, identity, objects, _ = storage
    notes = NotesService(database)
    for suffix in ["a", "b", "c"]:
        notes.create(identity, note_for(workspace, objects[0], "note_" + suffix), "page-" + suffix)
    first = notes.list(workspace, limit=1)
    second = notes.list(workspace, limit=1, cursor=first.next_cursor)
    assert [first.items[0].id, second.items[0].id] == ["note_a", "note_b"]
    with pytest.raises(ApiError):
        notes.list(workspace, ref_id=objects[0].id, limit=1, cursor=first.next_cursor)
    with pytest.raises(ApiError):
        notes.list(workspace, limit=2, cursor=first.next_cursor)
    with pytest.raises(ApiError):
        NotesService(database).list(workspace, limit=1, cursor=first.next_cursor)
    assert notes.list(workspace, ref_id="block_absent").items == []


def test_note_index_corruption_fails_closed(storage):
    database, workspace, identity, objects, _ = storage
    notes = NotesService(database)
    notes.create(identity, note_for(workspace, objects[0]), "index-note")
    with database.transaction() as connection:
        connection.execute("UPDATE notes_index SET anchor_state='unresolved' WHERE note_id='note_test'")
    with pytest.raises(ApiError) as damaged:
        notes.list(workspace)
    assert damaged.value.code == "CONTENT_HASH_MISMATCH"


def test_explicit_read_bookmark_cas_roundtrip_restart_and_no_inferred_evidence(http):
    client, headers, (database, workspace, _, objects, _) = http
    empty = client.get("/api/v1/learning/progress").json()
    assert empty == {"revision": 1, "readings": [], "route_steps": [], "bookmarks": []}
    assert count(database, "learning_progress") == count(database, "learning_events") == 0
    ref = reference(objects[1]).model_dump(mode="json")
    request = {"kind": "read_marked", "ref": ref, "expected_revision": 1, "value": True}
    first = client.post("/api/v1/learning/actions", json=request, headers=headers)
    assert first.status_code == 200 and first.json()["progress_revision"] == 2
    assert client.post("/api/v1/learning/actions", json=request, headers=headers).json() == first.json()
    assert client.post("/api/v1/learning/actions", json=request, headers={**headers, "Idempotency-Key": "stale-action"}).status_code == 412
    request.update(kind="bookmark_set", expected_revision=2)
    assert client.post("/api/v1/learning/actions", json=request, headers={**headers, "Idempotency-Key": "bookmark"}).json()["progress_revision"] == 3
    request.update(kind="read_marked", expected_revision=3, value=False)
    assert client.post("/api/v1/learning/actions", json=request, headers={**headers, "Idempotency-Key": "unread"}).status_code == 200
    result = client.get("/api/v1/learning/progress?course_id=course_notes").json()
    assert result["revision"] == 4 and result["readings"] == [{"ref": ref, "read": False, "read_at": None}]
    assert result["bookmarks"][0]["value"] is True and result["bookmarks"][0]["updated_at"].endswith("Z")
    assert result["route_steps"] == []
    restarted = Database(database.settings)
    restarted.initialize()
    assert LearningService(restarted).progress(workspace).model_dump(mode="json") == result
    assert count(database, "learning_events") == 3 and count(database, "evidence") == 0
    with database.connect() as connection:
        rows = connection.execute("SELECT kind,payload_json FROM learning_events ORDER BY occurred_at").fetchall()
        assert [row["kind"] for row in rows] == ["read_marked", "bookmark_set", "read_marked"]
        assert '"value":false' in rows[-1]["payload_json"]


@pytest.mark.parametrize("patch", [{"kind": "grade_finalized"}, {"origin": "native"}, {"actor": "server"}, {"value": "true"}, {"expected_revision": True}, {"score": 1}])
def test_action_public_contract_rejects_trusted_event_forgery_and_coercion(http, patch):
    client, headers, (database, _, _, objects, _) = http
    request = {"kind": "read_marked", "ref": reference(objects[0]).model_dump(mode="json"), "expected_revision": 1, "value": True, **patch}
    response = client.post("/api/v1/learning/actions", json=request, headers=headers)
    assert response.status_code == 422
    assert count(database, "learning_events") == 0


def test_action_transaction_failure_rolls_back_event_progress_and_receipt(storage):
    database, _, identity, objects, _ = storage
    with database.transaction() as connection:
        connection.execute("CREATE TRIGGER fail_progress BEFORE UPDATE ON learning_progress BEGIN SELECT RAISE(ABORT,'synthetic projection failure'); END")
    with pytest.raises(ApiError) as failure:
        LearningService(database).action(identity, LearningActionRequest(kind="read_marked", ref=reference(objects[0]), expected_revision=1, value=True), "failure")
    assert failure.value.code == "LEARNING_STORAGE_UNAVAILABLE"
    assert count(database, "learning_events") == count(database, "learning_progress") == count(database, "idempotency") == 0


def test_reading_projection_exact_block_aggregation_explicit_unmark_and_stale(storage):
    database, workspace, identity, objects, _ = storage
    learning = LearningService(database)
    block, lesson, _ = objects
    ref = reference(lesson)
    key = f"{ref.entity}:{ref.id}:{ref.revision}:{ref.sha256}"
    with database.transaction() as connection:
        assert reading_states(connection, workspace, [ref], {key: [reference(block)]}) == {key: "unread"}
    learning.action(identity, LearningActionRequest(kind="read_marked", ref=reference(block), expected_revision=1, value=True), "read-block")
    with database.transaction() as connection:
        assert reading_states(connection, workspace, [ref], {key: [reference(block)]}) == {key: "read"}
    learning.action(identity, LearningActionRequest(kind="read_marked", ref=ref, expected_revision=2, value=False), "unmark-lesson")
    with database.transaction() as connection:
        assert reading_states(connection, workspace, [ref], {key: [reference(block)]}) == {key: "unread"}
    new, bodies = tree(revision=2)
    ContentService(database).publish(workspace, new, bodies)
    newref = reference(new[1])
    newkey = f"{newref.entity}:{newref.id}:{newref.revision}:{newref.sha256}"
    with database.transaction() as connection:
        assert reading_states(connection, workspace, [newref], {newkey: [reference(new[0])]}) == {newkey: "stale"}
        assert reading_states(connection, workspace, [ref], {key: [reference(block)]}) == {key: "unread"}


def test_cross_workspace_note_and_learning_operations_are_isolated(storage):
    database, workspace, identity, objects, _ = storage
    other = "workspace_other_notes"
    with database.transaction() as connection:
        connection.execute("INSERT INTO workspace(id,title,created_at) VALUES(?,?,?)", (other, "合成隔离", utc_now()))
    other_identity = replace(identity, workspace_id=other)
    notes = NotesService(database)
    original = note_for(workspace, objects[0])
    notes.create(identity, original, "workspace-note")
    assert notes.list(other).items == []
    with pytest.raises(ApiError) as denied:
        notes.delete(other_identity, original.id, reference(original).sha256, "cross-delete")
    assert denied.value.status == 404
    for read in [ContentService(database).current, ContentService(database).revisions]:
        with pytest.raises(ApiError) as denied:
            read(other, original.id)
        assert denied.value.status == 404
    with pytest.raises(ApiError) as denied:
        LearningService(database).action(other_identity, LearningActionRequest(kind="bookmark_set", ref=reference(objects[0]), expected_revision=1, value=True), "cross-action")
    assert denied.value.status == 404
    assert LearningService(database).progress(other).revision == 1


@pytest.mark.parametrize("role", ["learner", "author"])
def test_independent_guard_blocks_all_six_routes_and_idempotent_replay(http, role):
    client, headers, (database, workspace, _, objects, _) = http
    note = note_for(workspace, objects[0])
    first = client.post("/api/v1/notes", json=note.model_dump(mode="json"), headers=headers)
    if role == "author":
        assert client.post("/api/v1/session/role", json={"role": "author"}, headers={**headers, "Idempotency-Key": "role"}).status_code == 200
    concept = dm.Concept(id="concept_notes_guard", revision=1, title="合成概念")
    question = dm.QuestionPublic(id="question_notes_guard", revision=1, kind="numeric", stem_markdown="合成题", concept_ids=[concept.id], skill="compute", exposure_group="synthetic_guard", input_instructions="数值")
    assessment = dm.AssessmentBlueprint(id="assessment_notes_guard", revision=1, title="合成测试", question_refs=[reference(question)], allowed_modes=["independent"])
    ContentService(database).publish(workspace, [concept, question, assessment], {})
    policy = dm.PolicySnapshot(mode="independent", tutor_scope="operation_help_only", allow_web=False, allow_materials=False)
    with database.transaction() as connection:
        connection.execute("INSERT INTO attempts(id,workspace_id,assessment_id,assessment_revision,mode,policy_json,question_refs_json,solution_refs_private_json,status,revision,created_at) VALUES(?,?,?,1,'independent',?,'[]','[]','active',1,?)",
                           ("attempt_notes_guard", workspace, assessment.id, canonical_bytes(policy).decode(), utc_now()))
    operations = [
        ("get", "/api/v1/notes", None), ("get", "/api/v1/learning/progress", None),
        ("get", "/api/v1/objects/note_test/current", None), ("get", "/api/v1/objects/note_test/revisions", None),
        ("post", "/api/v1/notes", note.model_dump(mode="json")),
        ("patch", "/api/v1/notes/note_test", {**note.model_dump(mode="json"), "revision": 2}),
        ("delete", "/api/v1/notes/note_test", None),
        ("post", "/api/v1/learning/actions", {"kind": "read_marked", "ref": reference(objects[0]).model_dump(mode="json"), "expected_revision": 2, "value": True}),
    ]
    for method, path, body in operations:
        response = client.request(method, path, json=body, headers={**headers, "If-Match": first.headers["etag"]})
        assert response.status_code == 409 and response.json()["error"]["code"] == "ASSESSMENT_ACTIVE"
        assert "合成笔记" not in response.text
    assert count(database, "learning_events") == 1


@pytest.mark.parametrize("path", ["/notes?limit=101", "/notes?limit=1&limit=2", "/notes?unknown=secret", "/learning/progress?course_id=a&course_id=b", "/learning/progress?unknown=secret"])
def test_query_contract_is_strict(http, path):
    client, _, _ = http
    response = client.get("/api/v1" + path)
    assert response.status_code == 422 and "secret" not in response.text


@pytest.mark.parametrize("etag,status", [(None, 428), ("*", 422), ('W/"' + "0" * 64 + '"', 422), ("0" * 64, 422), ('"' + "0" * 64 + '","' + "1" * 64 + '"', 422)])
def test_note_if_match_requires_one_strong_exact_hash(http, etag, status):
    client, headers, (_, workspace, _, objects, _) = http
    note = note_for(workspace, objects[0])
    assert client.post("/api/v1/notes", json=note.model_dump(mode="json"), headers=headers).status_code == 201
    delete_headers = {**headers, "Idempotency-Key": "delete-condition"}
    if etag is not None:
        delete_headers["If-Match"] = etag
    assert client.delete("/api/v1/notes/note_test", headers=delete_headers).status_code == status


def test_note_mutation_requires_session_csrf_idempotency_and_extra_fields_fail(http):
    client, headers, (database, workspace, _, objects, _) = http
    note = note_for(workspace, objects[0]).model_dump(mode="json")
    assert client.post("/api/v1/notes", json=note, headers={"Origin": database.settings.origin}).status_code == 403
    assert client.post("/api/v1/notes", json=note, headers={key: value for key, value in headers.items() if key != "Idempotency-Key"}).status_code == 422
    assert client.post("/api/v1/notes", json={**note, "trusted": True}, headers=headers).status_code == 422
    with TestClient(http_app(database), base_url=database.settings.origin) as anonymous:
        assert anonymous.get("/api/v1/notes").status_code == 401
    assert count(database, "learning_events") == 0


def test_main_application_exposes_note_history_and_automatic_stale_hook(storage):
    from services.api.app.main import create_app

    database, workspace, identity, objects, _ = storage
    old = note_for(workspace, objects[0])
    NotesService(database).create(identity, old, "main-note")
    newer, bodies = tree(revision=2)
    ContentService(database).publish(workspace, newer, bodies)
    with TestClient(create_app(database.settings), base_url=database.settings.origin) as client:
        bootstrap = client.post("/api/v1/session/bootstrap", json={"one_time_code": issue_bootstrap_code(database)}, headers={"Origin": database.settings.origin})
        assert bootstrap.status_code == 200
        note = client.get("/api/v1/notes").json()["items"][0]
        assert note["revision"] == 2 and note["anchor_state"] == "stale"
        current = client.get("/api/v1/objects/note_test/current")
        assert current.status_code == 200
        assert current.json()["sha256"] == metadata_sha256(dm.Note.model_validate(note))
        revisions = client.get("/api/v1/objects/note_test/revisions").json()["items"]
        assert [item["ref"]["revision"] for item in revisions] == [2, 1]
        assert revisions[-1]["ref"]["sha256"] == metadata_sha256(old)
        assert client.get("/api/v1/blocks/note_test?revision=1").status_code == 404
        assert client.get("/api/v1/learning/progress").json()["revision"] == 2


def test_publication_and_note_invalidation_roll_back_together(storage):
    database, workspace, identity, objects, _ = storage
    notes = NotesService(database)
    old = note_for(workspace, objects[0])
    notes.create(identity, old, "atomic-stale-note")
    before = {table: count(database, table) for table in ["revisions", "notes_index", "outbox", "learning_events"]}
    with database.transaction() as connection:
        connection.execute("CREATE TRIGGER fail_stale_note BEFORE INSERT ON notes_index WHEN NEW.note_revision=2 BEGIN SELECT RAISE(ABORT,'synthetic stale note failure'); END")
    newer, bodies = tree(revision=2)
    with pytest.raises(ApiError) as failure:
        ContentService(database).publish(workspace, newer, bodies)
    assert failure.value.code == "CONTENT_STORAGE_UNAVAILABLE"
    assert {table: count(database, table) for table in before} == before
    assert ContentService(database).current(workspace, objects[0].id) == reference(objects[0])
    assert notes.list(workspace).items == [old]


def test_multi_revision_publication_invalidates_existing_note_once_at_final_pointer(storage):
    database, workspace, identity, objects, _ = storage
    notes = NotesService(database)
    notes.create(identity, note_for(workspace, objects[0]), "multi-stale-note")
    second, bodies2 = tree(revision=2)
    third, bodies3 = tree(revision=3)
    with database.transaction() as connection:
        result = ContentService(database).publish_in_transaction(connection, workspace, [second[0], third[0]], {**bodies2, **bodies3}, import_history=True)
    assert result == [reference(second[0]), reference(third[0])]
    note = notes.list(workspace).items[0]
    assert note.revision == 2 and note.anchor_state == "stale"
    assert count(database, "learning_events") == 1
    assert ContentService(database).current(workspace, third[0].id) == reference(third[0])


def test_stale_state_cannot_be_cleared_without_explicit_new_anchor(storage):
    database, workspace, identity, objects, _ = storage
    notes = NotesService(database)
    notes.create(identity, note_for(workspace, objects[0]), "cannot-clear")
    newer, bodies = tree(revision=2)
    ContentService(database).publish(workspace, newer, bodies)
    stale = notes.list(workspace).items[0]
    candidate = dm.Note.model_validate({**stale.model_dump(), "revision": stale.revision + 1, "anchor_state": "exact"})
    with pytest.raises(ApiError) as failure:
        notes.update(identity, stale.id, candidate, reference(stale).sha256, "state-only-reset")
    assert failure.value.code == "ANCHOR_INVALID"


@pytest.mark.parametrize("entity", ["lesson", "course", "note"])
def test_new_anchor_requires_an_actual_block_body(storage, entity):
    database, workspace, identity, objects, _ = storage
    notes = NotesService(database)
    original = note_for(workspace, objects[0])
    original_ref = notes.create(identity, original, "body-note")
    target = original_ref if entity == "note" else reference(next(value for value in objects if value.entity == entity))
    candidate = dm.Note.model_validate({**original.model_dump(), "id": "note_target", "anchor": {**original.anchor.model_dump(), "ref": target.model_dump()}})
    with pytest.raises(ApiError) as failure:
        notes.create(identity, candidate, "invalid-body-note")
    assert failure.value.code == "ANCHOR_BODY_UNAVAILABLE"


def test_two_connections_compete_for_one_progress_revision(storage):
    database, workspace, identity, objects, _ = storage
    request = LearningActionRequest(kind="bookmark_set", ref=reference(objects[0]), expected_revision=1, value=True)

    def attempt(key):
        try:
            return LearningService(database).action(identity, request, key)
        except ApiError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, ["competing-a", "competing-b"]))
    assert sum(not isinstance(result, ApiError) for result in results) == 1
    assert [result.status for result in results if isinstance(result, ApiError)] == [412]
    assert LearningService(database).progress(workspace).revision == 2
    assert count(database, "learning_events") == count(database, "idempotency") == 1


def test_course_filter_retains_old_exact_refs_but_excludes_other_courses(storage):
    database, workspace, identity, objects, _ = storage
    learning = LearningService(database)
    learning.action(identity, LearningActionRequest(kind="read_marked", ref=reference(objects[0]), expected_revision=1, value=True), "first-course-read")
    other, bodies = tree("_other_course")
    ContentService(database).publish(workspace, other, bodies)
    learning.action(identity, LearningActionRequest(kind="read_marked", ref=reference(other[0]), expected_revision=2, value=True), "other-course-read")
    newer, bodies = tree(revision=2)
    ContentService(database).publish(workspace, newer, bodies)
    assert [item.ref for item in learning.progress(workspace, objects[-1].id).readings] == [reference(objects[0])]
    assert len(learning.progress(workspace).readings) == 2


def test_replay_survives_new_local_session_and_rejects_changed_payload(storage):
    database, _, identity, objects, _ = storage
    learning = LearningService(database)
    request = LearningActionRequest(kind="bookmark_set", ref=reference(objects[0]), expected_revision=1, value=True)
    result = learning.action(identity, request, "resume-action")
    assert LearningService(Database(database.settings)).action(replace(identity, id="session_restarted"), request, "resume-action") == result
    with pytest.raises(ApiError) as conflict:
        learning.action(identity, LearningActionRequest(**{**request.model_dump(), "value": False}), "resume-action")
    assert conflict.value.code == "IDEMPOTENCY_CONFLICT"
    assert count(database, "learning_events") == 1


def test_duplicate_if_match_and_delete_body_are_rejected(http):
    client, headers, (_, workspace, _, objects, _) = http
    note = note_for(workspace, objects[0])
    created = client.post("/api/v1/notes", json=note.model_dump(mode="json"), headers=headers)
    assert created.status_code == 201
    duplicate = [*headers.items(), ("If-Match", created.headers["etag"]), ("If-Match", created.headers["etag"])]
    assert client.delete("/api/v1/notes/note_test", headers=duplicate).status_code == 422
    response = client.request("DELETE", "/api/v1/notes/note_test", json={"purge": True}, headers={**headers, "If-Match": created.headers["etag"]})
    assert response.status_code == 422
    assert len(client.get("/api/v1/notes").json()["items"]) == 1


def test_note_anchoring_never_accepts_a_corrupted_blob(storage):
    database, workspace, identity, objects, _ = storage
    digest = objects[0].body_sha256
    (database.settings.data_dir / "blobs" / digest[:2] / digest).write_bytes(b"SYNTHETIC_CORRUPTED_BODY")
    with pytest.raises(ApiError):
        NotesService(database).create(identity, note_for(workspace, objects[0]), "bad-blob")
    assert count(database, "notes_index") == count(database, "learning_events") == 0
