"""Real import, SQLite and HTTP practice history; no deterministic grades claimed."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import sqlite3

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256
from services.api.app.application.content import ContentService
from services.api.app.application.errors import ApiError
from services.api.app.application.imports import ImportService
from services.api.app.application.practice import HINT_RULE_VERSION, PracticeService
from services.api.app.application.practice_content import PracticeContent
from services.api.app.import_dto import ImportCommitRequest
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database, utc_now
from services.api.app.infrastructure.import_worker import ImportWorker
from services.api.app.infrastructure.security import SessionIdentity, issue_bootstrap_code
from services.api.app.interfaces.boundary import install_boundary
from services.api.app.interfaces.http import create_router
from services.api.app.interfaces.practice_http import create_practice_router
from services.api.app.practice_dto import PracticeHintRequest, PracticeSessionCreate, PracticeSolutionRequest, PracticeSubmitRequest
from tests.practice_fixtures import practice_fixture


@pytest.fixture
def storage(tmp_path):
    database = Database(Settings(data_dir=tmp_path / "data"))
    workspace = database.initialize()
    identity = SessionIdentity("session_practice_test", workspace, "learner", "unused", "2099-01-01T00:00:00Z")
    fixture = practice_fixture("practice")
    ingestion = ImportService(database)
    author = replace(identity, role="author")
    staged = ingestion.stage(author, data=fixture.archive, filename="synthetic.learnpack.zip", kind="learnpack", key="source")
    worker = ImportWorker(database)
    try:
        assert worker.run_once()
        preview = ingestion.preview(author, staged.import_id)
        assert preview.status == "preview_ready"
        ingestion.commit(author, staged.import_id, ImportCommitRequest(expected_input_sha256=staged.input_sha256,
            accepted_warning_codes=sorted({warning.code for warning in preview.warnings if warning.severity == "warning"}), id_mapping=[]), "commit")
        yield database, identity, fixture, PracticeService(database)
    finally:
        worker.stop()


def start(storage, *, key="create"):
    _, identity, fixture, service = storage
    return service.create_session(identity, PracticeSessionCreate(practice_ref=reference(fixture.practice)), key)


def insert_new_solution(database, solution):
    """Controlled test-only publication of a new answer version, not a product API."""
    with database.transaction() as connection:
        connection.execute("INSERT INTO solutions(question_id,question_revision,solution_revision,private_json,sha256,review_status) VALUES(?,?,?,?,?,?)",
            (solution.question_ref.id, solution.question_ref.revision, solution.revision,
             canonical_bytes(solution).decode(), metadata_sha256(solution), solution.review_status))


def counts(database):
    tables = ("practice_sessions", "practice_responses", "practice_exposures", "exposures", "learning_events", "learning_progress", "idempotency", "outbox", "evidence", "grades")
    with database.connect() as connection:
        return {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in tables}


def error_code(code, call):
    with pytest.raises(ApiError) as caught:
        call()
    assert caught.value.code == code
    return caught.value


def test_real_author_import_creates_only_public_session_and_freezes_five_private_versions(storage):
    database, identity, fixture, service = storage
    first = start(storage)
    assert first == start(storage)
    assert first.revision == 1 and first.status == "active" and first.responses == [] and first.results is None
    assert first.questions == list(fixture.questions)
    assert first.assisted is False and first.exposure_event_ids == []
    assert [item.highest_hint_level for item in first.assistance] == [0] * 5
    public = first.model_dump_json()
    for field in ("accepted_answers", "solution_revision", "grading_kind", "absolute_tolerance", "rubric_markdown", "solution_refs"):
        assert field not in public
    with database.connect() as connection:
        row = connection.execute("SELECT * FROM practice_sessions WHERE id=?", (first.id,)).fetchone()
        frozen = json.loads(row["solution_refs_json"])
        assert [item["sha256"] for item in frozen] == [metadata_sha256(solution) for solution in fixture.solutions]
        assert [item["solution_revision"] for item in frozen] == [1] * 5
        assert {item[0] for item in connection.execute("SELECT review_status FROM solutions")} == {"needs_review"}
    restarted = Database(database.settings)
    restarted.initialize()
    assert PracticeService(restarted).get_session(identity, first.id) == first
    assert counts(database)["learning_events"] == counts(database)["exposures"] == 0


def test_old_question_and_solution_versions_remain_exact_after_new_content_and_answers(storage):
    database, identity, fixture, service = storage
    first = start(storage)
    revised_answer = dm.SolutionPrivate.model_validate({**fixture.solutions[0].model_dump(), "revision": 2, "solution_markdown": "SYNTHETIC_NEW_PRIVATE_EXPLANATION"})
    insert_new_solution(database, revised_answer)
    old_answer = service.solution(identity, first.id, PracticeSolutionRequest(question_id=fixture.questions[0].id, expected_revision=1), "old-answer")
    assert old_answer.solution_markdown == fixture.solutions[0].solution_markdown
    later = start(storage, key="later")
    assert service.solution(identity, later.id, PracticeSolutionRequest(question_id=fixture.questions[0].id, expected_revision=1), "new-answer").solution_markdown == revised_answer.solution_markdown
    revised = practice_fixture("practice", revision=2)
    ContentService(database).publish(identity.workspace_id, revised.public_objects, revised.bodies)
    assert service.get_session(identity, first.id).questions == list(fixture.questions)
    latest = service.create_session(identity, PracticeSessionCreate(practice_ref=reference(revised.practice)), "new-questions")
    assert latest.questions == list(revised.questions)
    error_code("SOLUTION_UNAVAILABLE", lambda: service.solution(identity, latest.id,
        PracticeSolutionRequest(question_id=revised.questions[0].id, expected_revision=1), "no-revised-answer"))


def test_missing_solution_is_frozen_unavailable_even_when_one_is_published_later(storage):
    database, identity, _, service = storage
    fixture = practice_fixture("missing", profile="learner")
    ContentService(database).publish(identity.workspace_id, fixture.public_objects, fixture.bodies)
    first = service.create_session(identity, PracticeSessionCreate(practice_ref=reference(fixture.practice)), "missing")
    before = counts(database)
    request = PracticeSolutionRequest(question_id=fixture.questions[0].id, expected_revision=1)
    error_code("SOLUTION_UNAVAILABLE", lambda: service.solution(identity, first.id, request, "unavailable"))
    assert counts(database) == before
    insert_new_solution(database, fixture.solutions[0])
    error_code("SOLUTION_UNAVAILABLE", lambda: service.solution(identity, first.id, request, "still-unavailable"))
    assert service.get_session(identity, first.id).revision == 1
    later = service.create_session(identity, PracticeSessionCreate(practice_ref=reference(fixture.practice)), "missing-new")
    assert service.solution(identity, later.id, request, "available").review_status == "needs_review"


def test_full_response_snapshot_cas_replay_clear_and_restart(storage):
    database, identity, fixture, service = storage
    first = start(storage)
    responses = [dm.ResponseDraft(question_id=question.id, answer="合成作答 🧠", steps_markdown="保留条件 e\u0301") for question in fixture.questions]
    request = dm.ResponsesWrite(expected_revision=1, responses=responses)
    saved = service.save_responses(identity, first.id, request, "save")
    assert saved.revision == 2 and saved.saved_at.endswith("Z")
    assert service.save_responses(identity, first.id, request, "save") == saved
    assert PracticeService(Database(database.settings)).get_session(identity, first.id).responses == responses
    error_code("REVISION_CONFLICT", lambda: service.save_responses(identity, first.id, request, "stale"))
    error_code("IDEMPOTENCY_CONFLICT", lambda: service.save_responses(identity, first.id, dm.ResponsesWrite(expected_revision=2, responses=[]), "save"))
    service.save_responses(identity, first.id, dm.ResponsesWrite(expected_revision=2, responses=responses[:1]), "replace")
    assert service.get_session(identity, first.id).responses == responses[:1]
    service.save_responses(identity, first.id, dm.ResponsesWrite(expected_revision=3, responses=[]), "clear")
    assert service.get_session(identity, first.id).responses == []
    assert counts(database)["learning_events"] == 0


@pytest.mark.parametrize("invalid_kind", ["duplicate", "unassigned"])
def test_response_snapshot_rejects_duplicate_and_unassigned_questions_without_mutation(storage, invalid_kind):
    database, identity, fixture, service = storage
    first = start(storage)
    response = dm.ResponseDraft(question_id=fixture.questions[0].id if invalid_kind == "duplicate" else "question_not_assigned", answer="No write")
    before = counts(database)
    request = dm.ResponsesWrite(expected_revision=1, responses=[response, response] if invalid_kind == "duplicate" else [response])
    failure = error_code("SCHEMA_INVALID" if invalid_kind == "duplicate" else "QUESTION_NOT_ASSIGNED", lambda: service.save_responses(identity, first.id, request, "invalid"))
    assert failure.status == 422 and counts(database) == before
    assert service.get_session(identity, first.id).revision == 1


def test_two_real_connections_compete_for_same_response_revision_without_silent_overwrite(storage):
    _, identity, fixture, service = storage
    first = start(storage)
    def write(text):
        try:
            return service.save_responses(identity, first.id,
                dm.ResponsesWrite(expected_revision=1, responses=[dm.ResponseDraft(question_id=fixture.questions[0].id, answer=text)]), text).revision
        except ApiError as error:
            return error.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(write, ["candidate-A", "candidate-B"]))
    assert sorted(outcomes) == [2, 412]
    assert service.get_session(identity, first.id).responses[0].answer in {"candidate-A", "candidate-B"}


def test_submit_freezes_saved_attempt_with_null_scores_and_no_solution_even_after_later_help(storage):
    database, identity, fixture, service = storage
    first = start(storage)
    saved = service.save_responses(identity, first.id, dm.ResponsesWrite(expected_revision=1,
        responses=[dm.ResponseDraft(question_id=fixture.questions[0].id, answer=fixture.solutions[0].accepted_answers[0])]), "saved")
    request = PracticeSubmitRequest(expected_revision=saved.revision)
    submitted = service.submit(identity, first.id, request, "submit")
    assert submitted.evidence_label == "practice" and not submitted.assisted
    assert len(submitted.results) == 5 and all(item.status == "needs_review" and item.score is None and item.solution_markdown is None for item in submitted.results)
    assert service.submit(identity, first.id, request, "submit") == submitted
    with database.connect() as connection:
        immutable = connection.execute("SELECT submission_json,submission_sha256 FROM practice_sessions WHERE id=?", (first.id,)).fetchone()
        assert [row[0] for row in connection.execute("SELECT kind FROM learning_events")] == ["practice_submitted"]
    error_code("PRACTICE_NOT_ACTIVE", lambda: service.save_responses(identity, first.id,
        dm.ResponsesWrite(expected_revision=submitted.revision, responses=[]), "post-submit-save"))
    error_code("PRACTICE_NOT_ACTIVE", lambda: service.submit(identity, first.id, PracticeSubmitRequest(expected_revision=submitted.revision), "submit-again"))
    hint = service.hint(identity, first.id, PracticeHintRequest(question_id=fixture.questions[0].id, expected_revision=submitted.revision, level=1), "after-submit-hint")
    revealed = service.solution(identity, first.id, PracticeSolutionRequest(question_id=fixture.questions[0].id, expected_revision=hint.revision), "after-submit-answer")
    restored = service.get_session(identity, first.id)
    assert restored.status == "submitted" and restored.results == submitted.results and restored.assisted
    assert restored.revision == revealed.revision and len(restored.exposure_event_ids) == 2
    with database.connect() as connection:
        assert tuple(connection.execute("SELECT submission_json,submission_sha256 FROM practice_sessions WHERE id=?", (first.id,)).fetchone()) == tuple(immutable)
        assert connection.execute("PRAGMA foreign_key_check").fetchone() is None
    assert counts(database)["grades"] == counts(database)["evidence"] == 0


def test_empty_attempt_submission_is_needs_review_not_zero(storage):
    _, identity, _, service = storage
    first = start(storage)
    result = service.submit(identity, first.id, PracticeSubmitRequest(expected_revision=1), "empty-submit")
    assert all(item.score is None and item.status == "needs_review" for item in result.results)
    assert service.get_session(identity, first.id).responses == []


def test_all_five_question_kinds_get_versioned_public_rules_without_private_lookup(storage, monkeypatch):
    database, identity, fixture, service = storage
    first = start(storage)
    def forbidden(*args):
        raise AssertionError("Rule hints must not read private answers")
    monkeypatch.setattr(PracticeContent, "solution", forbidden)
    revision = 1
    for question in fixture.questions:
        for level in (1, 2, 3):
            request = PracticeHintRequest(question_id=question.id, expected_revision=revision, level=level)
            result = service.hint(identity, first.id, request, f"hint-{question.id}-{level}")
            assert result.source == "rules" and result.rule_version == HINT_RULE_VERSION and result.level == level
            assert result.markdown and result.revision == revision + 1
            revision = result.revision
    restored = service.get_session(identity, first.id)
    assert restored.assisted and len(restored.exposure_event_ids) == 15
    assert all(item.highest_hint_level == 3 and not item.solution_revealed for item in restored.assistance)
    assert counts(database)["learning_events"] == counts(database)["exposures"] == 15
    again = service.hint(identity, first.id, PracticeHintRequest(question_id=fixture.questions[0].id, expected_revision=revision, level=2), "already-revealed-level")
    assert again.revision == revision and counts(database)["exposures"] == 15


def test_explicit_solution_is_guarded_deduplicated_and_displays_unapproved_review_state(storage):
    database, identity, fixture, service = storage
    first = start(storage)
    request = PracticeSolutionRequest(question_id=fixture.questions[0].id, expected_revision=1)
    result = service.solution(identity, first.id, request, "reveal")
    assert result.review_status == "needs_review" and result.solution_markdown == fixture.solutions[0].solution_markdown
    assert service.solution(identity, first.id, request, "reveal") == result
    again = service.solution(identity, first.id, PracticeSolutionRequest(question_id=request.question_id, expected_revision=2), "reveal-again")
    assert again == result
    restored = service.get_session(identity, first.id)
    assert restored.assistance[0].solution_revealed and restored.assisted
    assert result.solution_markdown not in restored.model_dump_json()
    assert counts(database)["exposures"] == counts(database)["learning_events"] == 1


@pytest.mark.parametrize("operation", ["save", "hint", "solution", "submit"])
def test_transaction_fault_rolls_back_all_practice_and_learning_side_effects(storage, operation):
    database, identity, fixture, service = storage
    first = start(storage)
    if operation == "save":
        service.save_responses(identity, first.id, dm.ResponsesWrite(expected_revision=1,
            responses=[dm.ResponseDraft(question_id=fixture.questions[0].id, answer="previous durable draft")]), "prior-save")
        first = service.get_session(identity, first.id)
    target = {"save": "BEFORE INSERT ON practice_responses", "hint": "BEFORE INSERT ON practice_exposures", "solution": "BEFORE INSERT ON practice_exposures", "submit": "BEFORE UPDATE OF submission_json ON practice_sessions"}[operation]
    with database.transaction() as connection:
        connection.execute(f"CREATE TRIGGER synthetic_failure {target} BEGIN SELECT RAISE(ABORT,'synthetic transaction failure'); END")
    before = counts(database)
    calls = {
        "save": lambda: service.save_responses(identity, first.id, dm.ResponsesWrite(expected_revision=first.revision, responses=[dm.ResponseDraft(question_id=fixture.questions[0].id, answer="candidate")]), "fault"),
        "hint": lambda: service.hint(identity, first.id, PracticeHintRequest(question_id=fixture.questions[0].id, expected_revision=1, level=1), "fault"),
        "solution": lambda: service.solution(identity, first.id, PracticeSolutionRequest(question_id=fixture.questions[0].id, expected_revision=1), "fault"),
        "submit": lambda: service.submit(identity, first.id, PracticeSubmitRequest(expected_revision=1), "fault"),
    }
    assert error_code("PRACTICE_STORAGE_UNAVAILABLE", calls[operation]).status == 503
    assert counts(database) == before
    assert service.get_session(identity, first.id) == first


@pytest.mark.parametrize("role", ["learner", "author"])
def test_active_independent_guard_precedes_all_queries_writes_and_private_replay(storage, role):
    database, identity, fixture, service = storage
    first = start(storage)
    request = PracticeSolutionRequest(question_id=fixture.questions[0].id, expected_revision=1)
    service.solution(identity, first.id, request, "reveal-before-guard")
    assessment = dm.AssessmentBlueprint(id="assessment_guard", revision=1, title="Guard", question_refs=[reference(fixture.questions[0])], allowed_modes=["independent"])
    ContentService(database).publish(identity.workspace_id, [assessment], {})
    policy = dm.PolicySnapshot(mode="independent", tutor_scope="operation_help_only", allow_web=False, allow_materials=False)
    with database.transaction() as connection:
        connection.execute("INSERT INTO attempts(id,workspace_id,assessment_id,assessment_revision,mode,policy_json,question_refs_json,solution_refs_private_json,status,revision,created_at) VALUES(?,?,?,1,'independent',?,'[]','[]','active',1,?)",
            ("attempt_practice_guard", identity.workspace_id, assessment.id, canonical_bytes(policy).decode(), utc_now()))
    identity = replace(identity, role=role)
    before = counts(database)
    calls = [lambda: service.list_sets(identity), lambda: service.get_session(identity, first.id),
        lambda: service.create_session(identity, PracticeSessionCreate(practice_ref=reference(fixture.practice)), "create"),
        lambda: service.save_responses(identity, first.id, dm.ResponsesWrite(expected_revision=2, responses=[]), "guard-save"),
        lambda: service.hint(identity, first.id, PracticeHintRequest(question_id=fixture.questions[0].id, expected_revision=2, level=1), "guard-hint"),
        lambda: service.solution(identity, first.id, request, "reveal-before-guard"),
        lambda: service.submit(identity, first.id, PracticeSubmitRequest(expected_revision=2), "guard-submit")]
    for call in calls:
        assert error_code("ASSESSMENT_ACTIVE", call).status == 409
    assert counts(database) == before


def test_private_hash_corruption_never_falls_back_to_latest_or_leaks_into_public_session(storage):
    database, identity, fixture, service = storage
    first = start(storage)
    insert_new_solution(database, dm.SolutionPrivate.model_validate({**fixture.solutions[0].model_dump(), "revision": 2, "solution_markdown": "DO_NOT_SUBSTITUTE_LATEST"}))
    with database.transaction() as connection:
        connection.execute("DROP TRIGGER solution_no_update")
        connection.execute("UPDATE solutions SET sha256=? WHERE question_id=? AND solution_revision=1", ("0" * 64, fixture.questions[0].id))
    before = counts(database)
    assert service.get_session(identity, first.id) == first
    error_code("CONTENT_HASH_MISMATCH", lambda: service.solution(identity, first.id, PracticeSolutionRequest(question_id=fixture.questions[0].id, expected_revision=1), "corrupted"))
    assert counts(database) == before


def test_workspace_boundary_and_exact_practice_hash(storage):
    database, identity, fixture, service = storage
    first = start(storage)
    with database.transaction() as connection:
        connection.execute("INSERT INTO workspace(id,title,preferences_json,created_at) VALUES('workspace_other','Synthetic','{}',?)", (utc_now(),))
    other = replace(identity, workspace_id="workspace_other")
    assert service.list_sets(other).items == []
    error_code("PRACTICE_SESSION_MISSING", lambda: service.get_session(other, first.id))
    error_code("REFERENCE_MISSING", lambda: service.create_session(other, PracticeSessionCreate(practice_ref=reference(fixture.practice)), "cross-workspace"))
    error_code("PRACTICE_SESSION_MISSING", lambda: service.solution(other, first.id, PracticeSolutionRequest(question_id=fixture.questions[0].id, expected_revision=1), "cross-reveal"))
    error_code("REFERENCE_HASH_MISMATCH", lambda: service.create_session(identity, PracticeSessionCreate(practice_ref=dm.ContentRef(entity="practice_set", id=fixture.practice.id, revision=1, sha256="0" * 64)), "wrong-sha"))


def test_current_set_pagination_and_precise_historical_course_lesson_membership(storage):
    database, identity, fixture, service = storage
    for prefix in ("alpha", "beta"):
        extra = practice_fixture(prefix, profile="learner")
        ContentService(database).publish(identity.workspace_id, extra.public_objects, extra.bodies)
    page1 = service.list_sets(identity, limit=2)
    page2 = service.list_sets(identity, limit=2, cursor=page1.next_cursor)
    assert page1.next_cursor and page2.next_cursor is None
    assert len({item.ref.id for item in page1.items + page2.items}) == 3
    error_code("SCHEMA_INVALID", lambda: service.list_sets(identity, limit=1, cursor=page1.next_cursor))
    error_code("SCHEMA_INVALID", lambda: service.list_sets(identity, limit=2, cursor=page1.next_cursor + "A"))
    revised = practice_fixture("replacement", profile="learner")
    new_course = dm.Course.model_validate({**fixture.course.model_dump(), "revision": 2, "lesson_refs": [reference(revised.lesson)], "sections": []})
    ContentService(database).publish(identity.workspace_id, [*revised.public_objects, new_course], revised.bodies)
    projected = service.list_sets(identity, course_id=fixture.course.id)
    assert {item.ref.id for item in projected.items} == {fixture.practice.id, revised.practice.id}
    assert len(service.list_sets(identity, course_id=fixture.course.id, lesson_id=fixture.lesson.id).items) == 1
    assert service.list_sets(identity, course_id=fixture.course.id, lesson_id="lesson_alpha").items == []


def test_history_set_pages_preserve_same_id_distinct_revisions_and_frozen_lesson_parents(storage):
    database, identity, fixture, service = storage
    original_session = start(storage)
    revised = practice_fixture("practice", revision=2)
    ContentService(database).publish(identity.workspace_id, revised.public_objects, revised.bodies)
    first_page = service.list_sets(identity, course_id=fixture.course.id, limit=1)
    assert len(first_page.items) == 1 and first_page.items[0].ref == reference(fixture.practice)
    assert first_page.items[0].lesson_ref == reference(fixture.lesson)
    second_page = service.list_sets(identity, course_id=fixture.course.id, limit=1, cursor=first_page.next_cursor)
    assert second_page.next_cursor is None and second_page.items[0].ref == reference(revised.practice)
    assert second_page.items[0].lesson_ref == reference(revised.lesson)
    assert service.get_session(identity, original_session.id).lesson_ref == reference(fixture.lesson)
    latest = service.create_session(identity, PracticeSessionCreate(practice_ref=second_page.items[0].ref), "create-revision-two")
    assert latest.lesson_ref == reference(revised.lesson) and latest.questions == list(revised.questions)


def test_sql_guards_preserve_frozen_assignments_and_submissions(storage):
    database, identity, fixture, service = storage
    first = start(storage)
    service.save_responses(identity, first.id, dm.ResponsesWrite(expected_revision=1, responses=[dm.ResponseDraft(question_id=fixture.questions[0].id, answer="original")]), "save")
    service.submit(identity, first.id, PracticeSubmitRequest(expected_revision=2), "submit")
    statements = [
        ("UPDATE practice_sessions SET question_refs_json='[]' WHERE id=?", (first.id,)),
        ("UPDATE practice_sessions SET submission_json='{}' WHERE id=?", (first.id,)),
        ("UPDATE practice_sessions SET status='active' WHERE id=?", (first.id,)),
        ("DELETE FROM practice_responses WHERE session_id=?", (first.id,)),
        ("UPDATE practice_responses SET answer_json='{}' WHERE session_id=?", (first.id,)),
    ]
    for sql, parameters in statements:
        with pytest.raises(sqlite3.IntegrityError), database.transaction() as connection:
            connection.execute(sql, parameters)
    assert service.get_session(identity, first.id).responses[0].answer == "original"


def test_legacy_incomplete_session_binding_is_explicitly_unavailable_instead_of_rebound(storage):
    database, identity, fixture, service = storage
    with database.transaction() as connection:
        connection.execute("INSERT INTO practice_sessions(id,workspace_id,practice_id,practice_revision,question_refs_json,solution_refs_json,status,revision,created_at) VALUES(?,?,?,1,?,?,'active',1,?)",
            ("practice_legacy", identity.workspace_id, fixture.practice.id, canonical_bytes([reference(fixture.questions[0]).model_dump(mode="json")]).decode(), "[]", utc_now()))
    error_code("PRACTICE_SNAPSHOT_INVALID", lambda: service.get_session(identity, "practice_legacy"))


def test_real_http_bootstrap_and_reader_to_practice_roundtrip_without_private_preload(storage):
    database, _, fixture, _ = storage
    app = FastAPI()
    install_boundary(app, database.settings, database)
    app.include_router(create_router(database.settings, database))
    app.include_router(create_practice_router(database))
    with TestClient(app, base_url=database.settings.origin) as client:
        auth = client.post("/api/v1/session/bootstrap", json={"one_time_code": issue_bootstrap_code(database)}, headers={"Origin": database.settings.origin})
        assert auth.status_code == 200
        headers = {"Origin": database.settings.origin, "X-CSRF-Token": auth.json()["csrf_token"], "Idempotency-Key": "http-create"}
        listed = client.get(f"/api/v1/practice/sets?course_id={fixture.course.id}&lesson_id={fixture.lesson.id}")
        assert listed.status_code == 200 and listed.json()["items"][0]["question_count"] == 5
        created = client.post("/api/v1/practice/sessions", json={"practice_ref": listed.json()["items"][0]["ref"]}, headers=headers)
        assert created.status_code == 201
        identifier = created.json()["id"]
        assert client.get(f"/api/v1/practice/sessions/{identifier}").json() == created.json()
        saved = client.put(f"/api/v1/practice/sessions/{identifier}/responses", json={"expected_revision": 1, "responses": [{"question_id": fixture.questions[0].id, "answer": "choice_five"}]}, headers={**headers, "Idempotency-Key": "http-save"})
        assert saved.status_code == 200 and saved.json()["revision"] == 2
        result = client.post(f"/api/v1/practice/sessions/{identifier}/submit", json={"expected_revision": 2}, headers={**headers, "Idempotency-Key": "http-submit"})
        assert result.status_code == 200 and all(item["score"] is None for item in result.json()["results"])
        assert "private_json" not in result.text and "accepted_answers" not in result.text
