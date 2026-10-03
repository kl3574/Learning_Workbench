"""Real generic Jobs HTTP projections, with original command ACK preservation."""

from fastapi.testclient import TestClient
import pytest

from services.api.app.import_dto import JobSnapshot
from services.api.app.infrastructure.tutor_repository import TutorRepository
from services.api.app.infrastructure.security import COOKIE_NAME
from tests.integration.test_retrieval import all_rows
from tests.integration.test_tutor_http import command, http_tutor as shared_http_tutor, start


@pytest.fixture
def http_tutor(tmp_path):
    yield from shared_http_tutor.__wrapped__(tmp_path)


@pytest.mark.parametrize('action', ['get', 'cancel'])
def test_generic_tutor_jobs_return_the_actual_http_job_snapshot(http_tutor, action):
    database, identity, token, app, _, headers, _, _ = http_tutor
    _, _, _, run = start(http_tutor)
    identifier = run['run']['id']
    client = TestClient(app, base_url=database.settings.origin, raise_server_exceptions=False)
    try:
        client.cookies.set(COOKIE_NAME, token)
        if action == 'get':
            response = client.get('/api/v1/jobs/' + identifier)
        else:
            response = client.post('/api/v1/jobs/' + identifier + '/cancel',
                json={'expected_revision': 1}, headers=command(headers, 'generic-cancel'))
    finally:
        client.close()
    assert response.status_code == 200, response.text
    snapshot = JobSnapshot.model_validate(response.json())
    assert snapshot.id == identifier and snapshot.workspace_id == identity.workspace_id
    assert snapshot.kind == 'tutor' and snapshot.result_refs == snapshot.warnings == []
    assert snapshot.error is None and '请解释条件' not in response.text
    assert snapshot.status == ('queued' if action == 'get' else 'cancelled')
    with database.connect() as connection:
        row = connection.execute('SELECT * FROM jobs WHERE id=?', (identifier,)).fetchone()
        assert snapshot.revision == row['revision']
        assert snapshot.created_at == row['created_at'] and snapshot.updated_at == row['updated_at']


def running(http_tutor):
    database, identity, _, _, _, _, _, _ = http_tutor
    _, _, _, run = start(http_tutor)
    identifier = run['run']['id']
    with database.transaction() as connection:
        repo = TutorRepository(connection, identity.workspace_id)
        lease = repo.jobs.claim(repo.jobs.load(identifier), 90)
        repo.sync_job(identifier)
    return identifier, lease


def finish_cancel(http_tutor, identifier, lease):
    database, identity, _, _, _, _, _, _ = http_tutor
    with database.transaction() as connection:
        repo = TutorRepository(connection, identity.workspace_id)
        view = repo.view(identifier)
        repo.finish(identifier, 'cancelled', view.result, '', lease=lease)


def test_generic_original_ack_and_terminal_noop_replay_preserve_real_old_event(http_tutor):
    database, _, _, _, client, headers, _, _ = http_tutor
    identifier, lease = running(http_tutor)
    path = '/api/v1/jobs/' + identifier + '/cancel'
    body = {'expected_revision': lease.revision}
    stop = client.post(path, json=body, headers=command(headers, 'stop'))
    assert stop.status_code == 200, stop.text
    original = JobSnapshot.model_validate(stop.json())
    assert original.status == 'running' and original.revision == lease.revision + 1
    with database.connect() as connection:
        row = connection.execute('SELECT * FROM jobs WHERE id=?', (identifier,)).fetchone()
        assert row['cancel_requested'] and row['lease_owner'] == lease.owner
    finish_cancel(http_tutor, identifier, lease)
    terminal = client.get('/api/v1/jobs/' + identifier)
    assert terminal.status_code == 200
    assert terminal.json()['revision'] == original.revision + 1
    assert terminal.json()['updated_at'] > original.updated_at
    before = all_rows(database)
    replay = client.post(path, json=body, headers=command(headers, 'stop'))
    assert replay.status_code == 200 and replay.json() == original.model_dump(mode='json')
    assert all_rows(database) == before
    # Stale expected_revision on a terminal task is a no-op, including exactly r-1.
    stale = {'expected_revision': original.revision}
    noop = client.post(path, json=stale, headers=command(headers, 'terminal-noop'))
    assert noop.status_code == 200 and noop.json() == terminal.json()
    before = all_rows(database)
    repeated = client.post(path, json=stale, headers=command(headers, 'terminal-noop'))
    assert repeated.status_code == 200 and repeated.json() == noop.json()
    assert all_rows(database) == before


def test_generic_and_run_cancel_route_identity_are_independent_and_preserve_body(http_tutor):
    database, _, _, _, client, headers, _, _ = http_tutor
    _, _, _, run = start(http_tutor)
    identifier = run['run']['id']
    generic, specific = '/api/v1/jobs/' + identifier + '/cancel', '/api/v1/runs/' + identifier + '/cancel'
    body = {'expected_revision': 1}
    before = all_rows(database)
    stale = client.post(generic, json={'expected_revision': 2}, headers=command(headers, 'stale'))
    assert stale.status_code == 412 and all_rows(database) == before
    stopped = client.post(generic, json=body, headers=command(headers, 'same-key'))
    assert stopped.status_code == 200
    control = client.post(specific, json=body, headers=command(headers, 'same-key'))
    assert control.status_code == 200
    assert set(control.json()) == {'id', 'status', 'job_revision', 'cancel_requested'}
    with database.connect() as connection:
        routes = connection.execute("SELECT route FROM tutor_commands WHERE key='same-key' ORDER BY route").fetchall()
        assert [row[0] for row in routes] == [f'POST /jobs/{identifier}/cancel', f'POST /runs/{identifier}/cancel']
    before = all_rows(database)
    assert client.post(generic, json=body, headers=command(headers, 'same-key')).json() == stopped.json()
    assert client.post(specific, json=body, headers=command(headers, 'same-key')).json() == control.json()
    conflict = client.post(generic, json={'expected_revision': 2}, headers=command(headers, 'same-key'))
    assert conflict.status_code == 409 and conflict.json()['error']['code'] == 'IDEMPOTENCY_CONFLICT'
    assert all_rows(database) == before


