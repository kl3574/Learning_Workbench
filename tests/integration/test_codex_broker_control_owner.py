"""Owned HTTP/SQLite controls with an explicit pure peer, never a real CLI."""
import json
import sqlite3

import pytest

from services.api.app.application.errors import ApiError
from services.api.app.application.codex_broker_control_models import BrokerInterruptPrepared, BrokerInterruptStarted
from services.api.app.infrastructure.codex_broker_control_repository import CodexBrokerControlRepository
from services.api.app.main import create_app
from services.api.app.security import issue_bootstrap_code

from tests.integration.test_codex_turn_dispatch_http import consent_case, base_consent_case, queued
from tests.integration.test_codex_turn_preparation_http import identity

__all__ = ['consent_case', 'base_consent_case']


def test_owned_cancel_pairs_one_rpc_without_treating_empty_ack_as_stop(consent_case):
    case, _, sid, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    worker = case.app.state.codex_turn_worker
    calls, failures = [], []

    def control_peer(raw):
        value = json.loads(raw)
        calls.append(raw)
        assert value['method'] == 'turn/interrupt'
        assert value['params']['turnId'] == 'synthetic-turn-original'
        return [json.dumps({'id': value['id'], 'result': {}}).encode()]

    def peer(_gate):
        try:
            worker.bind_control_peer('synthetic-turn-original', control_peer)
            body = {'turn_id': prep['turn_id'], 'expected_session_revision': 4}
            ack = case.post(f'sessions/{sid}/interrupt', body, 'original-stop')
            assert ack.status_code == 200
            assert calls == []  # Transaction/HTTP path is persistence-only.
            assert worker.interrupt_once() is True
            assert worker.interrupt_once() is False
            before = case.dump()
            assert case.post(f'sessions/{sid}/interrupt', body, 'original-stop').content == ack.content
            assert case.get('turns/' + prep['turn_id']).json()['execution'] == 'active'
            assert case.dump() == before
            assert len(calls) == 1
            with case.app.state.database.transaction(immediate=False) as conn:
                snapshot = worker.controls.read_control(conn, identity(case), prep['turn_id'])
                assert snapshot.exchange.control_reply_observed and not snapshot.exchange.terminal_notification_observed
                assert snapshot.mapping.upstream_thread_id != snapshot.mapping.local_thread_id
                assert json.loads(calls[0])['params']['threadId'] == snapshot.mapping.upstream_thread_id
        except Exception as error:
            failures.append(error)
            raise

    case.app.state.synthetic_executor.peer = peer
    assert worker.run_once() is True
    if failures:
        raise failures[0]
    assert case.app.state.synthetic_transport_calls == []
    assert len(calls) == 1


def run_peer(case, body):
    failures = []
    def peer(_gate):
        try:
            body()
        except Exception as error:
            failures.append(error)
            raise
    case.app.state.synthetic_executor.peer = peer
    assert case.app.state.codex_turn_worker.run_once() is True
    if failures:
        raise failures[0]
    assert case.app.state.synthetic_transport_calls == []


def stop(case, sid, tid, key='stop'):
    body = {'turn_id':tid, 'expected_session_revision':case.get('sessions/'+sid).json()['revision']}
    result = case.post(f'sessions/{sid}/interrupt', body, key)
    assert result.status_code == 200
    return body, result


@pytest.mark.parametrize('first', ['jobs', 'session'])
def test_two_routes_and_new_keys_never_send_two_or_promote_terminal_frame(consent_case, first):
    case, _, sid, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    worker, calls = case.app.state.codex_turn_worker, []
    def transport(raw):
        request = json.loads(raw)
        calls.append(raw)
        before = case.dump()
        # A control reply can arrive while another safe HTTP read/new stop runs.
        assert case.get('turns/'+prep['turn_id']).json()['execution'] == 'active'
        assert case.dump() == before
        stop(case, sid, prep['turn_id'], 'inside-send')
        return [json.dumps({'id':request['id'],'result':{}}).encode(),
            json.dumps({'method':'turn/completed','params':{'threadId':request['params']['threadId'],
                'turn':{'id':request['params']['turnId'],'items':[],'status':'interrupted'}}}).encode()]
    def body():
        worker.bind_control_peer('synthetic-turn-paired', transport)
        if first == 'jobs':
            response = case.client.post('/api/v1/jobs/'+prep['job']['id']+'/cancel',
                json={'expected_revision':3},headers={**case.headers,'Idempotency-Key':'jobs-first'})
            assert response.status_code == 200
        old_body, ack = stop(case, sid, prep['turn_id'])
        assert worker.interrupt_once() is True
        stop(case, sid, prep['turn_id'], 'new-key')
        assert worker.interrupt_once() is False and len(calls) == 1
        assert case.post(f'sessions/{sid}/interrupt',old_body,'stop').content == ack.content
        view = case.get('turns/'+prep['turn_id']).json()
        assert view['execution'] == 'active' and view['outcome'] is None and view['manifest_id'] is None
        with case.app.state.database.transaction(immediate=False) as conn:
            snapshot = worker.controls.read_control(conn,identity(case),prep['turn_id'])
            assert snapshot.exchange.control_reply_observed and snapshot.exchange.terminal_notification_observed
            assert sum(r.event.kind=='interrupt_started' for r in snapshot.records) == 1
    run_peer(case, body)


