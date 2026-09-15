"""Real Content/Context/Tutor/Jobs/SQLite HTTP and observer boundaries.

No production provider/proof is registered; no external model is called.
The direct StreamingResponse iterator tests observe real persisted events while
changing the actual local session between two deliveries, without a browser.
"""
import asyncio

from fastapi.routing import APIRoute, iter_route_contexts
from fastapi.testclient import TestClient
import pytest
from starlette.requests import Request

from packages.contracts import domain_models as dm
from services.api.app.application.assessment import AssessmentService
from services.api.app.application.sessions import SessionService
from services.api.app.assessment_dto import AssessmentAttemptCreate
from services.api.app.dto import RoleRequest
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import (
    COOKIE_NAME, consume_bootstrap, issue_bootstrap_code,
)
from services.api.app.main import create_app
from tests.assessment_fixtures import assessment_fixture
from tests.integration.test_retrieval import all_rows, publish_small
from tests.integration.test_assessment_attempts import import_fixture


@pytest.fixture
def http_tutor(tmp_path):
    database = Database(Settings(data_dir=tmp_path / 'data'))
    database.initialize()
    token, identity = consume_bootstrap(database, issue_bootstrap_code(database))
    blocks, lesson, _ = publish_small(database, identity, 'http_tutor', ['原创合成材料：条件必须完整。\n'])
    app = create_app(database.settings)
    client = TestClient(app, base_url=database.settings.origin)
    client.cookies.set(COOKIE_NAME, token)
    headers = {'Origin': database.settings.origin, 'X-CSRF-Token': identity.csrf_token}
    yield database, identity, token, app, client, headers, blocks[0], lesson
    client.close()


def command(headers, key):
    return {**headers, 'Idempotency-Key': key}


def start(http_tutor):
    _, identity, _, _, client, headers, block, _ = http_tutor
    # This is the Reader's real public block context, with no implicit parent lift.
    scope = dm.ViewContext(view_kind='lesson', active_ref=reference(block)).model_dump(mode='json')
    binding = {'practice': None, 'assessment': None}
    body = {'scope': scope, 'binding': binding, 'title': '原创合成对话'}
    thread = client.post('/api/v1/threads', json=body, headers=command(headers, 'thread'))
    assert thread.status_code == 201, thread.text
    request = {'request': {'thread_id': thread.json()['id'], 'workspace_id': identity.workspace_id,
                          'message': '请解释条件。', 'intent': 'explain', 'context': scope,
                          'web_search': False, 'consent_id': None},
               'expected_thread_revision': thread.json()['revision'], 'binding': binding}
    ack = client.post('/api/v1/tutor/runs', json=request, headers=command(headers, 'run'))
    assert ack.status_code == 202, ack.text
    return body, thread.json(), request, ack.json()


def cancel(http_tutor, run):
    _, _, _, _, client, headers, _, _ = http_tutor
    response = client.post('/api/v1/runs/' + run['run']['id'] + '/cancel',
                           json={'expected_revision': run['job_revision']},
                           headers=command(headers, 'cancel'))
    assert response.status_code == 200, response.text
    return response


def test_real_http_local_prepare_cancel_original_ack_and_terminal_sse_are_zero_repeat_work(http_tutor):
    database, _, _, app, client, headers, _, _ = http_tutor
    _, thread, request, ack = start(http_tutor)
    run_id = ack['run']['id']
    assert app.state.tutor_worker.run_once()
    current = client.get('/api/v1/runs/' + run_id)
    assert current.status_code == 200, current.text
    prepared = current.json()
    assert prepared['run']['status'] == 'awaiting_approval'
    assert prepared['context']['included'][0]['material_review'] == 'unreviewed'
    assert prepared['latest_proposal_id'] is None and prepared['consent_id'] is None
    assert prepared['result']['provider'] is None
    stopped = cancel(http_tutor, prepared)
    assert set(stopped.json()) == {'id', 'status', 'job_revision', 'cancel_requested'}
    assert stopped.json()['status'] == 'cancelled'
    before = all_rows(database)
    replay = client.post('/api/v1/tutor/runs', json=request, headers=command(headers, 'run'))
    assert replay.json() == ack
    assert client.get('/api/v1/runs/' + run_id).json()['run']['status'] == 'cancelled'
    pages = client.get('/api/v1/threads').json()
    assert [item['id'] for item in pages['items']] == [thread['id']]
    messages = client.get('/api/v1/threads/' + thread['id'] + '/messages')
    assert messages.status_code == 200
    stream = client.get('/api/v1/runs/' + run_id + '/events')
    assert stream.status_code == 200 and stream.headers['content-type'].startswith('text/event-stream')
    events = [line for line in stream.text.splitlines() if line.startswith('event: ')]
    assert events[0] == 'event: queued' and events[-1] == 'event: cancelled'
    assert events.count('event: cancelled') == 1 and 'event: context_ready' in events
    latest = client.get('/api/v1/runs/' + run_id).json()
    seq = latest['run']['last_seq']
    resumed = client.get('/api/v1/runs/' + run_id + '/events?after_seq=' + str(seq - 1),
                         headers={'Last-Event-ID': run_id + ':' + str(seq - 1)})
    assert resumed.text.count('event: cancelled') == 1
    assert client.get('/api/v1/runs/' + run_id + '/events?after_seq=' + str(seq)).text == ''
    assert all_rows(database) == before
    assert app.state.tutor_worker.run_once() is False