@pytest.mark.parametrize('mode', ['independent', 'open_book'])
def test_generic_control_under_real_assessment_policy_has_no_subject_payload(http_tutor, mode):
    from services.api.app.application.assessment import AssessmentService
    from services.api.app.assessment_dto import AssessmentAttemptCreate
    from services.api.app.infrastructure.content_repository import reference
    from tests.assessment_fixtures import assessment_fixture
    from tests.integration.test_assessment_attempts import import_fixture

    database, identity, _, _, client, headers, _, _ = http_tutor
    _, _, _, run = start(http_tutor)
    identifier = run['run']['id']
    path = '/api/v1/jobs/' + identifier
    stopped = client.post(path + '/cancel', json={'expected_revision': 1}, headers=command(headers, 'stop'))
    assert stopped.status_code == 200
    fixture = assessment_fixture('genericpolicy' + mode.replace('_', ''))
    import_fixture(database, identity, fixture, 'policy-source')
    AssessmentService(database).create_attempt(identity, fixture.assessment.id,
        AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode=mode), 'attempt')
    assert client.get('/api/v1/runs/' + identifier).status_code == 409
    before = all_rows(database)
    snapshot = client.get(path)
    replay = client.post(path + '/cancel', json={'expected_revision': 1}, headers=command(headers, 'stop'))
    assert snapshot.status_code == replay.status_code == 200
    assert snapshot.json() == replay.json() == stopped.json()
    assert set(snapshot.json()) == set(JobSnapshot.model_fields)
    assert snapshot.json()['result_refs'] == snapshot.json()['warnings'] == []
    assert snapshot.json()['error'] is None
    assert all_rows(database) == before


@pytest.mark.parametrize('fault', ['later_real_snapshot', 'private_progress', 'missing_user'])
def test_generic_original_ack_rejects_forged_or_missing_owned_history(http_tutor, fault):
    from packages.contracts.canonical import canonical_bytes, sha256_bytes

    database, _, _, _, client, headers, _, _ = http_tutor
    identifier, lease = running(http_tutor)
    path = '/api/v1/jobs/' + identifier + '/cancel'
    body = {'expected_revision': lease.revision}
    original = client.post(path, json=body, headers=command(headers, 'stop'))
    assert original.status_code == 200
    finish_cancel(http_tutor, identifier, lease)
    later = client.get('/api/v1/jobs/' + identifier)
    assert later.status_code == 200 and later.json()['revision'] > original.json()['revision']
    with database.transaction() as connection:
        if fault == 'missing_user':
            ids = [row[0] for row in connection.execute("SELECT id FROM messages WHERE run_id=? AND role='user'", (identifier,))]
            assert len(ids) == 1
            connection.execute('DELETE FROM tutor_messages WHERE message_id=?', (ids[0],))
            connection.execute('DELETE FROM messages WHERE id=?', (ids[0],))
        else:
            forged = later.json() if fault == 'later_real_snapshot' else original.json()
            if fault == 'private_progress':
                forged['progress']['label'] = '不应通过控制回执输出的合成正文'
            raw = canonical_bytes(forged)
            connection.execute("UPDATE tutor_commands SET ack_json=?,ack_sha256=? WHERE route=? AND key='stop'",
                (raw.decode(), sha256_bytes(raw), f'POST /jobs/{identifier}/cancel'))
    before = all_rows(database)
    refused = client.post(path, json=body, headers=command(headers, 'stop'))
    assert refused.status_code == 409 and refused.json()['error']['code'] == 'TUTOR_INTEGRITY_ERROR'
    assert all_rows(database) == before


def test_corrupt_original_cancel_timestamp_is_a_safe_integrity_failure(http_tutor):
    database, _, token, app, _, headers, _, _ = http_tutor
    _, _, _, run = start(http_tutor)
    identifier = run['run']['id']
    path = '/api/v1/jobs/' + identifier + '/cancel'
    body = {'expected_revision': 1}
    client = TestClient(app, base_url=database.settings.origin, raise_server_exceptions=False)
    client.cookies.set(COOKIE_NAME, token)
    try:
        original = client.post(path, json=body, headers=command(headers, 'stop'))
        assert original.status_code == 200
        with database.transaction() as connection:
            connection.execute("UPDATE tutor_commands SET created_at='invalid-time' WHERE route=? AND key='stop'",
                (f'POST /jobs/{identifier}/cancel',))
        before = all_rows(database)
        refused = client.post(path, json=body, headers=command(headers, 'stop'))
        assert refused.status_code == 409 and refused.json()['error']['code'] == 'TUTOR_INTEGRITY_ERROR'
        assert 'invalid-time' not in refused.text and all_rows(database) == before
    finally:
        client.close()
