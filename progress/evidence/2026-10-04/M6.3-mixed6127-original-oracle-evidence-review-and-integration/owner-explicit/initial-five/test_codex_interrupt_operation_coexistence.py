"""Real v4 stop/v5 operation histories coexist; trusted memory peers only."""
import json

import pytest

from packages.contracts.canonical import canonical_bytes
from services.api.app.application.codex_operation_profile import (
    CodexOperationRegistry, LiteralCommand, LiteralOperationProfile,
)
from services.api.app.application.errors import ApiError
from tests.integration.test_codex_generic_approval_http import callback_turn
from tests.integration.test_codex_operation_execution_boundaries import interpreter_events
from tests.integration.test_codex_turn_consent_http import full_preview_body
from tests.integration.test_codex_turn_dispatch_http import (
    base_consent_case, consent_case, start_body,
)
from tests.integration.test_codex_turn_interrupt_boundaries import interrupt

__all__ = ['consent_case', 'base_consent_case']


def literal_frame(original, text):
    command = LiteralCommand(version='codex-synthetic-literal-command-v1', text=text)
    return canonical_bytes({**json.loads(original), 'request_text': canonical_bytes(command).decode()})


def approval(case, identifier):
    response = case.client.get('/api/v1/approvals/' + identifier)
    assert response.status_code == 200
    return response.json()


def approve_operation(case, identifier, key):
    current = approval(case, identifier)
    assert current['operation']['kind'] == 'command' and current['validity'] == 'current'
    body = {'operation_sha256': current['operation_sha256'],
        'expected_revision': current['revision'], 'decision': 'approve_once'}
    response = decision(case, identifier, body, key)
    assert response.status_code == 200 and response.json()['revision'] == 2
    return body, response.content


def decision(case, identifier, body, key):
    return case.client.post('/api/v1/approvals/' + identifier + '/decision', json=body,
        headers={**case.headers, 'Idempotency-Key': key})


def run_peer(case, observe):
    """Surface callback assertions even when the adapter closes them as errors."""
    errors, executions = [], []
    def peer(gate):
        try:
            observe(gate)
        except Exception as error:
            errors.append(error)
            raise
    case.app.state.synthetic_executor.peer = peer
    with interpreter_events(lambda event: executions.append(True) if event == 'call' else None):
        assert case.app.state.codex_turn_worker.run_once() is True
    if errors:
        raise errors[0]
    return executions


def register_memory_operation(case):
    case.app.state.codex_turn_service.approvals.operations = CodexOperationRegistry([LiteralOperationProfile.current()])


def test_completed_operation_then_interrupt_preserves_full_original_decision(consent_case):
    case, prepared, request, original = callback_turn(consent_case)
    register_memory_operation(case)
    worker = case.app.state.codex_turn_worker
    receipts = []
    def observe(gate):
        gate.request(request.body, endpoint=request.endpoint, max_output_tokens=64)
        identifier = worker.receive_operation(literal_frame(original, '完成后保留 α\n'))
        body, original_ack = approve_operation(case, identifier, 'completed-approve')
        result = worker.execute_operation(identifier)
        assert result.text == '完成后保留 α\n'
        assert result.host_actions == result.provider_requests == result.files_written == 0
        completed = approval(case, identifier)
        assert completed['revision'] == 4 and completed['execution'] == 'completed'
        assert completed['result_sha256'] is not None
        stop_body, stop_ack = interrupt(case, prepared['session_id'], prepared['turn_id'], 'completed-interrupt')
        assert stop_ack.status_code == 200 and stop_ack.json()['status'] == 'interrupt_requested'
        replay = decision(case, identifier, body, 'completed-approve')
        assert replay.status_code == 200 and replay.content == original_ack
        assert approval(case, identifier) == completed
        receipts.append((identifier, body, original_ack, completed, stop_body, stop_ack.content))
    assert run_peer(case, observe) == [True]
    assert len(receipts) == 1 and len(case.app.state.synthetic_transport_calls) == 1
    identifier, body, original_ack, completed, stop_body, stop_ack = receipts[0]
    before = case.dump()
    current = case.get('turns/' + prepared['turn_id'])
    assert current.status_code == 200 and current.json()['outcome'] == 'cancelled'
    assert current.json()['approval_controls'][0]['revision'] == 4
    assert approval(case, identifier) == completed
    replay = decision(case, identifier, body, 'completed-approve')
    assert replay.status_code == 200 and replay.content == original_ack
    assert case.post('sessions/' + prepared['session_id'] + '/interrupt',
        stop_body, 'completed-interrupt').content == stop_ack
    result = case.get('turns/' + prepared['turn_id'] + '/result')
    assert result.status_code == 200 and result.json()['answer_markdown'] == 'Synthetic exact answer α\n'
    assert case.get('sessions/' + prepared['session_id']).json()['active_turn_id'] is None
    assert worker.run_once() is False and len(case.app.state.synthetic_transport_calls) == 1
    assert case.dump() == before


