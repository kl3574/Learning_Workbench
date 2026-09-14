"""Independent adversarial checks; SQLite fault injection is not a public API."""

import json

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256
from services.api.app.infrastructure.database import utc_now
from tests.contract import test_practice_public_projection as public_projection

create_session = public_projection.create_session
practice_http = public_projection.practice_http


def post(client, headers, session, action, body, key):
    return client.post(f"/api/v1/practice/sessions/{session['id']}/{action}", json=body,
                       headers={**headers, "Idempotency-Key": key})


def reveal(client, headers, session, key="reveal-original"):
    return post(client, headers, session, "solutions", {
        "question_id": session["questions"][0]["id"], "expected_revision": session["revision"],
    }, key)


def state(database, session_id):
    with database.connect() as connection:
        return {table: [dict(row) for row in connection.execute(f"SELECT * FROM {table} ORDER BY rowid")]
                for table in ("practice_sessions", "practice_responses", "practice_exposures", "exposures",
                              "learning_events", "learning_progress", "outbox", "idempotency")}


def test_frozen_private_revision_survives_later_solution_and_missing_frozen_body_fails_closed(practice_http):
    client, headers, database, _ = practice_http
    original = create_session(client, headers)
    question_id = original["questions"][0]["id"]
    with database.transaction() as connection:
        row = connection.execute("SELECT * FROM solutions WHERE question_id=?", (question_id,)).fetchone()
        private = dm.SolutionPrivate.model_validate_json(row["private_json"])
        newer = private.model_copy(update={"revision": private.revision + 1,
                                           "solution_markdown": "合成新增答案修订，旧会话不得读取。"})
        connection.execute("INSERT INTO solutions VALUES(?,?,?,?,?,?)", (question_id, private.question_ref.revision,
            newer.revision, canonical_bytes(newer).decode(), metadata_sha256(newer), newer.review_status))
    old_answer = reveal(client, headers, original)
    assert old_answer.status_code == 200, old_answer.text
    assert old_answer.json()["solution_markdown"] == private.solution_markdown
    new_session = client.post("/api/v1/practice/sessions", json={"practice_ref": original["practice_ref"]},
                              headers={**headers, "Idempotency-Key": "create-newer"}).json()
    new_answer = reveal(client, headers, new_session, "reveal-newer")
    assert new_answer.status_code == 200 and new_answer.json()["solution_markdown"] == newer.solution_markdown
    with database.transaction() as connection:
        connection.execute("DELETE FROM solutions WHERE question_id=? AND solution_revision=?", (question_id, private.revision))
    retry = reveal(client, headers, {**original, "revision": old_answer.json()["revision"]}, "missing-frozen")
    assert retry.status_code == 409 and retry.json()["error"]["code"] == "CONTENT_HASH_MISMATCH"
    assert newer.solution_markdown not in retry.text


def test_missing_private_assignment_cannot_adopt_a_later_solution(practice_http):
    client, headers, database, _ = practice_http
    with database.transaction() as connection:
        originals = [dict(row) for row in connection.execute("SELECT * FROM solutions")]
        connection.execute("DELETE FROM solutions")
    session = create_session(client, headers)
    before = state(database, session["id"])
    unavailable = reveal(client, headers, session)
    assert unavailable.status_code == 409 and unavailable.json()["error"]["code"] == "SOLUTION_UNAVAILABLE"
    assert state(database, session["id"]) == before
    with database.transaction() as connection:
        for row in originals:
            connection.execute("INSERT INTO solutions VALUES(?,?,?,?,?,?)", tuple(row[key] for key in (
                "question_id", "question_revision", "solution_revision", "private_json", "sha256", "review_status")))
    late = reveal(client, headers, session, "still-missing-at-creation")
    assert late.status_code == 409 and late.json()["error"]["code"] == "SOLUTION_UNAVAILABLE"
    assert state(database, session["id"]) == before


def test_help_after_submission_changes_current_assistance_without_rewriting_original_receipt(practice_http):
    client, headers, database, _ = practice_http
    session = create_session(client, headers)
    submitted = post(client, headers, session, "submit", {"expected_revision": 1}, "submit-original")
    assert submitted.status_code == 200, submitted.text
    receipt = submitted.json()
    assert receipt["assisted"] is False
    with database.connect() as connection:
        original = tuple(connection.execute("SELECT submission_json,submission_sha256 FROM practice_sessions WHERE id=?", (session["id"],)).fetchone())
    answer = reveal(client, headers, {**session, "revision": receipt["revision"]})
    assert answer.status_code == 200, answer.text
    current = client.get(f"/api/v1/practice/sessions/{session['id']}").json()
    assert current["status"] == "submitted" and current["assisted"] is True
    assert current["results"] == receipt["results"]
    assert all(item["score"] is None and item["status"] == "needs_review" for item in current["results"])
    replay = post(client, headers, session, "submit", {"expected_revision": 1}, "submit-original")
    assert replay.status_code == 200 and replay.json() == receipt
    with database.connect() as connection:
        assert tuple(connection.execute("SELECT submission_json,submission_sha256 FROM practice_sessions WHERE id=?", (session["id"],)).fetchone()) == original
        assert connection.execute("SELECT COUNT(*) FROM learning_events WHERE kind='practice_submitted'").fetchone()[0] == 1


