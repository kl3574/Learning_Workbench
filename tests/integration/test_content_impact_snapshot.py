"""Read-only impact from durable Content publication events and exact revisions."""

import json

import pytest

from packages.contracts import domain_models as dm
from services.api.app.application.content import ContentService
from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.config import Settings
from tests.integration.test_content_repository import tree


@pytest.fixture
def published(tmp_path):
    database = Database(Settings(data_dir=tmp_path / "data"))
    workspace = database.initialize()
    service = ContentService(database)
    original, bodies = tree()
    service.publish(workspace, original, bodies)
    return database, workspace, service, original


def invalidation_id(database, old_id):
    with database.connect() as connection:
        row = connection.execute(
            "SELECT id FROM outbox WHERE event_type='content.dependencies_invalidated' "
            "AND json_extract(payload_json,'$.old_ref.id')=? ORDER BY rowid DESC LIMIT 1",
            (old_id,),
        ).fetchone()
    assert row is not None
    return row["id"]


def test_revision_qualified_dependencies_are_separate_from_conservative_ids(published):
    database, workspace, service, original = published
    old_block = original[1]
    new_block = old_block.model_copy(update={"revision": 2, "title": "修改后的合成块"})
    new_lesson = dm.Lesson(id="lesson_new", revision=1, title="新引用", objectives=[],
                           block_refs=[reference(new_block)])
    service.publish(workspace, [new_block, new_lesson], {})

    snapshot = service.impact_snapshot(workspace, invalidation_id(database, old_block.id))

    assert snapshot.old_ref == reference(old_block)
    assert snapshot.new_ref == reference(new_block)
    assert snapshot.reason == "content_revision_published"
    assert snapshot.affected_ids == ("block", "course", "lesson", "lesson_new")
    assert snapshot.exact_dependency_refs == (reference(original[2]), reference(original[3]))
    assert snapshot.conservative_only_ids == ("lesson_new",)
    assert snapshot.applicability == "pending_review"


def test_tampered_exact_dependency_cannot_downgrade_a_confirmed_edge_to_id_only(published):
    database, workspace, service, original = published
    old_block = original[1]
    new_block = old_block.model_copy(update={"revision": 2, "title": "修改后的合成块"})
    service.publish(workspace, [new_block], {})
    event_id = invalidation_id(database, old_block.id)
    with database.transaction() as connection:
        connection.execute(
            "UPDATE object_dependencies SET target_revision=2 "
            "WHERE owner_id='lesson' AND owner_revision=1 AND target_id='block' AND relation='reference'"
        )

    with pytest.raises(ApiError) as caught:
        service.impact_snapshot(workspace, event_id)
    assert caught.value.code == "CONTENT_HASH_MISMATCH"


def test_cross_workspace_dependency_row_is_integrity_failure_not_a_foreign_read(published):
    database, workspace, service, original = published
    old_block = original[1]
    new_block = old_block.model_copy(update={"revision": 2, "title": "修改后的合成块"})
    service.publish(workspace, [new_block], {})
    event_id = invalidation_id(database, old_block.id)
    with database.transaction() as connection:
        connection.execute("INSERT INTO workspace(id,title,created_at) VALUES('workspace_other','合成工作区','2026-09-14T00:00:00Z')")
    foreign = dm.Concept(id="concept_foreign", revision=1, title="他工作区概念")
    service.publish("workspace_other", [foreign], {})
    with database.transaction() as connection:
        connection.execute(
            "UPDATE object_dependencies SET target_id=? "
            "WHERE owner_id='lesson' AND owner_revision=1 AND target_id='concept' AND relation='concept'",
            (foreign.id,),
        )

    with pytest.raises(ApiError) as caught:
        service.impact_snapshot(workspace, event_id)
    assert caught.value.code == "CONTENT_HASH_MISMATCH"


def test_historical_event_uses_historical_edges_not_later_added_owners(published):
    database, workspace, service, original = published
    old_block = original[1]
    second_lesson = original[2].model_copy(update={"revision": 2, "title": "仍引用旧块"})
    service.publish(workspace, [second_lesson], {})
    new_block = old_block.model_copy(update={"revision": 2, "title": "修改后的合成块"})
    service.publish(workspace, [new_block], {})
    event_id = invalidation_id(database, old_block.id)
    later_lesson = dm.Lesson(id="lesson_later", revision=1, title="晚于事件的旧版引用", objectives=[],
                             block_refs=[reference(old_block)])
    service.publish(workspace, [later_lesson], {})

    snapshot = service.impact_snapshot(workspace, event_id)
    assert snapshot.affected_ids == ("block", "course", "lesson")
    assert snapshot.exact_dependency_refs == (reference(original[2]), reference(second_lesson), reference(original[3]))
    assert "lesson_later" not in snapshot.affected_ids


def test_shared_concept_does_not_invent_question_dependency_on_edited_block(tmp_path):
    from tests.assessment_fixtures import assessment_fixture

    database = Database(Settings(data_dir=tmp_path / "data"))
    workspace = database.initialize()
    fixture = assessment_fixture("impactsibling")
    service = ContentService(database)
    service.publish(workspace, fixture.public_objects, fixture.bodies)
    changed = fixture.block.model_copy(update={"revision": 2, "title": "新版合成例题"})
    service.publish(workspace, [changed], {})

    snapshot = service.impact_snapshot(workspace, invalidation_id(database, fixture.block.id))
    assert fixture.questions[0].id not in snapshot.affected_ids
    assert all(ref.entity != "question" for ref in snapshot.exact_dependency_refs)
    assert snapshot.applicability == "pending_review"


