"""Independent assessment corruption and cross-operation race probes, using real SQLite."""

from concurrent.futures import ThreadPoolExecutor
import json

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes
from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.content_repository import reference
from tests.integration.test_assessment_learning_port import assessment_learning_state

state = assessment_learning_state


def create(state, key):
    _, identity, fixture, service = state
    request = dm.AttemptCreate(assessment_ref=reference(fixture.assessment), mode='independent')
    return service.create_attempt(identity, fixture.assessment.id, request, key)


def count_effects(database):
    with database.connect() as connection:
        return {table: connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
                for table in ('attempts', 'responses', 'learning_events', 'outbox', 'idempotency')}


def test_create_replay_cannot_redirect_old_key_to_other_active_attempt(state):
    database, identity, fixture, service = state
    first = create(state, 'first')
    service.abandon(identity, first.id, dm.AttemptSubmit(expected_revision=1), 'abandon-first')
    current = create(state, 'second')
    with database.transaction() as connection:
        connection.execute('UPDATE idempotency SET result_json=? WHERE actor=? AND route=? AND key=?',
            (canonical_bytes(current).decode(), identity.workspace_id, f'POST /assessments/{fixture.assessment.id}/attempts', 'first'))
    before = count_effects(database)
    with pytest.raises(ApiError):
        create(state, 'first')
    assert count_effects(database) == before
    assert service.get_attempt(identity, current.id) == current


@pytest.mark.parametrize('field', ['stem', 'frozen_ref'])
def test_create_replay_rejects_cached_public_question_or_ref_not_matching_frozen_assignment(state, field):
    database, identity, fixture, service = state
    current = create(state, 'create')
    with database.transaction() as connection:
        row = connection.execute('SELECT result_json FROM idempotency WHERE actor=? AND key=?', (identity.workspace_id, 'create')).fetchone()
        damaged = json.loads(row['result_json'])
        if field == 'stem':
            damaged['questions'][0]['stem_markdown'] = 'Synthetic unrelated cached question text; not the frozen allocation.'
        else:
            damaged['preflight']['prior_seen']['questions'][0]['question_ref']['sha256'] = '0' * 64
        connection.execute('UPDATE idempotency SET result_json=? WHERE actor=? AND key=?',
            (canonical_bytes(damaged).decode(), identity.workspace_id, 'create'))
    before = count_effects(database)
    with pytest.raises(ApiError):
        create(state, 'create')
    assert count_effects(database) == before
    assert service.get_attempt(identity, current.id) == current


def test_last_save_and_submit_compete_without_mixed_or_lost_authoritative_responses(state):
    database, identity, fixture, service = state
    current = create(state, 'create')
    old = [dm.ResponseDraft(question_id=fixture.questions[0].id, answer='old saved response')]
    saved = service.save_responses(identity, current.id, dm.ResponsesWrite(expected_revision=1, responses=old), 'initial-save')
    candidate = [dm.ResponseDraft(question_id=fixture.questions[1].id, answer='candidate response')]
    def save():
        try:
            return service.save_responses(identity, current.id, dm.ResponsesWrite(expected_revision=saved.revision, responses=candidate), 'racing-save')
        except ApiError as error:
            return error
    def submit():
        try:
            return service.submit(identity, current.id, dm.AttemptSubmit(expected_revision=saved.revision), 'racing-submit')
        except ApiError as error:
            return error
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(save), pool.submit(submit)]
        outcomes = [future.result() for future in futures]
    assert sum(isinstance(result, ApiError) for result in outcomes) == 1
    final = service.get_attempt(identity, current.id)
    responses = service.get_responses(identity, current.id)
    with database.connect() as connection:
        row = connection.execute('SELECT * FROM attempts WHERE id=?', (current.id,)).fetchone()
        submissions = connection.execute("SELECT COUNT(*) FROM outbox WHERE event_type='assessment.grading.requested'").fetchone()[0]
        if final.status == 'submitted':
            assert responses.responses == old and submissions == 1
            assert json.loads(row['submission_json'])['responses'] == [response.model_dump(mode='json') for response in old]
        else:
            assert final.status == 'active' and responses.responses == candidate and submissions == 0
            assert row['submission_json'] is None


@pytest.mark.parametrize('damage', ['wrong_type', 'wrong_workspace', 'wrong_event'])
def test_submitted_outbox_corruption_blocks_get_and_replay_without_repair_or_new_work(state, damage):
    database, identity, _, service = state
    current = create(state, 'create')
    submitted = service.submit(identity, current.id, dm.AttemptSubmit(expected_revision=1), 'submit')
    with database.transaction() as connection:
        outbox_id = connection.execute('SELECT grading_outbox_id FROM attempts WHERE id=?', (current.id,)).fetchone()[0]
        row = connection.execute('SELECT * FROM outbox WHERE id=?', (outbox_id,)).fetchone()
        payload = json.loads(row['payload_json'])
        if damage == 'wrong_type':
            connection.execute("UPDATE outbox SET event_type='unrelated.event' WHERE id=?", (outbox_id,))
        else:
            payload['workspace_id' if damage == 'wrong_workspace' else 'event_id'] = 'synthetic_wrong_binding'
            connection.execute('UPDATE outbox SET payload_json=? WHERE id=?', (canonical_bytes(payload).decode(), outbox_id))
    before = count_effects(database)
    for call in (lambda: service.get_attempt(identity, submitted.id),
                 lambda: service.submit(identity, submitted.id, dm.AttemptSubmit(expected_revision=1), 'submit')):
        with pytest.raises(ApiError) as error:
            call()
        assert error.value.code == 'ASSESSMENT_SNAPSHOT_INVALID'
    assert count_effects(database) == before
