"""Real file/HTTP/worker/SQLite import workflows using original synthetic input."""

import hashlib
from pathlib import Path
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest

from services.api.app.config import Settings
from services.api.app.main import create_app
from services.api.app.security import COOKIE_NAME, issue_bootstrap_code

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def importing(tmp_path):
    settings = Settings(data_dir=tmp_path / "data")
    app = create_app(settings)
    with TestClient(app, base_url=settings.origin) as client:
        response = client.post("/api/v1/session/bootstrap", json={"one_time_code": issue_bootstrap_code(app.state.database)},
                               headers={"Origin": settings.origin})
        assert response.status_code == 200
        yield app, client, settings
    assert not app.state.import_worker.is_alive()


def headers(client, settings, key=None):
    session = client.get("/api/v1/session").json()
    return {"Origin": settings.origin, "X-CSRF-Token": session["csrf_token"], "Idempotency-Key": key or uuid4().hex}


def upload(client, settings, data, filename="synthetic.md", kind="auto", key=None, target=None):
    fields = {"kind": kind}
    if target is not None:
        fields["target_course_id"] = target
    response = client.post("/api/v1/imports", data=fields, files={"file": (filename, data)}, headers=headers(client, settings, key))
    assert response.status_code == 202, response.text
    assert response.json()["input_sha256"] == hashlib.sha256(data).hexdigest()
    return response.json()


def preview(client, id):
    deadline = time.monotonic() + 10
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/imports/{id}")
        assert response.status_code == 200, response.text
        value = response.json()
        if value["status"] not in {"staged", "parsing"}:
            return value
        time.sleep(0.05)
    pytest.fail("Live worker did not produce an observable import state within the test budget")


def confirm(client, settings, candidate, key=None):
    return client.post(f"/api/v1/imports/{candidate['id']}/commit", json={
        "expected_input_sha256": candidate["input_sha256"],
        "accepted_warning_codes": [w["code"] for w in candidate["warnings"] if w["severity"] != "error"],
        "id_mapping": [],
    }, headers=headers(client, settings, key))


def block_preview(client, candidate, containing=None):
    drafts = [client.get(f"/api/v1/drafts/{id}").json() for id in candidate["preview_refs"]]
    return next(d for d in drafts if d["kind"] == "block" and
                (containing is None or containing in d["payload"]["body_markdown"]))


def test_upload_preview_confirm_and_original_download_are_real_and_durable(importing):
    _, client, settings = importing
    data = "# 原创合成教材\n\n## 数学小节\n\n保留中文 🧠 与 $x^2$。\n".encode()
    staged = upload(client, settings, data)
    candidate = preview(client, staged["import_id"])
    assert candidate["status"] == "preview_ready", candidate
    assert client.get("/api/v1/courses").json()["items"] == []
    draft = block_preview(client, candidate, "$x^2$")
    assert "$x^2$" in draft["payload"]["body_markdown"]
    assert draft["state"] == "draft"
    source = client.get(f"/api/v1/sources/{draft['payload']['source_id']}")
    assert source.status_code == 200
    artifact = source.json()["artifact"]
    original = client.get(artifact["download_path"])
    assert original.content == data
    assert original.headers["content-type"] == "application/octet-stream"
    assert original.headers["content-disposition"].startswith("attachment;")
    assert original.headers["etag"] == f'"{hashlib.sha256(data).hexdigest()}"'
    job = client.get(f"/api/v1/jobs/{staged['job']['id']}").json()
    assert job["status"] == "awaiting_approval" and job["result_refs"] == []
    accepted = confirm(client, settings, candidate)
    assert accepted.status_code == 200, accepted.text
    refs = accepted.json()["course_refs"]
    assert refs and accepted.json()["migration_receipt_id"]
    for ref in refs:
        assert client.get(f"/api/v1/courses/{ref['id']}?revision={ref['revision']}").status_code == 200
    body_ref = draft["payload"]["metadata"]
    body = client.get(f"/api/v1/blocks/{body_ref['id']}/body?revision={body_ref['revision']}")
    assert body.text == draft["payload"]["body_markdown"]
    assert client.get(f"/api/v1/jobs/{staged['job']['id']}").json()["status"] == "completed"
    with TestClient(create_app(settings), base_url=settings.origin) as restarted:
        restarted.cookies.set(COOKIE_NAME, client.cookies[COOKIE_NAME])
        assert restarted.get(f"/api/v1/imports/{candidate['id']}").json()["status"] == "committed"
        assert restarted.get(artifact["download_path"]).content == data


