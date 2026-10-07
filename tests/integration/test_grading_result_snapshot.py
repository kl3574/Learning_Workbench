"""Real WAL readers and grading workers, with test-owned scheduling controls."""

from contextlib import contextmanager
from dataclasses import replace
import sqlite3
from threading import Event, Thread

import pytest

from services.api.app.application.content import ContentService
from services.api.app.application.errors import ApiError
from services.api.app.application.grading import GradingService, GradingWorker
from services.api.app.assessment_dto import AssessmentGradingJob, AssessmentGradingResult
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.content_repository import reference
from tests.integration.test_assessment_grading import real_author, review_request, submitted
from tests.integration.test_assessment_attempts import insert_answer, start, storage as assessment_storage


@pytest.fixture
def storage(tmp_path):
    return assessment_storage.__wrapped__(tmp_path)


class ObservedDatabase(Database):
    def __init__(self, settings, *, read_only=False, non_waiting=False):
        super().__init__(settings)
        self.read_only = read_only
        self.non_waiting = non_waiting
        self.transactions = []
        self.denied_writes = []
        self.changes = []

    @contextmanager
    def connect(self, *, busy_timeout_ms=10000):
        # Zero busy timeout belongs only to this worker's lock observation.
        with super().connect(busy_timeout_ms=0 if self.non_waiting else busy_timeout_ms) as connection:
            def trace(statement):
                token = statement.strip().upper()
                if token in {"BEGIN", "BEGIN IMMEDIATE", "COMMIT", "ROLLBACK"}:
                    self.transactions.append(token)

            def authorize(action, _first, _second, _database, _trigger):
                if action in {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
                              sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_DROP_TABLE,
                              sqlite3.SQLITE_ALTER_TABLE, sqlite3.SQLITE_CREATE_INDEX,
                              sqlite3.SQLITE_DROP_INDEX, sqlite3.SQLITE_CREATE_TRIGGER,
                              sqlite3.SQLITE_DROP_TRIGGER, sqlite3.SQLITE_CREATE_VIEW,
                              sqlite3.SQLITE_DROP_VIEW}:
                    self.denied_writes.append(action)
                    return sqlite3.SQLITE_DENY
                return sqlite3.SQLITE_OK

            connection.set_trace_callback(trace)
            if self.read_only:
                connection.set_authorizer(authorize)
            try:
                yield connection
            finally:
                self.changes.append(connection.total_changes)


class PausedProjection(GradingService):
    def __init__(self, database):
        super().__init__(database)
        self.entered = Event()
        self.release = Event()

    def _project(self, *args, **kwargs):
        value = super()._project(*args, **kwargs)
        self.entered.set()
        if not self.release.wait(10):
            raise AssertionError("controlled projection was not released")
        return value


def begin_reader(service, identity, identifier):
    values, errors = [], []

    def read():
        try:
            values.append(service.result(identity, identifier))
        except BaseException as error:
            errors.append(error)

    thread = Thread(target=read, name="owned-grading-result-reader")
    thread.start()
    return thread, values, errors


def release_reader(service, thread):
    service.release.set()
    thread.join(10)
    assert not thread.is_alive(), "owned result reader did not terminate"


def test_result_read_snapshot_does_not_reserve_worker_writer_and_keeps_old_grade(storage):
    database, learner, fixture, _ = storage
    final = submitted(storage)
    assert GradingWorker(database).run_once()
    original = GradingService(database).result(learner, final.id)
    assert isinstance(original, AssessmentGradingResult) and original.grading_revision == 1
    assert original.current_review_policy.tutor_scope == "operation_help_only"
    GradingService(database).regrade(real_author(database), final.id, review_request(fixture), "snapshot-review")

    read_database = ObservedDatabase(database.settings, read_only=True)
    service = PausedProjection(read_database)
    worker_database = ObservedDatabase(database.settings, non_waiting=True)
    thread, values, errors = begin_reader(service, learner, final.id)
    worker_error = None
    worked = False
    try:
        assert service.entered.wait(10), "result did not reach controlled projection"
        try:
            worked = GradingWorker(worker_database).run_once()
        except sqlite3.OperationalError as error:
            worker_error = (error.sqlite_errorcode, error.sqlite_errorname)
    finally:
        release_reader(service, thread)

    assert not errors, f"result reader failed: {errors!r}"
    assert worker_error is None, f"worker lock: {worker_error}; reader transactions={read_database.transactions}; worker transactions={worker_database.transactions}"
    assert worked
    assert read_database.denied_writes == [] and set(read_database.changes) == {0}
    assert len(values) == 1 and isinstance(values[0], AssessmentGradingJob)
    waiting = values[0]
    assert waiting.status == "queued" and waiting.last_completed_result is not None
    assert waiting.last_completed_result.grading_revision == 1
    assert [entry.grading_revision for entry in waiting.history] == [1]
    assert waiting.last_completed_result.model_dump(exclude={"current_review_policy"}) == original.model_dump(exclude={"current_review_policy"})
    assert waiting.current_review_policy.tutor_scope == "academic"
    assert waiting.last_completed_result.current_review_policy == waiting.current_review_policy
    assert AssessmentGradingJob.model_validate(waiting.model_dump()) == waiting
    assert read_database.transactions == ["BEGIN", "COMMIT", "BEGIN IMMEDIATE", "COMMIT"]
    current = GradingService(database).result(learner, final.id)
    assert isinstance(current, AssessmentGradingResult)
    assert current.grading_revision == 2 and current.status == "graded"
    assert [entry.grading_revision for entry in current.history] == [1, 2]