@pytest.mark.parametrize('approved', [False, True], ids=['pending', 'approved-not-executed'])
def test_interrupt_before_operation_execution_refuses_without_interpreter_or_second_model(consent_case, approved):
    case, prepared, request, original = callback_turn(consent_case)
    register_memory_operation(case)
    worker = case.app.state.codex_turn_worker
    receipts = []
    def observe(gate):
        gate.request(request.body, endpoint=request.endpoint, max_output_tokens=64)
        identifier = worker.receive_operation(literal_frame(original, 'Never execute this memory operation'))
        original_decision = approve_operation(case, identifier, 'unexecuted-approve') if approved else None
        stop_body, stopped = interrupt(case, prepared['session_id'], prepared['turn_id'], 'unexecuted-interrupt')
        assert stopped.status_code == 200 and stopped.json()['status'] == 'interrupt_requested'
        before = case.dump()
        with pytest.raises(ApiError) as refused:
            worker.execute_operation(identifier)
        assert refused.value.code == ('CODEX_CANCELLED' if approved else 'CODEX_BINDING_INVALID')
        view = approval(case, identifier)
        assert view['execution'] == 'not_started' and view['validity'] == 'closed'
        assert view['started_at'] is None and view['result_sha256'] is None
        assert case.dump() == before
        receipts.append((identifier, original_decision, stop_body, stopped.content))
    assert run_peer(case, observe) == []
    assert len(receipts) == 1 and len(case.app.state.synthetic_transport_calls) == 1
    identifier, original_decision, stop_body, stopped = receipts[0]
    before = case.dump()
    view = approval(case, identifier)
    assert view['revision'] == (3 if approved else 2)
    assert view['decision'] == ('approve_once' if approved else 'pending')
    assert view['execution'] == 'not_started' and view['validity'] == 'closed'
    assert view['started_at'] is None and view['result_sha256'] is None
    assert case.get('turns/' + prepared['turn_id']).json()['outcome'] == 'cancelled'
    assert case.post('sessions/' + prepared['session_id'] + '/interrupt',
        stop_body, 'unexecuted-interrupt').content == stopped
    if original_decision is not None:
        body, ack = original_decision
        replay = decision(case, identifier, body, 'unexecuted-approve')
        assert replay.status_code == 200 and replay.content == ack
    assert worker.run_once() is False and len(case.app.state.synthetic_transport_calls) == 1
    assert case.dump() == before


def next_callback(case, sid, original):
    """New permission through real HTTP; read the complete request from its owner."""
    current = case.get('sessions/' + sid)
    assert current.status_code == 200 and current.json()['active_turn_id'] is None
    body = {'message': 'New turn after a stopped turn; fresh permission α', 'context_refs': [],
        'expected_session_revision': current.json()['revision'], 'provider_id': 'codex_peer',
        'tools': {'max_tool_calls': 1, 'wall_seconds': 30}}
    prepared = case.post(f'sessions/{sid}/turn-preparations', body, 'next-prepare')
    assert prepared.status_code == 202 and prepared.json()['validity'] == 'current'
    value = prepared.json()
    provider = case.client.get('/api/v1/providers/codex_peer/config')
    assert provider.status_code == 200
    preview = {**full_preview_body(value), 'expected_provider_revision': provider.json()['revision']}
    proposal = case.post('consent-previews', preview, 'next-preview')
    assert proposal.status_code == 201
    granted = case.post('consents', {'proposal_id': proposal.json()['id'],
        'proposal_sha256': proposal.json()['proposal_sha256']}, 'next-grant')
    assert granted.status_code == 201
    started = case.post(f'sessions/{sid}/turns', start_body(value, granted.json()), 'next-start')
    assert started.status_code == 202
    owner = case.app.state.codex_turn_service.outbound_owner
    with case.app.state.database.transaction(immediate=False) as conn:
        state = owner.owned_states(conn, case.app.state.database.workspace_id())[0][value['turn_id']]
        request = owner.prepared_request(state)
    frame = canonical_bytes({**json.loads(original), 'turn_id': value['turn_id'],
        'rpc_id': 'next_rpc', 'item_id': 'next_item'})
    return value, request, frame