def test_upload_and_confirmation_replay_do_not_create_duplicate_objects(importing):
    app, client, settings = importing
    data = b"# Synthetic\n\nExact replay.\n"
    first = upload(client, settings, data, key="same-upload")
    assert upload(client, settings, data, key="same-upload") == first
    conflict = client.post("/api/v1/imports", data={"kind": "auto"}, files={"file": ("synthetic.md", b"different")}, headers=headers(client, settings, "same-upload"))
    assert conflict.status_code == 409
    candidate = preview(client, first["import_id"])
    accepted = confirm(client, settings, candidate, key="same-confirm")
    assert accepted.status_code == 200, accepted.text
    assert confirm(client, settings, candidate, key="same-confirm").json() == accepted.json()
    with app.state.database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM ingestion_imports").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM job_events WHERE type IN ('completed','failed','cancelled')").fetchone()[0] == 1
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_cancelled_preview_does_not_publish_and_cannot_be_confirmed(importing):
    app, client, settings = importing
    staged = upload(client, settings, b"# Synthetic cancellation\n")
    candidate = preview(client, staged["import_id"])
    response = client.post(f"/api/v1/imports/{candidate['id']}/cancel", json={"expected_input_sha256": candidate["input_sha256"]}, headers=headers(client, settings))
    assert response.status_code == 200 and response.json()["status"] == "cancelled"
    assert confirm(client, settings, candidate).status_code == 409
    assert client.get("/api/v1/courses").json()["items"] == []
    with app.state.database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM revisions").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM learning_events").fetchone()[0] == 0


def test_html_has_safe_preview_but_exact_original_is_preserved(importing):
    _, client, settings = importing
    data = b'<html><body><h1>Synthetic HTML</h1><script>window.BAD_SECRET=1</script><p onclick="bad()">Text \\(x^2\\)</p><img src="https://example.invalid/track"></body></html>'
    staged = upload(client, settings, data, filename="synthetic.html")
    candidate = preview(client, staged["import_id"])
    assert candidate["status"] == "preview_ready", candidate
    draft = block_preview(client, candidate, "x^2")
    all_drafts = [client.get(f"/api/v1/drafts/{id}").json() for id in candidate["preview_refs"]]
    text = "\n".join(d["payload"]["body_markdown"] for d in all_drafts if d["kind"] == "block")
    assert "x^2" in text and "Text" in text
    assert all(value not in text for value in ["<script", "BAD_SECRET", "onclick", "https://example.invalid"])
    assert any(w["severity"] == "warning" for w in candidate["warnings"])
    source = client.get(f"/api/v1/sources/{draft['payload']['source_id']}").json()
    assert client.get(source["artifact"]["download_path"]).content == data
    unacknowledged = client.post(f"/api/v1/imports/{candidate['id']}/commit", json={
        "expected_input_sha256": candidate["input_sha256"], "accepted_warning_codes": [], "id_mapping": [],
    }, headers=headers(client, settings))
    assert unacknowledged.status_code == 409


