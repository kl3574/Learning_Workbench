"""HTTP security, strict DTOs, read-only errors and original command replay."""

from dataclasses import replace

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from services.api.app.evidence_applicability_dto import (
    EvidenceApplicabilityDecisionView, EvidenceImpactDecisionReceipt, EvidenceImpactDecisionWrite,
)
from services.api.app.infrastructure.security import COOKIE_NAME, consume_bootstrap, issue_bootstrap_code
from services.api.app.main import create_app
from tests.integration.test_evidence_applicability_decisions import case, change, command, tables, storage

__all__ = ['case', 'storage']


@pytest.fixture
def http_case(case):
    database, _, _, _, evidence, _ = case
    token, identity = consume_bootstrap(database, issue_bootstrap_code(database))
    with database.transaction() as conn:
        conn.execute("UPDATE local_sessions SET role='author' WHERE id=?", (identity.id,))
    author = replace(identity, role='author')
    app = create_app(database.settings)
    # Storage initialized above; do not start unrelated worker maintenance in readonly assertions.
    client = TestClient(app, base_url=database.settings.origin)
    client.cookies.set(COOKIE_NAME, token)
    event = change(case)
    headers = {'Origin': database.settings.origin, 'X-CSRF-Token': identity.csrf_token, 'Idempotency-Key': 'http-decision'}
    yield case, client, author, event, headers
    client.close()


def test_actual_http_routes_strict_origin_private_response_replay_restart(http_case):
    case, client, author, event, headers = http_case
    database, _, _, _, evidence, _ = case
    path = f'/api/v1/learning/evidence/{evidence.id}'
    before = tables(database)
    read = client.get(path + '/applicability', params={'event_id': event})
    assert read.status_code == 200, read.text
    assert read.headers['cache-control'] == 'no-store' and read.headers['vary'] == 'Cookie'
    view = EvidenceApplicabilityDecisionView.model_validate(read.json())
    assert view.event_decision_head == 0 and view.original_evidence == evidence
    assert tables(database) == before
    body = command(view, event).model_dump(mode='json')
    accepted = client.post(path + '/applicability-decisions', json=body, headers=headers)
    assert accepted.status_code == 200, accepted.text
    receipt = EvidenceImpactDecisionReceipt.model_validate(accepted.json())
    assert receipt.actor_session_id == author.id
    after = tables(database)
    assert client.post(path + '/applicability-decisions', json=body, headers=headers).json() == accepted.json()
    current = client.get(path + '/applicability').json()
    assert current['applicability'] == 'usable' and current['decisions'] == [accepted.json()]
    assert tables(database) == after
    fresh = TestClient(create_app(database.settings), base_url=database.settings.origin)
    try:
        fresh.cookies.update(client.cookies)
        assert fresh.get(path + '/applicability').json() == current
        assert fresh.post(path + '/applicability-decisions', json=body, headers=headers).json() == accepted.json()
        assert tables(database) == after
    finally:
        fresh.close()
    schema = client.app.openapi()
    route = schema['paths']['/api/v1/learning/evidence/{id}/applicability-decisions']['post']
    assert route['requestBody']['content']['application/json']['schema']['$ref'].endswith('/EvidenceImpactDecisionWrite')
    for name in ('EvidenceImpactDecisionWrite', 'EvidenceImpactDecisionReceipt', 'EvidenceApplicabilityDecisionView'):
        model = schema['components']['schemas'][name]
        assert model['additionalProperties'] is False
        assert set(model['required']) == set(model['properties'])


@pytest.mark.parametrize('query', [
    '?limit=0', '?limit=101', '?limit=true', '?limit=1.0', '?limit=+1', '?limit=',
    '?event_id=', '?event_id=null', '?event_id=event_unknown', '?event_id=event_x&event_id=event_x',
    '?cursor=', '?cursor=fake', '?limit=1&limit=1', '?extra=1',
])
def test_bad_read_query_and_body_are_422_zero_write(http_case, query):
    case, client, _, _, _ = http_case
    database, _, _, _, evidence, _ = case
    path = f'/api/v1/learning/evidence/{evidence.id}/applicability'
    before = tables(database)
    response = client.get(path + query)
    assert response.status_code == 422, response.text
    assert response.headers['cache-control'] == 'no-store'
    assert client.request('GET', path, content='{}').status_code == 422
    assert tables(database) == before


@pytest.mark.parametrize('mutation', [
    {'expected_decision_revision': True}, {'expected_decision_revision': -1}, {'reason': ' '},
    {'reason': 'x' * 2001}, {'decision': 'approved'}, {'actor_session_id': 'session_fake'},
    {'original_evidence': {}}, {'evidence_artifact_ids': ['artifact_x', 'artifact_x']},
    {'evidence_artifact_ids': None}, {'expected_current_basis_sha256': 'fake'},
])
def test_bad_commands_strict_dto_never_change_tables(http_case, mutation):
    case, client, _, event, headers = http_case
    database, _, _, _, evidence, _ = case
    root = f'/api/v1/learning/evidence/{evidence.id}'
    view = EvidenceApplicabilityDecisionView.model_validate(client.get(root + '/applicability').json())
    body = command(view, event).model_dump(mode='json') | mutation
    before = tables(database)
    response = client.post(root + '/applicability-decisions', json=body, headers=headers)
    assert response.status_code == 422, response.text
    assert tables(database) == before
    with pytest.raises(ValidationError):
        EvidenceImpactDecisionWrite.model_validate(body)


def test_origin_csrf_key_duplicate_headers_and_role_recheck(http_case):
    case, client, author, event, headers = http_case
    database, _, _, _, evidence, _ = case
    path = f'/api/v1/learning/evidence/{evidence.id}'
    view = EvidenceApplicabilityDecisionView.model_validate(client.get(path + '/applicability').json())
    body = command(view, event).model_dump(mode='json')
    before = tables(database)
    for removed, expected in [('Origin', 403), ('X-CSRF-Token', 403), ('Idempotency-Key', 400)]:
        assert client.post(path + '/applicability-decisions', json=body,
            headers={name: value for name, value in headers.items() if name != removed}).status_code == expected
    assert client.post(path + '/applicability-decisions?extra=1', json=body, headers=headers).status_code == 422
    duplicated = [*headers.items(), ('Idempotency-Key', 'another')]
    assert client.post(path + '/applicability-decisions', json=body, headers=duplicated).status_code == 400
    assert client.post(path + '/applicability-decisions', content='{"event_id":"a","event_id":"b"}',
        headers=headers | {'Content-Type': 'application/json'}).status_code == 422
    assert tables(database) == before
    assert client.post(path + '/applicability-decisions', json=body, headers=headers).status_code == 200
    with database.transaction() as conn:
        conn.execute("UPDATE local_sessions SET role='learner' WHERE id=?", (author.id,))
    before = tables(database)
    assert client.get(path + '/applicability').status_code == 403
    assert client.post(path + '/applicability-decisions', json=body, headers=headers).status_code == 403
    assert tables(database) == before
