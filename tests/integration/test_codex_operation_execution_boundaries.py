"""Real owner lifecycle around an explicitly registered, memory-only interpreter."""
import json
import sys
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor

import pytest
from packages.contracts.canonical import canonical_bytes
from services.api.app.application.errors import ApiError
from services.api.app.application.codex_operation_profile import CodexOperationRegistry, LiteralOperationProfile, LiteralCommand
from tests.integration.test_codex_generic_approval_http import callback_turn
from tests.integration.test_codex_generic_approval_boundaries import decision
from tests.integration.test_codex_turn_dispatch_http import consent_case, base_consent_case

__all__ = ['consent_case', 'base_consent_case']


@contextmanager
def interpreter_events(observe):
    """Observe only the current test thread; never replace frozen tool code.

    The callback targets the one actual execute code object. Return-event fault
    injection models a lost receipt after execution, not a new licensed wrapper.
    No external process, frame values, credential or system state is inspected.
    """
    code = CodexOperationRegistry.execute.__code__
    previous = sys.getprofile()
    def trace(frame, event, arg):
        if previous is not None:
            previous(frame, event, arg)
        if frame.f_code is code:
            observe(event)
    sys.setprofile(trace)
    try:
        yield
    finally:
        sys.setprofile(previous)


def exercise(values, observe, monkeypatch):
    case, prepared, request, old = callback_turn(values)
    owner, worker = case.app.state.codex_turn_service.approvals, case.app.state.codex_turn_worker
    owner.operations = CodexOperationRegistry([LiteralOperationProfile.current()])
    raw = canonical_bytes({**json.loads(old), 'request_text': canonical_bytes(LiteralCommand(
        version='codex-synthetic-literal-command-v1', text='Actual synthetic memory result')).decode()})
    executions, identifiers, errors = [], [], []
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
    with interpreter_events(lambda event: executions.append(True) if event == 'call' else None):
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
        def crash(event):
            if event == 'return':
                attempts.append(True)
                raise ValueError('Synthetic missing execution receipt after actual interpreter')
        with interpreter_events(crash):
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
        def withdraw(event):
            if event == 'return':
                assert case.client.post('/api/v1/session/role', json={'role':'learner'},
                    headers={**case.headers, 'Idempotency-Key':'late-role'}).status_code == 200
        with interpreter_events(withdraw):
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


