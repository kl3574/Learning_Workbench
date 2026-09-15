import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from services.api.app.config import Settings
from services.api.app.main import create_app
from services.api.app.security import COOKIE_NAME, consume_bootstrap, issue_bootstrap_code, token_hash


@pytest.fixture
def runtime(tmp_path):
    settings = Settings(data_dir=tmp_path)
    application = create_app(settings)
    with TestClient(application, base_url=settings.origin) as client:
        yield application, client, settings


def login(application, client, settings):
    code = issue_bootstrap_code(application.state.database)
    response = client.post("/api/v1/session/bootstrap", json={"one_time_code": code}, headers={"Origin": settings.origin})
    assert response.status_code == 200
    return {"Origin": settings.origin, "X-CSRF-Token": response.json()["csrf_token"]}


def test_health_is_public_and_readiness_is_authenticated(runtime):
    application, client, settings = runtime
    assert client.get("/health").json() == {"status": "ok", "build_version": "0.1.0"}
    assert client.get("/api/v1/readiness").status_code == 401
    login(application, client, settings)
    assert client.get("/api/v1/readiness").json() == {
        "database_ready": True, "worker_ready": True, "data_schema_version": "3.0.0",
        "migrations_pending": False, "providers_configured": False,
    }


@pytest.mark.parametrize("host", ["evil.example:8765", "127.0.0.1.evil.example:8765", "127.0.0.1:9999", "localhost:8765"])
def test_dns_rebinding_and_unconfigured_host_rejected(runtime, host):
    _, client, _ = runtime
    assert client.get("/health", headers={"Host": host}).json()["error"]["code"] == "HOST_DENIED"


@pytest.mark.parametrize("origin", ["https://evil.example", "null", "http://127.0.0.1:5173", "http://127.0.0.1:8765.evil.example", "http://localhost:8765"])
def test_untrusted_origin_cannot_bootstrap(runtime, origin):
    application, client, settings = runtime
    code = issue_bootstrap_code(application.state.database)
    response = client.post("/api/v1/session/bootstrap", json={"one_time_code": code}, headers={"Origin": origin})
    assert response.status_code == 403
    assert client.post("/api/v1/session/bootstrap", json={"one_time_code": code}, headers={"Origin": settings.origin}).status_code == 200


def test_missing_origin_rejected_even_with_valid_code(runtime):
    application, client, _ = runtime
    code = issue_bootstrap_code(application.state.database)
    assert client.post("/api/v1/session/bootstrap", json={"one_time_code": code}).status_code == 403


def test_duplicate_host_and_origin_are_rejected(runtime):
    _, client, settings = runtime
    assert client.get("/health", headers=[("Host", "127.0.0.1:8765"), ("Host", "evil.example")]).status_code == 400
    assert client.get("/health", headers=[("Origin", settings.origin), ("Origin", "https://evil.example")]).status_code == 403


def test_explicit_dev_origin_is_accepted(tmp_path):
    settings = Settings(data_dir=tmp_path, ui_origin="http://127.0.0.1:5173")
    application = create_app(settings)
    with TestClient(application, base_url=settings.ui_origin) as client:
        code = issue_bootstrap_code(application.state.database)
        assert client.post("/api/v1/session/bootstrap", json={"one_time_code": code}, headers={"Origin": settings.ui_origin}).status_code == 200


def test_bootstrap_is_atomic_single_use_and_cookie_is_protected(runtime):
    application, client, settings = runtime
    code = issue_bootstrap_code(application.state.database)
    response = client.post("/api/v1/session/bootstrap", json={"one_time_code": code}, headers={"Origin": settings.origin})
    cookie = response.headers["set-cookie"]
    assert "HttpOnly" in cookie and "SameSite=strict" in cookie and "Path=/" in cookie
    assert client.post("/api/v1/session/bootstrap", json={"one_time_code": code}, headers={"Origin": settings.origin}).status_code == 401
    with application.state.database.connect() as connection:
        persisted = "\n".join(connection.iterdump())
        assert code not in persisted and client.cookies[COOKIE_NAME] not in persisted
        assert response.json()["csrf_token"] not in persisted


