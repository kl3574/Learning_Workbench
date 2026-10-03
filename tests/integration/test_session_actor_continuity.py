"""Non-secret actor continuity is read from the authenticated persisted session."""
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from services.api.app.dto import SessionResponse
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import COOKIE_NAME, issue_bootstrap_code, token_hash
from services.api.app.main import create_app
from tests.integration.test_retrieval import all_rows
from tests.integration.test_authoring_http import command
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_draft_edit_http import published_base
from tests.integration.test_review_http import prepared_review_http as prepared_review_http


def test_actual_session_actor_survives_reload_role_cycle_and_app_restart(tmp_path):
    settings = Settings(data_dir=tmp_path / 'data')
    database = Database(settings)
    workspace = database.initialize()
    client = TestClient(create_app(settings), base_url=settings.origin)
    bootstrap = client.post('/api/v1/session/bootstrap', json={'one_time_code': issue_bootstrap_code(database)},
        headers={'Origin': settings.origin})
    assert bootstrap.status_code == 200
    cookie = client.cookies[COOKIE_NAME]
    with database.connect() as connection:
        actor = connection.execute('SELECT id FROM local_sessions WHERE token_hash=?', (token_hash(cookie),)).fetchone()[0]
    before = all_rows(database)
    response = client.get('/api/v1/session')
    session = response.json()
    assert session['actor_session_id'] == actor
    assert session['workspace_id'] == workspace
    assert actor not in {cookie, token_hash(cookie), session['csrf_token'], token_hash(session['csrf_token'])}
    assert response.headers['cache-control'] == 'no-store'
    assert client.get('/api/v1/session').json() == session
    assert all_rows(database) == before
    headers = {'Origin': settings.origin, 'X-CSRF-Token': session['csrf_token']}
    author = client.post('/api/v1/session/role', json={'role': 'author'}, headers={**headers, 'Idempotency-Key': 'author'})
    assert author.status_code == 200 and author.json()['actor_session_id'] == actor
    assert author.headers['cache-control'] == 'no-store'
    assert set(author.json()) == set(session)
    learner = client.post('/api/v1/session/role', json={'role': 'learner'}, headers={**headers, 'Idempotency-Key': 'learner'})
    assert learner.status_code == 200 and learner.json()['actor_session_id'] == actor
    # Original role ACK is a receipt, not the current role after the later change.
    assert client.post('/api/v1/session/role', json={'role': 'author'}, headers={**headers, 'Idempotency-Key': 'author'}).json() == author.json()
    assert client.get('/api/v1/session').json()['role'] == 'learner'
    client.close()
    restarted = TestClient(create_app(settings), base_url=settings.origin)
    restarted.cookies.set(COOKIE_NAME, cookie)
    before = all_rows(database)
    assert restarted.get('/api/v1/session').json() == session
    assert all_rows(database) == before
    assert restarted.get('/api/v1/session', params={'actor_session_id': 'session_forged'}).status_code == 422
    assert restarted.get('/api/v1/session', headers={'X-Actor-Session-ID': 'session_forged'}).json()['actor_session_id'] == actor
    forged = restarted.post('/api/v1/session/role', json={'role': 'author', 'actor_session_id': 'session_forged'},
        headers={**headers, 'Idempotency-Key': 'forged'})
    assert forged.status_code == 422
    assert all_rows(database) == before
    fresh = restarted.post('/api/v1/session/bootstrap', json={'one_time_code': issue_bootstrap_code(database)},
        headers={'Origin': settings.origin})
    assert fresh.status_code == 200
    next_session = restarted.get('/api/v1/session').json()
    assert next_session['workspace_id'] == workspace and next_session['actor_session_id'] != actor
    restarted.close()


def test_actor_is_required_and_closed_in_both_actual_response_contracts():
    value = {'workspace_id': 'workspace_test', 'role': 'learner', 'csrf_token': 'synthetic-only',
        'active_independent_attempt_id': None, 'active_open_book_attempt_id': None}
    with pytest.raises(ValidationError):
        SessionResponse.model_validate(value)
    value['actor_session_id'] = 'session_independent_id'
    assert SessionResponse.model_validate(value).actor_session_id == value['actor_session_id']
    with pytest.raises(ValidationError):
        SessionResponse.model_validate({**value, 'actor_id': 'session_forged'})


