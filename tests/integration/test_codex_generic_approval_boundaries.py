"""Counterexamples around real callback ownership, immutable facts and delivery."""
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest

from packages.contracts.canonical import canonical_bytes
from services.api.app.application.errors import ApiError
from tests.integration.test_codex_generic_approval_http import callback_turn
from tests.integration.test_codex_turn_dispatch_http import consent_case, base_consent_case
from tests.integration.test_codex_bootstrap_http import make_case
from tests.integration.test_assessment_learning_port import assessment_learning_state

__all__ = ['consent_case', 'base_consent_case']
assessment_state = assessment_learning_state


def decision(case, identifier, body, key='decision'):
    return case.client.post('/api/v1/approvals/'+identifier+'/decision', json=body,
        headers={**case.headers, 'Idempotency-Key': key})


def body_for(case, turn_id):
    basis = case.get('turns/'+turn_id).json()['approval_controls'][0]
    return {'expected_revision': basis['revision'], 'operation_sha256': basis['operation_sha256'], 'decision': 'decline'}


def exercise(values, observation):
    case, prepared, request, raw = callback_turn(values)
    worker = case.app.state.codex_turn_worker
    errors, identifiers = [], []
    def peer(gate):
        try:
            gate.request(request.body, endpoint=request.endpoint, max_output_tokens=64)
            identifier = worker.receive_operation(raw)
            identifiers.append(identifier)
            observation(case, prepared, raw, identifier)
        except Exception as error:
            errors.append(error)
            raise
    case.app.state.synthetic_executor.peer = peer
    assert worker.run_once() is True
    if errors:
        raise errors[0]
    assert len(identifiers) == 1
    return case, prepared, raw, identifiers[0]


def test_duplicate_original_callback_after_decline_is_read_only(consent_case):
    def observe(case, prepared, raw, identifier):
        worker = case.app.state.codex_turn_worker
        before = case.dump()
        assert worker.receive_operation(raw) == identifier and case.dump() == before
        assert decision(case, identifier, body_for(case, prepared['turn_id'])).status_code == 200
        before = case.dump()
        assert worker.receive_operation(raw) == identifier and case.dump() == before
    case, _, _, _ = exercise(consent_case, observe)
    assert len(case.app.state.synthetic_transport_calls) == 1


@pytest.mark.parametrize('change', ['rpc_reuse', 'thread', 'turn', 'extra', 'array'])
def test_callback_identity_and_closed_shape_are_checked(consent_case, change):
    def observe(case, prepared, raw, identifier):
        frame = json.loads(raw)
        if change == 'rpc_reuse':
            frame['request_text'] += ' changed'
        elif change == 'thread':
            frame['thread_id'] = 'other_thread'
        elif change == 'turn':
            frame['turn_id'] = 'other_turn'
        elif change == 'extra':
            frame['permission'] = 'session_wide'
        else:
            frame = []
        before = case.dump()
        with pytest.raises(ApiError) as error:
            case.app.state.codex_turn_worker.receive_operation(canonical_bytes(frame))
        assert error.value.code == 'CODEX_BINDING_INVALID' and case.dump() == before
    case, prepared, _, identifier = exercise(consent_case, observe)
    control = case.get('turns/'+prepared['turn_id']).json()
    assert control['approval_ids'] == [identifier]
    assert control['approval_controls'][0]['validity'] == 'closed'
    assert control['approval_controls'][0]['decision'] == 'pending'
    assert control['outcome'] == 'failed' and control['error_code'] == 'CODEX_OPERATION_UNSUPPORTED'


def test_new_actor_learner_can_decline_without_subject_access(consent_case, tmp_path):
    case, runtime, _, _, _, _ = consent_case
    other = make_case(tmp_path, codex_bootstrap_runtime=runtime)
    def observe(case, prepared, raw, identifier):
        body = body_for(other, prepared['turn_id'])
        assert decision(other, identifier, {**body, 'decision': 'approve_once'}).status_code == 403
        assert other.client.post('/api/v1/session/role', json={'role': 'learner'},
            headers={**other.headers, 'Idempotency-Key': 'learner'}).status_code == 200
        before = case.dump()
        assert other.client.get('/api/v1/approvals/'+identifier).status_code == 403
        assert body_for(other, prepared['turn_id']) == body and case.dump() == before
        ack = decision(other, identifier, body)
        assert ack.status_code == 200 and ack.json()['actor_session_id'] == other.actor_id
        before = case.dump()
        assert decision(other, identifier, body).content == ack.content and case.dump() == before
    try:
        exercise(consent_case, observe)
    finally:
        other.client.close()


