"""Read-only impact from durable Content publication events and exact revisions."""

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Event

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
    assert snapshot.evidence_version == "owner_frozen_v1"


def test_pure_concept_id_edge_stays_conservative_after_revision_row_tamper(tmp_path):
    from tests.assessment_fixtures import assessment_fixture

    database = Database(Settings(data_dir=tmp_path / "data"))
    workspace = database.initialize()
    fixture = assessment_fixture("impactconcept")
    service = ContentService(database)
    service.publish(workspace, fixture.public_objects, fixture.bodies)
    changed = fixture.concept.model_copy(update={"revision": 2, "title": "修改概念条件"})
    service.publish(workspace, [changed], {})
    event_id = invalidation_id(database, fixture.concept.id)

    before = service.impact_snapshot(workspace, event_id)
    assert fixture.questions[0].id in before.conservative_only_ids
    assert all(ref.entity != "question" for ref in before.exact_dependency_refs)
    with database.transaction() as connection:
        connection.execute(
            "UPDATE object_dependencies SET target_revision=2 WHERE owner_id=? AND owner_revision=1 "
            "AND target_id=? AND relation='concept'",
            (fixture.questions[0].id, fixture.concept.id),
        )
    assert service.impact_snapshot(workspace, event_id) == before


def test_wall_clock_collision_does_not_rewrite_frozen_historical_impact(published, monkeypatch):
    from services.api.app.infrastructure import content_repository

    database, workspace, service, original = published
    monkeypatch.setattr(content_repository, "utc_now", lambda: "2026-09-28T07:00:00.000000Z")
    old_block = original[1]
    new_block = old_block.model_copy(update={"revision": 2, "title": "同微秒新修订"})
    service.publish(workspace, [new_block], {})
    event_id = invalidation_id(database, old_block.id)
    before = service.impact_snapshot(workspace, event_id)
    later = dm.Lesson(id="lesson_same_microsecond", revision=1, title="同微秒稍后引用旧块", objectives=[],
                      block_refs=[reference(old_block)])
    service.publish(workspace, [later], {})

    assert service.impact_snapshot(workspace, event_id) == before
    assert later.id not in before.affected_ids


def test_impact_read_holds_attempt_writer_gate_and_is_sqlite_query_only(tmp_path, monkeypatch):
    from services.api.app.application import content as content_module
    from tests.integration.test_assessment_attempts import storage as assessment_storage, start

    storage = assessment_storage.__wrapped__(tmp_path)
    database, identity, fixture, _ = storage
    service = ContentService(database)
    changed = fixture.concept.model_copy(update={"revision": 2, "title": "合成变更"})
    service.publish(identity.workspace_id, [changed], {})
    event_id = invalidation_id(database, fixture.concept.id)
    entered, release = Event(), Event()
    original = content_module.impact_snapshot

    def paused(connection, workspace_id, identifier):
        assert connection.execute("PRAGMA query_only").fetchone()[0] == 1
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("INSERT INTO outbox(id,event_type,payload_json) VALUES('outbox_forbidden','test','{}')")
        entered.set()
        assert release.wait(5)
        return original(connection, workspace_id, identifier)

    monkeypatch.setattr(content_module, "impact_snapshot", paused)
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(service.impact_snapshot, identity.workspace_id, event_id)
        try:
            assert entered.wait(5)
            probe = sqlite3.connect(database.path, timeout=0, isolation_level=None)
            try:
                with pytest.raises(sqlite3.OperationalError, match="locked"):
                    probe.execute("BEGIN IMMEDIATE")
            finally:
                probe.rollback()
                probe.close()
        finally:
            release.set()
        assert pending.result(timeout=5).evidence_version == "owner_frozen_v1"

    attempt = start(storage, key="impact-after-read")
    assert attempt.status == "active"
    with pytest.raises(ApiError) as caught:
        service.impact_snapshot(identity.workspace_id, event_id)
    assert caught.value.code == "ASSESSMENT_ACTIVE"


