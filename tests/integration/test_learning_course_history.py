"""Course-filtered learning records retain exact members of published history."""

from fastapi.testclient import TestClient
import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from services.api.app.application.content import ContentService
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.security import issue_bootstrap_code
from services.api.app.main import create_app


def lesson_tree(suffix: str, revision: int = 1):
    body = f"Synthetic {suffix} revision {revision}.\n".encode()
    block = dm.ContentBlock(id=f"block_history_{suffix}", revision=revision, kind="text", title=f"Block {suffix}",
        body_path=f"{suffix}-{revision}.md", body_sha256=sha256_bytes(body))
    lesson = dm.Lesson(id=f"lesson_history_{suffix}", revision=revision, title=f"Lesson {suffix}", objectives=[], block_refs=[reference(block)])
    return block, lesson, {block.body_path: body}


@pytest.fixture
def history_http(tmp_path):
    settings = Settings(data_dir=tmp_path / "data")
    app = create_app(settings)
    with TestClient(app, base_url=settings.origin) as client:
        bootstrap = client.post("/api/v1/session/bootstrap", json={"one_time_code": issue_bootstrap_code(app.state.database)}, headers={"Origin": settings.origin})
        assert bootstrap.status_code == 200
        workspace = bootstrap.json()["workspace_id"]
        headers = {"Origin": settings.origin, "X-CSRF-Token": bootstrap.json()["csrf_token"]}
        yield app.state.database, client, workspace, headers


def action(client, headers, ref, key, kind="read_marked"):
    revision = client.get("/api/v1/learning/progress").json()["revision"]
    result = client.post("/api/v1/learning/actions", json={"kind": kind, "ref": ref.model_dump(mode="json"), "expected_revision": revision, "value": True}, headers={**headers, "Idempotency-Key": key})
    assert result.status_code == 200


def test_old_and_new_course_members_retain_toolbar_and_outline_reading_consistency(history_http):
    database, client, workspace, headers = history_http
    content = ContentService(database)
    old_block, old_lesson, old_bodies = lesson_tree("old")
    old_course = dm.Course(id="course_history", revision=1, title="Original chapter", audience="synthetic", lesson_refs=[reference(old_lesson)])
    content.publish(workspace, [old_block, old_lesson, old_course], old_bodies)
    action(client, headers, reference(old_lesson), "read-old")
    action(client, headers, reference(old_block), "bookmark-old", "bookmark_set")
    note = dm.Note(id="note_history", revision=1, workspace_id=workspace, markdown="Native note on original chapter",
        anchor=dm.Selection(ref=reference(old_block), exact_quote="Synthetic", start_codepoint=0, end_codepoint=9))
    assert client.post("/api/v1/notes", json=note.model_dump(mode="json"), headers={**headers, "Idempotency-Key": "note-old"}).status_code == 201

    new_block, new_lesson, new_bodies = lesson_tree("new")
    new_course = dm.Course(id=old_course.id, revision=2, title="Replacement chapter", audience="synthetic", lesson_refs=[reference(new_lesson)])
    content.publish(workspace, [new_block, new_lesson, new_course], new_bodies)
    action(client, headers, reference(new_lesson), "read-new")
    projected = client.get("/api/v1/learning/progress?course_id=course_history").json()
    assert {item["ref"]["id"] for item in projected["readings"]} == {old_lesson.id, new_lesson.id}
    assert projected["bookmarks"] == client.get("/api/v1/learning/progress").json()["bookmarks"]
    assert projected["bookmarks"][0]["ref"] == reference(old_block).model_dump(mode="json")
    for revision, lesson in [(1, old_lesson), (2, new_lesson)]:
        outline = client.get(f"/api/v1/courses/course_history/outline?revision={revision}").json()
        directory = outline["sections"][0]["lessons"][0]
        toolbar = next(item for item in projected["readings"] if item["ref"] == reference(lesson).model_dump(mode="json"))
        assert directory["reading_state"] == "read" and toolbar["read"] is True and toolbar["read_at"]
    assert len(client.get(f"/api/v1/notes?ref_id={old_block.id}").json()["items"]) == 1


def test_history_filter_excludes_other_courses_and_never_includes_unreferenced_same_id_revisions(history_http):
    database, client, workspace, headers = history_http
    content = ContentService(database)
    block, lesson, bodies = lesson_tree("member")
    course = dm.Course(id="course_history_scope", revision=1, title="Member course", audience="synthetic", lesson_refs=[reference(lesson)])
    content.publish(workspace, [block, lesson, course], bodies)
    action(client, headers, reference(block), "read-member")
    other_block, other_lesson, other_bodies = lesson_tree("other")
    other_course = dm.Course(id="course_history_other", revision=1, title="Other course", audience="synthetic", lesson_refs=[reference(other_lesson)])
    content.publish(workspace, [other_block, other_lesson, other_course], other_bodies)
    action(client, headers, reference(other_block), "read-other")
    unreferenced, _, unreferenced_body = lesson_tree("member", revision=2)
    content.publish(workspace, [unreferenced], unreferenced_body)
    action(client, headers, reference(unreferenced), "read-unreferenced-revision")
    action(client, headers, reference(unreferenced), "bookmark-unreferenced-revision", "bookmark_set")
    scoped = client.get("/api/v1/learning/progress?course_id=course_history_scope").json()
    assert [item["ref"] for item in scoped["readings"]] == [reference(block).model_dump(mode="json")]
    assert scoped["bookmarks"] == []
    other = client.get("/api/v1/learning/progress?course_id=course_history_other").json()
    assert [item["ref"] for item in other["readings"]] == [reference(other_block).model_dump(mode="json")]
    assert len(client.get("/api/v1/learning/progress").json()["readings"]) == 3