@pytest.mark.parametrize('field, expected', [('expected_revision', 412), ('operation_sha256', 409)])
def test_decision_has_real_cas_and_original_hash(consent_case, field, expected):
    def observe(case, prepared, raw, identifier):
        body = body_for(case, prepared['turn_id'])
        before = case.dump()
        changed = {**body, field: 7 if field == 'expected_revision' else '0'*64}
        response = decision(case, identifier, changed)
        assert response.status_code == expected and case.dump() == before
        ack = decision(case, identifier, body)
        assert ack.status_code == 200
        before = case.dump()
        assert decision(case, identifier, {**body, 'decision': 'approve_once'}).status_code == 409
        assert case.dump() == before
    exercise(consent_case, observe)


def test_decision_and_stop_failure_roll_back_every_owner(consent_case, monkeypatch):
    def observe(case, prepared, raw, identifier):
        turns = case.app.state.codex_turn_service
        original = turns.request_stop
        def fail(*args):
            raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', 'Synthetic transaction failure.')
        monkeypatch.setattr(turns, 'request_stop', fail)
        before = case.dump()
        body = body_for(case, prepared['turn_id'])
        assert decision(case, identifier, body).status_code == 503 and case.dump() == before
        monkeypatch.setattr(turns, 'request_stop', original)
        assert decision(case, identifier, body).status_code == 200
    exercise(consent_case, observe)


def test_subject_delivery_rechecks_role_after_original_snapshot(consent_case, monkeypatch):
    def observe(case, prepared, raw, identifier):
        owner = case.app.state.codex_turn_service.approvals
        original = owner.read_pending_operation
        entered, release = Event(), Event()
        def held(*args):
            value = original(*args)
            entered.set()
            assert release.wait(10)
            return value
        monkeypatch.setattr(owner, 'read_pending_operation', held)
        with ThreadPoolExecutor(max_workers=1) as pool:
            response = pool.submit(case.client.get, '/api/v1/approvals/'+identifier)
            try:
                assert entered.wait(10)
                assert case.client.post('/api/v1/session/role', json={'role': 'learner'},
                    headers={**case.headers, 'Idempotency-Key': 'withdraw-subject'}).status_code == 200
                before = case.dump()
            finally:
                release.set()
            rejected = response.result(timeout=10)
        assert rejected.status_code == 403 and 'operation' not in rejected.json() and case.dump() == before
        assert decision(case, identifier, body_for(case, prepared['turn_id'])).status_code == 200
    exercise(consent_case, observe)


@pytest.mark.parametrize('damage', ['tail', 'family', 'core', 'member', 'shape'])
def test_damaged_history_rejects_safe_get_full_get_and_original_ack(consent_case, damage):
    original = []
    def observe(case, prepared, raw, identifier):
        body = body_for(case, prepared['turn_id'])
        ack = decision(case, identifier, body)
        assert ack.status_code == 200
        original.append(body)
    case, prepared, _, identifier = exercise(consent_case, observe)
    with case.app.state.database.transaction() as conn:
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'codex_approval_%'"):
            conn.execute('DROP TRIGGER '+row[0])
        if damage == 'tail':
            conn.execute('DELETE FROM codex_approval_events WHERE approval_id=? AND seq=2', (identifier,))
        elif damage == 'family':
            for table in ('heads', 'events', 'members', 'commands'):
                conn.execute('DELETE FROM codex_approval_'+table)
            conn.execute('DELETE FROM approvals WHERE id=?', (identifier,))
        elif damage == 'core':
            conn.execute('DELETE FROM approvals WHERE id=?', (identifier,))
        elif damage == 'member':
            conn.execute('DELETE FROM codex_approval_members WHERE approval_id=? AND seq=2', (identifier,))
        else:
            conn.execute("UPDATE codex_approval_events SET record_json='[]' WHERE approval_id=? AND seq=1", (identifier,))
    before = case.dump()
    responses = [case.get('turns/'+prepared['turn_id']), case.client.get('/api/v1/approvals/'+identifier),
        decision(case, identifier, original[0])]
    assert [(r.status_code, r.json()['error']['code']) for r in responses] == [(409, 'CODEX_HISTORY_DAMAGED')]*3
    assert case.dump() == before


