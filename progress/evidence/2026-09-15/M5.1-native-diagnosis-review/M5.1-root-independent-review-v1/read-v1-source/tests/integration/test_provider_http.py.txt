"""Actual local HTTP controls and frozen consent persistence; no provider calls."""

from datetime import UTC, datetime, timedelta
import socket

from fastapi.testclient import TestClient
import pytest

from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.security import issue_bootstrap_code
from services.api.app.main import create_app
from tests.provider_fixture import provider_source
from tests.integration.test_provider_consents import ControlledPreparation


def client_for(database, *, source_registry=None, preparer=None):
    application = create_app(database.settings, outbound_sources=source_registry, request_preparer=preparer)
    application.state.provider_service.secret_store.initialize()
    client = TestClient(application, base_url=database.settings.origin)
    response = client.post('/api/v1/session/bootstrap', json={'one_time_code': issue_bootstrap_code(database)},
                           headers={'Origin': database.settings.origin})
    assert response.status_code == 200
    return client, {'Origin': database.settings.origin, 'X-CSRF-Token': response.json()['csrf_token']}


def config_body(revision=0):
    return {'expected_revision': revision, 'adapter': 'compatible_chat',
            'base_url': 'https://provider.example/v1', 'model': 'controlled-byte-model',
            'embedding_model': None, 'endpoint_policy': 'public_https', 'pricing': None}


def write_headers(headers, key):
    return {**headers, 'Idempotency-Key': key}


def no_network(monkeypatch):
    attempts = []
    def forbidden(*args, **kwargs):
        attempts.append(True)
        raise AssertionError('configuration/consent HTTP must never resolve a remote destination')
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    return attempts


def test_real_http_config_secret_original_ack_current_read_and_exact_delete(tmp_path, monkeypatch):
    database = Database(Settings(data_dir=tmp_path / 'http-config'))
    database.initialize()
    client, headers = client_for(database)
    attempts = no_network(monkeypatch)
    path = '/api/v1/providers/provider_http/config'
    first = client.put(path, json=config_body(), headers=write_headers(headers, 'create'))
    assert first.status_code == 200
    assert first.json()['revision'] == 1 and first.json()['secret_present'] is False
    secret_path = '/api/v1/providers/provider_http/secret'
    original = {'expected_revision': 1, 'secret': 'synthetic-http-secret-first'}
    saved = client.post(secret_path, json=original, headers=write_headers(headers, 'save-original'))
    assert saved.status_code == 200 and saved.json()['revision'] == 2
    changed = client.post(secret_path, json={'expected_revision': 2, 'secret': 'synthetic-http-secret-second'},
                          headers=write_headers(headers, 'replace'))
    assert changed.status_code == 200 and changed.json()['revision'] == 3
    replay = client.post(secret_path, json=original, headers=write_headers(headers, 'save-original'))
    assert replay.json() == saved.json()
    current = client.get(path)
    assert current.json()['revision'] == 3 and current.json()['secret_present'] is True
    capabilities = client.get('/api/v1/providers/capabilities')
    assert capabilities.status_code == 200
    assert capabilities.json()['items'][0]['configured'] is True
    assert capabilities.json()['items'][0]['chat'] is False
    assert capabilities.json()['items'][0]['streaming'] is False
    assert client.get('/api/v1/readiness').json()['providers_configured'] is True
    # A fresh factory and a newly bootstrapped session reuse durable complete
    # commands, not the previous process's in-memory acknowledgement.
    restarted, restarted_headers = client_for(database)
    replay_after_restart = restarted.post(secret_path, json=original,
                                         headers=write_headers(restarted_headers, 'save-original'))
    assert replay_after_restart.json() == saved.json()
    assert restarted.get(path).json() == current.json()
    stale = client.delete(secret_path, headers={**write_headers(headers, 'stale-delete'),
                                               'If-Match': '"' + saved.json()['config_sha256'] + '"'})
    assert stale.status_code == 412
    deleted = client.delete(secret_path, headers={**write_headers(headers, 'delete'),
                                                 'If-Match': '"' + current.json()['config_sha256'] + '"'})
    assert deleted.status_code == 200 and deleted.json()['revision'] == 4
    assert deleted.json()['secret_present'] is False
    for response in (first, saved, changed, replay, current, capabilities, stale, deleted):
        assert 'synthetic-http-secret' not in response.text
        assert 'locator' not in response.text and 'fingerprint' not in response.text
        assert response.headers['cache-control'] == 'no-store'
    assert attempts == []


