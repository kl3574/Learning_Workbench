"""Real local consumption/lifecycle with an explicit protocol-only peer."""
from tests.integration.test_codex_turn_consent_http import consent_case, grant_fixture

__all__ = ['consent_case']


def start_body(preparation, consent):
    return {'preparation_id': preparation['id'], 'preparation_sha256': preparation['preparation_sha256'],
        'consent_id': consent['id'], 'expected_session_revision': preparation['session_revision']}


def test_start_really_consumes_consent_and_queues_one_job_without_execution(consent_case):
    case, runtime, sid, _, bootstrap_body, bootstrap_ack = consent_case
    _, preparation, _, _, _, consent = grant_fixture(consent_case)
    body = start_body(preparation.json(), consent.json())
    response = case.post(f'sessions/{sid}/turns', body, 'start-original')
    assert response.status_code == 202
    value = response.json()
    assert value == {'turn_id': preparation.json()['turn_id'], 'session_revision': 4,
        'job': {'id': preparation.json()['job']['id'], 'status': 'queued'}}
    before = case.dump()
    control = case.get('turns/' + value['turn_id']).json()
    assert control['job'] == value['job'] and control['job_revision'] == 2
    assert control['execution'] == 'not_started' and control['started_at'] is None
    dispatch = case.get('consents/' + consent.json()['id']).json()['dispatch']
    assert dispatch is not None and dispatch['started_at'] is None and dispatch['consumed_provider_calls'] == 0
    assert case.post(f'sessions/{sid}/turns', body, 'start-original').content == response.content
    assert case.post(f'sessions/{sid}/turns', {**body, 'expected_session_revision': 4}, 'new-start').status_code == 409
    assert case.post('sessions', bootstrap_body, 'bootstrap-session').content == bootstrap_ack
    assert case.dump() == before and len(runtime.calls) == 1
