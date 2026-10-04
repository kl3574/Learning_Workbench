"""Owned HTTP/SQLite controls with an explicit pure peer, never a real CLI."""
import json

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
