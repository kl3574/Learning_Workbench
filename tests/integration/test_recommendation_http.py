"""Real recommendation HTTP boundary and immutable command replay, no mock handlers."""

from fastapi.testclient import TestClient
import pytest

from packages.contracts import domain_models as dm
from services.api.app.application.profile import ProfileService
from services.api.app.application.recommendations import RecommendationWorker
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import issue_bootstrap_code
from services.api.app.main import create_app
from tests.integration.test_assessment_attempts import start
from tests.integration.test_learning_evidence import storage as evidence_storage
from tests.integration.test_learner_profile import request as profile_request
from tests.integration.test_recommendation_source_ports import all_table_rows


def client_for(database):
    client = TestClient(create_app(database.settings), base_url=database.settings.origin)
    response = client.post('/api/v1/session/bootstrap', json={'one_time_code': issue_bootstrap_code(database)},
                           headers={'Origin': database.settings.origin})
    assert response.status_code == 200
    headers = {'Origin': database.settings.origin, 'X-CSRF-Token': response.json()['csrf_token']}
    return client, headers


@pytest.fixture
def storage(tmp_path):
    return evidence_storage.__wrapped__(tmp_path)


def test_empty_http_reads_and_invalid_commands_have_no_persistence_effect(tmp_path):
    database = Database(Settings(data_dir=tmp_path / 'http-empty'))
    database.initialize()
    client, headers = client_for(database)
    before = all_table_rows(database)
    page = client.get('/api/v1/recommendations')
    assert page.status_code == 200
    assert page.json()['projection_state'] == 'missing' and page.json()['items'] == []
    assert page.json()['snapshot_id'] is None and page.json()['generated_at'] is None
    assert page.headers['cache-control'] == 'no-store'
    for query in ('?unknown=1', '?limit=1&limit=2', '?limit=101', '?limit=0', '?limit=true',
                  '?recommendation_id=recommendation_missing&course_id=course_missing',
                  '?recommendation_id=recommendation_missing&cursor=fake'):
        assert client.get('/api/v1/recommendations' + query).status_code == 422
    assert client.get('/api/v1/recommendations?recommendation_id=recommendation_missing').status_code == 404
    path = '/api/v1/recommendations/recommendation_missing/decision'
    body = {'decision': 'accepted', 'reason': None}
    assert client.post(path, json=body, headers=headers).status_code == 400
    for match in ('*', '0' * 64, 'W/"' + '0' * 64 + '"', '"' + 'A' * 64 + '"'):
        assert client.post(path, json=body, headers={**headers, 'Idempotency-Key': 'original', 'If-Match': match}).status_code == 400
    valid = {**headers, 'Idempotency-Key': 'original', 'If-Match': '"' + '0' * 64 + '"'}
    assert client.post(path, json=body, headers=valid).status_code == 404
    for changed in ({'decision': 'accepted'}, {'decision': 'pending', 'reason': None},
                    {**body, 'revision': 2}, {**body, 'reason': False}):
        assert client.post(path, json=changed, headers=valid).status_code == 422
    for name in ('Idempotency-Key', 'If-Match'):
        duplicate = list(valid.items()) + [(name, valid[name])]
        assert client.post(path, json=body, headers=duplicate).status_code == 400
    assert client.post(path, json=body, headers={**valid, 'X-CSRF-Token': 'invalid'}).status_code == 403
    assert all_table_rows(database) == before


def test_http_ack_replay_current_correction_history_and_policy_are_distinct(storage):
    database, identity, fixture, assessment = storage
    profile = ProfileService(database)
    profile.save(identity, profile_request(goal_concept_ids=[fixture.concept.id]), 'goal')
    assert RecommendationWorker(database).run_once()
    client, headers = client_for(database)
    before = all_table_rows(database)
    listed = client.get('/api/v1/recommendations').json()
    assert listed['projection_state'] == 'ready' and listed['items']
    assert all_table_rows(database) == before
    first = listed['items'][0]
    path = f"/api/v1/recommendations/{first['id']}/decision"
    original_headers = {**headers, 'Idempotency-Key': 'accept-original', 'If-Match': f'"{first["decision_sha256"]}"'}
    original_body = {'decision': 'accepted', 'reason': None}
    original = client.post(path, json=original_body, headers=original_headers)
    assert original.status_code == 200 and original.json() == {'id': first['id'], 'revision': 2, 'applied': True}
    current = client.get('/api/v1/recommendations', params={'recommendation_id': first['id']}).json()['items'][0]
    assert current['decision'] == 'accepted' and current['decision_revision'] == 2
    correction_headers = {**headers, 'Idempotency-Key': 'correct', 'If-Match': f'"{current["decision_sha256"]}"'}
    correction = client.post(path, json={'decision': 'dismissed', 'reason': 'Changed plan'}, headers=correction_headers)
    assert correction.status_code == 200 and correction.json()['revision'] == 3
    after = all_table_rows(database)
    assert client.post(path, json=original_body, headers=original_headers).json() == original.json()
    assert all_table_rows(database) == after
    assert client.post(path, json=original_body, headers={**original_headers, 'Idempotency-Key': 'new-stale-cas'}).status_code == 412
    profile.save(identity, profile_request(2, goals=['New plan'], goal_concept_ids=[]), 'new-goal')
    assert RecommendationWorker(database).run_once()
    historical = client.get('/api/v1/recommendations', params={'recommendation_id': first['id']}).json()
    assert historical['projection_state'] == 'stale' and historical['items'][0]['decision'] == 'dismissed'
    assert client.post(path, json=original_body, headers=original_headers).json() == original.json()
    active = start(storage, key='policy-after-ack')
    assert client.get('/api/v1/recommendations', params={'recommendation_id': first['id']}).status_code == 409
    assert client.post(path, json=original_body, headers=original_headers).status_code == 409
    assessment.abandon(identity, active.id, dm.AttemptSubmit(expected_revision=1), 'release-policy')
    assert client.post(path, json=original_body, headers=original_headers).json() == original.json()
