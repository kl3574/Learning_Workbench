"""Real owner lifecycle around an explicitly registered, memory-only interpreter."""
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from packages.contracts.canonical import canonical_bytes
from services.api.app.application.errors import ApiError
from services.api.app.application.codex_operation_profile import CodexOperationRegistry, LiteralOperationProfile, LiteralCommand
from tests.integration.test_codex_generic_approval_http import callback_turn
from tests.integration.test_codex_generic_approval_boundaries import decision
from tests.integration.test_codex_turn_dispatch_http import consent_case, base_consent_case

__all__ = ['consent_case', 'base_consent_case']


def exercise(values, observe, monkeypatch):
    case, prepared, request, old = callback_turn(values)
    owner, worker = case.app.state.codex_turn_service.approvals, case.app.state.codex_turn_worker
    owner.operations = CodexOperationRegistry([LiteralOperationProfile.current()])
    raw = canonical_bytes({**json.loads(old), 'request_text': canonical_bytes(LiteralCommand(
        version='codex-synthetic-literal-command-v1', text='Actual synthetic memory result')).decode()})
    executions, identifiers, errors = [], [], []
    actual = owner.operations.execute
    def counted(*args):
        executions.append(args[1])
        return actual(*args)
    monkeypatch.setattr(owner.operations, 'execute', counted)
    def peer(gate):
        try:
            gate.request(request.body, endpoint=request.endpoint, max_output_tokens=64)
            identifier = worker.receive_operation(raw)
            identifiers.append(identifier)
            view = case.client.get('/api/v1/approvals/'+identifier).json()
            assert view['operation']['kind'] == 'command' and view['validity'] == 'current'
            body = {'expected_revision': 1, 'operation_sha256': view['operation_sha256'], 'decision': 'approve_once'}
            observe(case, prepared, worker, owner, identifier, body, raw, gate, request, executions)
        except Exception as error:
            errors.append(error)
            raise
    case.app.state.synthetic_executor.peer = peer
    assert worker.run_once() is True
    if errors:
        raise errors[0]
    assert len(identifiers) == 1
    assert len(case.app.state.synthetic_transport_calls) == 1
    return case, prepared, identifiers[0], executions


def test_original_result_and_callback_replay_never_execute_again(consent_case, monkeypatch):
    def observe(case, prep, worker, owner, identifier, body, raw, *rest):
        assert decision(case, identifier, body).status_code == 200
        first = worker.execute_operation(identifier)
        before = case.dump()
        assert worker.receive_operation(raw) == identifier
        assert worker.execute_operation(identifier) == first
        assert case.dump() == before
    case, _, identifier, calls = exercise(consent_case, observe, monkeypatch)
    assert len(calls) == 1
    assert case.client.get('/api/v1/approvals/'+identifier).json()['execution'] == 'completed'
    with pytest.raises(ApiError):
        case.app.state.codex_turn_worker.execute_operation(identifier)


@pytest.mark.parametrize('decline', [False, True])
def test_no_approval_or_decline_has_zero_execution(consent_case, monkeypatch, decline):
    def observe(case, prep, worker, owner, identifier, body, *rest):
        if decline:
            assert decision(case, identifier, {**body, 'decision': 'decline'}).status_code == 200
        before = case.dump()
        with pytest.raises(ApiError):
            worker.execute_operation(identifier)
        assert case.dump() == before
    case, _, identifier, calls = exercise(consent_case, observe, monkeypatch)
    assert calls == []
    view = case.client.get('/api/v1/approvals/'+identifier).json()
    assert view['execution'] == 'not_started' and view['validity'] == 'closed'


def test_approved_but_never_started_has_separate_close_and_original_ack(consent_case, monkeypatch):
    receipts = []
    def observe(case, prep, worker, owner, identifier, body, *rest):
        ack = decision(case, identifier, body)
        assert ack.status_code == 200
        receipts.append((body, ack.content))
    case, _, identifier, calls = exercise(consent_case, observe, monkeypatch)
    view = case.client.get('/api/v1/approvals/'+identifier).json()
    assert view['revision'] == 3 and view['execution'] == 'not_started' and view['started_at'] is None
    assert view['validity'] == 'closed' and view['decision'] == 'approve_once' and calls == []
    before = case.dump()
    assert decision(case, identifier, receipts[0][0]).content == receipts[0][1]
    assert case.dump() == before