@pytest.mark.parametrize("problem", ["unknown", "duplicate", "query", "no_csrf", "oversize"])
def test_bad_uploads_fail_without_staging_or_echoing_fields(importing, problem):
    app, client, settings = importing
    fields = [("kind", (None, "auto")), ("file", ("synthetic.md", b"text"))]
    path = "/api/v1/imports"
    sent_headers = headers(client, settings)
    if problem == "unknown":
        fields.append(("private_test_value", (None, "do not echo")))
    elif problem == "duplicate":
        fields.append(("kind", (None, "text")))
    elif problem == "query":
        path += "?unknown=private_test_value"
    elif problem == "no_csrf":
        del sent_headers["X-CSRF-Token"]
    else:
        sent_headers["Content-Length"] = str(settings.max_upload_bytes + 65537)
    response = client.post(path, files=fields, headers=sent_headers)
    assert response.status_code == {"unknown": 422, "duplicate": 422, "query": 422, "no_csrf": 403, "oversize": 413}[problem]
    assert "private_test_value" not in response.text and "do not echo" not in response.text
    with app.state.database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM ingestion_imports").fetchone()[0] == 0


def test_author_package_stores_answers_privately_and_does_not_trust_imported_review(importing):
    app, client, settings = importing
    role = client.post("/api/v1/session/role", json={"role": "author"}, headers=headers(client, settings))
    assert role.status_code == 200
    staged = upload(client, settings, (ROOT / "fixtures/synthetic/course-author.learnpack.zip").read_bytes(), filename="course-author.learnpack.zip")
    candidate = preview(client, staged["import_id"])
    assert candidate["status"] == "preview_ready", candidate
    draft = block_preview(client, candidate)
    source_id = draft["payload"]["source_id"]
    assert confirm(client, settings, candidate).status_code == 200
    with app.state.database.connect() as connection:
        rows = connection.execute("SELECT review_status FROM solutions").fetchall()
        assert rows and all(row["review_status"] != "approved" for row in rows)
    assert client.post("/api/v1/session/role", json={"role": "learner"}, headers=headers(client, settings)).status_code == 200
    assert client.get(f"/api/v1/sources/{source_id}").status_code == 403
    assert client.get(f"/api/v1/drafts/{draft['id']}").status_code == 403
    assert client.get("/api/v1/courses").status_code == 200


def test_worker_readiness_uses_live_thread_state(importing):
    app, client, _ = importing
    assert client.get("/api/v1/readiness").json()["worker_ready"] is True
    app.state.import_worker.stop()
    assert client.get("/api/v1/readiness").json()["worker_ready"] is False


def test_explicit_larger_text_budget_reaches_preview_commit_and_exact_readback(tmp_path):
    settings = Settings(data_dir=tmp_path / "expanded", max_block_characters=500_000)
    app = create_app(settings)
    original = b"synthetic long paragraph " + b"x" * 400_001
    with TestClient(app, base_url=settings.origin) as client:
        response = client.post("/api/v1/session/bootstrap", json={"one_time_code": issue_bootstrap_code(app.state.database)},
                               headers={"Origin": settings.origin})
        assert response.status_code == 200
        staged = upload(client, settings, original, filename="expanded.txt")
        candidate = preview(client, staged["import_id"])
        assert candidate["status"] == "preview_ready", candidate
        draft = block_preview(client, candidate)
        body = draft["payload"]["body_markdown"]
        assert len(body) > 400_000 and original.decode() in body
        assert confirm(client, settings, candidate).status_code == 200
        metadata = draft["payload"]["metadata"]
        published = client.get(f"/api/v1/blocks/{metadata['id']}/body?revision={metadata['revision']}")
        assert published.status_code == 200 and published.text == body
        assert hashlib.sha256(published.content).hexdigest() == metadata["body_sha256"]