@pytest.mark.parametrize("action,trigger", [("solutions", "practice_exposures"), ("submit", "outbox")])
def test_downstream_storage_failure_rolls_back_event_projection_and_retry_receipt(practice_http, action, trigger):
    client, headers, database, _ = practice_http
    session = create_session(client, headers)
    body = {"expected_revision": 1}
    if action == "solutions":
        body["question_id"] = session["questions"][0]["id"]
    with database.transaction() as connection:
        condition = " WHEN NEW.event_type='practice.submitted'" if trigger == "outbox" else ""
        connection.execute(f"CREATE TRIGGER synthetic_storage_failure BEFORE INSERT ON {trigger}{condition} BEGIN SELECT RAISE(ABORT,'synthetic downstream failure'); END")
    before = state(database, session["id"])
    failed = post(client, headers, session, action, body, "atomic-operation")
    assert failed.status_code == 503, failed.text
    assert "synthetic downstream failure" not in failed.text
    assert state(database, session["id"]) == before
    with database.transaction() as connection:
        connection.execute("DROP TRIGGER synthetic_storage_failure")
    success = post(client, headers, session, action, body, "atomic-operation")
    assert success.status_code == 200, success.text
    replay = post(client, headers, session, action, body, "atomic-operation")
    assert replay.status_code == 200 and replay.json() == success.json()
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM learning_events").fetchone()[0] == 1


@pytest.mark.parametrize("role", ["learner", "author"])
def test_guard_runs_before_known_private_answer_and_create_replays(practice_http, role):
    client, headers, database, _ = practice_http
    session = create_session(client, headers)
    first = reveal(client, headers, session)
    assert first.status_code == 200
    if role == "author":
        switched = client.post("/api/v1/session/role", json={"role": role}, headers={**headers, "Idempotency-Key": "independent-author"})
        assert switched.status_code == 200
    # The M3.2 start endpoint is not implemented here; this inserts its already
    # specified persisted guard state against a genuinely imported assessment.
    with database.transaction() as connection:
        workspace = database.workspace_id()
        assessment = connection.execute("SELECT id,current_revision FROM objects WHERE kind='assessment'").fetchone()
        policy = dm.PolicySnapshot(mode="independent", tutor_scope="operation_help_only", allow_web=False, allow_materials=False)
        connection.execute("INSERT INTO attempts(id,workspace_id,assessment_id,assessment_revision,mode,policy_json,question_refs_json,solution_refs_private_json,status,revision,created_at) VALUES(?,?,?,?,'independent',?,'[]','[]','active',1,?)",
            ("attempt_independent_review", workspace, assessment["id"], assessment["current_revision"], canonical_bytes(policy).decode(), utc_now()))
    before = state(database, session["id"])
    paths = [
        ("get", "/api/v1/practice/sets", None, "read"),
        ("get", f"/api/v1/practice/sessions/{session['id']}", None, "read"),
        ("post", "/api/v1/practice/sessions", {"practice_ref": session["practice_ref"]}, "create-practice"),
        ("put", f"/api/v1/practice/sessions/{session['id']}/responses", {"expected_revision": 2, "responses": []}, "guard-save"),
        ("post", f"/api/v1/practice/sessions/{session['id']}/submit", {"expected_revision": 2}, "guard-submit"),
        ("post", f"/api/v1/practice/sessions/{session['id']}/hints", {"expected_revision": 2, "question_id": session["questions"][0]["id"], "level": 1}, "guard-hint"),
        ("post", f"/api/v1/practice/sessions/{session['id']}/solutions", {"expected_revision": 1, "question_id": session["questions"][0]["id"]}, "reveal-original"),
    ]
    for method, path, body, key in paths:
        response = client.request(method, path, json=body, headers={**headers, "Idempotency-Key": key})
        assert response.status_code == 409 and response.json()["error"]["code"] == "ASSESSMENT_ACTIVE", response.text
        assert first.json()["solution_markdown"] not in response.text
    assert state(database, session["id"]) == before


def test_corrupt_exposure_event_cannot_bind_another_workspace_event(practice_http):
    client, headers, database, _ = practice_http
    session = create_session(client, headers)
    answer = reveal(client, headers, session)
    assert answer.status_code == 200
    with database.transaction() as connection:
        connection.execute("INSERT INTO workspace(id,title,created_at) VALUES('workspace_unrelated','合成其他工作区',?)", (utc_now(),))
        row = connection.execute("SELECT * FROM learning_events WHERE event_id=?", (answer.json()["exposure_event_id"],)).fetchone()
        event = json.loads(row["payload_json"])
        event.update(event_id="event_unrelated_workspace", workspace_id="workspace_unrelated", attempt_id="practice_unrelated")
        connection.execute("INSERT INTO learning_events VALUES(?,?,?,?,?,?)", (event["event_id"], event["workspace_id"], row["kind"], row["origin"], canonical_bytes(event).decode(), row["occurred_at"]))
        # No trigger is disabled. The existing FK proves existence, not workspace
        # or session association; the read boundary must reject this inconsistency.
        connection.execute("UPDATE exposures SET event_id=? WHERE event_id=?", (event["event_id"], answer.json()["exposure_event_id"]))
    restored = client.get(f"/api/v1/practice/sessions/{session['id']}")
    assert restored.status_code == 409, {"status": restored.status_code, "event_ids": restored.json().get("exposure_event_ids")}
    assert restored.json()["error"]["code"] == "PRACTICE_SNAPSHOT_INVALID"
    assert "event_unrelated_workspace" not in restored.text