def test_concurrent_bootstrap_has_one_winner(runtime):
    application, _, _ = runtime
    database = application.state.database
    code = issue_bootstrap_code(database)

    def consume():
        from services.api.app.errors import ApiError
        try:
            consume_bootstrap(database, code)
            return 200
        except ApiError as error:
            return error.status

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(lambda _: consume(), range(2))) == [200, 401]


def test_expired_code_and_session_rejected(runtime):
    application, client, settings = runtime
    database = application.state.database
    code = issue_bootstrap_code(database)
    with database.transaction() as connection:
        connection.execute("UPDATE bootstrap_codes SET expires_at='2000-01-01T00:00:00.000000Z' WHERE code_hash=?", (token_hash(code),))
    assert client.post("/api/v1/session/bootstrap", json={"one_time_code": code}, headers={"Origin": settings.origin}).status_code == 401
    login(application, client, settings)
    with database.transaction() as connection:
        connection.execute("UPDATE local_sessions SET expires_at='2000-01-01T00:00:00.000000Z'")
    assert client.get("/api/v1/session").status_code == 401


def test_csrf_get_recovery_logout_revocation_and_data_retention(runtime):
    application, client, settings = runtime
    headers = login(application, client, settings)
    assert client.get("/api/v1/session").json()["csrf_token"] == headers["X-CSRF-Token"]
    token = client.cookies[COOKIE_NAME]
    for csrf in (None, "wrong"):
        rejected = {"Origin": settings.origin}
        if csrf:
            rejected["X-CSRF-Token"] = csrf
        assert client.post("/api/v1/session/logout", json={}, headers=rejected).status_code == 403
    assert client.post("/api/v1/session/logout", json={}, headers=headers).json() == {"logged_out": True}
    client.cookies.set(COOKIE_NAME, token)
    assert client.get("/api/v1/session").status_code == 401
    with application.state.database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM workspace").fetchone()[0] == 1


def test_strict_request_validation_and_errors_never_reflect_inputs(runtime):
    application, client, settings = runtime
    headers = login(application, client, settings)
    secret = "/synthetic-private/provider-key-fixture"
    for body in [
        {"expected_revision": 1, "preferences": {"provider_secret": secret}},
        {"expected_revision": "1", "preferences": {}},
        {"expected_revision": 1, "preferences": {"reader_font_size": 29}},
        {"expected_revision": 1, "preferences": {"reader_font_size": True}},
        {"expected_revision": 1, "preferences": {"language": None}},
    ]:
        response = client.put("/api/v1/workspace/preferences", json=body, headers=headers)
        assert response.status_code == 422
        error = response.json()["error"]
        assert set(error) == {"code", "message", "request_id", "retryable", "details"}
        assert error["details"] == [] and secret not in response.text
        assert response.headers["x-request-id"] == error["request_id"]


def test_infrastructure_errors_are_sanitized(runtime, monkeypatch, caplog):
    application, client, settings = runtime
    login(application, client, settings)
    secret = "/private/person/database.sqlite secret-key-value"

    def fail():
        raise sqlite3.OperationalError(secret)

    monkeypatch.setattr(application.state.database, "connect", fail)
    response = client.get("/api/v1/session")
    assert response.status_code == 503
    assert secret not in response.text and secret not in caplog.text


def test_creation_role_idempotency_and_payload_conflict(runtime):
    application, client, settings = runtime
    headers = login(application, client, settings)
    assert client.post("/api/v1/session/role", json={"role": "author"}, headers=headers).status_code == 422
    headers["Idempotency-Key"] = "role-switch-1"
    response = client.post("/api/v1/session/role", json={"role": "author"}, headers=headers)
    assert response.status_code == 200 and response.json()["role"] == "author"
    assert client.post("/api/v1/session/role", json={"role": "author"}, headers=headers).json() == response.json()
    assert client.post("/api/v1/session/role", json={"role": "learner"}, headers=headers).status_code == 409
    with application.state.database.connect() as connection:
        assert connection.execute("SELECT count(*) FROM idempotency").fetchone()[0] == 1
        assert headers["X-CSRF-Token"] not in "\n".join(connection.iterdump())


