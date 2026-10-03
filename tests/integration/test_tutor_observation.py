"""Controlled metadata boundaries; no paid Provider or browser."""
from contextlib import contextmanager
import pytest

from services.api.app.application.tutor_worker import TutorWorker
from tests.integration.test_tutor_runs import started, NoTransport, build_material
from tests.integration import test_tutor_runs as fixture_module
from tests.integration import test_tutor_http as http_fixture_module

from tests.integration.test_retrieval import all_rows

tutor = fixture_module.tutor
http_tutor = http_fixture_module.http_tutor


def test_terminal_observer_is_after_actual_commit_and_cannot_change_result(tutor):
    database, identity, service, _ = tutor
    _, _, ack = started(tutor)
    seen = []
    def observe(run_id, status):
        # A separate connection can read this terminal: not an in-TX notification.
        current = service.read(identity, run_id)
        assert current.run.status == status == 'failed'
        seen.append((run_id, status))
        raise ValueError('SYNTHETIC_OBSERVER_FAILURE')
    worker = TutorWorker(database, service.context, NoTransport(), build_material, terminal_observer=observe)
    lease = worker.claim()
    worker._finish(identity, lease)
    assert seen == [(ack.run.id, 'failed')]
    before = all_rows(database)
    worker._finish(identity, lease)  # An already-terminal no-op is not a commit observation.
    assert seen == [(ack.run.id, 'failed')] and all_rows(database) == before


def test_failed_transaction_emits_no_terminal_commit(tutor, monkeypatch):
    database, identity, service, _ = tutor
    started(tutor)
    seen = []
    worker = TutorWorker(database, service.context, NoTransport(), build_material, terminal_observer=lambda *x: seen.append(x))
    lease = worker.claim()
    before = all_rows(database)
    original = database.transaction
    @contextmanager
    def failed(*args, **kwargs):
        with original(*args, **kwargs) as connection:
            yield connection
            raise RuntimeError('SYNTHETIC_PRECOMMIT_FAILURE')
    monkeypatch.setattr(database, 'transaction', failed)
    with pytest.raises(RuntimeError, match='SYNTHETIC_PRECOMMIT_FAILURE'):
        worker._finish(identity, lease)
    assert not seen and all_rows(database) == before


def test_selected_instance_read_and_send_share_context_without_body_capture(tutor):
    import asyncio
    from starlette.concurrency import run_in_threadpool
    from tests.tutor_observation import TutorObservation, TutorObservationMiddleware, install_owner_observation
    database, identity, service, _ = tutor
    worker = TutorWorker(database, service.context, NoTransport(), build_material)
    recorder = TutorObservation(capacity=20)
    install_owner_observation(service, worker, None, recorder)
    service.authorize(identity)  # Actual HTTP preparation authorizes before a Run exists.
    assert recorder.snapshot()['records'] == []
    _, _, ack = started(tutor)
    delivered = []
    async def application(scope, receive, send):
        view = await run_in_threadpool(service.read, identity, ack.run.id)
        assert view.run.id == ack.run.id
        await send({'type': 'http.response.start', 'status': 200, 'headers': []})
        await send({'type': 'http.response.body', 'body': f'id: {ack.run.id}:1\nevent: queued\ndata: PRIVATE_BODY\n\n'.encode()})
    wrapped = TutorObservationMiddleware(application, recorder)
    async def run():
        async def send(value):
            delivered.append(value)
        await wrapped({'type': 'http', 'method': 'GET', 'path': f'/api/v1/runs/{ack.run.id}/events',
            'query_string': b'after_seq=0', 'headers': [(b'x-tutor-observation', b'page:1'), (b'cookie', b'PRIVATE_COOKIE')]}, None, send)
    before = all_rows(database)
    asyncio.run(run())
    assert all_rows(database) == before
    snapshot = recorder.snapshot()
    events = snapshot['records']
    read = next(item for item in events if item['stage'] == 'owner_read_returned')
    sent = next(item for item in events if item['stage'] == 'asgi_send_returned')
    assert read['request'] == sent['request'] and read['correlation'] == sent['correlation'] == 'page:1'
    assert sent['seq'] == 1 and sent['event'] == 'queued' and sent['after'] == 0
    assert delivered[-1]['body'].endswith(b'data: PRIVATE_BODY\n\n')
    assert 'PRIVATE_' not in str(snapshot)


