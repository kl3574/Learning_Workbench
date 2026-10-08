"""Interrupt HTTP facts, real Jobs stop and durable recovery; synthetic peers only."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from threading import Barrier, Event
import json

from fastapi.testclient import TestClient
import pytest

from services.api.app.application.errors import ApiError
from services.api.app.application.codex_turn_interrupt_models import TurnInterruptRecorded
from services.api.app.infrastructure.codex_turn_repository import CodexTurnRepository
from services.api.app.main import create_app
from services.api.app.security import issue_bootstrap_code
from services.api.app.serialization import canonical_json, content_sha256
from tests.integration.test_codex_bootstrap_http import approve
from tests.integration.test_codex_turn_dispatch_http import consent_case, base_consent_case, queued
from tests.integration.test_codex_turn_consent_http import grant_fixture, make_consent_case
from tests.integration.test_assessment_learning_port import assessment_learning_state

__all__ = ['consent_case', 'base_consent_case']
assessment_state = assessment_learning_state


def interrupt(case, sid, tid, key='same-key', revision=None):
    body = {'turn_id': tid, 'expected_session_revision': revision if revision is not None else
            case.get('sessions/'+sid).json()['revision']}
    return body, case.post(f'sessions/{sid}/interrupt', body, key)


def cancel(case, job_id, revision, key='same-key'):
    return case.client.post('/api/v1/jobs/'+job_id+'/cancel', json={'expected_revision': revision},
        headers={**case.headers, 'Idempotency-Key': key})


@pytest.mark.parametrize('first', ['interrupt', 'jobs'])
def test_running_two_entrypoints_share_stop_and_original_snapshots(consent_case, first):
    case, _, sid, _, _, _ = consent_case
    prep, consent, _, _ = queued(consent_case)
    executor = case.app.state.synthetic_executor
    transport = executor.transport
    observed, errors = [], []
    def during_request(*args):
        try:
            if first == 'jobs':
                job_ack = cancel(case, prep['job']['id'], 3)
            body, ack = interrupt(case, sid, prep['turn_id'])
            assert ack.status_code == 200 and ack.json()['status'] == 'interrupt_requested'
            if first == 'interrupt':
                job_ack = cancel(case, prep['job']['id'], 4)
            assert job_ack.status_code == 200 and job_ack.json()['status'] == 'running'
            # Another explicit command observes the same requested state.
            revision = case.get('sessions/'+sid).json()['revision']
            _, repeated = interrupt(case, sid, prep['turn_id'], 'second-key')
            assert repeated.status_code == 200 and repeated.json() == ack.json()
            assert case.get('sessions/'+sid).json()['revision'] == revision == 5
            observed.append((body, ack.content, job_ack.content, 3 if first == 'jobs' else 4))
        except Exception as error:
            errors.append(error)
            raise
        return transport(*args)
    executor.transport = during_request
    assert case.app.state.codex_turn_worker.run_once() is True
    if errors:
        raise errors[0]
    body, ack, job_ack, job_revision = observed[0]
    control = case.get('turns/'+prep['turn_id']).json()
    assert control['outcome'] == 'cancelled' and control['job_revision'] == 5
    assert case.get('sessions/'+sid).json()['revision'] == 6
    result = case.get('turns/'+prep['turn_id']+'/result').json()
    assert result['answer_markdown'] == 'Synthetic exact answer α\n'
    assert result['usage']['input_tokens'] > 0
    assert case.get('consents/'+consent['id']).json()['dispatch']['consumed_provider_calls'] == 1
    before = case.dump()
    assert case.post(f'sessions/{sid}/interrupt', body, 'same-key').content == ack
    replay = cancel(case, prep['job']['id'], job_revision)
    assert replay.content == job_ack and replay.json()['status'] == 'running'
    assert case.get('turns/'+prep['turn_id']).json()['job']['status'] == 'cancelled'
    assert case.app.state.codex_turn_worker.run_once() is False
    assert len(case.app.state.synthetic_transport_calls) == 1 and case.dump() == before


def test_new_actor_learner_safe_stop_does_not_take_over_original_command(consent_case):
    case, _, sid, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    body, ack = interrupt(case, sid, prep['turn_id'])
    assert ack.status_code == 200
    response = case.client.post('/api/v1/session/bootstrap',
        json={'one_time_code': issue_bootstrap_code(case.app.state.database)}, headers={'Origin': case.headers['Origin']})
    case.headers['X-CSRF-Token'] = response.json()['csrf_token']
    current = case.client.get('/api/v1/session').json()
    assert current['actor_session_id'] != case.actor_id and current['role'] == 'learner'
    before = case.dump()
    assert case.post(f'sessions/{sid}/interrupt', body, 'same-key').status_code == 412
    assert case.get('turn-preparations/'+prep['id']).status_code == 403
    assert case.dump() == before
    _, observed = interrupt(case, sid, prep['turn_id'])
    assert observed.status_code == 200 and observed.json()['status'] == 'already_terminal'
    before = case.dump()
    assert interrupt(case, sid, prep['turn_id'])[1].content == observed.content and case.dump() == before


@pytest.mark.parametrize('mode', ['independent', 'open_book'])
def test_real_policy_allows_decrease_and_original_ack(assessment_state, mode):
    from tests.integration.test_assessment_policy import start
    from tests.integration.test_codex_turn_preparation_http import identity
    database, _, fixture, assessment = assessment_state
    for values in make_consent_case(database.settings.data_dir):
        case, _, sid, _, _, _ = values
        _, prepared, _, _, _, _ = grant_fixture(values)
        tid = prepared.json()['turn_id']
        if mode == 'independent':
            body, ack = interrupt(case, sid, tid)
            assert ack.status_code == 200
        start((database, identity(case), fixture, assessment), mode=mode)
        if mode == 'open_book':
            body, ack = interrupt(case, sid, tid)
            assert ack.status_code == 200 and ack.json()['status'] == 'interrupt_requested'
        before = case.dump()
        assert case.post(f'sessions/{sid}/interrupt', body, 'same-key').content == ack.content
        assert case.get('turns/'+tid).status_code == 200
        assert case.get('turn-preparations/'+prepared.json()['id']).status_code == 409
        assert case.dump() == before


def test_wrong_session_known_turn_unknown_and_cross_workspace_are_distinct(consent_case):
    case, _, sid, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    _, _, boot = approve(case, 'second')
    second = case.post('sessions', boot, 'second-session')
    assert second.status_code == 201
    before = case.dump()
    body = {'turn_id': prep['turn_id'], 'expected_session_revision': 4}
    assert case.post('sessions/'+second.json()['id']+'/interrupt', body, 'wrong').status_code == 409
    assert case.post(f'sessions/{sid}/interrupt', {**body, 'turn_id': 'missing_turn'}, 'missing').status_code == 404
    assert case.dump() == before
    with case.app.state.database.transaction() as conn:
        conn.execute("INSERT INTO workspace(id,title,created_at) VALUES('other_workspace','Synthetic','2026-01-01T00:00:00Z')")
        conn.execute("UPDATE local_sessions SET workspace_id='other_workspace' WHERE id=?", (case.actor_id,))
    before = case.dump()
    assert case.post(f'sessions/{sid}/interrupt', body, 'foreign').status_code == 404
    assert case.dump() == before


@pytest.mark.parametrize('damage', ['tail', 'member', 'stop_copy', 'commands', 'head', 'core', 'family'])
def test_damage_blocks_get_and_original_replay_without_repair(consent_case, damage):
    case, _, sid, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    body, ack = interrupt(case, sid, prep['turn_id'])
    assert ack.status_code == 200
    with case.app.state.database.transaction() as conn:
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'codex_turn_%'").fetchall():
            conn.execute('DROP TRIGGER '+row[0])
        if damage == 'tail':
            conn.execute('DELETE FROM codex_turn_events WHERE session_id=? AND seq=(SELECT MAX(seq) FROM codex_turn_events WHERE session_id=?)', (sid, sid))
        elif damage == 'member':
            conn.execute('DELETE FROM codex_turn_interrupts')
        elif damage == 'stop_copy':
            conn.execute("UPDATE codex_turn_interrupts SET stop_command_json='[]'")
        elif damage == 'commands':
            conn.execute("DELETE FROM codex_turn_commands WHERE route='interrupt'")
        elif damage == 'head':
            conn.execute('UPDATE codex_turn_heads SET revision=revision-1')
        elif damage == 'core':
            conn.execute('DELETE FROM runs WHERE id=?', (prep['job']['id'],))
        else:
            for table in ('interrupts', 'commands', 'event_members', 'events', 'heads', 'members', 'sessions'):
                conn.execute('DELETE FROM codex_turn_'+table)
    before = case.dump()
    for response in (case.get('turns/'+prep['turn_id']), case.get('sessions/'+sid),
                     case.post(f'sessions/{sid}/interrupt', body, 'same-key')):
        assert response.status_code == 409 and response.json()['error']['code'] == 'CODEX_HISTORY_DAMAGED'
    assert case.dump() == before


@pytest.mark.parametrize('after_append', [False, True])
def test_whole_stop_transaction_rolls_back_and_same_command_retries(consent_case, monkeypatch, after_append):
    case, _, sid, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    body = {'turn_id': prep['turn_id'], 'expected_session_revision': 4}
    original = CodexTurnRepository.append
    def fail(self, state, event, now):
        if not isinstance(event, TurnInterruptRecorded):
            return original(self, state, event, now)
        if after_append:
            original(self, state, event, now)
        raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', 'Synthetic transaction failure.')
    before = case.dump()
    monkeypatch.setattr(CodexTurnRepository, 'append', fail)
    assert case.post(f'sessions/{sid}/interrupt', body, 'same-key').status_code == 503
    assert case.dump() == before and case.app.state.synthetic_transport_calls == []
    monkeypatch.setattr(CodexTurnRepository, 'append', original)
    assert case.post(f'sessions/{sid}/interrupt', body, 'same-key').status_code == 200
    assert case.get('turns/'+prep['turn_id']).json()['outcome'] == 'cancelled'


def test_committed_stop_is_retained_but_logged_out_delivery_is_denied(consent_case, monkeypatch):
    case, _, sid, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    service = case.app.state.codex_turn_service
    original = service._deliver
    entered, release = Event(), Event()
    def held(*args, **kwargs):
        entered.set()
        assert release.wait(10)
        return original(*args, **kwargs)
    monkeypatch.setattr(service, '_deliver', held)
    body = {'turn_id': prep['turn_id'], 'expected_session_revision': 4}
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(case.post, f'sessions/{sid}/interrupt', body, 'same-key')
        try:
            assert entered.wait(10)
            with case.app.state.database.transaction() as conn:
                conn.execute("UPDATE local_sessions SET revoked_at='2026-01-01T00:00:00Z' WHERE id=?", (case.actor_id,))
                assert conn.execute('SELECT COUNT(*) FROM codex_turn_interrupts').fetchone()[0] == 1
                assert conn.execute('SELECT status FROM jobs WHERE id=?', (prep['job']['id'],)).fetchone()[0] == 'cancelled'
            before = case.dump()
        finally:
            release.set()
        response = future.result(timeout=10)
    assert response.status_code == 401 and 'turn_id' not in response.json()
    assert case.dump() == before


def test_lost_live_mapping_recovery_is_unknown_without_new_execution(consent_case, monkeypatch):
    from services.api.app.application import codex_turn_worker as module
    case, runtime, sid, proofs, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    worker = case.app.state.codex_turn_worker
    with ExitStack() as stack:
        assert worker._claim(stack)
        body, ack = interrupt(case, sid, prep['turn_id'])
        assert ack.status_code == 200
        assert case.get('turns/'+prep['turn_id']).json()['execution'] == 'active'
    later = (datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat().replace('+00:00', 'Z')
    monkeypatch.setattr(module, 'utc_now', lambda: later)
    restarted = create_app(case.app.state.settings, codex_bootstrap_runtime=runtime, codex_proofs=proofs)
    assert restarted.state.codex_turn_worker.recover() == 1
    assert case.get('turns/'+prep['turn_id']).json()['outcome'] == 'unknown'
    client = TestClient(restarted, base_url=case.app.state.settings.origin)
    client.cookies.update(case.client.cookies)
    try:
        before = case.dump()
        replay = client.post(f'/api/v1/codex/sessions/{sid}/interrupt', json=body,
            headers={**case.headers, 'Idempotency-Key': 'same-key'})
        assert replay.content == ack.content and case.dump() == before
        assert restarted.state.codex_turn_worker.recover() == 0
        assert restarted.state.codex_turn_worker.run_once() is False
        assert case.app.state.synthetic_transport_calls == [] and len(runtime.calls) == 1
    finally:
        client.close()


@pytest.mark.parametrize('change', ['extra', 'bool_revision', 'query', 'missing_key', 'missing_origin', 'missing_csrf'])
def test_strict_transport_rejects_without_effect(consent_case, change):
    case, _, sid, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    body = {'turn_id': prep['turn_id'], 'expected_session_revision': 4}
    headers = {**case.headers, 'Idempotency-Key': 'same-key'}
    path = f'/api/v1/codex/sessions/{sid}/interrupt'
    if change == 'extra':
        body['resume'] = True
    elif change == 'bool_revision':
        body['expected_session_revision'] = True
    elif change == 'query':
        path += '?turn_id=other'
    else:
        headers.pop({'missing_key': 'Idempotency-Key', 'missing_origin': 'Origin', 'missing_csrf': 'X-CSRF-Token'}[change])
    before = case.dump()
    response = case.client.post(path, json=body, headers=headers)
    assert response.status_code in {400, 403, 422} and case.dump() == before


@pytest.mark.parametrize('second_entry', ['same_command', 'new_key', 'jobs'])
def test_concurrent_entrypoints_linearize_once(consent_case, second_entry):
    case, _, sid, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    body = {'turn_id': prep['turn_id'], 'expected_session_revision': 4}
    barrier = Barrier(2)
    def invoke(second):
        barrier.wait(timeout=10)
        if second and second_entry == 'jobs':
            return cancel(case, prep['job']['id'], 2)
        key = 'other-key' if second and second_entry == 'new_key' else 'same-key'
        return case.post(f'sessions/{sid}/interrupt', body, key)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.submit(invoke, False), pool.submit(invoke, True)
        responses = [first.result(timeout=20), second.result(timeout=20)]
    if second_entry == 'same_command':
        assert [r.status_code for r in responses] == [200, 200]
        assert responses[0].content == responses[1].content
    else:
        assert sorted(r.status_code for r in responses) == [200, 412]
    assert case.get('sessions/'+sid).json()['revision'] == 6
    assert case.get('turns/'+prep['turn_id']).json()['job_revision'] == 3
    assert case.app.state.synthetic_transport_calls == []


def test_original_ack_after_new_turn_and_restart_is_not_a_current_ack(consent_case):
    from tests.integration.test_codex_turn_consent_http import consent_preparation
    case, runtime, sid, proofs, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    body, ack = interrupt(case, sid, prep['turn_id'])
    assert ack.status_code == 200
    _, next_turn = consent_preparation(case, sid, 6, 'next-prepare')
    assert next_turn.status_code == 202
    app = create_app(case.app.state.settings, codex_bootstrap_runtime=runtime, codex_proofs=proofs)
    client = TestClient(app, base_url=case.app.state.settings.origin)
    client.cookies.update(case.client.cookies)
    try:
        before = case.dump()
        replay = client.post(f'/api/v1/codex/sessions/{sid}/interrupt', json=body,
            headers={**case.headers, 'Idempotency-Key': 'same-key'})
        assert replay.content == ack.content and replay.json()['status'] == 'interrupt_requested'
        current = client.get('/api/v1/codex/sessions/'+sid).json()
        assert current['revision'] == 7 and current['active_turn_id'] == next_turn.json()['turn_id']
        assert case.dump() == before
        assert len(runtime.calls) == 1 and case.app.state.synthetic_transport_calls == []
    finally:
        client.close()


@pytest.mark.parametrize('field', ['inner_basis', 'inner_actor', 'outer_status', 'outer_revision'])
def test_rehashed_interrupt_facts_still_obey_original_stop_binding(consent_case, field):
    case, _, sid, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    body, ack = interrupt(case, sid, prep['turn_id'])
    assert ack.status_code == 200
    with case.app.state.database.transaction() as conn:
        row = conn.execute('SELECT * FROM codex_turn_events WHERE session_id=? ORDER BY seq DESC LIMIT 1', (sid,)).fetchone()
        value = json.loads(row['record_json'])
        event = value['event']
        if field == 'inner_basis':
            event['stop']['command']['body']['expected_revision'] += 1
        elif field == 'inner_actor':
            event['stop']['command']['actor_session_id'] = 'different_actor'
        elif field == 'outer_status':
            event['command']['ack']['status'] = 'already_terminal'
        else:
            event['command']['body']['expected_session_revision'] += 1
        for trigger in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'codex_turn_%'").fetchall():
            conn.execute('DROP TRIGGER '+trigger[0])
        digest = content_sha256(value)
        conn.execute('UPDATE codex_turn_events SET record_json=?,record_sha256=? WHERE session_id=? AND seq=?',
            (canonical_json(value), digest, sid, row['seq']))
        conn.execute('UPDATE codex_turn_event_members SET record_sha256=? WHERE session_id=? AND seq=?', (digest, sid, row['seq']))
        conn.execute('UPDATE codex_turn_heads SET head_sha256=? WHERE session_id=?', (digest, sid))
        conn.execute('UPDATE codex_turn_commands SET command_sha256=? WHERE session_id=? AND seq=?',
            (content_sha256(event['command']), sid, row['seq']))
        conn.execute('UPDATE codex_turn_interrupts SET event_sha256=?,stop_command_json=?,stop_command_sha256=? WHERE session_id=? AND seq=?',
            (digest, canonical_json(event['stop']['command']), content_sha256(event['stop']['command']), sid, row['seq']))
    before = case.dump()
    assert case.get('turns/'+prep['turn_id']).status_code == 409
    assert case.post(f'sessions/{sid}/interrupt', body, 'same-key').status_code == 409
    assert case.dump() == before


def test_interrupt_pending_unsupported_operation_retains_closed_approval(consent_case):
    from tests.integration.test_codex_generic_approval_boundaries import exercise
    original = []
    def observe(case, prepared, raw, identifier):
        control = case.get('turns/'+prepared['turn_id']).json()
        assert control['approval_controls'][0]['decision'] == 'pending'
        body, ack = interrupt(case, prepared['session_id'], prepared['turn_id'])
        assert ack.status_code == 200
        original.append((body, ack.content))
        pending = case.get('turns/'+prepared['turn_id']).json()['approval_controls'][0]
        assert pending['decision'] == 'pending' and pending['validity'] == 'closed'
    case, prepared, _, identifier = exercise(consent_case, observe)
    control = case.get('turns/'+prepared['turn_id']).json()
    assert control['outcome'] == 'cancelled'
    assert control['approval_controls'][0]['validity'] == 'closed'
    read = case.client.get('/api/v1/approvals/'+identifier)
    assert read.status_code == 200 and read.json()['execution'] == 'not_started'
    assert read.json()['decision'] == 'pending' and read.json()['validity'] == 'closed'
    before = case.dump()
    body, ack = original[0]
    assert case.post('sessions/'+prepared['session_id']+'/interrupt', body, 'same-key').content == ack
    assert case.dump() == before and len(case.app.state.synthetic_transport_calls) == 1


def test_late_response_cost_survives_interrupt_and_subject_permission_loss(consent_case):
    case, _, sid, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    executor = case.app.state.synthetic_executor
    original = executor.transport
    errors = []
    def transport(*args):
        try:
            _, ack = interrupt(case, sid, prep['turn_id'])
            assert ack.status_code == 200
            assert case.client.post('/api/v1/session/role', json={'role': 'learner'},
                headers={**case.headers, 'Idempotency-Key': 'learner'}).status_code == 200
        except Exception as error:
            errors.append(error)
            raise
        return original(*args)
    executor.transport = transport
    assert case.app.state.codex_turn_worker.run_once() is True
    if errors:
        raise errors[0]
    assert case.get('turns/'+prep['turn_id']).json()['outcome'] == 'cancelled'
    before = case.dump()
    assert case.get('turns/'+prep['turn_id']+'/result').status_code == 403
    assert case.dump() == before
    owner = case.app.state.codex_turn_service.outbound_owner
    with case.app.state.database.transaction(immediate=False) as conn:
        conn.execute('PRAGMA query_only=ON')
        state = owner.owned_states(conn, case.app.state.database.workspace_id())[0][prep['turn_id']]
        assert state.finished.execution_result.answer == 'Synthetic exact answer α\n'
        assert state.finished.usage.input_tokens > 0
    assert len(case.app.state.synthetic_transport_calls) == 1