def test_forward_migration_leaves_prior_outbox_event_explicitly_unverified(published):
    database, workspace, service, original = published
    changed = original[1].model_copy(update={"revision": 2, "title": "旧版事件模拟"})
    service.publish(workspace, [changed], {})
    event_id = invalidation_id(database, changed.id)
    with database.transaction() as connection:
        # Controlled 0019-era fixture: retain the real outbox/revisions, remove
        # only 0021-owned tables and its migration receipt before upgrade.
        connection.execute("DROP TABLE content_impact_snapshots")
        connection.execute("DROP TABLE content_impact_legacy_events")
        connection.execute("DELETE FROM schema_migrations WHERE version='0021_impact_event_snapshots'")
    assert database.initialize() == workspace

    snapshot = service.impact_snapshot(workspace, event_id)
    assert snapshot.evidence_version == "legacy_unverified"
    assert snapshot.exact_dependency_refs == ()
    assert snapshot.conservative_only_ids == ("course", "lesson")
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM content_impact_snapshots").fetchone()[0] == 0
        assert connection.execute("SELECT payload_json FROM content_impact_legacy_events WHERE event_id=?",
                                  (event_id,)).fetchone() is not None


def test_frozen_impact_evidence_is_insert_only_and_bound_to_original_event(published):
    database, workspace, service, original = published
    changed = original[1].model_copy(update={"revision": 2, "title": "不可变事件"})
    service.publish(workspace, [changed], {})
    event_id = invalidation_id(database, changed.id)
    with database.transaction() as connection:
        row = connection.execute("SELECT * FROM content_impact_snapshots WHERE event_id=?", (event_id,)).fetchone()
        assert row is not None and row["workspace_id"] == workspace
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE content_impact_snapshots SET snapshot_sha256=? WHERE event_id=?",
                               ("0" * 64, event_id))
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("DELETE FROM content_impact_snapshots WHERE event_id=?", (event_id,))
    assert service.impact_snapshot(workspace, event_id).evidence_version == "owner_frozen_v1"


def test_missing_new_snapshot_cannot_be_disguised_as_legacy(published):
    database, workspace, service, original = published
    changed = original[1].model_copy(update={"revision": 2, "title": "新事件不能降级"})
    service.publish(workspace, [changed], {})
    event_id = invalidation_id(database, changed.id)
    with database.transaction() as connection:
        assert connection.execute("SELECT 1 FROM content_impact_legacy_events WHERE event_id=?",
                                  (event_id,)).fetchone() is None
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("INSERT INTO content_impact_legacy_events(event_id,payload_json) "
                               "SELECT id,payload_json FROM outbox WHERE id=?", (event_id,))
        # Controlled corruption bypasses normal immutable trigger; read must
        # reject the absent new snapshot instead of manufacturing legacy status.
        connection.execute("DROP TRIGGER content_impact_snapshot_no_delete")
        connection.execute("DELETE FROM content_impact_snapshots WHERE event_id=?", (event_id,))

    with pytest.raises(ApiError) as caught:
        service.impact_snapshot(workspace, event_id)
    assert caught.value.code == "CONTENT_HASH_MISMATCH"


@pytest.mark.parametrize("damage", ["snapshot_sha", "workspace", "event_binding", "missing_exact_revision"])
def test_frozen_impact_read_rejects_snapshot_integrity_tamper(published, damage):
    database, workspace, service, original = published
    changed = original[1].model_copy(update={"revision": 2, "title": "篡改冻结证据"})
    service.publish(workspace, [changed], {})
    event_id = invalidation_id(database, changed.id)
    with database.transaction() as connection:
        # Deliberate storage bypass to exercise readback verification. Normal
        # application writes are stopped by the immutable migration trigger.
        connection.execute("DROP TRIGGER content_impact_snapshot_no_update")
        if damage == "snapshot_sha":
            connection.execute("UPDATE content_impact_snapshots SET snapshot_sha256=? WHERE event_id=?",
                               ("0" * 64, event_id))
        elif damage == "workspace":
            connection.execute(
                "INSERT INTO workspace(id,title,created_at) VALUES('workspace_other','合成工作区','2026-09-14T00:00:00Z')"
            )
            connection.execute("UPDATE content_impact_snapshots SET workspace_id='workspace_other' WHERE event_id=?",
                               (event_id,))
        else:
            row = connection.execute("SELECT snapshot_json FROM content_impact_snapshots WHERE event_id=?",
                                     (event_id,)).fetchone()
            payload = json.loads(row["snapshot_json"])
            if damage == "event_binding":
                payload["event_payload_sha256"] = "0" * 64
            else:
                payload["exact_dependency_refs"][0]["revision"] = 999
            from packages.contracts.canonical import canonical_bytes, sha256_bytes
            frozen = canonical_bytes(payload)
            connection.execute("UPDATE content_impact_snapshots SET snapshot_json=?,snapshot_sha256=? WHERE event_id=?",
                               (frozen.decode(), sha256_bytes(frozen), event_id))

    with pytest.raises(ApiError) as caught:
        service.impact_snapshot(workspace, event_id)
    assert caught.value.code == "CONTENT_HASH_MISMATCH"


