"""Real imported private pins, SQLite grading jobs and signed human review.

Imported solutions stay needs_review. Controlled approved-rule fixtures are tested
in the rule suite; integration never masquerades an imported answer as reviewed.
"""

from dataclasses import replace
import sqlite3

from fastapi.testclient import TestClient
import pytest

from packages.contracts import domain_models as dm
from services.api.app.application.errors import ApiError
from services.api.app.application.grading import GradingService, GradingWorker
from services.api.app.assessment_dto import AssessmentAttemptCreate, AssessmentGradingResult, RegradeItemReview, RegradeRequest
from services.api.app.import_dto import JobCancelRequest
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.grading_repository import GradingRepository
from services.api.app.infrastructure.security import consume_bootstrap, issue_bootstrap_code
from services.api.app.main import create_app
from tests.integration.test_assessment_attempts import storage as assessment_storage, start


@pytest.fixture
def storage(tmp_path):
    return assessment_storage.__wrapped__(tmp_path)


def submitted(storage, mode="independent"):
    _, identity, _, service = storage
    attempt = start(storage, mode=mode)
    return service.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=attempt.revision), "submit")


def real_author(database):
    _, identity = consume_bootstrap(database, issue_bootstrap_code(database))
    with database.transaction() as connection:
        connection.execute("UPDATE local_sessions SET role='author' WHERE id=?", (identity.id,))
    return replace(identity, role="author")


def review_request(fixture, revision=1, count=None):
    return RegradeRequest(expected_grading_revision=revision, reason="Explicit human review of submitted synthetic answers.", item_reviews=[
        RegradeItemReview(question_id=q.id, score=0.5 * q.max_score, feedback_markdown="Human rubric decision with bounded partial credit.") for q in fixture.questions[:count]])


def counts(database):
    with database.connect() as connection:
        return {name: connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in ("grades", "assessment_grade_audits", "assessment_manual_reviews", "jobs", "job_events", "learning_events", "evidence")}


def test_real_queue_grades_unreviewed_without_zero_or_private_release_and_preserves_submit_receipt(storage):
    database, learner, fixture, assessment = storage
    final = submitted(storage)
    service = GradingService(database)
    waiting = service.result(learner, final.id)
    assert isinstance(waiting, dm.JobRef) and waiting.status == "queued"
    assert final.grading_status == "pending"
    before = counts(database)
    assert GradingWorker(database).run_once()
    actual = service.result(learner, final.id)
    assert isinstance(actual, AssessmentGradingResult)
    assert actual.status == "needs_review" and actual.grading_revision == 1
    assert actual.solution_reviews == [] and actual.manual_reviews == []
    assert all(item.score is None and item.status == "needs_review" and item.solution_markdown is None for item in actual.items)
    assert [item.question_ref for item in actual.items] == [reference(q) for q in fixture.questions]
    assert assessment.get_attempt(learner, final.id).grading_status == "needs_review"
    assert assessment.submit(learner, final.id, dm.AttemptSubmit(expected_revision=1), "submit") == final
    assert not GradingWorker(database).run_once()
    after = counts(database)
    assert after["grades"] == after["assessment_grade_audits"] == 1
    assert after["learning_events"] == before["learning_events"] == 1 and after["evidence"] == 0
    assert "private_pin" not in actual.model_dump_json() and "accepted_answers" not in actual.model_dump_json()
    with database.connect() as connection:
        assert {row[0] for row in connection.execute("SELECT review_status FROM solutions")} == {"needs_review"}
        assert connection.execute("SELECT COUNT(*) FROM job_events WHERE job_id=? AND type IN ('completed','failed','cancelled')", (waiting.id,)).fetchone()[0] == 1