def test_http_keys_cas_unknown_fields_and_failed_reads_cannot_create_work(http_tutor):
    database, _, _, _, client, headers, _, _ = http_tutor
    _, _, body, ack = start(http_tutor)
    before = all_rows(database)
    assert client.post('/api/v1/tutor/runs', json=body, headers=headers).status_code == 400
    assert client.post('/api/v1/tutor/runs', json=body,
                       headers=command(headers, 'bad key')).status_code == 400
    changed = {**body, 'unexpected': 'synthetic'}
    assert client.post('/api/v1/tutor/runs', json=changed,
                       headers=command(headers, 'bad-body')).status_code == 422
    id = ack['run']['id']
    assert client.get('/api/v1/runs/' + id + '/events?after_seq=2').status_code == 409
    assert client.get('/api/v1/runs/' + id + '/events?after_seq=1&after_seq=1').status_code == 400
    assert client.get('/api/v1/runs/' + id + '?unexpected=1').status_code == 400
    assert client.post('/api/v1/runs/' + id + '/cancel',
                       json={'expected_revision': 2}, headers=command(headers, 'stale')).status_code == 412
    assert all_rows(database) == before


@pytest.mark.parametrize('mode', ['independent', 'open_book'])
def test_real_test_policy_precedes_bad_cursors_but_safe_control_survives(http_tutor, mode):
    database, identity, _, _, client, headers, block, _ = http_tutor
    _, thread, _, ack = start(http_tutor)
    cancel(http_tutor, ack)
    fixture = assessment_fixture('tutorpolicy' + mode.replace('_', ''))
    import_fixture(database, identity, fixture, 'policy-source')
    assessment = AssessmentService(database)
    assessment.create_attempt(identity, fixture.assessment.id,
                              AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode=mode), 'attempt')
    for path in ['/api/v1/threads?unknown=1',
                 '/api/v1/threads/' + thread['id'] + '/messages?cursor=',
                 '/api/v1/runs/' + ack['run']['id'] + '/events?after_seq=invalid']:
        response = client.get(path)
        assert response.status_code == 409, response.text
        assert response.json()['error']['code'] in {'ASSESSMENT_ACTIVE', 'POLICY_DENIED'}
    controlled = client.post('/api/v1/runs/' + ack['run']['id'] + '/cancel',
                             json={'expected_revision': 1}, headers=command(headers, 'terminal-noop'))
    assert controlled.status_code == 200
    assert set(controlled.json()) == {'id', 'status', 'job_revision', 'cancel_requested'}
    material = client.get('/api/v1/blocks/' + block.id + '/body?revision=1')
    assert material.status_code == (200 if mode == 'open_book' else 409)


@pytest.mark.parametrize('change', ['logout', 'role'])
def test_actual_session_change_between_deliveries_stops_observer_without_new_event(http_tutor, change):
    database, identity, token, app, _, _, _, _ = http_tutor
    _, _, _, ack = start(http_tutor)
    cancel(http_tutor, ack)
    id = ack['run']['id']
    endpoint = next(context.original_route.endpoint for context in iter_route_contexts(app.routes)
                    if isinstance(context.original_route, APIRoute)
                    and context.path == '/api/v1/runs/{id}/events')

    async def observe():
        async def receive():
            return {'type': 'http.request', 'body': b'', 'more_body': False}
        request = Request({'type': 'http', 'method': 'GET', 'path': '/api/v1/runs/' + id + '/events',
                           'app': app, 'query_string': b'', 'headers': [(b'cookie', (COOKIE_NAME + '=' + token).encode())]}, receive=receive)
        request.state.identity = identity
        response = await endpoint(id, request)
        iterator = response.body_iterator
        first = await anext(iterator)
        assert b'event: queued' in first
        sessions = SessionService(database)
        if change == 'logout':
            sessions.logout(identity)
        else:
            sessions.switch_role(identity, RoleRequest(role='author'), 'role')
        before = all_rows(database)
        with pytest.raises(StopAsyncIteration):
            await anext(iterator)
        assert all_rows(database) == before
    asyncio.run(observe())