def test_job_cancel_checks_revision_and_returns_full_snapshot(importing):
    _, client, settings = importing
    staged = upload(client, settings, b"# Synthetic job cancellation\n")
    candidate = preview(client, staged["import_id"])
    job_url = f"/api/v1/jobs/{staged['job']['id']}"
    job = client.get(job_url).json()
    stale = client.post(job_url + "/cancel", json={"expected_revision": job["revision"] - 1}, headers=headers(client, settings))
    assert stale.status_code == 412
    cancelled = client.post(job_url + "/cancel", json={"expected_revision": job["revision"]}, headers=headers(client, settings, "cancel-job"))
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelled" and cancelled.json()["result_refs"] == []
    assert cancelled.json()["workspace_id"] == job["workspace_id"]
    replay = client.post(job_url + "/cancel", json={"expected_revision": job["revision"]}, headers=headers(client, settings, "cancel-job"))
    assert replay.json() == cancelled.json()
    assert client.get(f"/api/v1/imports/{candidate['id']}").json()["status"] == "cancelled"


def test_m2_3_extraction_is_explicitly_unimplemented_and_never_publishes(importing):
    app, client, settings = importing
    staged = upload(client, settings, b"%PDF-1.4\nSynthetic placeholder for unsupported-format testing\n", filename="synthetic.pdf")
    candidate = preview(client, staged["import_id"])
    assert candidate["status"] == "failed" and candidate["preview_refs"] == []
    assert any(w["code"] == "EXTRACTION_NOT_IMPLEMENTED" for w in candidate["warnings"])
    job = client.get(f"/api/v1/jobs/{staged['job']['id']}").json()
    assert job["status"] == "failed" and job["error"]["code"] == "EXTRACTION_NOT_IMPLEMENTED"
    with app.state.database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM revisions").fetchone()[0] == 0


def test_active_independent_attempt_blocks_every_import_subject_port_even_author(importing):
    app, client, settings = importing
    assert client.post("/api/v1/session/role", json={"role": "author"}, headers=headers(client, settings)).status_code == 200
    staged = upload(client, settings, b"# Synthetic protected original\n")
    candidate = preview(client, staged["import_id"])
    draft = block_preview(client, candidate)
    source = client.get(f"/api/v1/sources/{draft['payload']['source_id']}").json()
    job = client.get(f"/api/v1/jobs/{staged['job']['id']}").json()
    workspace = client.get("/api/v1/session").json()["workspace_id"]
    # Directly establishing the policy tests subject-data enforcement only;
    # it does not claim the later M3 attempt-creation workflow exists.
    with app.state.database.transaction() as connection:
        connection.execute("INSERT INTO objects(id,workspace_id,kind) VALUES('assessment_import_guard',?,'assessment')", (workspace,))
        connection.execute("INSERT INTO revisions(object_id,revision,sha256,metadata_json,created_at) VALUES('assessment_import_guard',1,?,'{}','2026-09-14T00:00:00Z')", ("0" * 64,))
        connection.execute("INSERT INTO attempts(id,workspace_id,assessment_id,assessment_revision,mode,policy_json,question_refs_json,solution_refs_private_json,status,revision,created_at) VALUES('attempt_import_guard',?,'assessment_import_guard',1,'independent','{}','[]','[]','active',1,'2026-09-14T00:00:00Z')", (workspace,))
    for path in [f"/imports/{candidate['id']}", f"/jobs/{job['id']}", f"/drafts/{draft['id']}", f"/sources/{source['id']}"]:
        response = client.get("/api/v1" + path)
        assert response.status_code == 409 and response.json()["error"]["code"] == "ASSESSMENT_ACTIVE"
    response = client.get(source["artifact"]["download_path"])
    assert response.status_code == 409 and "etag" not in response.headers
    assert confirm(client, settings, candidate).status_code == 409
    assert client.post(f"/api/v1/imports/{candidate['id']}/cancel", json={"expected_input_sha256": candidate["input_sha256"]}, headers=headers(client, settings)).status_code == 409
    assert client.post(f"/api/v1/jobs/{job['id']}/cancel", json={"expected_revision": job["revision"]}, headers=headers(client, settings)).status_code == 409
    assert client.post("/api/v1/imports", data={"kind": "text"}, files={"file": ("another.txt", b"blocked")}, headers=headers(client, settings)).status_code == 409