def test_signed_actual_author_regrade_is_new_immutable_grade_and_does_not_approve_answers(storage):
    database, learner, fixture, assessment = storage
    final = submitted(storage)
    worker = GradingWorker(database)
    assert worker.run_once()
    service = GradingService(database)
    original = service.result(learner, final.id)
    with pytest.raises(ApiError, match="当前有效作者"):
        service.regrade(replace(learner, role="author"), final.id, review_request(fixture), "forged")
    author = real_author(database)
    request = review_request(fixture)
    job = service.regrade(author, final.id, request, "review")
    assert service.regrade(author, final.id, request, "review") == job
    assert worker.run_once()
    result = service.result(learner, final.id)
    assert isinstance(result, AssessmentGradingResult) and result.status == "graded" and result.grading_revision == 2
    assert all(item.score == item.max_score * .5 and item.solution_markdown for item in result.items)
    assert {item.review_status for item in result.solution_reviews} == {"needs_review"}
    assert result.eligibility_status == "not_evaluated"
    assert len(result.manual_reviews) == 1 and result.manual_reviews[0].actor_role == "author"
    assert author.id not in result.model_dump_json()
    with database.connect() as connection:
        old = GradingRepository(connection, learner.workspace_id).load_grade(GradingRepository(connection, learner.workspace_id).attempts.load(final.id), 1)
        assert old and old[0].model_dump() == original.model_dump(exclude={"manual_reviews", "solution_reviews", "eligibility_status"})
        assert connection.execute("SELECT COUNT(*) FROM grades").fetchone()[0] == 2
        assert {row[0] for row in connection.execute("SELECT review_status FROM solutions")} == {"needs_review"}
    with pytest.raises(ApiError) as conflict:
        service.regrade(author, final.id, request, "stale")
    assert conflict.value.status == 412
    assert assessment.get_attempt(learner, final.id).grading_revision == 2


def test_cancel_stale_lease_cannot_commit_and_explicit_review_recovers_original_submission(storage):
    database, learner, fixture, _ = storage
    final = submitted(storage)
    worker = GradingWorker(database)
    lease = worker.claim()
    assert lease
    result, audit = worker.compute(lease)
    service = GradingService(database)
    job = service.job(learner, lease.job_id)
    cancelled = service.cancel(learner, lease.job_id, JobCancelRequest(expected_revision=job.revision), "cancel")
    assert cancelled.status == "cancelled"
    assert service.cancel(learner, lease.job_id, JobCancelRequest(expected_revision=job.revision), "cancel") == cancelled
    assert not worker.finish(lease, result, audit)
    assert counts(database)["grades"] == 0
    author = real_author(database)
    retry = service.regrade(author, final.id, review_request(fixture, revision=0), "recover")
    assert retry.id != lease.job_id and worker.run_once()
    assert service.result(learner, final.id).grading_revision == 1


def test_expired_worker_reclaim_discards_old_owner_and_has_one_terminal(storage):
    database, learner, _, _ = storage
    final = submitted(storage)
    old = GradingWorker(database)
    lease = old.claim()
    assert lease
    result, audit = old.compute(lease)
    with database.transaction() as connection:
        connection.execute("UPDATE jobs SET lease_until='2000-01-01T00:00:00Z' WHERE id=?", (lease.job_id,))
    assert GradingWorker(Database(database.settings)).run_once()
    assert not old.finish(lease, result, audit)
    assert GradingService(database).result(learner, final.id).grading_revision == 1
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM grades").fetchone()[0] == 1
        assert connection.execute("SELECT retry_count FROM jobs WHERE id=?", (lease.job_id,)).fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM job_events WHERE job_id=? AND type IN ('completed','failed','cancelled')", (lease.job_id,)).fetchone()[0] == 1


def test_atomic_terminal_failure_rolls_back_grade_attempt_and_audit(storage):
    database, learner, _, assessment = storage
    final = submitted(storage)
    worker = GradingWorker(database)
    lease = worker.claim()
    assert lease
    result, audit = worker.compute(lease)
    before = counts(database)
    with database.transaction() as connection:
        connection.execute("CREATE TRIGGER injected_terminal_failure BEFORE INSERT ON job_events WHEN NEW.type='completed' BEGIN SELECT RAISE(ABORT,'synthetic failure'); END")
    with pytest.raises(sqlite3.IntegrityError):
        worker.finish(lease, result, audit)
    assert counts(database) == before
    assert assessment.get_attempt(learner, final.id).status == "grading"
    with database.transaction() as connection:
        connection.execute("DROP TRIGGER injected_terminal_failure")
    assert worker.finish(lease, result, audit)


def test_partial_human_review_stays_null_for_others_and_independent_answer_stays_private(storage):
    database, learner, fixture, _ = storage
    final = submitted(storage)
    worker = GradingWorker(database)
    assert worker.run_once()
    service = GradingService(database)
    author = real_author(database)
    service.regrade(author, final.id, review_request(fixture, count=1), "partial")
    assert worker.run_once()
    result = service.result(learner, final.id)
    assert isinstance(result, AssessmentGradingResult) and result.status == "needs_review"
    assert result.items[0].score == .5 * fixture.questions[0].max_score
    assert all(item.score is None for item in result.items[1:])
    assert all(item.solution_markdown is None for item in result.items)
    assert result.solution_reviews == []