def test_frozen_impact_insert_failure_rolls_back_content_pointer_and_outbox(published):
    database, workspace, service, original = published
    changed = original[1].model_copy(update={"revision": 2, "title": "必须原子发布"})
    with database.connect() as connection:
        before = tuple(connection.iterdump())
    with database.transaction() as connection:
        connection.execute(
            "CREATE TRIGGER fail_impact_evidence BEFORE INSERT ON content_impact_snapshots "
            "BEGIN SELECT RAISE(ABORT,'synthetic impact storage failure'); END"
        )
    with pytest.raises(ApiError) as caught:
        service.publish(workspace, [changed], {})
    assert caught.value.code == "CONTENT_STORAGE_UNAVAILABLE"
    assert service.current(workspace, changed.id) == reference(original[1])
    with database.connect() as connection:
        connection.execute("DROP TRIGGER fail_impact_evidence")
        after = tuple(connection.iterdump())
    assert before == after


def test_mutated_current_edge_does_not_rewrite_owner_frozen_exact_ref(published):
    database, workspace, service, original = published
    old_block = original[1]
    new_block = old_block.model_copy(update={"revision": 2, "title": "修改后的合成块"})
    service.publish(workspace, [new_block], {})
    event_id = invalidation_id(database, old_block.id)
    frozen = service.impact_snapshot(workspace, event_id)
    with database.transaction() as connection:
        connection.execute(
            "UPDATE object_dependencies SET target_revision=2 "
            "WHERE owner_id='lesson' AND owner_revision=1 AND target_id='block' AND relation='reference'"
        )

    # The old live-edge read would reject this modified row. The publication
    # transaction now freezes the explicit ContentRef closure; this read
    # validates that frozen evidence, not the current dependency table.
    assert service.impact_snapshot(workspace, event_id) == frozen
    assert reference(original[2]) in frozen.exact_dependency_refs


def test_cross_workspace_edge_mutation_does_not_rewrite_frozen_impact(published):
    database, workspace, service, original = published
    old_block = original[1]
    new_block = old_block.model_copy(update={"revision": 2, "title": "修改后的合成块"})
    service.publish(workspace, [new_block], {})
    event_id = invalidation_id(database, old_block.id)
    frozen = service.impact_snapshot(workspace, event_id)
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

    # A later foreign target in the mutable edge table is outside the frozen
    # event proof and must not leak a foreign ref into historical impact.
    assert service.impact_snapshot(workspace, event_id) == frozen


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


@pytest.mark.parametrize("damage", ["old_hash", "new_hash", "missing_old_revision", "affected_ids",
                                    "duplicate_key", "missing_pair"])
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
        elif damage == "missing_old_revision":
            payload["old_ref"]["revision"] = 999
        elif damage == "affected_ids":
            payload["affected_ids"] = [new_block.id]
        elif damage == "duplicate_key":
            connection.execute("UPDATE outbox SET payload_json=? WHERE id=?",
                               (row["payload_json"][:-1] + ',"reason":"content_revision_published"}', event_id))
        else:
            connection.execute("DELETE FROM outbox WHERE event_type='content.published' AND payload_json=?",
                               (row["payload_json"],))
        if damage in {"old_hash", "new_hash", "missing_old_revision", "affected_ids"}:
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
    assert fixture.questions[0].id in snapshot.conservative_only_ids
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