@pytest.mark.parametrize('mapping', ['absent', 'late'])
def test_absent_mapping_zero_rpc_and_late_binding_uses_original_stop(consent_case, mapping):
    case, _, sid, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    worker, calls = case.app.state.codex_turn_worker, []
    def body():
        stop(case, sid, prep['turn_id'])
        assert worker.interrupt_once() is False
        with case.app.state.database.transaction(immediate=False) as conn:
            assert worker.controls.read_control(conn,identity(case),prep['turn_id']) is None
        if mapping == 'late':
            worker.bind_control_peer('synthetic-turn-late', lambda raw:calls.append(raw) or [])
            assert worker.interrupt_once() is True
        assert len(calls) == (1 if mapping=='late' else 0)
    run_peer(case, body)


@pytest.mark.parametrize('mode', ['learner', 'logout'])
def test_safe_new_actor_or_late_logout_does_not_inherit_or_erase_control(consent_case, mode):
    case, _, sid, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    worker, calls = case.app.state.codex_turn_worker, []
    def body():
        worker.bind_control_peer('synthetic-turn-safe',lambda raw:calls.append(raw) or [])
        if mode == 'learner':
            response = case.client.post('/api/v1/session/bootstrap',json={'one_time_code':issue_bootstrap_code(case.app.state.database)},
                headers={'Origin':case.headers['Origin']})
            case.headers['X-CSRF-Token'] = response.json()['csrf_token']
            current = case.client.get('/api/v1/session').json()
            assert current['role'] == 'learner' and current['actor_session_id'] != case.actor_id
            assert case.get('turn-preparations/'+prep['id']).status_code == 403
        stop(case,sid,prep['turn_id'])
        if mode == 'logout':
            with case.app.state.database.transaction() as conn:
                conn.execute("UPDATE local_sessions SET revoked_at='2026-01-01T00:00:00Z' WHERE id=?",(case.actor_id,))
        assert worker.interrupt_once() is True and worker.interrupt_once() is False
        assert len(calls) == 1
    run_peer(case,body)


@pytest.mark.parametrize('failure', ['prepared', 'started'])
def test_caller_transaction_rollback_does_not_spend_or_lose_control(consent_case, monkeypatch, failure):
    case, _, sid, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    worker, calls = case.app.state.codex_turn_worker, []
    original = CodexBrokerControlRepository.append
    def failing(self, *args):
        event = args[-2]
        value = original(self,*args)
        if isinstance(event,BrokerInterruptPrepared if failure=='prepared' else BrokerInterruptStarted):
            raise ApiError(503,'CODEX_RUNTIME_UNAVAILABLE','Synthetic caller transaction failure.')
        return value
    def body():
        worker.bind_control_peer('synthetic-turn-rollback',lambda raw:calls.append(raw) or [])
        old_body = {'turn_id':prep['turn_id'],'expected_session_revision':4}
        if failure == 'prepared':
            before = case.dump()
            monkeypatch.setattr(CodexBrokerControlRepository,'append',failing)
            assert case.post(f'sessions/{sid}/interrupt',old_body,'rollback').status_code == 503
            assert case.dump() == before
            monkeypatch.setattr(CodexBrokerControlRepository,'append',original)
            assert case.post(f'sessions/{sid}/interrupt',old_body,'rollback').status_code == 200
        else:
            stop(case,sid,prep['turn_id'])
            before = case.dump()
            monkeypatch.setattr(CodexBrokerControlRepository,'append',failing)
            with pytest.raises(ApiError):
                worker.interrupt_once()
            assert case.dump() == before
            monkeypatch.setattr(CodexBrokerControlRepository,'append',original)
        assert calls == [] and worker.interrupt_once() is True
        assert worker.interrupt_once() is False and len(calls) == 1
    run_peer(case,body)


@pytest.mark.parametrize('failure', ['lost', 'transport'])
def test_lost_or_unknown_control_never_resends_and_new_reader_does_not_take_live_owner(consent_case, failure):
    case, runtime, sid, proofs, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    worker, calls = case.app.state.codex_turn_worker, []
    def transport(raw):
        calls.append(raw)
        raise ValueError('Synthetic unknown control transport')
    def body():
        worker.bind_control_peer('synthetic-turn-unknown',transport)
        old_body, ack = stop(case,sid,prep['turn_id'])
        restarted = create_app(case.app.state.settings,codex_bootstrap_runtime=runtime,codex_proofs=proofs)
        with case.app.state.database.transaction() as conn:
            assert restarted.state.codex_turn_worker.controls.recover_control(conn,identity(case),prep['turn_id']) is False
        if failure == 'lost':
            worker.controls._live.pop(prep['turn_id'])
        assert worker.interrupt_once() is (failure=='transport')
        stop(case,sid,prep['turn_id'],'new-stop')
        assert worker.interrupt_once() is False
        assert case.post(f'sessions/{sid}/interrupt',old_body,'stop').content == ack.content
        with case.app.state.database.transaction(immediate=False) as conn:
            snapshot = worker.controls.read_control(conn,identity(case),prep['turn_id'])
            assert snapshot.closed.reason == ('live_mapping_lost' if failure=='lost' else 'transport_unknown')
            assert (snapshot.started is not None) == (failure=='transport')
        assert len(calls) == (1 if failure=='transport' else 0)
    run_peer(case,body)