def test_cannot_inflate_score_or_review_other_assignment_and_no_signature_side_effect(storage):
    database, _, fixture, _ = storage
    final = submitted(storage)
    assert GradingWorker(database).run_once()
    author = real_author(database)
    service = GradingService(database)
    before = counts(database)
    for question_id, score in [(fixture.questions[0].id, 1e10), ("question_not_assigned", 0.0)]:
        with pytest.raises(ApiError) as caught:
            service.regrade(author, final.id, RegradeRequest(expected_grading_revision=1, reason="Explicit review",
                item_reviews=[RegradeItemReview(question_id=question_id, score=score, feedback_markdown="review")]), question_id)
        assert caught.value.status == 422
    assert counts(database) == before


def test_newer_approved_private_fixture_cannot_change_attempt_frozen_answer(storage):
    from tests.integration.test_assessment_attempts import insert_answer
    database, learner, fixture, _ = storage
    final = submitted(storage)
    # A controlled newer immutable private revision is not a product approval action.
    for old in fixture.solutions:
        insert_answer(database, old.model_copy(update={"revision": 2, "review_status": "approved"}))
    assert GradingWorker(database).run_once()
    value = GradingService(database).result(learner, final.id)
    assert isinstance(value, AssessmentGradingResult)
    assert all(item.score is None for item in value.items)
    with database.connect() as connection:
        repo = GradingRepository(connection, learner.workspace_id)
        grade = repo.load_grade(repo.attempts.load(final.id))
        assert grade and all(trace.private_pin.solution_revision == 1 for trace in grade[1].traces)


@pytest.mark.parametrize("damage", ["outbox", "job_input", "job_terminal", "private_audit", "review_signature"])
def test_persisted_corruption_fails_closed_without_returning_scores(storage, damage):
    database, learner, fixture, _ = storage
    final = submitted(storage)
    assert GradingWorker(database).run_once()
    service = GradingService(database)
    if damage == "review_signature":
        author = real_author(database)
        service.regrade(author, final.id, review_request(fixture), "review")
        assert GradingWorker(database).run_once()
    with database.transaction() as connection:
        if damage == "outbox":
            connection.execute("UPDATE outbox SET payload_json='{}' WHERE event_type='assessment.grading.requested'")
        elif damage == "job_input":
            connection.execute("UPDATE jobs SET input_json='{}' WHERE kind='assessment_grading'")
        elif damage == "job_terminal":
            connection.execute("UPDATE job_events SET payload_json='{}' WHERE type='completed' AND job_id IN (SELECT job_id FROM assessment_grade_jobs)")
        elif damage == "private_audit":
            connection.execute("DROP TRIGGER assessment_grade_audit_no_update")
            connection.execute("UPDATE assessment_grade_audits SET private_json='{}'")
        else:
            connection.execute("UPDATE grading_signing_keys SET secret=?", (bytes(32),))
    with pytest.raises(ApiError) as caught:
        service.result(learner, final.id)
    assert caught.value.code == "ASSESSMENT_SNAPSHOT_INVALID"


def test_grading_http_real_login_role_cas_job_dispatch_and_no_private_trace(storage):
    database, _, fixture, _ = storage
    token, identity = consume_bootstrap(database, issue_bootstrap_code(database))
    app = create_app(database.settings)
    with TestClient(app, base_url="http://127.0.0.1:8765") as client:
        app.state.import_worker.stop()
        client.cookies.set("learning_session", token)
        headers = {"Origin": "http://127.0.0.1:8765", "X-CSRF-Token": identity.csrf_token}
        request = AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode="independent")
        response = client.post(f"/api/v1/assessments/{fixture.assessment.id}/attempts", json=request.model_dump(mode="json"), headers={**headers, "Idempotency-Key": "http-start"})
        assert response.status_code == 201
        identifier = response.json()["id"]
        assert client.get(f"/api/v1/attempts/{identifier}/result").status_code == 409
        response = client.post(f"/api/v1/attempts/{identifier}/submit", json={"expected_revision": 1}, headers={**headers, "Idempotency-Key": "http-submit"})
        assert response.status_code == 202
        pending = client.get(f"/api/v1/attempts/{identifier}/result")
        assert pending.status_code == 202 and pending.json()["status"] == "queued"
        job_id = pending.json()["id"]
        assert client.get(f"/api/v1/jobs/{job_id}").json()["kind"] == "assessment_grading"
        assert GradingWorker(database).run_once()
        result = client.get(f"/api/v1/attempts/{identifier}/result")
        assert result.status_code == 200 and result.json()["status"] == "needs_review"
        assert "private_pin" not in result.text and "accepted_answers" not in result.text
        body = review_request(fixture).model_dump(mode="json")
        denied = client.post(f"/api/v1/attempts/{identifier}/regrade", json=body, headers={**headers, "Idempotency-Key": "http-review"})
        assert denied.status_code == 403
        role = client.post("/api/v1/session/role", json={"role": "author"}, headers={**headers, "Idempotency-Key": "role-author"})
        assert role.status_code == 200
        accepted = client.post(f"/api/v1/attempts/{identifier}/regrade", json=body, headers={**headers, "Idempotency-Key": "http-review"})
        assert accepted.status_code == 202
        assert GradingWorker(database).run_once()
        result = client.get(f"/api/v1/attempts/{identifier}/result")
        assert result.status_code == 200 and result.json()["grading_revision"] == 2
        assert all(item["solution_markdown"] for item in result.json()["items"])
        assert client.get(f"/api/v1/jobs/{accepted.json()['id']}").json()["status"] == "completed"
        client.post("/api/v1/session/role", json={"role": "learner"}, headers={**headers, "Idempotency-Key": "role-learner"})
        assert client.post(f"/api/v1/attempts/{identifier}/regrade", json=body, headers={**headers, "Idempotency-Key": "http-review"}).status_code == 403


