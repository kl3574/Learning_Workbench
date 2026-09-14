from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from services.api.app.config import Settings
from services.api.app.main import create_app
from services.api.app.security import COOKIE_NAME, issue_bootstrap_code


@pytest.fixture
def authenticated(tmp_path):
    settings = Settings(data_dir=tmp_path)
    application = create_app(settings)
    with TestClient(application, base_url=settings.origin) as client:
        code = issue_bootstrap_code(application.state.database)
        response = client.post("/api/v1/session/bootstrap", json={"one_time_code": code}, headers={"Origin": settings.origin})
        headers = {"Origin": settings.origin, "X-CSRF-Token": response.json()["csrf_token"]}
        yield application, client, settings, headers


def test_empty_workspace_is_real_and_has_no_fabricated_content(authenticated):
    application, client, _, _ = authenticated
    response = client.get("/api/v1/workbench/session").json()
    assert response["navigation"] == "route" and response["tabs"] == [] and response["revision"] == 1
    with application.state.database.connect() as connection:
        for table in ("objects", "revisions", "grades", "learning_events", "jobs"):
            assert connection.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0


def test_layout_and_exact_missing_reference_snapshot_survive_restart(authenticated):
    _, client, settings, headers = authenticated
    snapshot = client.get("/api/v1/workbench/session").json()
    reference = {"entity": "lesson", "id": "lesson_synthetic_missing", "revision": 7, "sha256": "a" * 64}
    snapshot.update({
        "navigation": "textbook", "nav_width": 344, "agent_width": 410, "nav_collapsed": True,
        "expanded_keys": ["chapter_alpha", "chapter_beta"], "directory_scroll": 220.5,
        "tabs": [{"id": "tab_a", "context": {"view_kind": "lesson", "active_ref": reference, "attached_refs": [], "selection": None, "attempt_id": None}, "pinned": True, "scroll_offset": 184.5}],
        "active_tab_id": "tab_a",
    })
    saved = client.put("/api/v1/workbench/session", json={"expected_revision": 1, "session": snapshot}, headers=headers)
    assert saved.status_code == 200
    expected = {**snapshot, "revision": 2}
    assert saved.json() == expected
    with TestClient(create_app(settings), base_url=settings.origin) as restarted:
        restarted.cookies.set(COOKIE_NAME, client.cookies[COOKIE_NAME])
        assert restarted.get("/api/v1/workbench/session").json() == expected
        assert restarted.get("/api/v1/session").json()["csrf_token"] == headers["X-CSRF-Token"]


def test_workbench_cas_rejects_stale_save_without_overwrite(authenticated):
    _, client, _, headers = authenticated
    snapshot = client.get("/api/v1/workbench/session").json()
    first = {**snapshot, "nav_width": 330}
    assert client.put("/api/v1/workbench/session", json={"expected_revision": 1, "session": first}, headers=headers).status_code == 200
    stale = {**snapshot, "nav_width": 270}
    rejected = client.put("/api/v1/workbench/session", json={"expected_revision": 1, "session": stale}, headers=headers)
    assert rejected.status_code == 412 and rejected.json()["error"]["code"] == "REVISION_MISMATCH"
    assert client.get("/api/v1/workbench/session").json()["nav_width"] == 330


def test_competing_writes_have_one_winner(authenticated):
    _, client, _, headers = authenticated
    snapshot = client.get("/api/v1/workbench/session").json()

    def save(width):
        return client.put("/api/v1/workbench/session", json={"expected_revision": 1, "session": {**snapshot, "nav_width": width}}, headers=headers).status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(save, [310, 340])) == [200, 412]
    assert client.get("/api/v1/workbench/session").json()["revision"] == 2


@pytest.mark.parametrize("changes", [{"grade": 100}, {"nav_width": 500}, {"agent_width": 500}, {"directory_scroll": -1}, {"active_tab_id": "missing_tab"}, {"revision": 9}])
def test_invalid_or_business_data_cannot_enter_ui_session(authenticated, changes):
    _, client, _, headers = authenticated
    snapshot = client.get("/api/v1/workbench/session").json()
    assert client.put("/api/v1/workbench/session", json={"expected_revision": 1, "session": {**snapshot, **changes}}, headers=headers).status_code == 422
    assert client.get("/api/v1/workbench/session").json() == snapshot


def test_preference_patch_is_persistent_and_uses_its_own_revision(authenticated):
    _, client, _, headers = authenticated
    workspace = client.get("/api/v1/workspace").json()
    response = client.put("/api/v1/workspace/preferences", json={"expected_revision": workspace["revision"], "preferences": {"reader_font_size": 24, "default_learning_minutes": 45}}, headers=headers)
    assert response.json() == {"id": workspace["id"], "revision": 2, "applied": True}
    assert client.get("/api/v1/workspace").json()["preferences"]["reader_font_size"] == 24
    assert client.get("/api/v1/workbench/session").json()["revision"] == 1
    assert client.put("/api/v1/workspace/preferences", json={"expected_revision": 1, "preferences": {"reader_font_size": 20}}, headers=headers).status_code == 412
    assert client.get("/api/v1/workspace").json()["preferences"]["reader_font_size"] == 24


def test_duplicate_json_keys_and_non_finite_numbers_are_rejected(authenticated):
    _, client, _, headers = authenticated
    headers["Content-Type"] = "application/json"
    for body in ('{"expected_revision":1,"expected_revision":1,"preferences":{}}', '{"expected_revision":1,"preferences":{"reader_font_size":NaN}}'):
        response = client.put("/api/v1/workspace/preferences", content=body, headers=headers)
        assert response.status_code == 422 and response.json()["error"]["code"] == "SCHEMA_INVALID"


def test_http_json_is_utf8_only(authenticated):
    _, client, _, headers = authenticated
    headers["Content-Type"] = "application/json"
    body = '{"expected_revision":1,"preferences":{}}'.encode("utf-16")
    response = client.put("/api/v1/workspace/preferences", content=body, headers=headers)
    assert response.status_code == 422 and response.json()["error"]["code"] == "SCHEMA_INVALID"


def test_unknown_query_parameters_are_not_silently_accepted(authenticated):
    _, client, _, _ = authenticated
    response = client.get("/api/v1/workspace?unknown=private-material")
    assert response.status_code == 422 and "private-material" not in response.text


def test_static_same_origin_html_is_served_with_security_headers(tmp_path):
    static = tmp_path / "static"
    static.mkdir()
    (static / "index.html").write_text("<!doctype html><title>Synthetic shell</title>", encoding="utf-8")
    settings = Settings(data_dir=tmp_path / "data", static_dir=static)
    with TestClient(create_app(settings), base_url=settings.origin) as client:
        response = client.get("/")
        assert response.status_code == 200 and "Synthetic shell" in response.text
        assert response.headers["referrer-policy"] == "no-referrer"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
        assert client.get("/../workspace.sqlite3").status_code == 404