def test_real_independent_attempt_blocks_summaries_and_grant_replay_but_keeps_controls_and_revoke(tmp_path):
    from services.api.app.application.assessment import AssessmentService
    from services.api.app.application.errors import ApiError
    from services.api.app.provider_dto import ConsentPreviewWrite
    from tests.assessment_fixtures import assessment_fixture
    from tests.integration.test_assessment_attempts import import_fixture, start
    from tests.integration.test_recommendation_source_ports import all_table_rows

    database, identity, source, registry, job = provider_source(tmp_path)
    client, headers = client_for(database, source_registry=registry, preparer=ControlledPreparation())
    config_path = '/api/v1/providers/provider_policy/config'
    assert client.put(config_path, json=config_body(), headers=write_headers(headers, 'config')).status_code == 200
    assert client.post('/api/v1/providers/provider_policy/secret', json={'expected_revision': 1,
        'secret': 'synthetic-policy-key'}, headers=write_headers(headers, 'secret')).status_code == 200
    preview_body = {'job_id': job, 'expected_job_revision': 1, 'provider_id': 'provider_policy',
        'expected_provider_revision': 2, 'expires_at': (datetime.now(UTC) + timedelta(hours=1)).isoformat().replace('+00:00', 'Z'),
        'budget': {'max_input_tokens': 10000, 'max_output_tokens': 100, 'max_provider_calls': 1,
                   'max_search_calls': 0, 'max_tool_calls': 0, 'max_cost_usd': None}}
    proposal = client.app.state.consent_service.preview(identity, ConsentPreviewWrite.model_validate(preview_body), 'preview')
    grant_body = {'proposal_id': proposal.id, 'proposal_sha256': proposal.proposal_sha256}
    granted = client.post('/api/v1/consents', json=grant_body, headers=write_headers(headers, 'grant-original'))
    assert granted.status_code == 201
    fixture = assessment_fixture('providerpolicy')
    import_fixture(database, identity, fixture, 'policy-material')
    storage = (database, identity, fixture, AssessmentService(database))
    with pytest.raises(ApiError) as excluded:
        start(storage, key='cannot-overlap-source')
    assert excluded.value.code == 'SUBJECT_WORK_ACTIVE'
    source.cancel(identity, job)
    assert start(storage, key='start-after-source-cancelled').status == 'active'
    before = all_table_rows(database)
    for response in (
        client.get('/api/v1/consents'),
        client.get('/api/v1/consents/preview/' + proposal.id),
        client.post('/api/v1/consents', json=grant_body, headers=write_headers(headers, 'grant-original')),
        client.post('/api/v1/consents/preview', json=preview_body, headers=write_headers(headers, 'preview')),
    ):
        assert response.status_code == 409 and response.json()['error']['code'] == 'ASSESSMENT_ACTIVE'
        assert 'references' not in response.text and 'messages' not in response.text
    assert client.get(config_path).status_code == 200
    assert client.get('/api/v1/providers/capabilities').status_code == 200
    assert all_table_rows(database) == before
    assert client.put(config_path, json=config_body(2), headers=write_headers(headers, 'control-during-attempt')).status_code == 200
    revoked = client.post('/api/v1/consents/' + granted.json()['id'] + '/revoke', json={'expected_revision': 1},
                          headers=write_headers(headers, 'stop-during-attempt'))
    assert revoked.status_code == 200 and revoked.json()['applied'] is True


@pytest.mark.parametrize('query', ['?unknown=x', '?limit=1&limit=2', '?consent_id=consent_x&limit=20',
                                   '?consent_id=consent_x&cursor=abc', '?cursor=', '?cursor=%20',
                                   '?limit=20.0', '?limit=true', '?limit=101', '?limit=0'])
def test_http_query_rejects_unknown_duplicate_mixed_or_noninteger(tmp_path, query):
    database = Database(Settings(data_dir=tmp_path / 'query'))
    database.initialize()
    client, _ = client_for(database)
    response = client.get('/api/v1/consents' + query)
    assert response.status_code == 422
    assert response.json()['error']['code'] == 'SCHEMA_INVALID'


