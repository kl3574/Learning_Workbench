"""Real imported answers, immutable grading history and HTTP byte-budget seams."""

from dataclasses import replace
import json

from fastapi.testclient import TestClient
import pytest

from packages.contracts import domain_models as dm
from services.api.app.application.assessment_evidence_access import completed_grade_keys, completed_grade_witness, submission_witness
from services.api.app.application.errors import ApiError
from services.api.app.application.grading import GradingService, GradingWorker
from services.api.app.assessment_dto import AssessmentGradingResult
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.security import consume_bootstrap, issue_bootstrap_code
from services.api.app.main import create_app
from tests.integration.test_assessment_attempts import start
from tests.integration.test_assessment_grading import real_author, review_request, storage as grading_storage, submitted


@pytest.fixture
def storage(tmp_path):
    return grading_storage.__wrapped__(tmp_path)


def client_for(database, *, budget=None):
    token, _ = consume_bootstrap(database, issue_bootstrap_code(database))
    settings = database.settings if budget is None else replace(database.settings, max_grading_history_response_bytes=budget)
    client = TestClient(create_app(settings), base_url="http://127.0.0.1:8765")
    # No lifespan: every queue transition below is deliberately driven by a real worker.
    client.cookies.set("learning_session", token)
    return client


def immutable_rows(database):
    with database.connect() as connection:
        return [tuple(row) for row in connection.execute(
            "SELECT attempt_id,grading_revision,result_json FROM grades ORDER BY attempt_id,grading_revision")]


def test_witness_ports_verify_original_submission_and_grade_without_mutation(storage):
    database, identity, fixture, assessment = storage
    attempt = start(storage)
    with database.connect() as connection:
        with pytest.raises(ApiError) as error:
            submission_witness(connection, identity.workspace_id, attempt.id)
        assert error.value.code == "ATTEMPT_NOT_SUBMITTED"
    saved = assessment.save_responses(identity, attempt.id, dm.ResponsesWrite(expected_revision=1,
        responses=[dm.ResponseDraft(question_id=fixture.questions[0].id, answer="中文 🧠", steps_markdown="保留原过程")]), "save")
    assessment.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=saved.revision), "submit")
    assert GradingWorker(database).run_once()
    with database.connect() as connection:
        witness = submission_witness(connection, identity.workspace_id, attempt.id)
        raw = connection.execute("SELECT * FROM attempts WHERE id=?", (attempt.id,)).fetchone()
        assert witness.assignment_sha256 == raw["snapshot_sha256"]
        assert witness.submission_sha256 == raw["submission_sha256"]
        assert witness.question_refs == [reference(q) for q in fixture.questions]
        assert all(item.state == "unseen" for item in witness.prior_seen.questions)
        keys = completed_grade_keys(connection, identity.workspace_id, attempt.id)
        assert [(item.attempt_id, item.grading_revision) for item in keys] == [(attempt.id, 1)]
        completed = completed_grade_witness(connection, identity.workspace_id, attempt.id, 1)
        assert completed.submission_sha256 == witness.submission_sha256
        assert completed.result.items[0].score is None
        assert all(item.solution_markdown is None for item in completed.result.items)
        assert connection.total_changes == 0


def test_submission_freeze_hook_failure_rolls_back_actual_submit_then_same_command_recovers(storage, monkeypatch):
    import services.api.app.application.evidence as evidence
    database, identity, _, assessment = storage
    attempt = start(storage)
    original = evidence.freeze_submission_prerequisites
    def fail_after_freezing(*args):
        original(*args)
        raise ApiError(503, "SYNTHETIC_FREEZE_FAILURE", "受控事务末端失败。")
    with monkeypatch.context() as patch:
        patch.setattr(evidence, "freeze_submission_prerequisites", fail_after_freezing)
        with pytest.raises(ApiError, match="受控事务末端失败"):
            assessment.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), "same-submit")
    assert assessment.get_attempt(identity, attempt.id).status == "active"
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM learning_events").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM learning_submission_bases").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM assessment_grade_jobs").fetchone()[0] == 0
        assert connection.execute("SELECT submission_json FROM attempts WHERE id=?", (attempt.id,)).fetchone()[0] is None
    done = assessment.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), "same-submit")
    assert done.status == "submitted"
    assert GradingWorker(database).run_once()