def test_actual_background_worker_finishes_without_poll_creating_jobs(storage):
    import time
    database, learner, _, assessment = storage
    final = submitted(storage)
    with TestClient(create_app(database.settings), base_url="http://127.0.0.1:8765") as client:
        assert client.get("/health").status_code == 200
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            state = assessment.get_attempt(learner, final.id)
            if state.status == "needs_review":
                break
            time.sleep(.02)
        assert state.status == "needs_review"
    snapshot = GradingService(Database(database.settings)).result(learner, final.id)
    assert isinstance(snapshot, AssessmentGradingResult) and snapshot.grading_revision == 1


def test_stopping_single_worker_prevents_late_commit_and_keeps_lease_recoverable(storage):
    from services.api.app.infrastructure.import_worker import ImportWorker
    database, learner, _, _ = storage
    final = submitted(storage)
    coordinator = ImportWorker(database)
    lease = coordinator.grading.claim()
    assert lease
    result, audit = coordinator.grading.compute(lease)
    coordinator.stop()
    assert not coordinator.grading.finish(lease, result, audit)
    job = GradingService(database).job(learner, lease.job_id)
    assert job.status == "running" and counts(database)["grades"] == 0
    with database.transaction() as connection:
        connection.execute("UPDATE jobs SET lease_until='2000-01-01T00:00:00Z' WHERE id=?", (lease.job_id,))
    assert ImportWorker(Database(database.settings)).run_once()
    assert GradingService(database).result(learner, final.id).grading_revision == 1


def test_real_job_failure_is_safe_and_explicit_human_recovery_preserves_submission(storage, monkeypatch):
    import services.api.app.application.grading as grading
    database, learner, fixture, assessment = storage
    final = submitted(storage)
    original = grading.grade_item
    def failure(**kwargs):
        raise ValueError("synthetic-private-diagnostic-not-for-http")
    monkeypatch.setattr(grading, "grade_item", failure)
    worker = GradingWorker(database)
    assert worker.run_once()
    service = GradingService(database)
    failed = service.result(learner, final.id)
    assert isinstance(failed, dm.JobRef) and failed.status == "failed"
    snapshot = service.job(learner, failed.id)
    assert snapshot.error and snapshot.error.code == "GRADING_FAILED"
    assert "synthetic-private" not in snapshot.model_dump_json()
    assert assessment.get_attempt(learner, final.id).grading_status == "failed"
    assert counts(database)["grades"] == 0
    monkeypatch.setattr(grading, "grade_item", original)
    service.regrade(real_author(database), final.id, review_request(fixture, revision=0), "after-failure")
    assert worker.run_once()
    assert service.result(learner, final.id).grading_revision == 1


