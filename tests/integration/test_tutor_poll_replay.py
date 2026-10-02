"""Actual HTTP polling/replay during the real SQLite + synthetic Provider chain."""
import asyncio

from services.api.app.infrastructure.content_repository import reference
from services.api.app.tutor_dto import TutorContextBinding, TutorThreadCreate
from packages.contracts import domain_models as dm
from tests.integration.test_retrieval import all_rows
from tests.integration import test_tutor_http as http_fixture
from tests.integration.test_tutor_http import command
from tests.integration.test_tutor_runs import approved, configured
from tests.provider_protocol_fixture import local_provider


http_tutor = http_fixture.http_tutor

def test_actual_http_observers_and_original_ack_replay_do_not_change_final_run(http_tutor, tmp_path):
    database, identity, _, app, client, headers, block, _ = http_tutor
    create = TutorThreadCreate(scope=dm.ViewContext(view_kind='lesson', active_ref=reference(block)),
        binding=TutorContextBinding(practice=None, assessment=None), title='original synthetic polling thread')
    tutor = database, identity, app.state.tutor_service, create
    answer = 'Original synthetic protocol answer; no quality claim.\n'
    async def run():
        async with local_provider(text=answer) as server:
            worker, consents, _ = configured(tutor, tmp_path, server.base_url)
            _, request, ack, _, _ = await asyncio.to_thread(approved, tutor, worker, consents)
            url = '/api/v1/runs/' + ack.run.id
            done = asyncio.Event()
            async def poll():
                sequence = 0
                observed = []
                while True:
                    response = await asyncio.to_thread(client.get, url)
                    assert response.status_code == 200, response.text
                    current = response.json()
                    assert current['run']['id'] == ack.run.id
                    assert current['run']['last_seq'] >= sequence
                    sequence = current['run']['last_seq']
                    observed.append(current['run']['status'])
                    if done.is_set():
                        return observed
                    await asyncio.sleep(.25)
            observers = [asyncio.create_task(poll()) for _ in range(4)]
            try:
                assert await asyncio.to_thread(worker.run_once)
            finally:
                done.set()
                observations = await asyncio.gather(*observers)
            assert all(observations)
            current = client.get(url).json()
            assert current['run']['status'] == 'completed'
            assert current['run']['answer_markdown'] == answer
            assert current['result']['provider']['outcome'] == 'complete'
            assert len(server.requests) == 1
            before = all_rows(database)
            original = client.post('/api/v1/tutor/runs', json=request.model_dump(mode='json'),
                headers=command(headers, 'start'))
            assert original.status_code == 202
            assert original.json() == ack.model_dump(mode='json')
            assert original.json()['run']['status'] == 'queued'
            assert client.get(url).json() == current
            last = current['run']['last_seq']
            replay = client.get(url + '/events', params={'after_seq': last - 1})
            assert replay.status_code == 200 and replay.text.count('event: completed') == 1
            assert client.get(url + '/events', params={'after_seq': last}).text == ''
            assert all_rows(database) == before
            assert not await asyncio.to_thread(worker.run_once)
            assert len(server.requests) == 1
    asyncio.run(run())