def test_committed_start_without_receipt_recovers_unknown_in_new_application(consent_case, monkeypatch):
    from datetime import datetime, timedelta, timezone
    from services.api.app.main import create_app
    class Interrupted(BaseException):
        pass
    receipts = []
    def observe(case, prep, worker, owner, identifier, body, *rest):
        ack = decision(case, identifier, body)
        assert ack.status_code == 200
        receipts.append((body, ack.content))
        def interrupted(event):
            if event == 'call':
                raise Interrupted()
        with interpreter_events(interrupted):
            with pytest.raises(Interrupted):
                worker.execute_operation(identifier)
        view = case.client.get('/api/v1/approvals/'+identifier).json()
        assert view['execution'] == 'started' and view['revision'] == 3
        with pytest.raises(ApiError) as error:
            worker.execute_operation(identifier)
        assert error.value.code == 'CODEX_OUTCOME_UNKNOWN'
        # A lost owner can leave the already committed permit, not a fake
        # zero-execution assertion. This seam suppresses only final convergence.
        monkeypatch.setattr(worker, '_finish', lambda *args:None)
    case, prepared, identifier, calls = exercise(consent_case, observe, monkeypatch)
    _, runtime, _, proofs, _, _ = consent_case
    app = create_app(case.app.state.settings, codex_bootstrap_runtime=runtime, codex_proofs=proofs)
    worker = app.state.codex_turn_worker
    assert worker.recover() == 0
    later = (datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat().replace('+00:00','Z')
    monkeypatch.setattr('services.api.app.application.codex_turn_worker.utc_now', lambda:later)
    assert worker.recover() == 1
    view = case.client.get('/api/v1/approvals/'+identifier).json()
    assert view['revision'] == 4 and view['execution'] == 'unknown'
    assert case.get('turns/'+prepared['turn_id']).json()['outcome'] == 'unknown'
    before = case.dump()
    assert worker.recover() == 0 and worker.run_once() is False
    assert decision(case, identifier, receipts[0][0]).content == receipts[0][1]
    assert case.dump() == before and calls == [True]


def test_result_transaction_failure_retains_started_and_unknown_without_reexecution(consent_case, monkeypatch):
    def observe(case, prep, worker, owner, identifier, body, *rest):
        assert decision(case, identifier, body).status_code == 200
        actual = owner._append
        def fail(*args):
            actual(*args)
            if args[4].kind == 'finished':
                raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', 'Synthetic receipt transaction failure')
        monkeypatch.setattr(owner, '_append', fail)
        with pytest.raises(ApiError):
            worker.execute_operation(identifier)
        monkeypatch.setattr(owner, '_append', actual)
        view = case.client.get('/api/v1/approvals/'+identifier).json()
        assert view['execution'] == 'started' and view['revision'] == 3
        with pytest.raises(ApiError) as error:
            worker.execute_operation(identifier)
        assert error.value.code == 'CODEX_OUTCOME_UNKNOWN'
    case, prepared, identifier, calls = exercise(consent_case, observe, monkeypatch)
    assert len(calls) == 1
    assert case.client.get('/api/v1/approvals/'+identifier).json()['execution'] == 'unknown'
    assert case.get('turns/'+prepared['turn_id']).json()['outcome'] == 'unknown'


@pytest.mark.parametrize('damage', ['start_tail', 'finish_tail', 'member', 'core', 'shape', 'whole_family'])
def test_supported_history_damage_rejects_safe_full_and_original_ack(consent_case, monkeypatch, damage):
    receipts = []
    def observe(case, prep, worker, owner, identifier, body, *rest):
        ack = decision(case, identifier, body)
        assert ack.status_code == 200
        receipts.append(body)
        worker.execute_operation(identifier)
    case, prepared, identifier, _ = exercise(consent_case, observe, monkeypatch)
    with case.app.state.database.transaction() as conn:
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'codex_approval_%'"):
            conn.execute('DROP TRIGGER '+row[0])
        if damage.endswith('_tail'):
            conn.execute('DELETE FROM codex_approval_events WHERE approval_id=? AND seq=?',
                (identifier, 3 if damage == 'start_tail' else 4))
        elif damage == 'member':
            conn.execute('DELETE FROM codex_approval_members WHERE approval_id=? AND seq=3', (identifier,))
        elif damage == 'core':
            conn.execute('DELETE FROM approvals WHERE id=?', (identifier,))
        elif damage == 'shape':
            conn.execute("UPDATE codex_approval_events SET record_json='[]' WHERE approval_id=? AND seq=4", (identifier,))
        else:
            for table in ('events','members','commands','heads'):
                conn.execute('DELETE FROM codex_approval_'+table+' WHERE approval_id=?', (identifier,))
            conn.execute('DELETE FROM approvals WHERE id=?', (identifier,))
    before = case.dump()
    responses = [case.client.get('/api/v1/approvals/'+identifier), case.get('turns/'+prepared['turn_id']),
        decision(case, identifier, receipts[0])]
    assert [item.status_code for item in responses] == [409,409,409]
    assert all(item.json()['error']['code'] == 'CODEX_HISTORY_DAMAGED' for item in responses)
    unchanged = case.dump() == before
    assert unchanged


def test_completed_history_and_ack_survive_new_application_empty_registry(consent_case, monkeypatch):
    from fastapi.testclient import TestClient
    from services.api.app.main import create_app
    receipts = []
    def observe(case, prep, worker, owner, identifier, body, *rest):
        ack = decision(case, identifier, body)
        assert ack.status_code == 200
        receipts.append((body,ack.content))
        worker.execute_operation(identifier)
    case, prepared, identifier, calls = exercise(consent_case, observe, monkeypatch)
    _, runtime, _, proofs, _, _ = consent_case
    app = create_app(case.app.state.settings, codex_bootstrap_runtime=runtime, codex_proofs=proofs)
    client = TestClient(app, base_url=case.app.state.settings.origin)
    client.cookies.update(case.client.cookies)
    before = case.dump()
    try:
        assert app.state.codex_turn_worker.recover() == 0
        assert app.state.codex_turn_worker.run_once() is False
        view = client.get('/api/v1/approvals/'+identifier).json()
        assert view['execution'] == 'completed' and view['revision'] == 4
        assert client.post('/api/v1/approvals/'+identifier+'/decision', json=receipts[0][0],
            headers={**case.headers,'Idempotency-Key':'decision'}).content == receipts[0][1]
        assert client.get('/api/v1/codex/turns/'+prepared['turn_id']).json()['approval_ids'] == [identifier]
        unchanged = case.dump() == before
        assert unchanged and len(calls) == 1
    finally:
        client.close()


def test_concurrent_same_key_approval_has_one_command_and_one_execution(consent_case, monkeypatch):
    def observe(case, prep, worker, owner, identifier, body, *rest):
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _:decision(case, identifier, body), range(2)))
        assert [response.status_code for response in responses] == [200,200]
        assert responses[0].content == responses[1].content
        with case.app.state.database.transaction(immediate=False) as conn:
            assert conn.execute('SELECT COUNT(*) FROM codex_approval_commands WHERE approval_id=?', (identifier,)).fetchone()[0] == 1
        worker.execute_operation(identifier)
    _, _, _, calls = exercise(consent_case, observe, monkeypatch)
    assert len(calls) == 1


def test_multiple_approvals_do_not_reserve_extra_tool_calls(consent_case, monkeypatch):
    def observe(case, prep, worker, owner, identifier, body, raw, *rest):
        next_id = worker.receive_operation(canonical_bytes({**json.loads(raw), 'rpc_id':'rpc_two', 'item_id':'item_two'}))
        second = case.client.get('/api/v1/approvals/'+next_id).json()
        assert decision(case, identifier, body).status_code == 200
        assert decision(case, next_id, {**body,'operation_sha256':second['operation_sha256']}, 'second').status_code == 200
        worker.execute_operation(identifier)
        before = case.dump()
        with pytest.raises(ApiError) as error:
            worker.execute_operation(next_id)
        assert error.value.code == 'CODEX_BUDGET_EXCEEDED' and case.dump() == before
    case, prep, _, calls = exercise(consent_case, observe, monkeypatch)
    controls = case.get('turns/'+prep['turn_id']).json()['approval_controls']
    assert len(calls) == 1 and [item['revision'] for item in controls] == [4,3]


def test_start_is_committed_before_interpreter_and_cannot_be_reentered(consent_case, monkeypatch):
    def observe(case, prep, worker, owner, identifier, body, *rest):
        assert decision(case, identifier, body).status_code == 200
        def checked(event):
            if event == 'call':
                view = case.client.get('/api/v1/approvals/'+identifier).json()
                assert view['revision'] == 3 and view['execution'] == 'started'
                with pytest.raises(ApiError) as error:
                    worker.execute_operation(identifier)
                assert error.value.code == 'CODEX_OUTCOME_UNKNOWN'
        with interpreter_events(checked):
            worker.execute_operation(identifier)
    _, _, _, calls = exercise(consent_case, observe, monkeypatch)
    assert len(calls) == 1