@pytest.mark.parametrize('stop_route', ['interrupt', 'jobs'])
def test_new_turn_operation_after_stop_keeps_new_active_when_old_terminal_is_read(consent_case, stop_route):
    case, old, _, original = callback_turn(consent_case)
    register_memory_operation(case)
    sid = old['session_id']
    if stop_route == 'interrupt':
        stop_body, stopped = interrupt(case, sid, old['turn_id'], 'old-stop')
        stop_path = f'/api/v1/codex/sessions/{sid}/interrupt'
    else:
        job = case.client.get('/api/v1/jobs/' + old['job']['id'])
        assert job.status_code == 200
        stop_body = {'expected_revision': job.json()['revision']}
        stop_path = '/api/v1/jobs/' + old['job']['id'] + '/cancel'
        stopped = case.client.post(stop_path, json=stop_body,
            headers={**case.headers, 'Idempotency-Key': 'old-stop'})
    assert stopped.status_code == 200
    old_control = case.get('turns/' + old['turn_id']).json()
    assert old_control['execution'] == 'terminal' and old_control['outcome'] == 'cancelled'
    assert case.app.state.synthetic_transport_calls == []
    prepared, request, frame = next_callback(case, sid, original)
    assert prepared['turn_id'] != old['turn_id'] and prepared['job']['id'] != old['job']['id']
    worker = case.app.state.codex_turn_worker
    receipts = []
    def observe(gate):
        gate.request(request.body, endpoint=request.endpoint, max_output_tokens=64)
        identifier = worker.receive_operation(literal_frame(frame, 'Fresh turn actual result α'))
        body, ack = approve_operation(case, identifier, 'next-operation-approve')
        before = case.dump()
        session = case.get('sessions/' + sid).json()
        assert session['active_turn_id'] == prepared['turn_id']
        assert case.get('turns/' + old['turn_id']).json() == old_control
        replay = case.client.post(stop_path, json=stop_body,
            headers={**case.headers, 'Idempotency-Key': 'old-stop'})
        assert replay.status_code == 200 and replay.content == stopped.content
        assert case.get('sessions/' + sid).json() == session
        page = case.get(f'sessions/{sid}/turns')
        assert page.status_code == 200
        assert {item['id'] for item in page.json()['items']} == {old['turn_id'], prepared['turn_id']}
        assert case.dump() == before
        result = worker.execute_operation(identifier)
        assert result.text == 'Fresh turn actual result α'
        assert result.host_actions == result.provider_requests == result.files_written == 0
        assert case.get('sessions/' + sid).json()['active_turn_id'] == prepared['turn_id']
        assert case.get('turns/' + old['turn_id']).json() == old_control
        receipts.append((identifier, body, ack))
    assert run_peer(case, observe) == [True]
    assert len(receipts) == 1 and len(case.app.state.synthetic_transport_calls) == 1
    identifier, body, ack = receipts[0]
    before = case.dump()
    assert approval(case, identifier)['execution'] == 'completed'
    assert case.get('turns/' + prepared['turn_id']).json()['outcome'] == 'completed'
    assert case.get('turns/' + old['turn_id']).json() == old_control
    assert case.get('sessions/' + sid).json()['active_turn_id'] is None
    replay = decision(case, identifier, body, 'next-operation-approve')
    assert replay.status_code == 200 and replay.content == ack
    assert worker.run_once() is False and len(case.app.state.synthetic_transport_calls) == 1
    assert case.dump() == before