@pytest.mark.parametrize("mode, expected_code", [
    ("independent", "ASSESSMENT_ACTIVE"),
    ("open_book", "ASSESSMENT_ANSWER_PROTECTED"),
    ("assisted", "ASSESSMENT_ANSWER_PROTECTED"),
])
def test_prepared_private_result_is_refused_after_current_policy_changes(storage, mode, expected_code):
    database, learner, fixture, _ = storage
    final = submitted(storage)
    assert GradingWorker(database).run_once()
    GradingService(database).regrade(real_author(database), final.id, review_request(fixture), "delivery-review")
    assert GradingWorker(database).run_once()
    allowed = GradingService(database).result(learner, final.id)
    assert isinstance(allowed, AssessmentGradingResult)
    assert all(item.solution_markdown is not None for item in allowed.items)

    # A different question in the exact same exposure group exercises the
    # existing group policy, rather than only matching an identical reference.
    question = fixture.questions[0].model_copy(update={"id": "question_delivery_related"})
    blueprint = fixture.assessment.model_copy(update={"id": "assessment_delivery_related", "question_refs": [reference(question)]})
    solution = fixture.solutions[0].model_copy(update={"id": "solution_delivery_related", "question_ref": reference(question)})
    ContentService(database).publish(learner.workspace_id, [question, blueprint], {})
    insert_answer(database, solution)
    related = replace(fixture, assessment=blueprint, questions=(question,), solutions=(solution,))
    assert reference(question) != reference(fixture.questions[0])
    assert question.exposure_group == fixture.questions[0].exposure_group

    read_database = ObservedDatabase(database.settings, read_only=True)
    service = PausedProjection(read_database)
    thread, values, errors = begin_reader(service, learner, final.id)
    try:
        assert service.entered.wait(10), "result did not reach controlled projection"
        start(storage, mode=mode, key="delivery-protection", fixture=related)
    finally:
        release_reader(service, thread)

    assert values == [], "prepared private result escaped the current delivery policy"
    assert len(errors) == 1 and isinstance(errors[0], ApiError)
    assert errors[0].code == expected_code
    assert read_database.denied_writes == [] and set(read_database.changes) == {0}
    with pytest.raises(ApiError) as caught:
        GradingService(database).result(learner, final.id)
    assert caught.value.code == expected_code


def test_prepared_pending_history_is_refused_after_worker_finishes_and_independent_starts(storage):
    database, learner, fixture, _ = storage
    final = submitted(storage)
    assert GradingWorker(database).run_once()
    GradingService(database).regrade(real_author(database), final.id, review_request(fixture), "pending-delivery-review")
    read_database = ObservedDatabase(database.settings, read_only=True)
    service = PausedProjection(read_database)
    thread, values, errors = begin_reader(service, learner, final.id)
    try:
        assert service.entered.wait(10), "result did not reach controlled projection"
        assert GradingWorker(ObservedDatabase(database.settings, non_waiting=True)).run_once()
        start(storage, mode="independent", key="pending-delivery-protection")
    finally:
        release_reader(service, thread)
    assert values == [], "pending history escaped the current independent policy"
    assert len(errors) == 1 and isinstance(errors[0], ApiError)
    assert errors[0].code == "ASSESSMENT_ACTIVE"
    assert read_database.denied_writes == [] and set(read_database.changes) == {0}
    with pytest.raises(ApiError) as caught:
        GradingService(database).result(learner, final.id)
    assert caught.value.code == "ASSESSMENT_ACTIVE"


def test_initial_pending_result_is_read_only_and_has_no_phantom_completed_grade(storage):
    database, learner, _, _ = storage
    final = submitted(storage)
    read_database = ObservedDatabase(database.settings, read_only=True)
    pending = GradingService(read_database).result(learner, final.id)
    assert isinstance(pending, AssessmentGradingJob)
    assert pending.status == "queued" and pending.history == [] and pending.last_completed_result is None
    assert AssessmentGradingJob.model_validate(pending.model_dump()) == pending
    assert read_database.denied_writes == [] and set(read_database.changes) == {0}
    assert read_database.transactions == ["BEGIN", "COMMIT", "BEGIN IMMEDIATE", "COMMIT"]
    assert GradingWorker(database).run_once()
    completed = GradingService(database).result(learner, final.id)
    assert isinstance(completed, AssessmentGradingResult) and completed.grading_revision == 1