def test_prior_approval_damage_blocks_next_claim_before_request(consent_case):
    from tests.integration.test_codex_turn_consent_http import consent_preparation, full_preview_body
    from tests.integration.test_codex_turn_dispatch_http import start_body
    def observe(case, prepared, raw, identifier):
        assert decision(case, identifier, body_for(case, prepared['turn_id'])).status_code == 200
    case, prepared, _, identifier = exercise(consent_case, observe)
    sid = prepared['session_id']
    _, next_prepared = consent_preparation(case, sid, case.get('sessions/'+sid).json()['revision'], 'next-prepare')
    value = next_prepared.json()
    proposal = case.post('consent-previews', full_preview_body(value), 'next-preview')
    consent = case.post('consents', {'proposal_id': proposal.json()['id'],
        'proposal_sha256': proposal.json()['proposal_sha256']}, 'next-grant')
    assert case.post(f'sessions/{sid}/turns', start_body(value, consent.json()), 'next-start').status_code == 202
    with case.app.state.database.transaction() as conn:
        conn.execute('DELETE FROM approvals WHERE id=?', (identifier,))
    case.app.state.synthetic_executor.peer = None
    before, calls = case.dump(), len(case.app.state.synthetic_transport_calls)
    with pytest.raises(ApiError) as error:
        case.app.state.codex_turn_worker.run_once()
    assert error.value.code == 'CODEX_HISTORY_DAMAGED'
    current_calls = len(case.app.state.synthetic_transport_calls)
    unchanged = case.dump() == before
    assert current_calls == calls and unchanged


def test_new_identifier_collision_cannot_overwrite_original_or_escape_as_500(consent_case, monkeypatch):
    from uuid import UUID
    from services.api.app.application import codex_approvals
    monkeypatch.setattr(codex_approvals, 'uuid4', lambda: UUID('01234567-89ab-4cde-8123-456789abcdef'))
    def observe(case, prepared, raw, identifier):
        frame = {**json.loads(raw), 'rpc_id': 'rpc_second', 'item_id': 'item_second'}
        before = case.dump()
        with pytest.raises(ApiError) as error:
            case.app.state.codex_turn_worker.receive_operation(canonical_bytes(frame))
        assert error.value.code == 'CODEX_BINDING_INVALID' and case.dump() == before
    exercise(consent_case, observe)


def test_callback_is_bound_to_live_worker_thread_not_a_public_intake(consent_case):
    def observe(case, prepared, raw, identifier):
        before = case.dump()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(case.app.state.codex_turn_worker.receive_operation, raw)
            with pytest.raises(ApiError) as error:
                future.result(timeout=10)
        assert error.value.code == 'CODEX_BINDING_INVALID' and case.dump() == before
    case, _, raw, _ = exercise(consent_case, observe)
    before = case.dump()
    with pytest.raises(ApiError) as error:
        case.app.state.codex_turn_worker.receive_operation(raw)
    assert error.value.code == 'CODEX_BINDING_INVALID' and case.dump() == before


def test_original_acks_survive_application_reconstruction(consent_case):
    from fastapi.testclient import TestClient
    from services.api.app.main import create_app
    original = []
    def observe(case, prepared, raw, identifier):
        body = body_for(case, prepared['turn_id'])
        response = decision(case, identifier, body)
        assert response.status_code == 200
        original.append((body, response.content))
    case, prepared, _, identifier = exercise(consent_case, observe)
    _, runtime, _, proofs, bootstrap_body, bootstrap_ack = consent_case
    app = create_app(case.app.state.settings, codex_bootstrap_runtime=runtime, codex_proofs=proofs)
    def retained_owners():
        with case.app.state.database.transaction(immediate=False) as conn:
            names = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND (name GLOB 'codex_*' OR name GLOB 'provider_codex_*' OR name IN ('jobs','job_events','runs','threads','approvals','context_snapshots')) ORDER BY name")]
            return {name: [tuple(row) for row in conn.execute('SELECT * FROM '+name+' ORDER BY rowid')] for name in names}
    retained = retained_owners()
    with TestClient(app, base_url=case.app.state.settings.origin):
        # Existing startup workers invalidate recommendations asynchronously.
        # Their unrelated writes are not part of an approval GET measurement.
        owners_unchanged = retained_owners() == retained
        assert owners_unchanged
    owners_unchanged = retained_owners() == retained
    assert owners_unchanged
    client = TestClient(app, base_url=case.app.state.settings.origin)
    client.cookies.update(case.client.cookies)
    try:
        # Measure real HTTP on the rebuilt application after startup workers
        # have actually stopped, without adding a sleep or timing assertion.
        before_reads = case.dump()
        response = client.post('/api/v1/approvals/'+identifier+'/decision', json=original[0][0],
            headers={**case.headers, 'Idempotency-Key': 'decision'})
        assert response.status_code == 200 and response.content == original[0][1]
        assert client.post('/api/v1/codex/sessions', json=bootstrap_body,
            headers={**case.headers, 'Idempotency-Key': 'bootstrap-session'}).content == bootstrap_ack
        assert client.get('/api/v1/codex/turns/'+prepared['turn_id']).json()['approval_ids'] == [identifier]
        reads_unchanged = case.dump() == before_reads
        assert reads_unchanged
    finally:
        client.close()
    owners_unchanged = retained_owners() == retained
    assert owners_unchanged and len(runtime.calls) == 1


