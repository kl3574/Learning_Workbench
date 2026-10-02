"""Real HTTP/SQLite security boundary, with an owner-call tripwire.

This suite proves rejection before dispatch, not numeric owner implementation.
The production composition does not register a substitute service for it.
"""
from dataclasses import dataclass
import json

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from services.api.app.application.sessions import SessionService
from services.api.app.dto import RoleRequest
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import COOKIE_NAME, consume_bootstrap, issue_bootstrap_code
from services.api.app.interfaces.boundary import install_boundary
from services.api.app.interfaces.restore_numeric_http import create_restore_numeric_router
from tests.contract.test_restore_numeric_dto import candidate, material
from tests.integration.test_authoring_numeric_provider_history import table_hashes


class OwnerMustNotRun:
    def preview(self, *args):
        raise AssertionError('invalid transport invoked owner preview')

    def read(self, *args):
        raise AssertionError('invalid transport invoked owner read')

    def decide(self, *args):
        raise AssertionError('invalid transport invoked owner decide')


@dataclass(repr=False)
class Transport:
    database: Database
    client: TestClient
    headers: dict[str, str]


@pytest.fixture
def transport(tmp_path):
    database = Database(Settings(data_dir=tmp_path / 'data'))
    database.initialize()
    token, identity = consume_bootstrap(database, issue_bootstrap_code(database))
    SessionService(database).switch_role(identity, RoleRequest(role='author'), 'author')
    app = FastAPI()
    install_boundary(app, database.settings, database)
    app.include_router(create_restore_numeric_router(OwnerMustNotRun()))
    with TestClient(app, base_url=database.settings.origin) as client:
        client.cookies.set(COOKIE_NAME, token)
        yield Transport(database, client, {
            'Origin': database.settings.origin, 'X-CSRF-Token': identity.csrf_token,
            'Idempotency-Key': 'synthetic_command',
        })


def request_parts(endpoint):
    prefix = '/api/v1/content/'
    if endpoint == 'preview':
        return 'POST', prefix + 'restore-drafts/restore_synthetic/numeric-checks', {
            'candidate': candidate(), 'material': material(),
        }
    path = prefix + 'restore-numeric-checks/check_synthetic'
    if endpoint == 'read':
        return 'GET', path, None
    return 'POST', path + '/decision', {
        'operation_sha256': 'a' * 64, 'decision': 'decline', 'expected_revision': 1,
    }


def rejected(case, method, path, *, expected, headers=None, **kwargs):
    before = table_hashes(case.database)
    response = case.client.request(method, path, headers=headers or case.headers, **kwargs)
    assert response.status_code == expected, response.text
    assert response.headers['cache-control'] == 'no-store'
    assert table_hashes(case.database) == before
    assert set(response.json()) == {'error'}
    return response


@pytest.mark.parametrize('endpoint', ['preview', 'read', 'decision'])
@pytest.mark.parametrize('fault', ['query', 'repeated_query', 'duplicate_key', 'bad_id', 'no_session'])
def test_closed_transport_rejects_before_owner_with_zero_writes(transport, endpoint, fault):
    method, path, body = request_parts(endpoint)
    headers = list(transport.headers.items())
    expected = 422
    if fault == 'query':
        path += '?workspace_id=foreign_workspace'
    elif fault == 'repeated_query':
        path += '?revision=1&revision=1'
    elif fault == 'duplicate_key':
        headers.append(('Idempotency-Key', 'second'))
        expected = 400
    elif fault == 'bad_id':
        path = path.replace('restore_synthetic', '123_invalid').replace('check_synthetic', '123_invalid')
    else:
        transport.client.cookies.clear()
        expected = 401
    rejected(transport, method, path, expected=expected, headers=headers,
             **({'json': body} if body is not None else {}))


@pytest.mark.parametrize('endpoint', ['preview', 'decision'])
@pytest.mark.parametrize('fault', ['missing_key', 'blank_key', 'long_key', 'csrf', 'origin',
                                   'extra_actor', 'bool_revision', 'missing_body', 'duplicate_json', 'nan'])
def test_strict_write_protocol_rejects_before_owner(transport, endpoint, fault):
    method, path, body = request_parts(endpoint)
    headers = dict(transport.headers)
    expected = 422
    if fault in {'missing_key', 'blank_key', 'long_key'}:
        expected = 400
        if fault == 'missing_key':
            del headers['Idempotency-Key']
        else:
            headers['Idempotency-Key'] = '' if fault == 'blank_key' else 'x' * 129
    elif fault in {'csrf', 'origin'}:
        headers['X-CSRF-Token' if fault == 'csrf' else 'Origin'] = (
            'synthetic-invalid' if fault == 'csrf' else 'https://invalid.example')
        expected = 403
    elif fault == 'extra_actor':
        body['actor_session_id'] = 'client_claimed_actor'
    elif fault == 'bool_revision':
        if endpoint == 'preview':
            body['candidate']['draft_revision'] = True
        else:
            body['expected_revision'] = True
    elif fault == 'missing_body':
        body = None
    if fault in {'duplicate_json', 'nan'}:
        headers['Content-Type'] = 'application/json'
        raw = json.dumps(body)
        raw = raw[:-1] + (', "decision":"decline"}' if fault == 'duplicate_json' else ', "value":NaN}')
        if fault == 'duplicate_json' and endpoint == 'preview':
            raw = '{"candidate":{},' + raw[1:]
        rejected(transport, method, path, expected=expected, headers=headers, content=raw)
    else:
        rejected(transport, method, path, expected=expected, headers=headers, json=body)


@pytest.mark.parametrize('body', ['{}', ' ', '{"approval":true}'])
def test_read_rejects_every_nonempty_body_without_dispatch(transport, body):
    method, path, _ = request_parts('read')
    rejected(transport, method, path, expected=422, content=body)


def test_write_validation_error_never_reflects_private_reason(transport):
    method, path, body = request_parts('preview')
    private_reason = 'synthetic private reason must not appear in errors'
    body['material']['reason'] = private_reason
    body['material']['variable_bindings'][0]['value_source']['end_codepoint'] = False
    response = rejected(transport, method, path, expected=422, json=body)
    assert private_reason not in response.text
