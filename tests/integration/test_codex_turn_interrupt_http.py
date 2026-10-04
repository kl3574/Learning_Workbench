"""Interrupt owns its original command; ordinary Jobs owns stopping the turn."""
import pytest

from tests.integration.test_codex_turn_dispatch_http import consent_case, base_consent_case, queued
from tests.integration.test_codex_turn_consent_http import grant_fixture

__all__ = ['consent_case', 'base_consent_case']


@pytest.mark.parametrize('phase', ['awaiting_approval', 'queued'])
def test_explicit_interrupt_stops_unstarted_job_and_replays_original_ack(consent_case, phase):
    case, _, sid, _, _, _ = consent_case
    if phase == 'queued':
        prepared, _, _, _ = queued(consent_case)
    else:
        _, preparation, _, _, _, _ = grant_fixture(consent_case)
        prepared = preparation.json()
    current = case.get('sessions/' + sid).json()
    body = {'turn_id': prepared['turn_id'], 'expected_session_revision': current['revision']}
    path = f'sessions/{sid}/interrupt'
    first = case.post(path, body, 'interrupt-original')
    assert first.status_code == 200
    assert first.json() == {'id': sid, 'turn_id': prepared['turn_id'], 'status': 'interrupt_requested'}
    control = case.get('turns/' + prepared['turn_id']).json()
    assert control['execution'] == 'terminal' and control['outcome'] == 'cancelled'
    assert control['cancel_requested'] and control['job']['status'] == 'cancelled'
    after = case.get('sessions/' + sid).json()
    assert after['revision'] == current['revision'] + 2 and after['active_turn_id'] is None
    before_replay = case.dump()
    replay = case.post(path, body, 'interrupt-original')
    assert replay.status_code == 200 and replay.content == first.content
    assert case.dump() == before_replay
    assert case.post(path, {**body, 'expected_session_revision': after['revision']}, 'interrupt-original').status_code == 409
    assert case.post(path, body, 'interrupt-stale').status_code == 412
    observed = case.post(path, {**body, 'expected_session_revision': after['revision']}, 'interrupt-terminal')
    assert observed.status_code == 200
    assert observed.json() == {'id': sid, 'turn_id': prepared['turn_id'], 'status': 'already_terminal'}
    assert case.get('sessions/' + sid).json() == after
    assert case.app.state.synthetic_transport_calls == []
    assert case.app.state.codex_turn_worker.run_once() is False


def test_interrupt_is_a_real_strict_registered_owner_route(consent_case):
    case = consent_case[0]
    path = '/api/v1/codex/sessions/{id}/interrupt'
    assert path in case.app.openapi()['paths']
    assert 'post' in case.app.openapi()['paths'][path]
    before = case.dump()
    response = case.post('sessions/missing/interrupt', {'turn_id': 'missing_turn', 'expected_session_revision': 2}, 'missing')
    assert response.status_code == 404 and response.json()['error']['code'] == 'REFERENCE_MISSING'
    assert case.dump() == before