@pytest.mark.parametrize('change,code', [('profile','CODEX_RUNTIME_UNAVAILABLE'), ('role','POLICY_DENIED'),
    ('revoke','CODEX_CONSENT_REVOKED'), ('cancel','CODEX_CANCELLED'), ('expiry','CODEX_TIMEOUT')])
def test_approval_does_not_grant_future_execution_permission(consent_case, monkeypatch, change, code):
    def observe(case, prep, worker, owner, identifier, body, *rest):
        assert decision(case, identifier, body).status_code == 200
        if change == 'profile':
            monkeypatch.setattr(owner.operations, '_profiles', ())
        elif change == 'role':
            assert case.client.post('/api/v1/session/role', json={'role':'learner'},
                headers={**case.headers, 'Idempotency-Key':'withdraw'}).status_code == 200
        elif change == 'revoke':
            consent = case.get('turns/'+prep['turn_id']).json()['consent_control']
            assert case.post('consents/'+consent['id']+'/revoke', {'expected_revision':consent['revision']}, 'revoke').status_code == 200
        elif change == 'cancel':
            job = case.client.get('/api/v1/jobs/'+prep['job']['id']).json()
            assert case.client.post('/api/v1/jobs/'+job['id']+'/cancel', json={'expected_revision':job['revision']},
                headers={**case.headers, 'Idempotency-Key':'cancel'}).status_code == 200
        else:
            expiry = case.client.get('/api/v1/approvals/'+identifier).json()['expires_at']
            monkeypatch.setattr('services.api.app.application.codex_operation_execution.utc_now', lambda:expiry)
        before = case.dump()
        with pytest.raises(ApiError) as error:
            worker.execute_operation(identifier)
        assert error.value.code == code and case.dump() == before
    case, prepared, identifier, calls = exercise(consent_case, observe, monkeypatch)
    assert calls == []
    assert case.get('turns/'+prepared['turn_id']).json()['approval_controls'][0]['revision'] == 3


def test_profile_withdrawal_blocks_approval_but_not_original_read(consent_case, monkeypatch):
    def observe(case, prep, worker, owner, identifier, body, *rest):
        monkeypatch.setattr(owner.operations, '_profiles', ())
        before = case.dump()
        view = case.client.get('/api/v1/approvals/'+identifier)
        assert view.status_code == 200 and view.json()['validity'] == 'unavailable'
        assert decision(case, identifier, body).status_code == 503
        assert case.dump() == before
    _, _, _, calls = exercise(consent_case, observe, monkeypatch)
    assert calls == []


def test_tool_budget_debits_once_and_rejects_another_operation(consent_case, monkeypatch):
    def observe(case, prep, worker, owner, identifier, body, raw, *rest):
        assert decision(case, identifier, body).status_code == 200
        worker.execute_operation(identifier)
        next_id = worker.receive_operation(canonical_bytes({**json.loads(raw), 'rpc_id':'second_rpc', 'item_id':'second_item'}))
        view = case.client.get('/api/v1/approvals/'+next_id).json()
        assert view['validity'] == 'changed'
        before = case.dump()
        denied = decision(case, next_id, {**body, 'operation_sha256':view['operation_sha256']}, 'second')
        assert denied.status_code == 409 and denied.json()['error']['code'] == 'CODEX_BUDGET_EXCEEDED'
        assert case.dump() == before
    _, _, _, calls = exercise(consent_case, observe, monkeypatch)
    assert len(calls) == 1


