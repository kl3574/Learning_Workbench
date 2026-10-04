"""Real local HTTP/SQLite turn control; synthetic bootstrap only, no CLI/model."""
import pytest

from tests.integration.test_codex_bootstrap_http import ControlledRuntime, approve, make_case


@pytest.fixture
def turn_case(tmp_path):
    runtime = ControlledRuntime()
    case = make_case(tmp_path, codex_bootstrap_runtime=runtime)
    case.app.state.provider_service.secret_store.initialize()
    response = case.client.put('/api/v1/providers/codex_local/config', json={
        'expected_revision': 0, 'adapter': 'compatible_chat', 'base_url': 'https://example.invalid',
        'model': 'synthetic-model', 'embedding_model': None, 'endpoint_policy': 'public_https', 'pricing': None,
    }, headers={**case.headers, 'Idempotency-Key': 'synthetic-config'})
    assert response.status_code == 200, response.text
    _, _, body = approve(case)
    response = case.post('sessions', body, 'bootstrap-session')
    assert response.status_code == 201, response.text
    yield case, runtime, response.json()['id'], body, response.content
    case.client.close()


def turn_body(revision=2):
    return {'message': 'Synthetic original Unicode α\nDo not execute.', 'context_refs': [],
            'expected_session_revision': revision, 'provider_id': 'codex_local',
            'tools': {'max_tool_calls': 0, 'wall_seconds': 30}}


def test_prepare_current_control_cancel_and_original_acks(turn_case, monkeypatch):
    case, runtime, session_id, bootstrap_body, bootstrap_ack = turn_case
    def forbidden(*args, **kwargs):
        pytest.fail('turn preparation or control read attempted execution')
    monkeypatch.setattr(runtime, 'execute', forbidden)
    response = case.post(f'sessions/{session_id}/turn-preparations', turn_body(), 'turn-original')
    assert response.status_code == 202, response.text
    original, ack = response.json(), response.content
    assert original['validity'] == 'unavailable' and original['session_revision'] == 3
    assert original['job']['status'] == 'awaiting_approval'
    assert original['proposal_id'] is None and original['consent_id'] is None
    before = case.dump()
    control = case.get('turns/' + original['turn_id'])
    assert control.status_code == 200, control.text
    assert control.json()['execution'] == 'not_started'
    assert control.json()['approval_controls'] == [] and control.json()['consent_control'] is None
    assert turn_body()['message'] not in control.text and 'context_refs' not in control.text
    current = case.get('sessions/' + session_id).json()
    assert current['revision'] == 3 and current['active_turn_id'] == original['turn_id']
    assert not any(current['capabilities'].values())
    assert case.get('turn-preparations/' + original['id']).json() == original
    assert case.get(f'sessions/{session_id}/turns').json()['items'] == [control.json()]
    assert case.dump() == before
    cancel = case.client.post('/api/v1/jobs/' + original['job']['id'] + '/cancel',
        json={'expected_revision': 1}, headers={**case.headers, 'Idempotency-Key': 'cancel-original'})
    assert cancel.status_code == 200 and cancel.json()['status'] == 'cancelled', cancel.text
    current = case.get('sessions/' + session_id).json()
    assert current['revision'] == 4 and current['active_turn_id'] is None
    assert case.get('turns/' + original['turn_id']).json()['outcome'] == 'cancelled'
    assert case.get('turn-preparations/' + original['id']).json()['validity'] == 'closed'
    before = case.dump()
    assert case.post(f'sessions/{session_id}/turn-preparations', turn_body(), 'turn-original').content == ack
    assert case.post('sessions', bootstrap_body, 'bootstrap-session').content == bootstrap_ack
    assert case.dump() == before and len(runtime.calls) == 1
