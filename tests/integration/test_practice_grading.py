"""Real SQLite integration with original synthetic inputs.

The explicitly named approved-domain fixture supplies a trusted-input premise to
the grader; it is not an import approval workflow or an actual human math review.
Normal imported fixtures remain needs_review through the production importer.
"""

from dataclasses import replace
import json
import sqlite3

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256
from services.api.app.application.content import ContentService
from services.api.app.application.practice import PracticeService
from services.api.app.application.practice_grading import PracticeGradeAudit
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database, utc_now
from services.api.app.infrastructure.practice_repository import PracticeRepository, StoredSubmission
from services.api.app.practice_dto import PracticeSessionCreate, PracticeSubmitRequest
from tests.integration.test_practice_sessions import counts, error_code, insert_new_solution, start, storage
from tests.practice_fixtures import practice_fixture

__all__ = ["storage"]


def approved_domain_fixture(database, identity):
    """Test-only assumed approval on new originals, never a hidden importer change."""
    fixture = practice_fixture("graded")
    questions = list(fixture.questions)
    questions[2] = questions[2].model_copy(update={"stem_markdown": "原创评分函数样例：填写一米的长度。",
                                                "input_instructions": "填写数值及单位；裸数使用 m。"})
    questions[3] = questions[3].model_copy(update={"stem_markdown": "原创评分函数样例：计算 2×3 的最终数值。",
                                                "input_instructions": "仅最终数值计分；步骤保留且未评分。"})
    solutions = []
    for index, (question, old) in enumerate(zip(questions, fixture.solutions, strict=True)):
        data = {**old.model_dump(), "question_ref": reference(question).model_dump(), "review_status": "approved",
                "rubric_markdown": ""}
        if index == 2:
            data.update(accepted_answers=["1"], unit="m", absolute_tolerance=0.001, relative_tolerance=0.0)
        if index == 3:
            data.update(unit=None)
        solutions.append(dm.SolutionPrivate.model_validate(data))
    fixture = replace(fixture, questions=tuple(questions), solutions=tuple(solutions),
                      practice=fixture.practice.model_copy(update={"question_refs": [reference(q) for q in questions]}))
    ContentService(database).publish(identity.workspace_id, fixture.public_objects, fixture.bodies)
    for solution in fixture.solutions:
        insert_new_solution(database, solution)
    return fixture


def audit(database, session_id):
    with database.connect() as connection:
        row = connection.execute("SELECT * FROM practice_grading_audits WHERE session_id=?", (session_id,)).fetchone()
        assert row is not None
        value = PracticeGradeAudit.model_validate_json(row["audit_json"])
        assert metadata_sha256(value) == row["audit_sha256"]
        return value, dict(row)


def test_normal_import_stays_unreviewed_with_private_trace_and_exact_submit_replay(storage):
    database, identity, fixture, service = storage
    session = start(storage)
    saved = service.save_responses(identity, session.id, dm.ResponsesWrite(expected_revision=1,
        responses=[dm.ResponseDraft(question_id=fixture.questions[0].id, answer="choice_five")]), "save")
    request = PracticeSubmitRequest(expected_revision=saved.revision)
    result = service.submit(identity, session.id, request, "submit")
    before = counts(database)
    assert all(item.score is None and item.status == "needs_review" for item in result.results)
    private, raw = audit(database, session.id)
    assert private.entries[0].private_trace.reason_codes == ["answer_unreviewed"]
    assert private.entries[0].private_trace.response.answer == "choice_five"
    assert private.submission_sha256 and raw["outbox_id"]
    assert service.submit(identity, session.id, request, "submit") == result
    assert counts(database) == before
    public = service.get_session(identity, session.id).model_dump_json()
    for field in ("private_trace", "private_pin", "accepted_answers", "numeric", "grading_audit_sha256"):
        # The public question kind 'numeric' is expected; a private numeric trace
        # property is not. Other markers must never enter this DTO.
        assert (f'"{field}":' if field == "numeric" else field) not in public
    assert all(item.solution_markdown is None for item in result.results)
    assert counts(database)["evidence"] == counts(database)["grades"] == 0


