"""Actual assessment submissions use a narrow, transaction-bound Learning port."""

from dataclasses import replace
import json

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes
from services.api.app.application.assessment import AssessmentService
from services.api.app.application.errors import ApiError
from services.api.app.application.imports import ImportService
from services.api.app.application.learning import LearningService, record_test_submitted, validate_test_submitted
from services.api.app.import_dto import ImportCommitRequest
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database, utc_now
from services.api.app.infrastructure.import_worker import ImportWorker
from services.api.app.infrastructure.learning_repository import LearningRepository
from services.api.app.infrastructure.security import SessionIdentity
from services.api.app.learning_dto import LearningActionRequest
from tests.assessment_fixtures import assessment_fixture


@pytest.fixture
def assessment_learning_state(tmp_path):
    database = Database(Settings(data_dir=tmp_path / 'data'))
    workspace = database.initialize()
    identity = SessionIdentity('session_assessment_learning', workspace, 'learner', 'unused', '2099-01-01T00:00:00Z')
    fixture = assessment_fixture('assessmentlearning')
    ingestion = ImportService(database)
    author = replace(identity, role='author')
    staged = ingestion.stage(author, data=fixture.archive, filename='original-assessment.learnpack.zip', kind='learnpack', key='source')
    worker = ImportWorker(database)
    try:
        assert worker.run_once()
        preview = ingestion.preview(author, staged.import_id)
        ingestion.commit(author, staged.import_id, ImportCommitRequest(expected_input_sha256=staged.input_sha256,
            accepted_warning_codes=sorted({w.code for w in preview.warnings if w.severity == 'warning'}), id_mapping=[]), 'commit')
        yield database, identity, fixture, AssessmentService(database)
    finally:
        worker.stop()


def create(state, key='create'):
    _, identity, fixture, service = state
    return service.create_attempt(identity, fixture.assessment.id,
        dm.AttemptCreate(assessment_ref=reference(fixture.assessment), mode='independent'), key)


def counts(database):
    with database.connect() as connection:
        return {table: connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                for table in ['learning_events', 'learning_progress', 'outbox', 'grades', 'evidence', 'idempotency']}


def test_actual_submit_preserves_progress_and_records_exactly_one_native_event(assessment_learning_state):
    database, identity, fixture, service = assessment_learning_state
    learning = LearningService(database)
    learning.action(identity, LearningActionRequest(kind='bookmark_set', ref=reference(fixture.block),
        expected_revision=1, value=True), 'bookmark-before-test')
    before = learning.progress(identity.workspace_id)
    created = create(assessment_learning_state)
    saved = service.save_responses(identity, created.id, dm.ResponsesWrite(expected_revision=created.revision,
        responses=[dm.ResponseDraft(question_id=fixture.questions[0].id, answer='choice_five', steps_markdown='原创作答')]), 'save')
    submitted = service.submit(identity, created.id, dm.AttemptSubmit(expected_revision=saved.revision), 'submit')
    assert submitted.status == 'submitted' and submitted.grading_status == 'not_graded'
    after = learning.progress(identity.workspace_id)
    assert after.revision == before.revision + 1
    assert (after.bookmarks, after.readings, after.route_steps) == (before.bookmarks, before.readings, before.route_steps)
    with database.connect() as connection:
        rows = connection.execute("SELECT * FROM learning_events WHERE kind='test_submitted'").fetchall()
        assert len(rows) == 1
        row = rows[0]
        event = dm.LearningEvent.model_validate_json(row['payload_json'])
        assert event.actor == 'server' and event.origin == 'native'
        assert event.ref == reference(fixture.assessment) and event.attempt_id == created.id
        assert event.workspace_id == identity.workspace_id and event.occurred_at == row['occurred_at']
        validate_test_submitted(connection, identity.workspace_id, event.event_id, event.ref, created.id)
    observed = counts(database)
    assert service.submit(identity, created.id, dm.AttemptSubmit(expected_revision=saved.revision), 'submit') == submitted
    assert counts(database) == observed
    assert observed['grades'] == observed['evidence'] == 0