def test_independent_guard_is_workspace_wide_across_sessions(runtime):
    application, client, settings = runtime
    headers = login(application, client, settings)
    workspace = client.get("/api/v1/session").json()["workspace_id"]
    with application.state.database.transaction() as connection:
        connection.execute("INSERT INTO objects(id,workspace_id,kind) VALUES('assessment_a',?,'assessment')", (workspace,))
        connection.execute("INSERT INTO revisions(object_id,revision,sha256,metadata_json,created_at) VALUES('assessment_a',1,?,'{}','2026-09-14T00:00:00Z')", (hashlib.sha256(b"synthetic").hexdigest(),))
        connection.execute("INSERT INTO attempts(id,workspace_id,assessment_id,assessment_revision,mode,policy_json,question_refs_json,solution_refs_private_json,status,revision,created_at) VALUES('attempt_a',?,'assessment_a',1,'independent','{}','[]','[]','active',1,'2026-09-14T00:00:00Z')", (workspace,))
    assert client.get("/api/v1/session").json()["active_independent_attempt_id"] == "attempt_a"
    assert client.get("/api/v1/workbench/session").status_code == 409
    headers["Idempotency-Key"] = "cannot-bypass-active-assessment"
    assert client.post("/api/v1/session/role", json={"role": "author"}, headers=headers).json()["error"]["code"] == "ASSESSMENT_ACTIVE"
    with TestClient(create_app(settings), base_url=settings.origin) as second:
        other_headers = login(application, second, settings)
        other_headers["Idempotency-Key"] = "second-session-role"
        assert second.get("/api/v1/session").json()["workspace_id"] == workspace
        assert second.get("/api/v1/workbench/session").status_code == 409
        assert second.post("/api/v1/session/role", json={"role": "author"}, headers=other_headers).status_code == 409


def test_payload_budget_and_unimplemented_routes(runtime):
    application, client, settings = runtime
    headers = login(application, client, settings)
    assert client.post("/api/v1/session/logout", content=b"x" * (settings.max_request_bytes + 1), headers=headers).status_code == 413
    # M5.1 now implements provider capabilities. The later Codex endpoint must not be
    # installed as a success stub or silently fall through to the SPA.
    assert client.get("/api/v1/codex/capabilities").status_code == 404
    assert "/api/v1/codex/capabilities" not in application.openapi()["paths"]


@pytest.mark.parametrize("host", ["0.0.0.0", "192.168.1.2", "example.com", "::"])
def test_public_bind_fails_before_initialization(tmp_path, host):
    with pytest.raises(ValueError, match="Public deployment"):
        Settings(data_dir=tmp_path, host=host)


def test_import_and_factory_do_not_create_application_data(tmp_path):
    data = tmp_path / "new-data"
    create_app(Settings(data_dir=data))
    assert not data.exists()


def test_local_data_files_have_private_modes(runtime):
    application, _, settings = runtime
    assert settings.data_dir.stat().st_mode & 0o777 == 0o700
    assert application.state.database.path.stat().st_mode & 0o777 == 0o600


def test_data_directory_cannot_be_inside_source_tree():
    from services.api.app.config import REPOSITORY_ROOT
    with pytest.raises(ValueError, match="outside"):
        Settings(data_dir=REPOSITORY_ROOT / "data")


@pytest.mark.parametrize("origin", ["https://remote.example:443", "http://127.0.0.1:5173/", "http://user:pass@127.0.0.1:5173", "http://127.0.0.1:5173/?key=secret"])
def test_dev_origin_rejects_remote_or_non_origin_values(tmp_path, origin):
    with pytest.raises(ValueError):
        Settings(data_dir=tmp_path, ui_origin=origin)
