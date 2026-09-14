"""Real SQLite and authenticated HTTP content reads; import UI is a later task."""

import hashlib

from fastapi.testclient import TestClient
import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256
from services.api.app.application.content import ContentService
from services.api.app.config import Settings
from services.api.app.main import create_app
from services.api.app.security import COOKIE_NAME, issue_bootstrap_code
from services.api.app.infrastructure.database import utc_now


def reference(value):
    return dm.ContentRef(entity=value.entity, id=value.id, revision=value.revision, sha256=metadata_sha256(value))


def tree(revision=1, suffix=""):
    data = f"# 合成内容 {revision}\n\n精确修订、中文和非 BMP 字符 🧠。\n\n$$x^2 \\ge 0$$\n".encode()
    block = dm.ContentBlock(
        id=f"block_http{suffix}", revision=revision, kind="worked_example", title="合成算例",
        body_path=f"content/block_http{suffix}.r{revision}.md", body_sha256=hashlib.sha256(data).hexdigest(),
    )
    lesson = dm.Lesson(id=f"lesson_http{suffix}", revision=revision, title="精确版本小节", objectives=[], block_refs=[reference(block)])
    course = dm.Course(id=f"course_http{suffix}", revision=revision, title="原创合成课程", audience="接口验收", lesson_refs=[reference(lesson)])
    return [block, lesson, course], {block.body_path: data}


@pytest.fixture
def content_http(tmp_path):
    settings = Settings(data_dir=tmp_path / "data")
    application = create_app(settings)
    with TestClient(application, base_url=settings.origin) as client:
        code = issue_bootstrap_code(application.state.database)
        bootstrap = client.post("/api/v1/session/bootstrap", json={"one_time_code": code}, headers={"Origin": settings.origin})
        assert bootstrap.status_code == 200
        workspace = bootstrap.json()["workspace_id"]
        service = ContentService(application.state.database)
        objects, bodies = tree()
        service.publish(workspace, objects, bodies)
        yield application, client, settings, service, workspace, objects, bodies


def test_exact_metadata_body_and_etags_survive_new_revision_and_restart(content_http):
    _, client, settings, service, workspace, old, bodies = content_http
    for value, route in zip(old, ["blocks", "lessons", "courses"], strict=True):
        response = client.get(f"/api/v1/{route}/{value.id}?revision=1")
        assert response.status_code == 200
        assert response.json() == value.model_dump(mode="json")
        assert response.headers["etag"] == f'"{metadata_sha256(value)}"'
    body = client.get("/api/v1/blocks/block_http/body?revision=1")
    assert body.content == bodies[old[0].body_path]
    assert body.headers["content-type"] == "text/markdown; charset=utf-8"
    assert body.headers["etag"] == f'"{old[0].body_sha256}"'
    assert body.headers["cache-control"] == "no-store"
    assert body.headers["x-content-type-options"] == "nosniff"

    newer, new_bodies = tree(2)
    service.publish(workspace, newer, new_bodies)
    current = client.get("/api/v1/objects/block_http/current")
    assert current.json() == reference(newer[0]).model_dump(mode="json")
    assert client.get("/api/v1/blocks/block_http/body?revision=1").content == body.content
    assert client.get("/api/v1/blocks/block_http/body?revision=2").content == new_bodies[newer[0].body_path]
    with TestClient(create_app(settings), base_url=settings.origin) as restarted:
        restarted.cookies.set(COOKIE_NAME, client.cookies[COOKIE_NAME])
        assert restarted.get("/api/v1/blocks/block_http/body?revision=1").content == body.content
        assert restarted.get("/api/v1/objects/block_http/current").json() == current.json()


@pytest.mark.parametrize("query", ["", "?revision=latest", "?revision=0", "?revision=1&revision=2", "?revision=1&secret=synthetic"])
def test_missing_invalid_or_ambiguous_revision_does_not_fall_back_to_latest(content_http, query):
    _, client, _, _, _, _, _ = content_http
    response = client.get("/api/v1/blocks/block_http" + query)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "SCHEMA_INVALID"
    assert "synthetic" not in response.text


def test_missing_revision_wrong_entity_and_anonymous_reads_are_rejected(content_http):
    _, client, settings, _, _, _, _ = content_http
    assert client.get("/api/v1/blocks/block_http?revision=99").status_code == 404
    assert client.get("/api/v1/lessons/block_http?revision=1").status_code == 404
    with TestClient(create_app(settings), base_url=settings.origin) as anonymous:
        for path in ["/courses", "/blocks/block_http?revision=1", "/blocks/block_http/body?revision=1", "/objects/block_http/current"]:
            assert anonymous.get("/api/v1" + path).status_code == 401