def test_assumed_approved_originals_grade_choice_text_units_and_final_value_only(storage):
    database, identity, _, service = storage
    fixture = approved_domain_fixture(database, identity)
    session = service.create_session(identity, PracticeSessionCreate(practice_ref=reference(fixture.practice)), "graded-create")
    responses = [dm.ResponseDraft(question_id=question.id, answer=answer, steps_markdown="原始步骤保留；不得执行")
                 for question, answer in zip(fixture.questions, ["choice_five", "  加法交换律  ", "100.1 cm", "6", "2*x"], strict=True)]
    saved = service.save_responses(identity, session.id, dm.ResponsesWrite(expected_revision=1, responses=responses), "graded-save")
    result = service.submit(identity, session.id, PracticeSubmitRequest(expected_revision=saved.revision), "graded-submit")
    assert [item.score for item in result.results] == [1.0, 1.0, 1.0, 1.0, None]
    assert result.results[4].status == "needs_review"
    assert "步骤未评分" in result.results[3].feedback_markdown
    private, before = audit(database, session.id)
    assert private.entries[2].private_trace.numeric.comparisons[0].matched is True
    assert private.entries[2].private_trace.numeric.user_to_base_factor == "0.01"
    assert [entry.private_trace.response for entry in private.entries] == responses
    restarted = Database(database.settings)
    restarted.initialize()
    readback = PracticeService(restarted).get_session(identity, session.id)
    assert readback.results == result.results and readback.responses == responses
    assert audit(restarted, session.id)[1] == before
    with database.connect() as connection:
        assert [row[0] for row in connection.execute("SELECT kind FROM learning_events")] == ["practice_submitted"]


def test_future_approved_revision_does_not_upgrade_already_frozen_unreviewed_practice(storage):
    database, identity, fixture, service = storage
    old = start(storage)
    new_solution = fixture.solutions[0].model_copy(update={"revision": 2, "review_status": "approved"})
    insert_new_solution(database, new_solution)
    newer = start(storage, key="later-session")
    for session in (old, newer):
        saved = service.save_responses(identity, session.id, dm.ResponsesWrite(expected_revision=1,
            responses=[dm.ResponseDraft(question_id=fixture.questions[0].id, answer="choice_five")]), "save")
        service.submit(identity, session.id, PracticeSubmitRequest(expected_revision=saved.revision), "submit")
    assert service.get_session(identity, old.id).results[0].score is None
    assert service.get_session(identity, newer.id).results[0].score == 1.0
    assert audit(database, old.id)[0].entries[0].private_trace.private_pin.solution_revision == 1
    assert audit(database, newer.id)[0].entries[0].private_trace.private_pin.solution_revision == 2


def test_frozen_missing_practice_answers_submit_as_unknown_without_adopting_later_answers(storage):
    database, identity, _, service = storage
    fixture = practice_fixture("missinggrade", profile="learner")
    ContentService(database).publish(identity.workspace_id, fixture.public_objects, fixture.bodies)
    session = service.create_session(identity, PracticeSessionCreate(practice_ref=reference(fixture.practice)), "missing")
    insert_new_solution(database, fixture.solutions[0].model_copy(update={"revision": 2, "review_status": "approved"}))
    result = service.submit(identity, session.id, PracticeSubmitRequest(expected_revision=1), "submit")
    assert all(item.score is None for item in result.results)
    assert all(entry.missing_reason == "frozen_solution_missing" and entry.private_trace is None
               for entry in audit(database, session.id)[0].entries)