def test_regrade_and_job_cache_cannot_bypass_new_independent_attempt_or_workspace(storage):
    database, learner, fixture, assessment = storage
    final = submitted(storage)
    assert GradingWorker(database).run_once()
    service = GradingService(database)
    author = real_author(database)
    request = review_request(fixture)
    job = service.regrade(author, final.id, request, "manual")
    assert GradingWorker(database).run_once()
    active = start(storage, key="another")
    assert active.id != final.id
    for call in (lambda: service.regrade(author, final.id, request, "manual"), lambda: service.job(author, job.id), lambda: service.result(author, final.id)):
        with pytest.raises(ApiError) as caught:
            call()
        assert caught.value.code == "ASSESSMENT_ACTIVE"
    with database.transaction() as connection:
        connection.execute("INSERT INTO workspace(id,title,created_at) VALUES('workspace_grading_other','synthetic','2026-09-14T00:00:00Z')")
    other = replace(author, workspace_id="workspace_grading_other")
    for call in (lambda: service.job(other, job.id), lambda: service.result(other, final.id)):
        with pytest.raises(ApiError) as caught:
            call()
        assert caught.value.status == 404
    assessment.abandon(learner, active.id, dm.AttemptSubmit(expected_revision=1), "abandon-other")
    assert service.regrade(author, final.id, request, "manual") == job


@pytest.mark.parametrize("terminal", ["failed", "cancelled"])
def test_http_failed_regrade_retains_real_previous_grade_without_private_answers_and_can_recover(storage, monkeypatch, terminal):
    database, learner, fixture, assessment = storage
    attempt = submitted(storage)
    service = GradingService(database)
    worker = GradingWorker(database)
    assert worker.run_once()
    author = real_author(database)
    service.regrade(author, attempt.id, review_request(fixture), "first-manual")
    assert worker.run_once()
    old = service.result(learner, attempt.id)
    assert isinstance(old, AssessmentGradingResult) and old.grading_revision == 2 and old.status == "graded"
    old_public = old.model_dump(mode="json")
    for item in old_public["items"]:
        item["solution_markdown"] = None
    old_public["solution_reviews"] = []
    with database.connect() as connection:
        old_raw = connection.execute("SELECT result_json FROM grades WHERE attempt_id=? AND grading_revision=2", (attempt.id,)).fetchone()[0]
    queued = service.regrade(author, attempt.id, review_request(fixture, revision=2, count=1), "second-manual")
    if terminal == "cancelled":
        current = service.job(author, queued.id)
        service.cancel(author, queued.id, JobCancelRequest(expected_revision=current.revision), "cancel-second")
    else:
        def failure(lease):
            raise ValueError("Synthetic failure before a later grading revision exists")
        with monkeypatch.context() as patch:
            patch.setattr(worker, "compute", failure)
            assert worker.run_once()
    # Real login + actual HTTP projection, with no background worker racing this controlled terminal.
    token, connected = consume_bootstrap(database, issue_bootstrap_code(database))
    client = TestClient(create_app(database.settings), base_url="http://127.0.0.1:8765")
    client.cookies.set("learning_session", token)
    response = client.get(f"/api/v1/attempts/{attempt.id}/result")
    assert response.status_code == 202
    pending = response.json()
    assert pending["id"] == queued.id and pending["status"] == terminal
    assert pending["last_completed_result"] == old_public
    assert pending["last_completed_result"]["items"][0]["score"] == .5 * fixture.questions[0].max_score
    assert pending["last_completed_result"]["manual_reviews"] == old_public["manual_reviews"]
    assert not any(item["solution_markdown"] for item in pending["last_completed_result"]["items"])
    assert client.get(f"/api/v1/jobs/{queued.id}").json()["status"] == terminal
    # A different active independent attempt still blocks even the old-score recovery projection.
    other = start(storage, key="other-active")
    assert client.get(f"/api/v1/attempts/{attempt.id}/result").status_code == 409
    assessment.abandon(learner, other.id, dm.AttemptSubmit(expected_revision=1), "end-other")
    headers = {"Origin": "http://127.0.0.1:8765", "X-CSRF-Token": connected.csrf_token, "Idempotency-Key": "recover-role"}
    assert client.post("/api/v1/session/role", json={"role": "author"}, headers=headers).status_code == 200
    body = review_request(fixture, revision=2).model_dump(mode="json")
    restored = client.post(f"/api/v1/attempts/{attempt.id}/regrade", json=body, headers={**headers, "Idempotency-Key": "explicit-recovery"})
    assert restored.status_code == 202 and restored.json()["id"] != queued.id
    assert GradingWorker(database).run_once()
    response = client.get(f"/api/v1/attempts/{attempt.id}/result")
    assert response.status_code == 200 and response.json()["grading_revision"] == 3
    with database.connect() as connection:
        assert connection.execute("SELECT result_json FROM grades WHERE attempt_id=? AND grading_revision=2", (attempt.id,)).fetchone()[0] == old_raw
        assert connection.execute("SELECT COUNT(*) FROM grades WHERE attempt_id=?", (attempt.id,)).fetchone()[0] == 3