def test_grade_finalization_hook_failure_rolls_back_completed_terminal_event_and_grade(storage, monkeypatch):
    import services.api.app.application.evidence as evidence
    database, identity, _, _ = storage
    final = submitted(storage)
    worker = GradingWorker(database)
    lease = worker.claim()
    assert lease
    result, audit = worker.compute(lease)
    original = evidence.record_grade_finalized
    def fail_after_finalization(*args):
        original(*args)
        raise ApiError(503, "SYNTHETIC_FINALIZE_FAILURE", "受控证据事务末端失败。")
    with monkeypatch.context() as patch:
        patch.setattr(evidence, "record_grade_finalized", fail_after_finalization)
        with pytest.raises(ApiError, match="受控证据事务末端失败"):
            worker.finish(lease, result, audit)
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM grades").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM evidence").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM learning_grade_bindings").fetchone()[0] == 0
        assert connection.execute("SELECT COUNT(*) FROM learning_events").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM job_events WHERE job_id=? AND type='completed'", (lease.job_id,)).fetchone()[0] == 0
        assert connection.execute("SELECT status FROM jobs WHERE id=?", (lease.job_id,)).fetchone()[0] == "running"
    assert worker.finish(lease, result, audit)
    assert isinstance(GradingService(database).result(identity, final.id), AssessmentGradingResult)


@pytest.mark.parametrize("pending", [False, True])
def test_http_full_history_limit_counts_actual_utf8_bytes_and_never_deletes_old_grades(storage, pending):
    database, identity, fixture, _ = storage
    final = submitted(storage)
    worker = GradingWorker(database)
    service = GradingService(database)
    assert worker.run_once()
    author = real_author(database)
    request = review_request(fixture)
    request = request.model_copy(update={"item_reviews": [item.model_copy(update={
        "feedback_markdown": "真实人工反馈，中文与 🧠 保留。"}) for item in request.item_reviews]})
    service.regrade(author, final.id, request, "human-first")
    assert worker.run_once()
    if pending:
        service.regrade(author, final.id, review_request(fixture, revision=2), "human-next")
    endpoint = f"/api/v1/attempts/{final.id}/result"
    raw = immutable_rows(database)
    response = client_for(database).get(endpoint)
    assert response.status_code == (202 if pending else 200)
    size = len(response.content)
    assert size > len(response.text)  # the transport budget is bytes, not code points
    body = response.json()
    assert [entry["grading_revision"] for entry in body["history"]] == [1, 2]
    history = json.dumps(body["history"], ensure_ascii=False)
    assert all(name not in history for name in ("feedback_markdown", "solution_markdown", "accepted_answers", "private_pin"))
    assert len(body["history"][0]["items"]) == len(fixture.questions)
    assert all(item["score"] is None for item in body["history"][0]["items"])
    assert all(item["score"] == .5 for item in body["history"][1]["items"])
    assert client_for(database, budget=size).get(endpoint).content == response.content
    too_small = client_for(database, budget=size - 1).get(endpoint)
    assert too_small.status_code == 413 and too_small.json()["error"]["code"] == "GRADING_HISTORY_RESPONSE_LIMIT"
    assert "history" not in too_small.json()
    assert client_for(database).get(endpoint).content == response.content
    assert immutable_rows(database) == raw


@pytest.mark.parametrize("mode,scope", [("independent", "operation_help_only"), ("open_book", "academic"), ("assisted", "academic")])
def test_actual_current_review_permission_and_exact_materials_not_frozen_mode_guess(storage, mode, scope):
    database, identity, fixture, _ = storage
    final = submitted(storage, mode=mode)
    service = GradingService(database)
    pending = service.result(identity, final.id)
    assert pending.current_review_policy.tutor_scope == scope
    assert pending.current_review_policy.allow_materials and not pending.current_review_policy.allow_web
    assert pending.history == [] and pending.last_completed_result is None
    assert GradingWorker(database).run_once()
    result = service.result(identity, final.id)
    assert isinstance(result, AssessmentGradingResult)
    assert [entry.question_ref for entry in result.review_materials] == [reference(q) for q in fixture.questions]
    for entry in result.review_materials:
        assert entry.materials
        assert all(material.course_ref == reference(fixture.course) for material in entry.materials)
        assert all(material.lesson_ref == reference(fixture.lesson) for material in entry.materials)
        assert all(material.block_ref == reference(fixture.block) for material in entry.materials)
    # needs_review remains protected only for independent mode once grading completes.
    assert result.current_review_policy.tutor_scope == ("operation_help_only" if mode == "independent" else "academic")
