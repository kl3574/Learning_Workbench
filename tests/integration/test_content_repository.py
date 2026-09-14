"""Real SQLite content storage and policy invariants, using only synthetic bodies."""

import json
import sqlite3

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes
from services.api.app.application.content import ContentService
from services.api.app.application.errors import ApiError
from services.api.app.config import Settings
from services.api.app.database import Database


def ref(value):
    return dm.ContentRef(entity=value.entity, id=value.id, revision=value.revision, sha256=metadata_sha256(value))


def tree(revision=1, suffix="", concept=True):
    data = f"# 合成教材 {revision} 🧠\n\n$x^2$\n".encode()
    c = dm.Concept(id=f"concept{suffix}", revision=revision, title="测试概念")
    block = dm.ContentBlock(id=f"block{suffix}", revision=revision, kind="worked_example", title="测试块",
                            body_path=f"content/block{suffix}.md", body_sha256=sha256_bytes(data),
                            concepts=[c.id] if concept else [])
    lesson = dm.Lesson(id=f"lesson{suffix}", revision=revision, title="测试节", objectives=[],
                       prerequisite_ids=[c.id] if concept else [], block_refs=[ref(block)])
    course = dm.Course(id=f"course{suffix}", revision=revision, title=f"测试课程{suffix}", audience="合成验证",
                       lesson_refs=[ref(lesson)], concept_refs=[ref(c)] if concept else [])
    return ([c, block, lesson, course] if concept else [block, lesson, course]), {block.body_path: data}


@pytest.fixture
def store(tmp_path):
    database = Database(Settings(data_dir=tmp_path / "data"))
    workspace = database.initialize()
    return database, ContentService(database), workspace


def count(database, table):
    assert table in {"objects", "revisions", "outbox", "content_blobs", "block_bodies", "object_dependencies"}
    with database.connect() as connection:
        return connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def second_workspace(database):
    with database.transaction() as connection:
        connection.execute("INSERT INTO workspace(id,title,created_at) VALUES('workspace_other','合成工作区','2026-09-14T00:00:00Z')")
    return "workspace_other"


def test_exact_revisions_immutable_and_durable_with_shared_logical_body_path(store):
    database, service, workspace = store
    old, old_bodies = tree()
    assert service.publish(workspace, old, old_bodies) == [ref(value) for value in old]
    new, new_bodies = tree(2)
    service.publish(workspace, new, new_bodies)
    restarted = ContentService(Database(database.settings))
    for value in old:
        assert restarted.read(workspace, value.entity, value.id, 1) == value
    for value in new:
        assert restarted.current(workspace, value.id) == ref(value)
    assert restarted.body(workspace, "block", 1) == (old_bodies["content/block.md"], old[1].body_sha256)
    assert restarted.body(workspace, "block", 2)[0] == new_bodies["content/block.md"]
    with database.transaction() as connection:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute("UPDATE revisions SET metadata_json='{}' WHERE object_id='block' AND revision=1")
    assert count(database, "revisions") == 8
    with database.connect() as connection:
        events = connection.execute("SELECT * FROM outbox WHERE event_type='content.dependencies_invalidated'").fetchall()
        assert len(events) == 4
        block = next(json.loads(row["payload_json"]) for row in events if json.loads(row["payload_json"])["old_ref"]["id"] == "block")
        assert {"block", "lesson", "course"} <= set(block["affected_ids"])
        assert block["old_ref"] == ref(old[1]).model_dump(mode="json")
        assert block["new_ref"] == ref(new[1]).model_dump(mode="json")
        assert all(row["delivered_at"] is None for row in events)


