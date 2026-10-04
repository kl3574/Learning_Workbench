"""Explicit synthetic interpreter; real owners/HTTP and exactly one model request."""
import json

from packages.contracts.canonical import canonical_bytes
from services.api.app.application.codex_operation_profile import (
    CodexOperationRegistry, LiteralCommand, LiteralOperationProfile,
)
from tests.integration.test_codex_generic_approval_http import callback_turn
from tests.integration.test_codex_turn_dispatch_http import consent_case, base_consent_case

__all__ = ['consent_case', 'base_consent_case']


def test_registered_complete_operation_approve_claim_and_result(consent_case):
    case, prepared, request, original_frame = callback_turn(consent_case)
    # Explicit trusted composition only. The production registry remains empty.
    case.app.state.codex_turn_service.approvals.operations = CodexOperationRegistry([LiteralOperationProfile.current()])
    command = LiteralCommand(version='codex-synthetic-literal-command-v1', text='Synthetic bounded result α')
    raw = canonical_bytes({**json.loads(original_frame), 'request_text': canonical_bytes(command).decode()})
    worker, executor = case.app.state.codex_turn_worker, case.app.state.synthetic_executor
    kinds, receipts = [], []
    def peer(gate):
        gate.request(request.body, endpoint=request.endpoint, max_output_tokens=64)
        identifier = worker.receive_operation(raw)
        view = case.client.get('/api/v1/approvals/'+identifier).json()
        kinds.append(view['operation']['kind'])
        assert view['operation']['kind'] == 'command' and view['validity'] == 'current'
        body = {'operation_sha256': view['operation_sha256'], 'expected_revision': 1, 'decision': 'approve_once'}
        ack = case.client.post('/api/v1/approvals/'+identifier+'/decision', json=body,
            headers={**case.headers, 'Idempotency-Key': 'approve-original'})
        assert ack.status_code == 200 and ack.json()['revision'] == 2
        assert case.client.get('/api/v1/approvals/'+identifier).json()['execution'] == 'not_started'
        result = worker.execute_operation(identifier)
        assert result.text == command.text
        assert result.host_actions == result.provider_requests == result.files_written == 0
        receipts.append((identifier, body, ack.content))
    executor.peer = peer
    assert worker.run_once() is True
    assert kinds == ['command'], 'only the registered complete interpreter may produce an approvable operation'
    assert len(receipts) == 1
    identifier, body, original_ack = receipts[0]
    view = case.client.get('/api/v1/approvals/'+identifier).json()
    assert view['revision'] == 4 and view['execution'] == 'completed' and view['result_sha256'] is not None
    before = case.dump()
    assert case.client.post('/api/v1/approvals/'+identifier+'/decision', json=body,
        headers={**case.headers, 'Idempotency-Key': 'approve-original'}).content == original_ack
    assert case.get('turns/'+prepared['turn_id']).json()['approval_controls'][0]['revision'] == 4
    unchanged = case.dump() == before
    assert unchanged and len(case.app.state.synthetic_transport_calls) == 1