def test_unknown_execution_consumes_once_and_never_replays(consent_case, monkeypatch):
    attempts = []
    def observe(case, prep, worker, owner, identifier, body, *rest):
        assert decision(case, identifier, body).status_code == 200
        def crash(*args):
            attempts.append(True)
            raise ValueError('Synthetic missing execution receipt')
        monkeypatch.setattr(owner.operations, 'execute', crash)
        for _ in range(2):
            with pytest.raises(ApiError) as error:
                worker.execute_operation(identifier)
            assert error.value.code == 'CODEX_OUTCOME_UNKNOWN'
    case, prepared, identifier, _ = exercise(consent_case, observe, monkeypatch)
    assert case.get('turns/'+prepared['turn_id']).json()['outcome'] == 'unknown'
    view = case.client.get('/api/v1/approvals/'+identifier).json()
    assert attempts == [True] and view['revision'] == 4 and view['execution'] == 'unknown'
    assert view['started_at'] is not None and view['finished_at'] is not None and view['result_sha256'] is None


def test_late_actual_result_survives_actor_loss_without_subject_delivery(consent_case, monkeypatch):
    def observe(case, prep, worker, owner, identifier, body, *rest):
        assert decision(case, identifier, body).status_code == 200
        actual = owner.operations.execute
        def withdraw(*args):
            result = actual(*args)
            assert case.client.post('/api/v1/session/role', json={'role':'learner'},
                headers={**case.headers, 'Idempotency-Key':'late-role'}).status_code == 200
            return result
        monkeypatch.setattr(owner.operations, 'execute', withdraw)
        worker.execute_operation(identifier)
        before = case.dump()
        assert case.client.get('/api/v1/approvals/'+identifier).status_code == 403
        assert case.get('turns/'+prep['turn_id']).json()['approval_controls'][0]['revision'] == 4
        assert case.dump() == before
    case, prepared, identifier, calls = exercise(consent_case, observe, monkeypatch)
    assert len(calls) == 1
    assert case.get('turns/'+prepared['turn_id']).json()['error_code'] == 'POLICY_DENIED'
    with case.app.state.database.transaction(immediate=False) as conn:
        owner = case.app.state.codex_turn_service.approvals
        _, _, history = owner.turns._owned_state(conn, case.app.state.database.workspace_id())
        state = owner.verify_history(conn, case.app.state.database.workspace_id(), history)[identifier]
        assert state.finished.outcome == 'completed' and state.finished.result.text == 'Actual synthetic memory result'


def test_tool_result_never_authorizes_another_model_request(consent_case, monkeypatch):
    def observe(case, prep, worker, owner, identifier, body, raw, gate, request, executions):
        assert decision(case, identifier, body).status_code == 200
        worker.execute_operation(identifier)
        with pytest.raises(ApiError):
            gate.request(request.body, endpoint=request.endpoint, max_output_tokens=64)
    case, prepared, _, calls = exercise(consent_case, observe, monkeypatch)
    assert len(calls) == 1
    assert case.get('turns/'+prepared['turn_id']).json()['outcome'] == 'failed'


def test_begin_transaction_failure_never_invokes_interpreter(consent_case, monkeypatch):
    def observe(case, prep, worker, owner, identifier, body, *rest):
        assert decision(case, identifier, body).status_code == 200
        actual = owner._append
        def fail(*args):
            actual(*args)
            if args[4].kind == 'started':
                raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', 'Synthetic start transaction rollback')
        monkeypatch.setattr(owner, '_append', fail)
        before = case.dump()
        with pytest.raises(ApiError):
            worker.execute_operation(identifier)
        assert case.dump() == before
        monkeypatch.setattr(owner, '_append', actual)
    _, _, _, calls = exercise(consent_case, observe, monkeypatch)
    assert calls == []


def test_wrong_thread_cannot_claim_original_operation(consent_case, monkeypatch):
    def observe(case, prep, worker, owner, identifier, body, *rest):
        assert decision(case, identifier, body).status_code == 200
        before = case.dump()
        with ThreadPoolExecutor(max_workers=1) as pool:
            attempt = pool.submit(worker.execute_operation, identifier)
            with pytest.raises(ApiError):
                attempt.result(timeout=10)
        assert case.dump() == before
    _, _, _, calls = exercise(consent_case, observe, monkeypatch)
    assert calls == []