def test_port_rejects_no_transaction_and_unsubmitted_attempt_without_events(assessment_learning_state):
    database, identity, fixture, _ = assessment_learning_state
    created = create(assessment_learning_state)
    before = counts(database)
    ref = reference(fixture.assessment)
    with database.connect() as connection, pytest.raises(ApiError) as no_transaction:
        record_test_submitted(connection, identity.workspace_id, ref, created.id)
    assert no_transaction.value.code == 'TRANSACTION_REQUIRED'
    with pytest.raises(ApiError) as active, database.transaction() as connection:
        record_test_submitted(connection, identity.workspace_id, ref, created.id)
    assert active.value.code == 'ASSESSMENT_STATE_INVALID'
    assert counts(database) == before


def test_learning_failure_rolls_back_actual_submission_and_its_request(assessment_learning_state, monkeypatch):
    database, identity, _, service = assessment_learning_state
    created = create(assessment_learning_state)
    before = counts(database)
    original = LearningRepository.test_submitted

    def fail_after_append(self, ref, attempt_id):
        original(self, ref, attempt_id)
        raise RuntimeError('injected learning failure after trusted append')

    monkeypatch.setattr(LearningRepository, 'test_submitted', fail_after_append)
    with pytest.raises(RuntimeError, match='injected learning failure'):
        service.submit(identity, created.id, dm.AttemptSubmit(expected_revision=created.revision), 'submit-rollback')
    assert service.get_attempt(identity, created.id).status == 'active'
    assert counts(database) == before


@pytest.mark.parametrize('field,value', [
    ('workspace_id', 'workspace_other'), ('event_id', 'event_wrong'), ('actor', 'learner'),
    ('origin', 'user_supplied_import'), ('kind', 'grade_finalized'), ('attempt_id', 'attempt_other'),
    ('occurred_at', '2020-01-01T00:00:00Z'),
])
def test_read_port_rejects_corrupt_event_payload_without_rewriting_history(assessment_learning_state, field, value):
    database, identity, fixture, service = assessment_learning_state
    created = create(assessment_learning_state)
    service.submit(identity, created.id, dm.AttemptSubmit(expected_revision=created.revision), 'submit')
    ref = reference(fixture.assessment)
    event = dm.LearningEvent(event_id='event_corrupt_test', workspace_id=identity.workspace_id,
        actor='server', origin='native', kind='test_submitted', ref=ref, occurred_at=utc_now(), attempt_id=created.id)
    changed = {**event.model_dump(mode='json'), field: value}
    # Explicit storage-corruption fixture, not an event accepted by the public API.
    with database.transaction() as connection:
        connection.execute('INSERT INTO learning_events(event_id,workspace_id,kind,origin,payload_json,occurred_at) VALUES(?,?,?,?,?,?)',
            (event.event_id, identity.workspace_id, event.kind, event.origin, canonical_bytes(changed).decode(), event.occurred_at))
    before = counts(database)
    with database.connect() as connection, pytest.raises(ApiError) as rejected:
        validate_test_submitted(connection, identity.workspace_id, event.event_id, ref, created.id)
    assert rejected.value.code == 'ASSESSMENT_SNAPSHOT_INVALID'
    assert counts(database) == before
    with database.connect() as connection:
        assert json.loads(connection.execute('SELECT payload_json FROM learning_events WHERE event_id=?', (event.event_id,)).fetchone()[0]) == changed


def test_new_active_independent_blocks_old_event_replay_validation(assessment_learning_state):
    database, identity, fixture, service = assessment_learning_state
    first = create(assessment_learning_state)
    service.submit(identity, first.id, dm.AttemptSubmit(expected_revision=first.revision), 'submit')
    with database.connect() as connection:
        event_id = connection.execute("SELECT event_id FROM learning_events WHERE kind='test_submitted'").fetchone()[0]
    create(assessment_learning_state, 'second-independent')
    with database.connect() as connection, pytest.raises(ApiError) as blocked:
        validate_test_submitted(connection, identity.workspace_id, event_id, reference(fixture.assessment), first.id)
    assert blocked.value.status == 409