def test_new_revision_can_reference_existing_exact_revisions_and_pure_ids(store):
    database, service, workspace = store
    values, bodies = tree()
    service.publish(workspace, values, bodies)
    lesson = values[2].model_copy(update={"revision": 2})
    service.publish(workspace, [lesson], {})
    assert service.read(workspace, "lesson", "lesson", 2) == lesson
    with database.connect() as connection:
        targets = connection.execute("SELECT target_id,target_revision,relation FROM object_dependencies WHERE owner_id='lesson' AND owner_revision=2").fetchall()
        assert {(row[0], row[1], row[2]) for row in targets} == {("block", 1, "reference"), ("concept", 1, "concept")}
    block = values[1].model_copy(update={"revision": 2})
    service.publish(workspace, [block], {})
    assert service.body(workspace, "block", 2) == service.body(workspace, "block", 1)
    assert count(database, "content_blobs") == 1


@pytest.mark.parametrize("method", ["read", "body", "current", "courses", "revisions"])
def test_workspace_isolation(store, method):
    database, service, workspace = store
    values, bodies = tree()
    service.publish(workspace, values, bodies)
    other = second_workspace(database)
    if method == "courses":
        assert service.courses(other).items == []
        return
    arguments = {"read": ("block", "block", 1), "body": ("block", 1), "current": ("block",), "revisions": ("block",)}
    with pytest.raises(ApiError) as result:
        getattr(service, method)(other, *arguments[method])
    assert result.value.status == 404


def test_cross_workspace_refs_pure_concepts_and_body_hash_reuse_fail_closed(store):
    database, service, workspace = store
    values, bodies = tree()
    service.publish(workspace, values, bodies)
    other = second_workspace(database)
    for candidate in [
        dm.Lesson(id="foreign_lesson", revision=1, title="不可跨工作区", objectives=[], block_refs=[ref(values[1])]),
        values[1].model_copy(update={"id": "foreign_block"}),
        values[1].model_copy(update={"id": "body_only", "concepts": []}),
    ]:
        with pytest.raises(ApiError):
            service.publish(other, [candidate], {})
    assert count(database, "objects") == 4


@pytest.mark.parametrize("fault", ["missing", "hash", "entity", "pure_id", "sections"])
def test_invalid_reference_and_structural_candidates_never_commit(store, fault):
    database, service, workspace = store
    values, bodies = tree()
    if fault == "missing":
        values = values[1:]
    elif fault == "hash":
        values[2] = values[2].model_copy(update={"block_refs": [ref(values[1]).model_copy(update={"sha256": "0" * 64})]})
    elif fault == "entity":
        values[2] = values[2].model_copy(update={"block_refs": [ref(values[0])]})
    elif fault == "pure_id":
        values[1] = values[1].model_copy(update={"concepts": ["concept_missing"]})
    else:
        values[-1] = values[-1].model_copy(update={"sections": [dm.CourseSection(id="section", title="错误", lesson_ids=["absent"])]})
    with pytest.raises(ApiError):
        service.publish(workspace, values, bodies)
    assert count(database, "objects") == count(database, "revisions") == count(database, "outbox") == 0


def test_concept_cycle_and_route_cycle_rejected_and_valid_projections_persist(store):
    database, service, workspace = store
    a = dm.Concept(id="concept_a", revision=1, title="A", prerequisite_ids=["concept_b"])
    b = dm.Concept(id="concept_b", revision=1, title="B", prerequisite_ids=["concept_a"])
    with pytest.raises(ApiError):
        service.publish(workspace, [a, b], {})
    assert count(database, "objects") == 0
    b = b.model_copy(update={"prerequisite_ids": []})
    service.publish(workspace, [a, b], {})
    values, bodies = tree(concept=False)
    values[-1] = values[-1].model_copy(update={"concept_refs": [ref(a), ref(b)]})
    service.publish(workspace, values, bodies)
    route = dm.Route(id="route", revision=1, title="路线", goal="合成验证", steps=[
        dm.RouteStep(id="first", title="前置", target=ref(values[0]), completion_rule="read"),
        dm.RouteStep(id="second", title="后续", target=ref(values[1]), completion_rule="read", requires_steps=["first"]),
    ])
    service.publish(workspace, [route], {})
    with database.connect() as connection:
        assert tuple(connection.execute("SELECT prerequisite_id,dependent_id FROM concept_edges").fetchone()) == ("concept_b", "concept_a")
        assert [tuple(row) for row in connection.execute("SELECT step_id,position FROM route_steps ORDER BY position")] == [("first", 0), ("second", 1)]
    cyclic = route.model_copy(update={"revision": 2, "steps": [route.steps[0].model_copy(update={"requires_steps": ["second"]}), route.steps[1]]})
    with pytest.raises(ApiError):
        service.publish(workspace, [cyclic], {})
    assert service.current(workspace, "route").revision == 1


