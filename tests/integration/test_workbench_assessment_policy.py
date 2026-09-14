"""Workbench metadata remains usable while material selections are redacted and preserved."""

from dataclasses import replace
import json

from fastapi.testclient import TestClient
import pytest

from packages.contracts import domain_models as dm
from services.api.app.application.assessment import AssessmentService
from services.api.app.application.workbench import WorkbenchService
from services.api.app.assessment_dto import AssessmentAttemptCreate
from services.api.app.dto import WorkbenchSaveRequest
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import COOKIE_NAME, SessionIdentity, issue_bootstrap_code
from services.api.app.main import create_app
from tests.assessment_fixtures import assessment_fixture
from tests.integration.test_assessment_attempts import import_fixture


@pytest.fixture
def prepared(tmp_path):
    database = Database(Settings(data_dir=tmp_path / "data"))
    workspace = database.initialize()
    identity = SessionIdentity("session_workbench_test", workspace, "learner", "unused", "2099-01-01T00:00:00Z")
    fixture = assessment_fixture("workbench")
    import_fixture(database, identity, fixture, "import")
    workbench = WorkbenchService(database)
    empty = workbench.read(workspace)
    selected = dm.Selection(ref=reference(fixture.block), exact_quote="本材料是原创软件验收样例", prefix="软件验收前文", suffix="软件验收后文", start_codepoint=0, end_codepoint=12)
    tab = dm.SavedTab(id="tab_material", context=dm.ViewContext(view_kind="lesson", active_ref=reference(fixture.lesson), selection=selected), pinned=True, scroll_offset=155)
    workbench.save(workspace, WorkbenchSaveRequest(expected_revision=empty.revision,
        session=empty.model_copy(update={"tabs": [tab], "active_tab_id": tab.id, "course_ref": reference(fixture.course)})))
    return database, identity, fixture, AssessmentService(database), selected


def login(client, database):
    response = client.post("/api/v1/session/bootstrap", json={"one_time_code": issue_bootstrap_code(database)}, headers={"Origin": database.settings.origin})
    assert response.status_code == 200
    return {"Origin": database.settings.origin, "X-CSRF-Token": response.json()["csrf_token"]}


def start(prepared, key="start"):
    _, identity, fixture, assessment, _ = prepared
    return assessment.create_attempt(identity, fixture.assessment.id,
        AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode="independent"), key)


@pytest.mark.parametrize("role", ["learner", "author"])
def test_active_independent_keeps_metadata_roundtrip_private_selection_and_restart(prepared, role):
    database, identity, fixture, assessment, selected = prepared
    with TestClient(create_app(database.settings), base_url=database.settings.origin) as client:
        headers = login(client, database)
        if role == "author":
            assert client.post("/api/v1/session/role", json={"role": role}, headers={**headers, "Idempotency-Key": "author"}).status_code == 200
        full = client.get("/api/v1/workbench/session")
        assert full.status_code == 200 and full.json()["tabs"][0]["context"]["selection"] is not None
        attempt = start(prepared)
        with database.connect() as connection:
            before = tuple(connection.execute("SELECT revision,session_json,updated_at FROM workbench_sessions WHERE workspace_id=?", (identity.workspace_id,)).fetchone())
        redacted = client.get("/api/v1/workbench/session")
        assert redacted.status_code == 200
        assert redacted.json()["tabs"][0]["context"]["selection"] is None
        assert selected.exact_quote not in redacted.text and selected.prefix not in redacted.text and selected.suffix not in redacted.text
        with database.connect() as connection:
            assert tuple(connection.execute("SELECT revision,session_json,updated_at FROM workbench_sessions WHERE workspace_id=?", (identity.workspace_id,)).fetchone()) == before
        snapshot = redacted.json()
        snapshot["agent_width"] = 420
        snapshot["tabs"].append({"id": "tab_own_attempt", "context": {"view_kind": "assessment_help", "active_ref": reference(fixture.assessment).model_dump(mode="json"), "attempt_id": attempt.id, "selection": None, "attached_refs": []}, "pinned": True, "scroll_offset": 77})
        snapshot["active_tab_id"] = "tab_own_attempt"
        # Full basis acquired before create is valid when entering the guard;
        # adding the newly-created attempt tab must not get an artificial 412.
        saved = client.put("/api/v1/workbench/session", json={"expected_revision": snapshot["revision"], "session": snapshot},
                           headers={**headers, "If-Match": full.headers["etag"]})
        assert saved.status_code == 200 and saved.json()["tabs"][0]["context"]["selection"] is None
        with database.connect() as connection:
            stored = json.loads(connection.execute("SELECT session_json FROM workbench_sessions WHERE workspace_id=?", (identity.workspace_id,)).fetchone()[0])
        assert stored["tabs"][0]["context"]["selection"] == selected.model_dump(mode="json")
        with TestClient(create_app(database.settings), base_url=database.settings.origin) as restarted:
            restarted.cookies.set(COOKIE_NAME, client.cookies[COOKIE_NAME])
            recovered = restarted.get("/api/v1/workbench/session")
            assert recovered.status_code == 200 and recovered.json() == saved.json()
            assert recovered.headers["etag"] == saved.headers["etag"]
            assert restarted.get(f"/api/v1/attempts/{attempt.id}").status_code == 200
        assessment.abandon(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), "abandon")
        restored = client.get("/api/v1/workbench/session")
        assert restored.json()["tabs"][0]["context"]["selection"] == selected.model_dump(mode="json")


