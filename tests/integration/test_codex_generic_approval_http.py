"""Real owners and HTTP; synthetic callback frames never execute a tool."""
from packages.contracts.canonical import canonical_bytes
from tests.integration.test_codex_turn_dispatch_http import consent_case, base_consent_case, start_body
from tests.integration.test_codex_turn_consent_http import full_preview_body

__all__ = ['consent_case', 'base_consent_case']


def callback_turn(values):
    case, _, sid, _, _, _ = values
    prepared = case.post(f'sessions/{sid}/turn-preparations', {
        'message': 'Synthetic operation approval; no host action.', 'context_refs': [],
        'expected_session_revision': 2, 'provider_id': 'codex_peer',
        'tools': {'max_tool_calls': 1, 'wall_seconds': 30}}, 'prepare').json()
    proposal = case.post('consent-previews', full_preview_body(prepared), 'preview')
    assert proposal.status_code == 201
    consent = case.post('consents', {'proposal_id': proposal.json()['id'],
        'proposal_sha256': proposal.json()['proposal_sha256']}, 'grant')
    assert consent.status_code == 201
    started = case.post(f'sessions/{sid}/turns', start_body(prepared, consent.json()), 'start')
    assert started.status_code == 202
    owner = case.app.state.codex_turn_service.outbound_owner
    with case.app.state.database.transaction(immediate=False) as conn:
        state = owner.owned_states(conn, case.app.state.database.workspace_id())[0][prepared['turn_id']]
        request = owner.prepared_request(state)
    frame = canonical_bytes({'version': 'codex-synthetic-operation-callback-v1', 'rpc_id': 'rpc_one',
        'thread_id': 'synthetic-thread', 'turn_id': prepared['turn_id'], 'item_id': 'item_one',
        'method': 'command/requestApproval', 'request_text': 'printf synthetic'})
    return case, prepared, request, frame


def test_unknown_generic_owner_routes_are_registered_and_remain_private(consent_case):
    case = consent_case[0]
    routes = {(route.path, method) for route in case.app.routes for method in getattr(route, 'methods', [])}
    assert ('/api/v1/approvals/{id}', 'GET') in routes
    assert ('/api/v1/approvals/{id}/decision', 'POST') in routes
    response = case.client.get('/api/v1/approvals/missing', headers=case.headers)
    assert response.status_code == 404
    assert response.json()['error']['code'] == 'REFERENCE_MISSING'
    response = case.client.post('/api/v1/approvals/missing/decision', headers={
        **case.headers, 'Idempotency-Key': 'missing'}, json={
        'expected_revision': 1, 'operation_sha256': '0'*64, 'decision': 'decline'})
    assert response.status_code == 404
    assert response.json()['error']['code'] == 'REFERENCE_MISSING'


def test_real_callback_safe_basis_decline_and_immutable_ack(consent_case):
    case, prepared, request, frame = callback_turn(consent_case)
    worker, executor = case.app.state.codex_turn_worker, case.app.state.synthetic_executor
    receipts = []
    def peer(gate):
        gate.request(request.body, endpoint=request.endpoint, max_output_tokens=64)
        identifier = worker.receive_operation(frame)
        control = case.get('turns/'+prepared['turn_id']).json()
        assert control['approval_ids'] == [identifier]
        basis = control['approval_controls'][0]
        view = case.client.get('/api/v1/approvals/'+identifier, headers=case.headers)
        assert view.status_code == 200 and view.json()['operation']['kind'] == 'unsupported'
        body = {'expected_revision': basis['revision'], 'operation_sha256': basis['operation_sha256'], 'decision': 'approve_once'}
        rejected = case.client.post('/api/v1/approvals/'+identifier+'/decision', json=body,
            headers={**case.headers, 'Idempotency-Key': 'reject-unsupported'})
        assert rejected.status_code == 409 and rejected.json()['error']['code'] == 'CODEX_OPERATION_UNSUPPORTED'
        body['decision'] = 'decline'
        ack = case.client.post('/api/v1/approvals/'+identifier+'/decision', json=body,
            headers={**case.headers, 'Idempotency-Key': 'original-decline'})
        assert ack.status_code == 200 and ack.json()['revision'] == 2
        receipts.append((identifier, body, ack.content))
    executor.peer = peer
    assert worker.run_once() is True
    assert len(receipts) == 1, 'actual callback must yield a durable HTTP decision'
    identifier, body, original = receipts[0]
    before = case.dump()
    replay = case.client.post('/api/v1/approvals/'+identifier+'/decision', json=body,
        headers={**case.headers, 'Idempotency-Key': 'original-decline'})
    assert replay.status_code == 200 and replay.content == original
    control = case.get('turns/'+prepared['turn_id']).json()
    assert control['approval_controls'][0]['decision'] == 'decline'
    assert control['outcome'] == 'cancelled'
    assert case.dump() == before and len(case.app.state.synthetic_transport_calls) == 1