def test_two_same_key_decisions_linearize_one_stop_and_original_ack(consent_case):
    def observe(case, prepared, raw, identifier):
        body = body_for(case, prepared['turn_id'])
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: decision(case, identifier, body), range(2)))
        assert [value.status_code for value in results] == [200, 200]
        assert results[0].content == results[1].content
        control = case.get('turns/'+prepared['turn_id']).json()
        assert control['cancel_requested'] is True and control['job_revision'] == 4
        with case.app.state.database.transaction(immediate=False) as conn:
            assert conn.execute('SELECT COUNT(*) FROM codex_approval_events').fetchone()[0] == 2
            assert conn.execute('SELECT COUNT(*) FROM codex_approval_commands').fetchone()[0] == 1
    case, prepared, _, _ = exercise(consent_case, observe)
    assert case.get('sessions/'+prepared['session_id']).json()['revision'] == 6


def test_other_workspace_cannot_read_or_decide_an_approval(consent_case, tmp_path):
    other = make_case(tmp_path/'separate-workspace')
    def observe(case, prepared, raw, identifier):
        before, other_before = case.dump(), other.dump()
        assert other.get('turns/'+prepared['turn_id']).status_code == 404
        assert other.client.get('/api/v1/approvals/'+identifier).status_code == 404
        assert decision(other, identifier, body_for(case, prepared['turn_id'])).status_code == 404
        unchanged = case.dump() == before and other.dump() == other_before
        assert unchanged
    try:
        exercise(consent_case, observe)
    finally:
        other.client.close()


@pytest.mark.parametrize('mode', ['independent', 'open_book'])
def test_policy_keeps_safe_control_and_original_decline_ack(assessment_state, mode):
    from tests.integration.test_assessment_policy import start
    from tests.integration.test_codex_turn_preparation_http import identity
    from tests.integration.test_codex_turn_consent_http import make_consent_case
    from tests.integration.test_codex_turn_dispatch_http import make_dispatch_case
    database, _, fixture, assessment = assessment_state
    for base in make_consent_case(database.settings.data_dir):
        for values in make_dispatch_case(base):
            original = []
            def observe(case, prepared, raw, identifier):
                if mode == 'open_book':
                    start((database, identity(case), fixture, assessment), mode=mode)
                    before = case.dump()
                    assert case.client.get('/api/v1/approvals/'+identifier).status_code == 409
                    assert case.get('turns/'+prepared['turn_id']).json()['approval_ids'] == [identifier]
                    unchanged = case.dump() == before
                    assert unchanged
                body = body_for(case, prepared['turn_id'])
                response = decision(case, identifier, body)
                assert response.status_code == 200
                original.append((body, response.content))
            case, prepared, _, identifier = exercise(values, observe)
            if mode == 'independent':
                start((database, identity(case), fixture, assessment), mode=mode)
            before = case.dump()
            assert case.client.get('/api/v1/approvals/'+identifier).status_code == 409
            assert case.get('turns/'+prepared['turn_id']).json()['approval_ids'] == [identifier]
            response = decision(case, identifier, original[0][0])
            assert response.status_code == 200 and response.content == original[0][1]
            unchanged = case.dump() == before
            assert unchanged