@pytest.mark.parametrize("next_state", ["full", "another_active"])
def test_late_redacted_put_cannot_clear_selection_after_policy_changes(prepared, next_state):
    database, identity, _, assessment, selected = prepared
    with TestClient(create_app(database.settings), base_url=database.settings.origin) as client:
        headers = login(client, database)
        attempt = start(prepared)
        baseline = client.get("/api/v1/workbench/session")
        assert baseline.status_code == 200
        candidate = baseline.json()
        candidate["nav_width"] = 340
        assessment.abandon(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), "abandon")
        if next_state == "another_active":
            start(prepared, "second")
        rejected = client.put("/api/v1/workbench/session", json={"expected_revision": candidate["revision"], "session": candidate}, headers={**headers, "If-Match": baseline.headers["etag"]})
        assert rejected.status_code == 412
        with database.connect() as connection:
            stored = json.loads(connection.execute("SELECT session_json FROM workbench_sessions WHERE workspace_id=?", (identity.workspace_id,)).fetchone()[0])
        assert stored["revision"] == candidate["revision"] and stored["nav_width"] != 340
        assert stored["tabs"][0]["context"]["selection"] == selected.model_dump(mode="json")


def test_legacy_missing_policy_token_rejects_ambiguous_clear_but_fresh_full_token_allows_explicit_clear(prepared):
    database, identity, _, assessment, _ = prepared
    with TestClient(create_app(database.settings), base_url=database.settings.origin) as client:
        headers = login(client, database)
        attempt = start(prepared)
        baseline = client.get("/api/v1/workbench/session")
        assert baseline.status_code == 200
        assessment.abandon(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), "abandon")
        body = {"expected_revision": baseline.json()["revision"], "session": baseline.json()}
        assert client.put("/api/v1/workbench/session", json=body, headers=headers).status_code == 412
        full = client.get("/api/v1/workbench/session")
        assert client.put("/api/v1/workbench/session", json=body, headers={**headers, "If-Match": full.headers["etag"]}).status_code == 200
        assert client.get("/api/v1/workbench/session").json()["tabs"][0]["context"]["selection"] is None


def test_changed_context_never_inherits_old_selection_and_other_workspace_stays_separate(prepared):
    database, identity, fixture, _, selected = prepared
    with TestClient(create_app(database.settings), base_url=database.settings.origin) as client:
        headers = login(client, database)
        start(prepared)
        baseline = client.get("/api/v1/workbench/session")
        assert baseline.status_code == 200
        changed = baseline.json()
        changed["tabs"][0]["context"]["active_ref"] = reference(fixture.block).model_dump(mode="json")
        changed["tabs"][0]["context"]["selection"] = selected.model_dump(mode="json")
        saved = client.put("/api/v1/workbench/session", json={"expected_revision": changed["revision"], "session": changed}, headers={**headers, "If-Match": baseline.headers["etag"]})
        assert saved.status_code == 200 and saved.json()["tabs"][0]["context"]["selection"] is None
        with database.connect() as connection:
            stored = json.loads(connection.execute("SELECT session_json FROM workbench_sessions WHERE workspace_id=?", (identity.workspace_id,)).fetchone()[0])
        assert stored["tabs"][0]["context"]["selection"] is None
        other_database = Database(replace(database.settings, data_dir=database.settings.data_dir.parent / "other"))
        other_workspace = other_database.initialize()
        assert WorkbenchService(other_database).read(other_workspace).tabs == []