def test_db_failure_after_files_keeps_only_unreferenced_safe_blob(store):
    database, service, workspace = store
    with database.transaction() as connection:
        connection.execute("CREATE TRIGGER injected_failure BEFORE INSERT ON outbox BEGIN SELECT RAISE(ABORT,'synthetic private failure'); END")
    values, bodies = tree()
    with pytest.raises(ApiError) as result:
        service.publish(workspace, values, bodies)
    assert result.value.status == 503 and "synthetic" not in result.value.message
    for table in ["objects", "revisions", "outbox", "content_blobs", "block_bodies", "object_dependencies"]:
        assert count(database, table) == 0
    digest = values[1].body_sha256
    assert (database.settings.data_dir / "blobs" / digest[:2] / digest).read_bytes() == bodies["content/block.md"]


def test_failed_new_revision_preserves_previous_pointer_and_dependencies(store):
    database, service, workspace = store
    old, bodies = tree()
    service.publish(workspace, old, bodies)
    old_counts = {table: count(database, table) for table in ["objects", "revisions", "outbox", "object_dependencies"]}
    with database.transaction() as connection:
        connection.execute("CREATE TRIGGER injected_failure BEFORE INSERT ON outbox WHEN NEW.event_type='content.dependencies_invalidated' BEGIN SELECT RAISE(ABORT,'injected'); END")
    new, bodies = tree(2)
    with pytest.raises(ApiError):
        service.publish(workspace, new, bodies)
    assert service.current(workspace, "block") == ref(old[1])
    assert {table: count(database, table) for table in old_counts} == old_counts


def test_file_failure_has_no_sql_references(store, monkeypatch):
    database, service, workspace = store
    def fail(*_args, **_kwargs):
        raise ApiError(503, "BLOB_STORAGE_UNAVAILABLE", "合成写入失败。")
    monkeypatch.setattr(service.blobs, "write", fail)
    values, bodies = tree()
    with pytest.raises(ApiError):
        service.publish(workspace, values, bodies)
    assert count(database, "objects") == count(database, "content_blobs") == 0


@pytest.mark.parametrize("problem", ["wrong_hash", "crlf", "utf8", "too_long", "private", "extra"])
def test_body_validation_rejects_invalid_bytes_and_private_namespace(store, problem):
    database, service, workspace = store
    values, bodies = tree(concept=False)
    block = values[0]
    if problem in {"wrong_hash", "crlf", "utf8", "too_long"}:
        body = {"wrong_hash": b"wrong", "crlf": b"a\r\nb", "utf8": b"\xff", "too_long": b"a" * 400001}[problem]
        bodies[block.body_path] = body
        if problem != "wrong_hash":
            block = block.model_copy(update={"body_sha256": sha256_bytes(body)})
    elif problem == "private":
        block = block.model_copy(update={"body_path": "private/secret.md"})
        bodies = {block.body_path: next(iter(bodies.values()))}
    else:
        bodies["private/secret.md"] = b"private synthetic data"
    with pytest.raises(ApiError):
        service.publish(workspace, [block], bodies)
    assert count(database, "objects") == count(database, "block_bodies") == 0


def test_corrupt_body_and_blob_metadata_fail_closed(store):
    database, service, workspace = store
    values, bodies = tree()
    service.publish(workspace, values, bodies)
    digest = values[1].body_sha256
    path = database.settings.data_dir / "blobs" / digest[:2] / digest
    path.write_bytes(b"synthetic corruption")
    with pytest.raises(ApiError) as result:
        service.body(workspace, "block", 1)
    assert result.value.code == "CONTENT_HASH_MISMATCH" and "corruption" not in result.value.message
    path.write_bytes(bodies[values[1].body_path])
    with database.transaction() as connection:
        connection.execute("UPDATE content_blobs SET relative_path='private/secrets' WHERE sha256=?", (digest,))
    with pytest.raises(ApiError):
        service.body(workspace, "block", 1)