@pytest.mark.parametrize("damage", ["old_hash", "new_hash", "affected_ids", "duplicate_key", "missing_pair"])
def test_event_integrity_fails_closed(published, damage):
    database, workspace, service, original = published
    new_block = original[1].model_copy(update={"revision": 2, "title": "修改后的合成块"})
    service.publish(workspace, [new_block], {})
    event_id = invalidation_id(database, new_block.id)
    with database.transaction() as connection:
        row = connection.execute("SELECT payload_json FROM outbox WHERE id=?", (event_id,)).fetchone()
        payload = json.loads(row["payload_json"])
        if damage in {"old_hash", "new_hash"}:
            payload["old_ref" if damage == "old_hash" else "new_ref"]["sha256"] = "0" * 64
        elif damage == "affected_ids":
            payload["affected_ids"] = [new_block.id]
        elif damage == "duplicate_key":
            connection.execute("UPDATE outbox SET payload_json=? WHERE id=?",
                               (row["payload_json"][:-1] + ',"reason":"content_revision_published"}', event_id))
        else:
            connection.execute("DELETE FROM outbox WHERE event_type='content.published' AND payload_json=?",
                               (row["payload_json"],))
        if damage in {"old_hash", "new_hash", "affected_ids"}:
            from packages.contracts.canonical import canonical_bytes
            connection.execute("UPDATE outbox SET payload_json=? WHERE id=?", (canonical_bytes(payload).decode(), event_id))

    with pytest.raises(ApiError) as caught:
        service.impact_snapshot(workspace, event_id)
    assert caught.value.code == "CONTENT_HASH_MISMATCH"


def test_event_is_workspace_scoped_and_read_does_not_write(published):
    database, workspace, service, original = published
    new_block = original[1].model_copy(update={"revision": 2, "title": "修改后的合成块"})
    service.publish(workspace, [new_block], {})
    event_id = invalidation_id(database, new_block.id)
    with database.transaction() as connection:
        connection.execute("INSERT INTO workspace(id,title,created_at) VALUES('workspace_other','合成工作区','2026-09-14T00:00:00Z')")
    with pytest.raises(ApiError) as caught:
        service.impact_snapshot("workspace_other", event_id)
    assert caught.value.status == 404
    with pytest.raises(ApiError) as caught:
        service.impact_snapshot(workspace, "outbox_missing")
    assert caught.value.status == 404

    with database.connect() as connection:
        before = tuple(connection.iterdump())
    first = service.impact_snapshot(workspace, event_id)
    second = service.impact_snapshot(workspace, event_id)
    with database.connect() as connection:
        after = tuple(connection.iterdump())
    assert first == second and before == after


def test_impact_read_preserves_real_attempt_private_pins_and_old_grade(tmp_path):
    from services.api.app.application.grading import GradingWorker
    from tests.integration.test_assessment_attempts import storage as assessment_storage, start

    storage = assessment_storage.__wrapped__(tmp_path)
    database, identity, fixture, assessment = storage
    attempt = start(storage)
    assessment.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=attempt.revision), "impact-submit")
    assert GradingWorker(database).run_once()
    service = ContentService(database)
    changed = fixture.concept.model_copy(update={"revision": 2, "title": "修改概念条件后的合成版本"})
    service.publish(identity.workspace_id, [changed], {})
    event_id = invalidation_id(database, fixture.concept.id)

    immutable_tables = ("attempts", "solutions", "grades", "evidence", "learning_events", "learning_evidence_refs")
    with database.connect() as connection:
        before = {name: tuple(tuple(row) for row in connection.execute(f"SELECT * FROM {name} ORDER BY rowid"))
                  for name in immutable_tables}
        assignment = connection.execute("SELECT question_refs_json,solution_refs_private_json FROM attempts WHERE id=?",
                                        (attempt.id,)).fetchone()
    snapshot = service.impact_snapshot(identity.workspace_id, event_id)
    with database.connect() as connection:
        after = {name: tuple(tuple(row) for row in connection.execute(f"SELECT * FROM {name} ORDER BY rowid"))
                 for name in immutable_tables}
    assert before == after
    assert reference(fixture.questions[0]) in snapshot.exact_dependency_refs
    assert snapshot.applicability == "pending_review"
    assert reference(fixture.questions[0]).model_dump(mode="json") in json.loads(assignment["question_refs_json"])


def test_existing_note_stale_revision_is_not_rewritten_by_impact_read(tmp_path):
    from services.api.app.application.notes import NotesService
    from tests.integration.test_notes_learning import note_for, storage as notes_storage, tree as notes_tree

    database, workspace, identity, objects, _ = notes_storage.__wrapped__(tmp_path)
    original_note = note_for(workspace, objects[0])
    NotesService(database).create(identity, original_note, "impact-note")
    changed, bodies = notes_tree(revision=2)
    ContentService(database).publish(workspace, [changed[0]], bodies)
    event_id = invalidation_id(database, objects[0].id)
    service = ContentService(database)
    current = NotesService(database).list(workspace).items
    assert len(current) == 1 and current[0].anchor_state == "stale" and current[0].revision == 2

    snapshot = service.impact_snapshot(workspace, event_id)

    assert reference(original_note) in snapshot.exact_dependency_refs
    assert NotesService(database).list(workspace).items == current
