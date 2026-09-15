"""Real local HTTP shape checks, without worker, browser or provider calls."""

import json

from fastapi.testclient import TestClient
from starlette.requests import Request
import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from services.api.app.application.content import ContentService
from services.api.app.application.retrieval import RetrievalService, json_bytes
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import issue_bootstrap_code
from services.api.app.main import create_app
from services.api.app.retrieval_dto import RetrievalQueryWrite
from tests.integration.test_retrieval import all_rows


@pytest.fixture
def local_http(tmp_path):
    database = Database(Settings(data_dir=tmp_path / 'http'))
    workspace = database.initialize()
    text = '真实未审 HTTP 边界材料：概率 😀\n'.encode()
    block = dm.ContentBlock(id='block_http_retrieval', revision=1, kind='text', title='合成未审材料',
        body_path='content/http-retrieval.md', body_sha256=sha256_bytes(text))
    ContentService(database).publish(workspace, [block], {block.body_path: text})
    application = create_app(database.settings)
    # No lifespan: keep workers stopped so queued/missing observations are exact.
    client = TestClient(application, base_url=database.settings.origin)
    bootstrap = client.post('/api/v1/session/bootstrap', json={'one_time_code': issue_bootstrap_code(database)},
                            headers={'Origin': database.settings.origin})
    assert bootstrap.status_code == 200
    headers = {'Origin': database.settings.origin, 'X-CSRF-Token': bootstrap.json()['csrf_token']}
    yield database, client, headers, reference(block).model_dump(mode='json')
    client.close()


def test_actual_scope_get_and_query_are_zero_write_and_rebuild_is_202_original_job(local_http):
    database, client, headers, ref = local_http
    before = all_rows(database)
    overview = client.get('/api/v1/index/status')
    assert overview.status_code == 200 and overview.json() == {'kind': 'overview', 'items': [], 'next_cursor': None}
    status = client.get('/api/v1/index/status', params={'scope_refs': json.dumps([ref, ref])})
    assert status.status_code == 200 and status.json()['state'] == 'missing'
    assert status.json()['scope_refs'] == [ref]
    body = {'query': '概率', 'scope_refs': [ref], 'limit': 10}
    response = client.post('/api/v1/retrieval/query', json=body, headers=headers)
    assert response.status_code == 200 and response.json()['result_state'] == 'not_ready'
    assert response.headers['cache-control'] == 'no-store'
    assert all_rows(database) == before
    # The same real session checked by the boundary drives the independent
    # application read; compare the exact complete HTTP encoding, not an estimate.
    from services.api.app.infrastructure.security import authenticate
    cookie = client.build_request('GET', '/').headers['cookie']
    identity = authenticate(database, Request({'type': 'http', 'headers': [(b'cookie', cookie.encode())]}))
    expected = RetrievalService(database).query(identity, RetrievalQueryWrite.model_validate(body))
    assert response.content == json_bytes(expected)
    rebuild = {'scope_refs': [ref], 'expected_corpus_sha256': status.json()['corpus_sha256'],
               'provider_id': None, 'consent_id': None}
    unsupported = client.post('/api/v1/index/rebuild', json={**rebuild, 'provider_id': 'provider_unused'},
                              headers={**headers, 'Idempotency-Key': 'unsupported'})
    assert unsupported.status_code == 409 and unsupported.json()['error']['code'] == 'CAPABILITY_UNSUPPORTED'
    assert all_rows(database) == before
    ack = client.post('/api/v1/index/rebuild', json=rebuild, headers={**headers, 'Idempotency-Key': 'build-original'})
    assert ack.status_code == 202 and ack.json()['status'] == 'queued' and set(ack.json()) == {'id', 'status'}
    after = all_rows(database)
    replay = client.post('/api/v1/index/rebuild', json=rebuild, headers={**headers, 'Idempotency-Key': 'build-original'})
    assert replay.status_code == 202 and replay.json() == ack.json()
    assert all_rows(database) == after


@pytest.mark.parametrize('params', [
    [('limit', '1'), ('limit', '2')], {'unknown': 'x'}, {'scope_refs': '[]', 'limit': '20'},
    {'scope_refs': '[]', 'cursor': 'abc'}, {'scope_refs': ''}, {'scope_refs': '[]'},
    {'scope_refs': 'null'}, {'scope_refs': '{}'}, {'scope_refs': '[NaN]'},
    {'cursor': ''}, {'cursor': ' '}, {'limit': 'true'}, {'limit': '1.0'},
    {'limit': '１'}, {'limit': '0'}, {'limit': '101'},
    {'scope_refs': '[{"entity":"block","entity":"course","id":"block_x","revision":1,"sha256":"' + 'a' * 64 + '"}]'},
])
def test_scope_url_rejects_duplicate_mixed_non_json_and_non_integer_fields_without_writes(local_http, params):
    database, client, _, _ = local_http
    before = all_rows(database)
    response = client.get('/api/v1/index/status', params=params)
    assert response.status_code == 422 and response.json()['error']['code'] == 'SCHEMA_INVALID'
    assert all_rows(database) == before


def test_query_requires_csrf_and_strict_json_but_no_command_key(local_http):
    database, client, headers, ref = local_http
    before = all_rows(database)
    body = {'query': '概率', 'scope_refs': [ref], 'limit': 1}
    assert client.post('/api/v1/retrieval/query', json=body,
                       headers={'Origin': database.settings.origin}).status_code == 403
    encoded = json.dumps(body).replace('"limit": 1', '"limit": 1, "limit": 2')
    duplicate = client.post('/api/v1/retrieval/query', content=encoded,
        headers={**headers, 'Content-Type': 'application/json'})
    assert duplicate.status_code == 422
    duplicated_header = client.post('/api/v1/retrieval/query', json=body,
        headers=[*headers.items(), ('Idempotency-Key', 'same'), ('Idempotency-Key', 'same')])
    assert duplicated_header.status_code == 422
    assert client.post('/api/v1/retrieval/query', json=body, headers=headers).status_code == 200
    assert all_rows(database) == before


def test_rebuild_requires_single_key_and_has_no_implicit_if_match_header(local_http):
    database, client, headers, ref = local_http
    status = client.get('/api/v1/index/status', params={'scope_refs': json.dumps([ref])}).json()
    body = {'scope_refs': [ref], 'expected_corpus_sha256': status['corpus_sha256'],
            'provider_id': None, 'consent_id': None}
    before = all_rows(database)
    missing = client.post('/api/v1/index/rebuild', json=body, headers=headers)
    assert missing.status_code == 400 and missing.json()['error']['code'] == 'IDEMPOTENCY_KEY_INVALID'
    duplicate = client.post('/api/v1/index/rebuild', json=body,
        headers=[*headers.items(), ('Idempotency-Key', 'one'), ('Idempotency-Key', 'one')])
    assert duplicate.status_code == 422
    assert all_rows(database) == before