def test_malformed_or_secret_bearing_public_metadata_is_never_returned(store):
    database, service, workspace = store
    values, bodies = tree()
    service.publish(workspace, values, bodies)
    metadata = values[1].model_dump(mode="json")
    metadata["answer"] = "private synthetic answer"
    with database.transaction() as connection:
        connection.execute("DROP TRIGGER revisions_no_update")
        connection.execute("UPDATE revisions SET metadata_json=?,sha256=? WHERE object_id='block'", (canonical_bytes(metadata).decode(), sha256_bytes(canonical_bytes(metadata))))
    with pytest.raises(ApiError) as result:
        service.read(workspace, "block", "block", 1)
    assert result.value.code == "CONTENT_HASH_MISMATCH" and "answer" not in result.value.message


def test_private_solution_is_not_accepted_or_loaded_from_public_objects(store):
    database, service, workspace = store
    concept = dm.Concept(id="concept", revision=1, title="合成概念")
    question = dm.QuestionPublic(id="question", revision=1, kind="numeric", stem_markdown="合成题干", concept_ids=[concept.id], skill="compute", exposure_group="group", input_instructions="数字")
    service.publish(workspace, [concept, question], {})
    solution = dm.SolutionPrivate(id="solution", revision=1, question_ref=ref(question), grading_kind="numeric_tolerance", accepted_answers=["private synthetic answer"], solution_markdown="私有解答", review_status="approved")
    with pytest.raises(ApiError):
        service.publish(workspace, [solution], {})
    with database.transaction() as connection:
        connection.execute("INSERT INTO solutions(question_id,question_revision,solution_revision,private_json,sha256,review_status) VALUES(?,1,1,?,?,'approved')", (question.id, canonical_bytes(solution).decode(), metadata_sha256(solution)))
    assert "private" not in service.read(workspace, "question", question.id, 1).model_dump_json()
    with pytest.raises(ApiError):
        service.read(workspace, "solution", question.id, 1)


@pytest.mark.parametrize("method", ["read", "body", "current", "courses", "revisions", "publish"])
def test_active_independent_attempt_blocks_all_material_ports(store, method):
    database, service, workspace = store
    values, bodies = tree()
    service.publish(workspace, values, bodies)
    question = dm.QuestionPublic(id="question", revision=1, kind="numeric", stem_markdown="合成题", concept_ids=["concept"], skill="compute", exposure_group="group", input_instructions="数字")
    assessment = dm.AssessmentBlueprint(id="assessment", revision=1, title="合成测试", question_refs=[ref(question)], allowed_modes=["independent"])
    service.publish(workspace, [question, assessment], {})
    with database.transaction() as connection:
        connection.execute("INSERT INTO attempts(id,workspace_id,assessment_id,assessment_revision,mode,policy_json,question_refs_json,solution_refs_private_json,status,revision,created_at) VALUES('attempt',?,'assessment',1,'independent','{}','[]','[]','active',1,'2026-09-14T00:00:00Z')", (workspace,))
    arguments = {"read": ("block", "block", 1), "body": ("block", 1), "current": ("block",), "courses": (), "revisions": ("block",), "publish": (tree(2)[0], tree(2)[1])}
    with pytest.raises(ApiError) as result:
        getattr(service, method)(workspace, *arguments[method])
    assert result.value.code == "ASSESSMENT_ACTIVE"