def test_edit_original_ack_requires_current_role_and_server_actor_is_not_client_claim(prepared_review_http):
    case = prepared_review_http
    base = published_base(case)
    actor = case.client.get('/api/v1/session').json()['actor_session_id']
    create = {'kind': 'block', 'base_ref': base.model_dump(mode='json'), 'title': 'Synthetic continuity'}
    created = case.client.post('/api/v1/drafts', json=create, headers={**command(case.headers, 'actor-create'), 'X-Actor-Session-ID': 'session_forged'})
    assert created.status_code == 201
    path = '/api/v1/drafts/' + created.json()['draft_id']
    patch = {'expected_revision': 1, 'patches': [{'field': 'title', 'value': 'Synthetic original title'}]}
    changed = case.client.patch(path, json=patch, headers=command(case.headers, 'actor-patch'))
    assert changed.status_code == 200
    before = table_hashes(case.database)
    assert case.client.post('/api/v1/drafts', json={**create, 'actor_session_id': 'session_forged'}, headers=command(case.headers, 'forged-create')).status_code == 422
    assert case.client.patch(path, json={**patch, 'actor_session_id': 'session_forged'}, headers=command(case.headers, 'forged-patch')).status_code == 422
    assert table_hashes(case.database) == before
    with case.database.connect() as connection:
        assert {row[0] for row in connection.execute('SELECT actor_id FROM draft_edit_commands')} == {actor}
    assert case.client.post('/api/v1/session/role', json={'role': 'learner'}, headers=command(case.headers, 'continuity-learner')).status_code == 200
    before = table_hashes(case.database)
    assert case.client.post('/api/v1/drafts', json=create, headers=command(case.headers, 'actor-create')).status_code == 403
    assert case.client.patch(path, json=patch, headers=command(case.headers, 'actor-patch')).status_code == 403
    assert table_hashes(case.database) == before
    assert case.client.post('/api/v1/session/role', json={'role': 'author'}, headers=command(case.headers, 'continuity-author')).status_code == 200
    assert case.client.get('/api/v1/session').json()['actor_session_id'] == actor
    before = table_hashes(case.database)
    assert case.client.post('/api/v1/drafts', json=create, headers=command(case.headers, 'actor-create')).json() == created.json()
    assert case.client.patch(path, json=patch, headers=command(case.headers, 'actor-patch')).json() == changed.json()
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('mode,field', [('independent', 'active_independent_attempt_id'), ('open_book', 'active_open_book_attempt_id')])
def test_actual_session_policy_blocks_original_edit_http_replay(prepared_review_http, mode, field):
    from services.api.app.infrastructure.content_repository import reference
    from tests.assessment_fixtures import assessment_fixture
    from tests.integration.test_assessment_attempts import import_fixture
    case = prepared_review_http
    base = published_base(case)
    body = {'kind': 'block', 'base_ref': base.model_dump(mode='json'), 'title': 'Synthetic Policy continuity'}
    created = case.client.post('/api/v1/drafts', json=body, headers=command(case.headers, 'policy-create'))
    assert created.status_code == 201
    path = '/api/v1/drafts/' + created.json()['draft_id']
    patch = {'expected_revision': 1, 'patches': [{'field': 'title', 'value': 'Synthetic protected edit'}]}
    assert case.client.patch(path, json=patch, headers=command(case.headers, 'policy-patch')).status_code == 200
    fixture = assessment_fixture('actorpolicy')
    import_fixture(case.database, case.identity, fixture, 'actor-policy-fixture')
    attempt = case.client.post(f'/api/v1/assessments/{fixture.assessment.id}/attempts',
        json={'assessment_ref': reference(fixture.assessment).model_dump(mode='json'), 'mode': mode}, headers=command(case.headers, 'policy-attempt'))
    assert attempt.status_code == 201, attempt.text
    before = table_hashes(case.database)
    session = case.client.get('/api/v1/session')
    assert session.status_code == 200 and session.json()[field]
    assert session.json()['actor_session_id'] == case.identity.id
    assert case.client.post('/api/v1/drafts', json=body, headers=command(case.headers, 'policy-create')).status_code == 409
    assert case.client.patch(path, json=patch, headers=command(case.headers, 'policy-patch')).status_code == 409
    assert table_hashes(case.database) == before
