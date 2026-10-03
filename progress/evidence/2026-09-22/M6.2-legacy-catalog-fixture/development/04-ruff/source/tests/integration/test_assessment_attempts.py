"""Real learnpack imports, SQLite transactions and seven HTTP routes; no grades fabricated."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json

from fastapi.testclient import TestClient
import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256
from services.api.app.application.assessment import AssessmentService
from services.api.app.application.content import ContentService
from services.api.app.application.errors import ApiError
from services.api.app.application.imports import ImportService
from services.api.app.application.practice import PracticeService
from services.api.app.assessment_dto import AssessmentAttemptCreate
from services.api.app.import_dto import ImportCommitRequest
from services.api.app.infrastructure.assessment_repository import AssessmentRepository
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database, utc_now
from services.api.app.infrastructure.import_worker import ImportWorker
from services.api.app.infrastructure.security import SessionIdentity, issue_bootstrap_code
from services.api.app.main import create_app
from services.api.app.practice_dto import PracticeSessionCreate, PracticeSolutionRequest
from tests.assessment_fixtures import assessment_fixture


def import_fixture(database, identity, fixture, key):
    ingestion = ImportService(database)
    author = replace(identity, role="author")
    staged = ingestion.stage(author, data=fixture.archive, filename="synthetic.learnpack.zip", kind="learnpack", key=key)
    worker = ImportWorker(database)
    try:
        assert worker.run_once()
        preview = ingestion.preview(author, staged.import_id)
        assert preview.status == "preview_ready"
        ingestion.commit(author, staged.import_id, ImportCommitRequest(expected_input_sha256=staged.input_sha256,
            accepted_warning_codes=sorted({item.code for item in preview.warnings if item.severity == "warning"}), id_mapping=[]), key + "-commit")
    finally:
        worker.stop()


@pytest.fixture
def storage(tmp_path):
    database = Database(Settings(data_dir=tmp_path / "data"))
    workspace = database.initialize()
    identity = SessionIdentity("session_assessment_test", workspace, "learner", "unused", "2099-01-01T00:00:00Z")
    fixture = assessment_fixture("assessment")
    import_fixture(database, identity, fixture, "source")
    return database, identity, fixture, AssessmentService(database)


def start(storage, *, mode="independent", key="start", fixture=None):
    _, identity, initial, service = storage
    fixture = fixture or initial
    return service.create_attempt(identity, fixture.assessment.id,
        AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode=mode), key)


def error_code(code, call):
    with pytest.raises(ApiError) as caught:
        call()
    assert caught.value.code == code
    return caught.value


def counts(database):
    names = ("attempts", "responses", "learning_events", "learning_progress", "outbox", "idempotency", "jobs", "grades", "evidence")
    with database.connect() as connection:
        return {name: connection.execute(f"SELECT COUNT(*) FROM {name}").fetchone()[0] for name in names}


def insert_answer(database, solution, *, digest=None):
    """Controlled version/corruption fixture, never a product approval workflow."""
    with database.transaction() as connection:
        connection.execute("INSERT INTO solutions(question_id,question_revision,solution_revision,private_json,sha256,review_status) VALUES(?,?,?,?,?,?)",
            (solution.question_ref.id, solution.question_ref.revision, solution.revision, canonical_bytes(solution).decode(),
             digest or metadata_sha256(solution), solution.review_status))


@pytest.mark.parametrize("mode", ["independent", "open_book", "assisted"])
def test_real_unreviewed_import_freezes_policy_answers_preflight_and_workspace_recovery(storage, mode):
    database, identity, fixture, service = storage
    catalog = service.list_assessments(identity, course_id=fixture.course.id)
    assert len(catalog.items) == 1 and catalog.items[0].preflight.startable
    assert catalog.items[0].preflight.course_refs == [reference(fixture.course)]
    before = counts(database)
    first = start(storage, mode=mode)
    assert first == start(storage, mode=mode)
    assert first.questions == list(fixture.questions) and first.status == "active" and first.revision == 1
    assert first.policy.mode == mode and first.policy.allow_web is False
    assert first.policy.allow_materials == (mode != "independent")
    assert first.policy.tutor_scope == ("academic" if mode == "assisted" else "operation_help_only")
    assert first.preflight.grading.status == "unreviewed" and first.preflight.grading.needs_review_count == 5
    assert first.grading_status == "not_graded" and first.preflight.prior_seen.status == "known"
    assert {item.state for item in first.preflight.prior_seen.questions} == {"unseen"}
    assert service.get_responses(identity, first.id).model_dump() == {"revision": 1, "responses": [], "saved_at": None}
    for secret in ("solution_revision", "private_pins", "accepted_answers", "solution_markdown", "rubric_markdown", "absolute_tolerance"):
        assert secret not in first.model_dump_json()
    with database.connect() as connection:
        record = AssessmentRepository(connection, identity.workspace_id).load(first.id)
        assert [pin.sha256 for pin in record.assignment.private_pins] == [metadata_sha256(answer) for answer in fixture.solutions]
        assert {row[0] for row in connection.execute("SELECT review_status FROM solutions")} == {"needs_review"}
    restarted = Database(database.settings)
    restarted.initialize()
    new_browser = replace(identity, id="session_reauthenticated", role="author")
    assert AssessmentService(restarted).get_attempt(new_browser, first.id) == first
    after = counts(database)
    assert after["attempts"] == before["attempts"] + 1
    assert after["learning_events"] == after["grades"] == after["evidence"] == 0


def test_full_response_snapshot_cas_replay_clear_and_terminal_readback(storage):
    database, identity, fixture, service = storage
    first = start(storage)
    responses = [dm.ResponseDraft(question_id=q.id, answer="中文 🧠", steps_markdown="条件 e\u0301") for q in fixture.questions]
    request = dm.ResponsesWrite(expected_revision=1, responses=responses)
    saved = service.save_responses(identity, first.id, request, "save")
    assert saved.revision == 2 and service.save_responses(identity, first.id, request, "save") == saved
    recovered = AssessmentService(Database(database.settings)).get_responses(identity, first.id)
    assert recovered.responses == responses and recovered.revision == 2 and recovered.saved_at is not None
    error_code("REVISION_CONFLICT", lambda: service.save_responses(identity, first.id, request, "stale"))
    error_code("IDEMPOTENCY_CONFLICT", lambda: service.save_responses(identity, first.id, dm.ResponsesWrite(expected_revision=2, responses=[]), "save"))
    service.save_responses(identity, first.id, dm.ResponsesWrite(expected_revision=2, responses=responses[:1]), "replace")
    assert service.get_responses(identity, first.id).responses == responses[:1]
    service.save_responses(identity, first.id, dm.ResponsesWrite(expected_revision=3, responses=[]), "clear")
    assert service.get_responses(identity, first.id).responses == []
    final = service.submit(identity, first.id, dm.AttemptSubmit(expected_revision=4), "submit")
    assert final.status == "submitted" and final.revision == 5
    assert service.get_responses(identity, first.id).responses == []
    assert service.get_responses(identity, first.id).revision == final.revision
    error_code("ATTEMPT_NOT_ACTIVE", lambda: service.save_responses(identity, first.id, dm.ResponsesWrite(expected_revision=5, responses=responses), "late"))


@pytest.mark.parametrize("case", ["duplicate", "unassigned"])
def test_invalid_assigned_responses_have_no_side_effect(storage, case):
    database, identity, fixture, service = storage
    first = start(storage)
    response = dm.ResponseDraft(question_id=fixture.questions[0].id if case == "duplicate" else "question_absent", answer="No mutation")
    before = counts(database)
    request = dm.ResponsesWrite(expected_revision=1, responses=[response, response] if case == "duplicate" else [response])
    assert error_code("SCHEMA_INVALID", lambda: service.save_responses(identity, first.id, request, "invalid")).status == 422
    assert counts(database) == before


def test_two_sqlite_connections_compete_for_whole_response_revision(storage):
    _, identity, fixture, service = storage
    first = start(storage)
    def save(text):
        try:
            return service.save_responses(identity, first.id, dm.ResponsesWrite(expected_revision=1,
                responses=[dm.ResponseDraft(question_id=fixture.questions[0].id, answer=text)]), text).revision
        except ApiError as error:
            return error.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save, ["localA", "localB"])) == [2, 412]
    assert service.get_responses(identity, first.id).responses[0].answer in {"localA", "localB"}


def test_submit_and_abandon_compete_once_and_never_reactivate(storage):
    database, identity, _, service = storage
    first = start(storage)
    def transition(name):
        try:
            return getattr(service, name)(identity, first.id, dm.AttemptSubmit(expected_revision=1), name).status
        except ApiError as error:
            return error.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(transition, ["submit", "abandon"]))
    assert 409 in outcomes
    assert ("submitted" in outcomes) != ("abandoned" in outcomes)
    current = service.get_attempt(identity, first.id)
    assert current.revision == 2
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM outbox WHERE event_type='assessment.grading.requested'").fetchone()[0] == int(current.status == "submitted")
        assert connection.execute("SELECT COUNT(*) FROM learning_events WHERE kind='test_submitted'").fetchone()[0] == int(current.status == "submitted")
    assert counts(database)["grades"] == counts(database)["evidence"] == 0


def test_submit_receipt_snapshot_event_outbox_and_one_real_job_are_atomic(storage):
    database, identity, fixture, service = storage
    first = start(storage)
    saved = service.save_responses(identity, first.id, dm.ResponsesWrite(expected_revision=1,
        responses=[dm.ResponseDraft(question_id=fixture.questions[0].id, answer="我的最后作答")]), "save")
    before = counts(database)
    request = dm.AttemptSubmit(expected_revision=saved.revision)
    submitted = service.submit(identity, first.id, request, "submit")
    assert service.submit(identity, first.id, request, "submit") == submitted
    error_code("IDEMPOTENCY_CONFLICT", lambda: service.submit(identity, first.id, dm.AttemptSubmit(expected_revision=3), "submit"))
    error_code("ATTEMPT_NOT_ACTIVE", lambda: service.abandon(identity, first.id, dm.AttemptSubmit(expected_revision=3), "abandon"))
    with database.connect() as connection:
        record = AssessmentRepository(connection, identity.workspace_id).load(first.id)
        assert record.submission is not None and record.submission.responses[0].answer == "我的最后作答"
        payload = json.loads(connection.execute("SELECT payload_json FROM learning_events WHERE event_id=?", (record.submission_event_id,)).fetchone()[0])
        assert payload["actor"] == "server" and payload["origin"] == "native" and payload["attempt_id"] == first.id
        assert payload["ref"] == reference(fixture.assessment).model_dump(mode="json")
        assert connection.execute("SELECT COUNT(*) FROM outbox WHERE event_type='assessment.grading.requested'").fetchone()[0] == 1
    assert counts(database)["jobs"] == before["jobs"] + 1
    assert counts(database)["grades"] == counts(database)["evidence"] == 0
    assert service.get_responses(identity, first.id).responses[0].answer == "我的最后作答"


def test_last_outbox_failure_rolls_back_submission_event_projection_and_receipt(storage):
    database, identity, _, service = storage
    first = start(storage)
    with database.transaction() as connection:
        connection.execute("CREATE TRIGGER test_fail_grading_request BEFORE INSERT ON outbox WHEN NEW.event_type='assessment.grading.requested' BEGIN SELECT RAISE(ABORT,'test-only atomic failure'); END")
    before = counts(database)
    error_code("ASSESSMENT_STORAGE_UNAVAILABLE", lambda: service.submit(identity, first.id, dm.AttemptSubmit(expected_revision=1), "retryable"))
    assert counts(database) == before
    assert service.get_attempt(identity, first.id).status == "active"
    with database.transaction() as connection:
        connection.execute("DROP TRIGGER test_fail_grading_request")
    assert service.submit(identity, first.id, dm.AttemptSubmit(expected_revision=1), "retryable").status == "submitted"


def test_own_active_create_replay_allowed_but_old_receipt_denied_under_other_active(storage):
    _, identity, fixture, service = storage
    first = start(storage)
    assert start(storage) == first
    service.abandon(identity, first.id, dm.AttemptSubmit(expected_revision=1), "abandon")
    second = start(storage, key="second")
    error_code("ASSESSMENT_ACTIVE", lambda: start(storage))
    error_code("ASSESSMENT_ACTIVE", lambda: service.get_attempt(identity, first.id))
    error_code("ASSESSMENT_ACTIVE", lambda: service.get_responses(identity, first.id))
    error_code("ASSESSMENT_ACTIVE", lambda: service.list_assessments(identity, course_id=fixture.course.id))
    assert service.get_attempt(identity, second.id) == second
    assert {item.state for item in second.preflight.prior_seen.questions} == {"seen"}
    assert {item.state for item in first.preflight.prior_seen.questions} == {"unseen"}


def test_missing_and_bad_private_pins_block_creation_but_remain_honest_preflight(storage):
    database, identity, _, service = storage
    missing = assessment_fixture("missing", profile="learner")
    import_fixture(database, identity, missing, "missing")
    item = next(item for item in service.list_assessments(identity).items if item.ref.id == missing.assessment.id)
    assert item.preflight.grading.missing_count == 5 and not item.preflight.startable
    before = counts(database)
    error_code("ASSESSMENT_ANSWER_UNAVAILABLE", lambda: start(storage, fixture=missing, key="missing-attempt"))
    assert counts(database) == before
    original = storage[2]
    broken = original.solutions[0].model_copy(update={"revision": 2})
    insert_answer(database, broken, digest="0" * 64)
    item = next(item for item in service.list_assessments(identity).items if item.ref.id == original.assessment.id)
    assert item.preflight.grading.damaged_count == 1 and not item.preflight.startable
    error_code("CONTENT_HASH_MISMATCH", lambda: start(storage, key="bad-attempt"))


def test_new_answer_revision_does_not_replace_frozen_preflight_or_private_pin(storage):
    database, identity, fixture, service = storage
    first = start(storage, mode="open_book")
    changed = fixture.solutions[0].model_copy(update={"revision": 2, "review_status": "draft", "solution_markdown": "SYNTHETIC_SECOND_ANSWER"})
    insert_answer(database, changed)
    second = start(storage, mode="open_book", key="second")
    with database.connect() as connection:
        repository = AssessmentRepository(connection, identity.workspace_id)
        assert repository.load(first.id).assignment.private_pins[0].solution_revision == 1
        assert repository.load(second.id).assignment.private_pins[0].solution_revision == 2
    assert service.get_attempt(identity, first.id).preflight.grading.needs_review_count == 5
    assert second.preflight.grading.draft_count == 1 and second.preflight.grading.needs_review_count == 4
    revised_content = assessment_fixture("assessment", revision=2)
    ContentService(database).publish(identity.workspace_id, revised_content.public_objects, revised_content.bodies)
    assert service.get_attempt(identity, first.id).questions == list(fixture.questions)
    assert service.get_attempt(identity, first.id).assessment_ref == reference(fixture.assessment)
    error_code("ASSESSMENT_ANSWER_UNAVAILABLE", lambda: start(storage, mode="open_book", key="new-public", fixture=revised_content))


def test_timed_and_unallowed_mode_are_explicitly_unavailable(storage):
    database, identity, fixture, service = storage
    timed = assessment_fixture("timed", time_limit_seconds=60)
    import_fixture(database, identity, timed, "timed")
    item = next(item for item in service.list_assessments(identity).items if item.ref.id == timed.assessment.id)
    assert item.time_limit_seconds == 60 and "TIMED_ASSESSMENT_UNAVAILABLE" in item.preflight.start_block_reason_codes
    error_code("TIMED_ASSESSMENT_UNAVAILABLE", lambda: start(storage, fixture=timed))
    restricted = fixture.assessment.model_copy(update={"revision": 2, "allowed_modes": ["open_book"]})
    ContentService(database).publish(identity.workspace_id, [restricted], {})
    error_code("ASSESSMENT_MODE_UNAVAILABLE", lambda: service.create_attempt(identity, restricted.id,
        AssessmentAttemptCreate(assessment_ref=reference(restricted), mode="independent"), "unsupported-mode"))


def test_workspace_ownership_precedes_replay_and_is_stable_across_sessions(storage):
    database, identity, fixture, service = storage
    first = start(storage)
    with database.transaction() as connection:
        connection.execute("INSERT INTO workspace(id,title,created_at) VALUES('workspace_other','synthetic',?)", (utc_now(),))
    other = replace(identity, id="session_other", workspace_id="workspace_other", role="author")
    error_code("ATTEMPT_MISSING", lambda: service.get_attempt(other, first.id))
    error_code("ATTEMPT_MISSING", lambda: service.get_responses(other, first.id))
    error_code("REFERENCE_MISSING", lambda: service.create_attempt(other, fixture.assessment.id,
        AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode="independent"), "start"))


def test_pending_independent_protects_previously_cached_practice_solution(storage):
    database, identity, fixture, service = storage
    practice = PracticeService(database)
    session = practice.create_session(identity, PracticeSessionCreate(practice_ref=reference(fixture.practice)), "practice")
    request = PracticeSolutionRequest(question_id=fixture.questions[0].id, expected_revision=1)
    assert practice.solution(identity, session.id, request, "private-answer").solution_markdown
    attempt = start(storage)
    error_code("ASSESSMENT_ACTIVE", lambda: practice.solution(identity, session.id, request, "private-answer"))
    submitted = service.submit(identity, attempt.id, dm.AttemptSubmit(expected_revision=1), "submit")
    assert submitted.grading_status == "pending"
    error_code("ASSESSMENT_ANSWER_PROTECTED", lambda: practice.solution(identity, session.id, request, "private-answer"))


def test_original_seven_http_routes_preserve_snapshots_with_real_queued_grading(storage):
    database, _, fixture, _ = storage
    application = create_app(database.settings)
    with TestClient(application) as client:
        client.base_url = "http://127.0.0.1:8765"
        headers = {"Origin": "http://127.0.0.1:8765"}
        connected = client.post("/api/v1/session/bootstrap", json={"one_time_code": issue_bootstrap_code(database)}, headers=headers)
        assert connected.status_code == 200
        headers["X-CSRF-Token"] = connected.json()["csrf_token"]
        page = client.get("/api/v1/assessments", params={"course_id": fixture.course.id})
        assert page.status_code == 200 and len(page.json()["items"]) == 1
        created = client.post(f"/api/v1/assessments/{fixture.assessment.id}/attempts",
            json={"assessment_ref": reference(fixture.assessment).model_dump(mode="json"), "mode": "independent"}, headers={**headers, "Idempotency-Key": "http-start"})
        assert created.status_code == 201, created.text
        attempt_id = created.json()["id"]
        assert client.get(f"/api/v1/attempts/{attempt_id}").json() == created.json()
        assert client.get(f"/api/v1/attempts/{attempt_id}/responses").json() == {"revision": 1, "responses": [], "saved_at": None}
        saved = client.put(f"/api/v1/attempts/{attempt_id}/responses", json={"expected_revision": 1,
            "responses": [{"question_id": fixture.questions[0].id, "answer": "我的 HTTP 作答"}]}, headers={**headers, "Idempotency-Key": "http-save"})
        assert saved.status_code == 200 and saved.json()["revision"] == 2
        submitted = client.post(f"/api/v1/attempts/{attempt_id}/submit", json={"expected_revision": 2}, headers={**headers, "Idempotency-Key": "http-submit"})
        assert submitted.status_code == 202 and submitted.json()["status"] == "submitted"
        assert client.get(f"/api/v1/attempts/{attempt_id}/responses").json()["responses"][0]["answer"] == "我的 HTTP 作答"
        result = client.get(f"/api/v1/attempts/{attempt_id}/result")
        assert result.status_code in {200, 202}
        if result.status_code == 202:
            assert result.json()["status"] in {"queued", "running"}
        else:
            assert result.json()["status"] == "needs_review"
            assert all(item["score"] is None for item in result.json()["items"])
        another = client.post(f"/api/v1/assessments/{fixture.assessment.id}/attempts",
            json={"assessment_ref": reference(fixture.assessment).model_dump(mode="json"), "mode": "open_book"}, headers={**headers, "Idempotency-Key": "http-second"})
        abandoned = client.post(f"/api/v1/attempts/{another.json()['id']}/abandon", json={"expected_revision": 1}, headers={**headers, "Idempotency-Key": "http-abandon"})
        assert abandoned.status_code == 200 and abandoned.json()["status"] == "abandoned"
        assert abandoned.headers["cache-control"] == "no-store"


def test_course_witness_uses_one_exact_historical_concept_set_and_never_unions_versions(storage):
    database, identity, fixture, service = storage
    content = ContentService(database)
    second_concept = dm.Concept(id="concept_second", revision=1, title="另一概念", skill_dimensions=["recall"])
    course_second = fixture.course.model_copy(update={"revision": 2, "concept_refs": [reference(second_concept)]})
    mixed_question = fixture.questions[0].model_copy(update={"revision": 2, "concept_ids": [fixture.concept.id, second_concept.id]})
    mixed_blueprint = fixture.assessment.model_copy(update={"revision": 2, "question_refs": [reference(mixed_question)]})
    content.publish(identity.workspace_id, [second_concept, course_second, mixed_question, mixed_blueprint], {})
    # No single historical Course contains both A and B, though their union does.
    listed = service.list_assessments(identity, course_id=fixture.course.id)
    assert [item.ref for item in listed.items] == [reference(fixture.assessment)]
    assert {item.ref.revision for item in service.list_assessments(identity).items} == {1, 2}
    course_both = fixture.course.model_copy(update={"revision": 3, "concept_refs": [reference(fixture.concept), reference(second_concept)]})
    other_course = course_both.model_copy(update={"id": "course_other", "revision": 1})
    content.publish(identity.workspace_id, [course_both, other_course], {})
    mixed = next(item for item in service.list_assessments(identity, course_id=fixture.course.id).items if item.ref.revision == 2)
    assert mixed.preflight.course_refs == [reference(course_both), reference(other_course)]
    assert [item.ref.revision for item in service.list_assessments(identity, course_id="course_other").items] == [1, 2]
    # Same concept ID at a later revision is not the exact old course dependency.
    later_concept = fixture.concept.model_copy(update={"revision": 2, "title": "概念条件已更新"})
    later_question = fixture.questions[0].model_copy(update={"revision": 3})
    later_blueprint = fixture.assessment.model_copy(update={"revision": 3, "question_refs": [reference(later_question)]})
    content.publish(identity.workspace_id, [later_concept, later_question, later_blueprint], {})
    assert [item.ref.revision for item in service.list_assessments(identity, course_id=fixture.course.id).items] == [1, 2]
    global_latest = next(item for item in service.list_assessments(identity).items if item.ref.revision == 3)
    assert global_latest.preflight.course_refs == []
    assert global_latest.preflight.target_concept_refs == [reference(later_concept)]


def test_pagination_includes_old_same_id_revisions_and_reports_recent_attempt_truncation(storage):
    database, identity, fixture, service = storage
    newer = fixture.assessment.model_copy(update={"revision": 2, "title": "第二修订"})
    ContentService(database).publish(identity.workspace_id, [newer], {})
    first = service.list_assessments(identity, limit=1)
    assert first.items[0].ref == reference(fixture.assessment) and first.next_cursor is not None
    second = service.list_assessments(identity, limit=1, cursor=first.next_cursor)
    assert second.items[0].ref == reference(newer) and second.next_cursor is None
    error_code("SCHEMA_INVALID", lambda: service.list_assessments(identity, limit=2, cursor=first.next_cursor))
    error_code("SCHEMA_INVALID", lambda: service.list_assessments(identity, limit=1, cursor=first.next_cursor + "bad"))
    for index in range(11):
        start(storage, mode="open_book", key=f"attempt-{index}")
    page = service.list_assessments(identity, limit=1)
    assert len(page.items[0].recent_attempts) == 10 and page.items[0].recent_attempts_truncated
    with database.connect() as connection:
        assert {item.id for item in page.items[0].recent_attempts} <= set(AssessmentRepository(connection, identity.workspace_id).history_ids())


def test_hashless_legacy_attempt_fails_closed_without_guessing_current(storage):
    database, identity, fixture, service = storage
    with database.transaction() as connection:
        connection.execute("INSERT INTO attempts(id,workspace_id,assessment_id,assessment_revision,mode,policy_json,question_refs_json,solution_refs_private_json,status,revision,created_at) "
            "VALUES('attempt_legacy',?,?,1,'open_book',?,'[]','[]','active',1,?)",
            (identity.workspace_id, fixture.assessment.id, canonical_bytes(dm.PolicySnapshot(mode="open_book", tutor_scope="operation_help_only", allow_web=False, allow_materials=True)).decode(), utc_now()))
    before = counts(database)
    error_code("ASSESSMENT_SNAPSHOT_INVALID", lambda: service.get_attempt(identity, "attempt_legacy"))
    error_code("ASSESSMENT_SNAPSHOT_INVALID", lambda: service.get_responses(identity, "attempt_legacy"))
    assert counts(database) == before


def test_two_concurrent_independent_starts_have_only_one_actual_allocation(storage):
    database, _, _, _ = storage
    def create(key):
        try:
            return start(storage, key=key).status
        except ApiError as error:
            return error.code
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(create, ["one", "two"]))
    assert sorted(outcomes) == ["ASSESSMENT_ACTIVE", "active"]
    with database.connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM attempts WHERE status='active'").fetchone()[0] == 1
    assert counts(database)["learning_events"] == 0


def test_corrupt_frozen_preflight_is_rejected_instead_of_reconstructed_from_current(storage):
    database, identity, _, service = storage
    first = start(storage, mode="open_book")
    # Explicit storage-fault injection; these writes are impossible through the
    # public API and normally rejected by the migration's immutable trigger.
    with database.transaction() as connection:
        connection.execute("DROP TRIGGER immutable_assessment_assignment")
        connection.execute("UPDATE attempts SET preflight_sha256=? WHERE id=?", ("0" * 64, first.id))
    before = counts(database)
    error_code("ASSESSMENT_SNAPSHOT_INVALID", lambda: service.get_attempt(identity, first.id))
    error_code("ASSESSMENT_SNAPSHOT_INVALID", lambda: service.get_responses(identity, first.id))
    assert counts(database) == before


@pytest.mark.parametrize("case", ["unknown_query", "duplicate_query", "large_limit", "duplicate_header", "unknown_body", "wrong_ref_entity", "private_field"])
def test_http_rejects_unknown_duplicate_and_private_contract_inputs_without_mutation(storage, case):
    database, _, fixture, _ = storage
    app = create_app(database.settings)
    with TestClient(app, base_url="http://127.0.0.1:8765") as client:
        headers = {"Origin": "http://127.0.0.1:8765"}
        authenticated = client.post("/api/v1/session/bootstrap", json={"one_time_code": issue_bootstrap_code(database)}, headers=headers)
        assert authenticated.status_code == 200
        headers.update({"X-CSRF-Token": authenticated.json()["csrf_token"], "Idempotency-Key": "strict-create"})
        before = counts(database)
        if case in {"unknown_query", "duplicate_query", "large_limit"}:
            query = {"unknown_query": "?unknown=1", "duplicate_query": "?limit=1&limit=2", "large_limit": "?limit=101"}[case]
            response = client.get("/api/v1/assessments" + query)
        else:
            payload = {"assessment_ref": reference(fixture.assessment).model_dump(mode="json"), "mode": "open_book"}
            if case == "unknown_body":
                payload["workspace_id"] = "workspace_fake"
            if case == "private_field":
                payload["solution_revision"] = 1
            if case == "wrong_ref_entity":
                payload["assessment_ref"]["entity"] = "question"
            supplied_headers = list(headers.items()) + [("Idempotency-Key", "other")] if case == "duplicate_header" else headers
            response = client.post(f"/api/v1/assessments/{fixture.assessment.id}/attempts", json=payload, headers=supplied_headers)
        assert response.status_code == 422, response.text
        assert counts(database) == before


def test_expired_creation_key_reuses_new_receipt_instance_without_permanent_allocation_lock(storage):
    database, identity, fixture, service = storage
    first = start(storage)
    service.abandon(identity, first.id, dm.AttemptSubmit(expected_revision=1), "abandon")
    route = f"POST /assessments/{fixture.assessment.id}/attempts"
    with database.transaction() as connection:
        original = dict(connection.execute("SELECT * FROM assessment_receipts WHERE workspace_id=? AND route=? AND key='start'", (identity.workspace_id, route)).fetchone())
        connection.execute("UPDATE idempotency SET expires_at='2000-01-01T00:00:00Z' WHERE actor=? AND route=? AND key='start'", (identity.workspace_id, route))
    second = start(storage)
    assert second.id != first.id and second.status == "active"
    assert start(storage) == second
    with database.connect() as connection:
        binding = dict(connection.execute("SELECT * FROM assessment_receipts WHERE workspace_id=? AND route=? AND key='start'", (identity.workspace_id, route)).fetchone())
        assert binding["attempt_id"] == second.id and binding["receipt_created_at"] != original["receipt_created_at"]
        assert binding["request_sha256"] == original["request_sha256"]
        assert binding["assignment_sha256"] != original["assignment_sha256"]
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []


def test_historical_receipt_revision_status_survive_submit_and_restart_without_rewriting(storage):
    database, identity, fixture, service = storage
    first = start(storage)
    request = dm.ResponsesWrite(expected_revision=1, responses=[dm.ResponseDraft(question_id=fixture.questions[0].id, answer="persisted")])
    saved = service.save_responses(identity, first.id, request, "save")
    submitted = service.submit(identity, first.id, dm.AttemptSubmit(expected_revision=2), "submit")
    restarted = AssessmentService(Database(database.settings))
    before = counts(database)
    assert start(storage) == first
    assert restarted.save_responses(identity, first.id, request, "save") == saved
    assert restarted.submit(identity, first.id, dm.AttemptSubmit(expected_revision=2), "submit") == submitted
    assert restarted.get_attempt(identity, first.id) == submitted
    assert counts(database) == before


@pytest.mark.parametrize("damage", ["different_target", "unknown_field", "non_object", "missing_binding", "different_instance"])
def test_save_cached_receipt_corruption_fails_closed_before_body_return(storage, damage):
    database, identity, fixture, service = storage
    first = start(storage)
    request = dm.ResponsesWrite(expected_revision=1, responses=[dm.ResponseDraft(question_id=fixture.questions[0].id, answer="saved")])
    saved = service.save_responses(identity, first.id, request, "save")
    route = f"PUT /attempts/{first.id}/responses"
    with database.transaction() as connection:
        result = saved.model_dump(mode="json")
        if damage == "different_target":
            result["id"] = "attempt_unrelated"
        elif damage == "unknown_field":
            result["untrusted_extra"] = "unrelated"
        elif damage == "non_object":
            result = []
        elif damage == "missing_binding":
            connection.execute("DELETE FROM assessment_receipts WHERE workspace_id=? AND route=? AND key='save'", (identity.workspace_id, route))
        else:
            connection.execute("UPDATE idempotency SET created_at='2000-01-01T00:00:00Z' WHERE actor=? AND route=? AND key='save'", (identity.workspace_id, route))
        if damage in {"different_target", "unknown_field", "non_object"}:
            connection.execute("UPDATE idempotency SET result_json=? WHERE actor=? AND route=? AND key='save'", (canonical_bytes(result).decode(), identity.workspace_id, route))
    before = counts(database)
    error_code("ASSESSMENT_SNAPSHOT_INVALID", lambda: service.save_responses(identity, first.id, request, "save"))
    assert service.get_attempt(identity, first.id) == saved
    assert counts(database) == before


def test_receipt_sealing_failure_rolls_back_submission_event_and_outbox_together(storage):
    database, identity, _, service = storage
    first = start(storage)
    with database.transaction() as connection:
        connection.execute("CREATE TRIGGER test_fail_receipt BEFORE INSERT ON assessment_receipts WHEN NEW.key='submit-final' BEGIN SELECT RAISE(ABORT,'test-only receipt failure'); END")
        receipts = connection.execute("SELECT COUNT(*) FROM assessment_receipts").fetchone()[0]
    before = counts(database)
    error_code("ASSESSMENT_STORAGE_UNAVAILABLE", lambda: service.submit(identity, first.id, dm.AttemptSubmit(expected_revision=1), "submit-final"))
    assert counts(database) == before
    assert service.get_attempt(identity, first.id) == first
    with database.transaction() as connection:
        assert connection.execute("SELECT COUNT(*) FROM assessment_receipts").fetchone()[0] == receipts
        connection.execute("DROP TRIGGER test_fail_receipt")
    submitted = service.submit(identity, first.id, dm.AttemptSubmit(expected_revision=1), "submit-final")
    assert submitted.status == "submitted" and submitted.revision == 2
    assert service.submit(identity, first.id, dm.AttemptSubmit(expected_revision=1), "submit-final") == submitted