def test_course_and_revision_pagination_uses_validated_server_cursors(content_http):
    _, client, _, service, workspace, _, _ = content_http
    for suffix in ["_b", "_c"]:
        values, bodies = tree(suffix=suffix)
        service.publish(workspace, values, bodies)
    first = client.get("/api/v1/courses?limit=1").json()
    assert len(first["items"]) == 1 and first["next_cursor"]
    item = first["items"][0]
    assert set(item) == {"ref", "title", "language", "lesson_count", "review_state"}
    assert item["review_state"] == "unreviewed"
    second = client.get("/api/v1/courses", params={"limit": 1, "cursor": first["next_cursor"]}).json()
    assert len(second["items"]) == 1 and second["items"][0]["ref"]["id"] != item["ref"]["id"]
    assert client.get("/api/v1/courses?cursor=arbitrary_client_value").status_code in (400, 422)
    assert client.get("/api/v1/courses?limit=101").status_code == 422
    assert client.get("/api/v1/courses?limit=1&limit=2").status_code == 422
    assert client.get("/api/v1/courses?q=not_present").json()["items"] == []

    values, bodies = tree(2)
    service.publish(workspace, values, bodies)
    revisions = client.get("/api/v1/objects/block_http/revisions?limit=1").json()
    assert len(revisions["items"]) == 1 and revisions["next_cursor"]
    next_page = client.get("/api/v1/objects/block_http/revisions", params={"limit": 1, "cursor": revisions["next_cursor"]}).json()
    assert {revisions["items"][0]["ref"]["revision"], next_page["items"][0]["ref"]["revision"]} == {1, 2}


def test_corrupt_blob_is_never_returned_as_a_successful_markdown_body(content_http):
    _, client, settings, _, _, objects, _ = content_http
    digest = objects[0].body_sha256
    (settings.data_dir / "blobs" / digest[:2] / digest).write_bytes(b"corrupt synthetic payload")
    response = client.get("/api/v1/blocks/block_http/body?revision=1")
    assert response.status_code >= 400
    assert "corrupt synthetic payload" not in response.text
    assert "error" in response.json()


def test_other_workspace_objects_are_not_exposed_by_any_content_query(content_http):
    application, client, _, service, _, _, _ = content_http
    other = "workspace_other_http"
    with application.state.database.transaction() as connection:
        connection.execute("INSERT INTO workspace(id,title,created_at) VALUES(?,?,?)", (other, "独立合成工作区", utc_now()))
    values, bodies = tree(suffix="_private_workspace")
    service.publish(other, values, bodies)
    for path in [
        "/courses/course_http_private_workspace?revision=1",
        "/lessons/lesson_http_private_workspace?revision=1",
        "/blocks/block_http_private_workspace?revision=1",
        "/blocks/block_http_private_workspace/body?revision=1",
        "/objects/block_http_private_workspace/current",
        "/objects/block_http_private_workspace/revisions",
    ]:
        response = client.get("/api/v1" + path)
        assert response.status_code == 404
        assert "etag" not in response.headers
    assert len(client.get("/api/v1/courses").json()["items"]) == 1


def test_active_independent_attempt_blocks_content_reads_even_in_author_role(content_http):
    application, client, settings, service, workspace, _, _ = content_http
    concept = dm.Concept(id="concept_guard", revision=1, title="合成概念")
    question = dm.QuestionPublic(
        id="question_guard", revision=1, kind="numeric", stem_markdown="合成数值问题", concept_ids=[concept.id],
        skill="compute", exposure_group="exposure_guard", input_instructions="填写数值",
    )
    assessment = dm.AssessmentBlueprint(
        id="assessment_guard", revision=1, title="合成测试策略", question_refs=[reference(question)], allowed_modes=["independent"],
    )
    service.publish(workspace, [concept, question, assessment], {})
    auth = client.get("/api/v1/session").json()
    response = client.post("/api/v1/session/role", json={"role": "author"}, headers={
        "Origin": settings.origin, "X-CSRF-Token": auth["csrf_token"], "Idempotency-Key": "http-content-author",
    })
    assert response.status_code == 200
    policy = dm.PolicySnapshot(mode="independent", tutor_scope="operation_help_only", allow_web=False, allow_materials=False)
    # This fixture establishes an active policy directly. It does not assert that
    # the not-yet-implemented attempt-creation endpoint works.
    with application.state.database.transaction() as connection:
        connection.execute(
            "INSERT INTO attempts(id,workspace_id,assessment_id,assessment_revision,mode,policy_json,question_refs_json,"
            "solution_refs_private_json,status,revision,created_at) VALUES(?,?,?,1,'independent',?,'[]','[]','active',1,?)",
            ("attempt_http_guard", workspace, assessment.id, policy.model_dump_json(), utc_now()),
        )
    for path in [
        "/courses", "/courses/course_http?revision=1", "/lessons/lesson_http?revision=1",
        "/blocks/block_http?revision=1", "/blocks/block_http/body?revision=1",
        "/objects/block_http/current", "/objects/block_http/revisions",
    ]:
        response = client.get("/api/v1" + path)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "ASSESSMENT_ACTIVE"
        assert "etag" not in response.headers
        assert "合成算例" not in response.text