def test_ring_overflow_and_malformed_values_are_incomplete_not_business_facts():
    from tests.tutor_observation import TutorObservation
    recorder = TutorObservation(capacity=2)
    recorder.bind('run_unit')
    for _ in range(3):
        recorder.emit('owner_read_returned', 'run_unit', status='running', seq=2, revision=1)
    recorder.emit('owner_read_returned', 'run_unit', text='PRIVATE_BODY')
    recorder.emit('owner_read_returned', 'run_other', status='running')
    snapshot = recorder.snapshot()
    assert len(snapshot['records']) == 2 and snapshot['omitted'] == 2 and snapshot['invalid'] == 1
    assert 'PRIVATE_BODY' not in str(snapshot)


def test_actual_loopback_provider_commit_and_tutor_commit_share_the_original_run(tutor, tmp_path):
    import asyncio
    from tests.integration.test_tutor_runs import configured, approved
    from tests.provider_protocol_fixture import local_provider
    from tests.tutor_observation import TutorObservation, install_owner_observation
    async def run():
        async with local_provider(text='PRIVATE_SYNTHETIC_ANSWER') as server:
            worker, consents, dispatch = configured(tutor, tmp_path, server.base_url)
            _, identity, service, _ = tutor
            recorder = TutorObservation()
            install_owner_observation(service, worker, dispatch, recorder)
            _, _, original, _, _ = await asyncio.to_thread(approved, tutor, worker, consents)
            assert await asyncio.to_thread(worker.run_once)
            actual = service.read(identity, original.run.id)
            assert actual.run.status == 'completed' and actual.run.answer_markdown == 'PRIVATE_SYNTHETIC_ANSWER'
            records = recorder.snapshot()['records']
            provider = [value for value in records if value['stage'] == 'provider_terminal_commit_returned']
            tutor_commits = [value for value in records if value['stage'] == 'tutor_terminal_committed']
            assert len(provider) == len(tutor_commits) == len(server.requests) == 1
            assert provider[0]['run'] == tutor_commits[0]['run'] == original.run.id
            assert provider[0]['receipt'] == actual.result.provider.receipt_id
            assert provider[0]['ordinal'] < tutor_commits[0]['ordinal']
            assert 'PRIVATE_SYNTHETIC_ANSWER' not in str(records)
    asyncio.run(run())


def test_http_preparation_does_not_capture_authorization_before_first_run(http_tutor):
    from tests.tutor_observation import TutorObservation, install_owner_observation
    database, _, _, app, client, _, _, _ = http_tutor
    recorder = TutorObservation()
    install_owner_observation(app.state.tutor_service, app.state.tutor_worker, None, recorder)
    # The real list HTTP route authorizes before any Run has been selected.
    before = all_rows(database)
    response = client.get('/api/v1/threads')
    assert response.status_code == 200
    assert all_rows(database) == before
    snapshot = recorder.snapshot()
    assert snapshot['selected_run'] is None and snapshot['records'] == []
    _, _, _, ack = http_fixture_module.start(http_tutor)
    selected = ack['run']['id']
    response = client.get('/api/v1/runs/' + selected)
    assert response.status_code == 200
    snapshot = recorder.snapshot()
    assert snapshot['selected_run'] == selected
    assert snapshot['records'][0]['stage'] == 'run_bound'
    assert all(item['run'] == selected for item in snapshot['records'])
    assert any(item['stage'] == 'owner_read_returned' for item in snapshot['records'])