def test_audit_insert_failure_rolls_back_submission_learning_outbox_and_idempotency(storage):
    database, identity, _, service = storage
    session = start(storage)
    with database.transaction() as connection:
        connection.execute("CREATE TRIGGER synthetic_audit_failure BEFORE INSERT ON practice_grading_audits "
                           "BEGIN SELECT RAISE(ABORT,'synthetic audit failure'); END")
    before = counts(database)
    request = PracticeSubmitRequest(expected_revision=1)
    error_code("PRACTICE_STORAGE_UNAVAILABLE", lambda: service.submit(identity, session.id, request, "atomic"))
    assert counts(database) == before
    assert service.get_session(identity, session.id).status == "active"
    with database.transaction() as connection:
        connection.execute("DROP TRIGGER synthetic_audit_failure")
    result = service.submit(identity, session.id, request, "atomic")
    assert service.submit(identity, session.id, request, "atomic") == result
    assert audit(database, session.id)[0].session_id == session.id


@pytest.mark.parametrize("damage", ["missing_audit", "forged_outbox", "forged_submit_receipt"])
def test_corrupted_grade_binding_fails_closed_even_on_idempotent_submit(storage, damage):
    database, identity, _, service = storage
    session = start(storage)
    request = PracticeSubmitRequest(expected_revision=1)
    result = service.submit(identity, session.id, request, "original")
    with database.transaction() as connection:
        if damage == "missing_audit":
            connection.execute("DELETE FROM practice_grading_audits WHERE session_id=?", (session.id,))
        elif damage == "forged_outbox":
            row = connection.execute("SELECT * FROM outbox WHERE event_type='practice.submitted'").fetchone()
            payload = json.loads(row["payload_json"])
            payload["grading_audit_sha256"] = "0" * 64
            connection.execute("UPDATE outbox SET payload_json=? WHERE id=?", (canonical_bytes(payload).decode(), row["id"]))
        else:
            forged = result.model_dump(mode="json")
            forged["id"] = "practice_session_unrelated"
            connection.execute("UPDATE idempotency SET result_json=? WHERE route=? AND key='original'",
                               (canonical_bytes(forged).decode(), f"POST /practice/sessions/{session.id}/submit"))
    error_code("PRACTICE_SNAPSHOT_INVALID", lambda: service.submit(identity, session.id, request, "original"))


def test_audit_cannot_be_overwritten_and_legacy_ungraded_submission_bytes_stay_readable(storage):
    database, identity, _, service = storage
    session = start(storage)
    with database.transaction() as connection:
        repository = PracticeRepository(connection, identity.workspace_id)
        record = repository.load(session.id)
        snapshot = StoredSubmission(revision=2, submitted_at=utc_now(), responses=[],
            results=[dm.ItemGrade(question_ref=ref, score=None, max_score=q.max_score, status="needs_review",
                                 feedback_markdown="M3.1 已保存，尚未执行评分。", solution_markdown=None)
                     for ref, q in zip(record.question_refs, session.questions, strict=True)],
            exposure_event_ids=[], assisted=False, assistance=session.assistance)
        repository.submit(record, snapshot)  # Explicit legacy ungraded fixture.
        before = tuple(connection.execute("SELECT submission_json,submission_sha256 FROM practice_sessions WHERE id=?", (session.id,)).fetchone())
    assert service.get_session(identity, session.id).results == snapshot.results
    database.initialize()
    with database.connect() as connection:
        assert tuple(connection.execute("SELECT submission_json,submission_sha256 FROM practice_sessions WHERE id=?", (session.id,)).fetchone()) == before
        assert connection.execute("SELECT COUNT(*) FROM practice_grading_audits").fetchone()[0] == 0
    current = start(storage, key="new")
    service.submit(identity, current.id, PracticeSubmitRequest(expected_revision=1), "new-submit")
    with database.transaction() as connection, pytest.raises(sqlite3.IntegrityError, match="immutable"):
        connection.execute("UPDATE practice_grading_audits SET audit_sha256=? WHERE session_id=?", ("0" * 64, current.id))