def test_pagination_summary_cursors_are_scoped_signed_and_bounded(store):
    database, service, workspace = store
    for suffix in ["_a", "_b", "_c"]:
        values, bodies = tree(suffix=suffix)
        service.publish(workspace, values, bodies)
    page = service.courses(workspace, limit=1)
    assert len(page.items) == 1 and page.next_cursor
    assert set(page.items[0].model_dump()) == {"ref", "title", "language", "lesson_count", "review_state"}
    assert page.items[0].review_state == "unreviewed"
    next_page = service.courses(workspace, limit=1, cursor=page.next_cursor)
    assert next_page.items[0].ref.id != page.items[0].ref.id
    assert service.courses(workspace, q="%_").items == []
    for kwargs in [{"limit": 101}, {"limit": True}, {"limit": 1, "cursor": "arbitrary"},
                   {"limit": 1, "cursor": page.next_cursor[:-4] + "abcd"},
                   {"limit": 2, "cursor": page.next_cursor}, {"limit": 1, "q": "different", "cursor": page.next_cursor}]:
        with pytest.raises(ApiError):
            service.courses(workspace, **kwargs)
    other = second_workspace(database)
    with pytest.raises(ApiError):
        service.courses(other, limit=1, cursor=page.next_cursor)
    with pytest.raises(ApiError):
        service.revisions(workspace, "course_a", limit=1, cursor=page.next_cursor)
    with pytest.raises(ApiError):
        ContentService(database).courses(workspace, limit=1, cursor=page.next_cursor)
    values, bodies = tree(2, suffix="_a")
    service.publish(workspace, values, bodies)
    revisions = service.revisions(workspace, "block_a", limit=1)
    assert revisions.items[0].ref.revision == 2
    assert service.revisions(workspace, "block_a", limit=1, cursor=revisions.next_cursor).items[0].ref.revision == 1
    with database.transaction() as connection:
        connection.execute("UPDATE objects SET lifecycle='archived' WHERE id='course_a'")
    assert "course_a" not in [item.ref.id for item in service.courses(workspace).items]
    assert service.read(workspace, "course", "course_a", 1).revision == 1
    assert service.revisions(workspace, "course_a").items[0].lifecycle == "archived"


def test_old_concept_id_dependencies_remain_frozen_when_current_moves(store):
    database, service, workspace = store
    a1 = dm.Concept(id="a", revision=1, title="A1", prerequisite_ids=["b"])
    b1 = dm.Concept(id="b", revision=1, title="B1")
    values, bodies = tree(concept=False)
    course1 = values[-1].model_copy(update={"concept_refs": [ref(a1)]})
    service.publish(workspace, [a1, b1, *values[:-1], course1], bodies)
    a2 = a1.model_copy(update={"revision": 2, "prerequisite_ids": []})
    b2 = b1.model_copy(update={"revision": 2, "prerequisite_ids": ["a"]})
    service.publish(workspace, [a2, b2], {})
    course2 = course1.model_copy(update={"revision": 2})
    service.publish(workspace, [course2], {})
    with database.connect() as connection:
        for revision in (1, 2):
            rows = connection.execute("SELECT target_id,target_revision FROM object_dependencies WHERE owner_id='course' AND owner_revision=? AND relation='concept' ORDER BY target_id", (revision,)).fetchall()
            assert [tuple(row) for row in rows] == [("a", 1), ("b", 1)]
            edges = connection.execute("SELECT prerequisite_id,dependent_id FROM concept_edges WHERE course_id='course' AND course_revision=?", (revision,)).fetchall()
            assert [tuple(row) for row in edges] == [("b", "a")]
    assert service.read(workspace, "course", "course", 1) == course1
    assert service.read(workspace, "course", "course", 2) == course2


def test_old_block_pure_concepts_do_not_rebind_to_new_candidate_concept(store):
    database, service, workspace = store
    values, bodies = tree()
    service.publish(workspace, values, bodies)
    concept2 = values[0].model_copy(update={"revision": 2})
    lesson2 = values[2].model_copy(update={"revision": 2, "prerequisite_ids": []})
    service.publish(workspace, [concept2, lesson2], {})
    with database.connect() as connection:
        row = connection.execute("SELECT target_revision FROM object_dependencies WHERE owner_id='block' AND owner_revision=1 AND relation='concept'").fetchone()
        assert row[0] == 1
    assert service.read(workspace, "lesson", "lesson", 2).block_refs == [ref(values[1])]