def test_secret_endpoint_headers_and_body_are_strict_and_nonreflective(tmp_path):
    database = Database(Settings(data_dir=tmp_path / 'headers'))
    database.initialize()
    client, headers = client_for(database)
    path = '/api/v1/providers/provider_http/secret'
    body = {'expected_revision': 1, 'secret': 'synthetic-http-secret-invalid'}
    assert client.post(path, json=body, headers=headers).status_code == 400
    good = write_headers(headers, 'original-key')
    for name in ('Idempotency-Key', 'Cookie', 'X-CSRF-Token', 'Content-Type'):
        extra = {'Cookie': 'learning_session=synthetic-duplicate', 'X-CSRF-Token': headers['X-CSRF-Token'],
                 'Content-Type': 'application/json', 'Idempotency-Key': 'original-key'}[name]
        values = list(good.items()) + [(name, extra)]
        if name == 'Cookie':
            values.append((name, extra))
        if name == 'Content-Type':
            values.append((name, extra))
        result = client.post(path, json=body, headers=values)
        assert result.status_code in {400, 401, 422}
        assert body['secret'] not in result.text
    for match in ('*', '0' * 64, 'W/"' + '0' * 64 + '"', '"' + 'A' * 64 + '"'):
        assert client.delete(path, headers={**good, 'If-Match': match}).status_code == 400
    valid = {**good, 'If-Match': '"' + '0' * 64 + '"'}
    assert client.request('DELETE', path, json={}, headers=valid).status_code == 422
    for invalid in ({**body, 'expected_revision': True}, {**body, 'secret': '  '}, {**body, 'echo': True}):
        result = client.post(path, json=invalid, headers=good)
        assert result.status_code == 422 and body['secret'] not in result.text


def test_real_http_frozen_preview_grant_revoke_and_replay_without_transport(tmp_path, monkeypatch):
    database, _, source, registry, job = provider_source(tmp_path)
    client, headers = client_for(database, source_registry=registry, preparer=ControlledPreparation())
    attempts = no_network(monkeypatch)
    configured = client.put('/api/v1/providers/provider_http/config', json=config_body(), headers=write_headers(headers, 'config'))
    assert configured.status_code == 200
    secret = client.post('/api/v1/providers/provider_http/secret', json={'expected_revision': 1,
                         'secret': 'synthetic-http-grant-key'}, headers=write_headers(headers, 'secret'))
    assert secret.status_code == 200
    preview_body = {'job_id': job, 'expected_job_revision': 1, 'provider_id': 'provider_http',
        'expected_provider_revision': 2, 'expires_at': (datetime.now(UTC) + timedelta(hours=1)).isoformat().replace('+00:00', 'Z'),
        'budget': {'max_input_tokens': 10000, 'max_output_tokens': 100,
                   'max_provider_calls': 1, 'max_search_calls': 0, 'max_tool_calls': 0, 'max_cost_usd': None}}
    response = client.post('/api/v1/consents/preview', json=preview_body, headers=write_headers(headers, 'preview'))
    assert response.status_code == 201
    proposal = response.json()
    assert proposal['summary']['budget']['timeout_seconds'] == 180
    assert proposal['summary']['references'][0]['character_count'] > 0
    assert 'content' not in proposal['summary']['messages'][0]
    grant_body = {'proposal_id': proposal['id'], 'proposal_sha256': proposal['proposal_sha256']}
    granted = client.post('/api/v1/consents', json=grant_body, headers=write_headers(headers, 'grant-original'))
    assert granted.status_code == 201 and granted.json()['status'] == 'active'
    identifier = granted.json()['id']
    current = client.get('/api/v1/consents', params={'consent_id': identifier})
    assert current.status_code == 200 and current.json()['items'][0]['dispatch'] is None
    revoked = client.post('/api/v1/consents/' + identifier + '/revoke', json={'expected_revision': 1},
                          headers=write_headers(headers, 'revoke'))
    assert revoked.status_code == 200 and revoked.json()['applied'] is True
    original = client.post('/api/v1/consents', json=grant_body, headers=write_headers(headers, 'grant-original'))
    assert original.json() == granted.json()
    now = client.get('/api/v1/consents', params={'consent_id': identifier})
    assert now.json()['items'][0]['status'] == 'revoked'
    assert now.json()['items'][0]['summary'] == proposal['summary']
    assert client.post('/api/v1/consents', json=grant_body, headers=write_headers(headers, 'new-grant')).status_code == 409
    assert attempts == []