def test_raw_rejections_keep_original_frames_and_prior_ack(consent_case):
    case, _, sid, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    worker, frames = case.app.state.codex_turn_worker, []
    def transport(raw):
        request = json.loads(raw)
        ack = json.dumps({'id':request['id'],'result':{}}).encode()
        frames.extend([ack,b'\xff',b'{"method":"other"}',ack])
        return frames
    def body():
        worker.bind_control_peer('synthetic-turn-raw',transport)
        stop(case,sid,prep['turn_id'])
        assert worker.interrupt_once() is True
        with case.app.state.database.transaction(immediate=False) as conn:
            snapshot = worker.controls.read_control(conn,identity(case),prep['turn_id'])
            observed = [r.event for r in snapshot.records if r.event.kind=='frame_observed']
            assert [o.frame.raw for o in observed] == frames
            assert [o.reason for o in observed] == [None,'invalid_json','unknown_method','duplicate']
            assert snapshot.exchange.control_reply_observed and len(snapshot.exchange.observations) == 1
    run_peer(case,body)


@pytest.mark.parametrize('damage', ['tail','member','head','family','mapping','raw'])
def test_damaged_broker_history_blocks_safe_get_and_old_ack_without_repair(consent_case, damage):
    case, _, sid, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    worker, failures = case.app.state.codex_turn_worker, []
    def peer(_gate):
        try:
            worker.bind_control_peer('synthetic-turn-damage',lambda raw:[])
            old_body, _ = stop(case,sid,prep['turn_id'])
            with case.app.state.database.transaction() as conn:
                for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'codex_broker_%'").fetchall():
                    conn.execute('DROP TRIGGER '+row[0])
                if damage == 'tail':
                    conn.execute('DELETE FROM codex_broker_records WHERE ordinal=2')
                elif damage == 'member':
                    conn.execute('DELETE FROM codex_broker_members WHERE ordinal=1')
                elif damage == 'head':
                    conn.execute('UPDATE codex_broker_heads SET event_count=1')
                elif damage == 'family':
                    for table in ('records','members','heads'):
                        conn.execute('DELETE FROM codex_broker_'+table)
                else:
                    conn.execute('UPDATE codex_broker_records SET record_json=? WHERE ordinal=?',
                        ('{}',1 if damage=='mapping' else 2))
            before = case.dump()
            for response in (case.get('turns/'+prep['turn_id']),case.get('sessions/'+sid),
                             case.post(f'sessions/{sid}/interrupt',old_body,'stop')):
                assert response.status_code == 409 and response.json()['error']['code']=='CODEX_HISTORY_DAMAGED'
            assert case.dump() == before
        except Exception as error:
            failures.append(error)
            raise
    case.app.state.synthetic_executor.peer = peer
    with pytest.raises(ApiError,match='') as result:
        worker.run_once()
    assert result.value.code == 'CODEX_HISTORY_DAMAGED'
    if failures:
        raise failures[0]
    assert case.app.state.synthetic_transport_calls == []


def test_existing_actor_cannot_register_callback_outside_execution(consent_case):
    case, _, _, _, _, _ = consent_case
    queued(consent_case)
    worker = case.app.state.codex_turn_worker
    before = case.dump()
    with pytest.raises(ApiError) as result:
        worker.bind_control_peer('synthetic-turn-forged',lambda raw:[])
    assert result.value.code == 'CODEX_BINDING_INVALID'
    assert worker.interrupt_once() is False and case.dump() == before


def test_all_broker_sql_identity_replacements_and_mutations_are_rejected(consent_case):
    case, _, sid, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    worker = case.app.state.codex_turn_worker
    def body():
        worker.bind_control_peer('synthetic-turn-sql',lambda raw:[])
        stop(case,sid,prep['turn_id'])
        for table in ('records','members','heads'):
            before = case.dump()
            statements = ['DELETE FROM codex_broker_'+table,
                'INSERT OR REPLACE INTO codex_broker_'+table+' SELECT * FROM codex_broker_'+table]
            if table != 'heads':
                statements.append('UPDATE codex_broker_'+table+' SET ordinal=ordinal')
            else:
                statements.append('UPDATE codex_broker_heads SET event_count=event_count')
            for statement in statements:
                with pytest.raises(sqlite3.IntegrityError):
                    with case.app.state.database.transaction() as conn:
                        conn.execute(statement)
                assert case.dump() == before
    run_peer(case,body)
