"""Original approval never authorizes changed in-memory interpreter code."""
import json
import pytest
from packages.contracts.canonical import canonical_bytes
from services.api.app.application.codex_operation_profile import CodexOperationRegistry, LiteralOperationProfile, LiteralCommand
from services.api.app.application.errors import ApiError
from tests.integration.test_codex_generic_approval_http import callback_turn
from tests.integration.test_codex_generic_approval_boundaries import decision
from tests.integration.test_codex_turn_dispatch_http import consent_case, base_consent_case

__all__ = ['consent_case', 'base_consent_case']


@pytest.mark.parametrize('scope', ['class', 'instance'])
def test_original_approval_cannot_claim_after_execution_wrapper_changes(consent_case, monkeypatch, scope):
    case, prepared, request, original = callback_turn(consent_case)
    owner, worker = case.app.state.codex_turn_service.approvals, case.app.state.codex_turn_worker
    owner.operations = CodexOperationRegistry([LiteralOperationProfile.current()])
    raw = canonical_bytes({**json.loads(original), 'request_text': canonical_bytes(LiteralCommand(
        version='codex-synthetic-literal-command-v1', text='Synthetic original text')).decode()})
    invoked, failures, receipts = [], [], []
    def peer(gate):
        try:
            gate.request(request.body, endpoint=request.endpoint, max_output_tokens=64)
            identifier = worker.receive_operation(raw)
            view = case.client.get('/api/v1/approvals/'+identifier).json()
            body = {'expected_revision': 1, 'operation_sha256': view['operation_sha256'], 'decision': 'approve_once'}
            ack = decision(case, identifier, body)
            assert ack.status_code == 200
            receipts.append((identifier, body, ack.content))
            actual = owner.operations.execute
            def changed(*args):
                invoked.append(True)
                return actual(*args[-2:])
            monkeypatch.setattr(CodexOperationRegistry if scope == 'class' else owner.operations, 'execute', changed)
            before = case.dump()
            with pytest.raises(ApiError) as denied:
                worker.execute_operation(identifier)
            assert denied.value.code == 'CODEX_RUNTIME_UNAVAILABLE'
            assert not invoked and case.dump() == before
            current = case.client.get('/api/v1/approvals/'+identifier).json()
            assert current['execution'] == 'not_started' and current['revision'] == 2
            assert current['validity'] == 'unavailable'
            assert decision(case, identifier, body).content == ack.content
            assert case.dump() == before
        except Exception as error:
            failures.append(error)
            raise
    case.app.state.synthetic_executor.peer = peer
    assert worker.run_once() is True
    if failures:
        raise failures[0]
    assert len(receipts) == 1 and not invoked
    identifier, body, ack = receipts[0]
    assert decision(case, identifier, body).content == ack
    assert case.client.get('/api/v1/approvals/'+identifier).json()['execution'] == 'not_started'
    assert len(case.app.state.synthetic_transport_calls) == 1
