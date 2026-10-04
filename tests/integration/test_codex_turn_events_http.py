"""Original Codex HTTP SSE replay observes one checked local synthetic request."""
import json
import asyncio
from fastapi.routing import APIRoute, iter_route_contexts
import pytest
from starlette.requests import Request

from services.api.app.codex_turn_dto import CodexTurnEvent
from tests.integration.test_codex_turn_dispatch_http import (
    base_consent_case, consent_case, queued, make_dispatch_case, assessment_state,
)
from tests.integration.test_codex_turn_consent_http import grant_fixture, consent_preparation, make_consent_case
from tests.integration.test_codex_artifact_manifest import execute
from services.api.app.application.sessions import SessionService
from services.api.app.dto import RoleRequest
from services.api.app.infrastructure.security import COOKIE_NAME, authenticate

__all__ = ['base_consent_case', 'consent_case', 'assessment_state']


def frames(response):
    assert response.status_code == 200, response.text
    assert response.headers['content-type'].startswith('text/event-stream')
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['vary'] == 'Cookie'
    result = []
    for raw in response.content.split(b'\n\n'):
        if not raw:
            continue
        lines = raw.split(b'\n')
        assert len(lines) == 3
        assert lines[0].startswith(b'id: ') and lines[1].startswith(b'event: ')
        assert lines[2].startswith(b'data: ')
        value = CodexTurnEvent.model_validate(json.loads(lines[2][6:]))
        assert lines[0] == f'id: {value.run_id}:{value.seq}'.encode()
        assert lines[1] == f'event: {value.payload.type}'.encode()
        result.append(value)
    return result


def test_real_completed_turn_events_replay_exact_answer_usage_without_execution(consent_case):
    case, _, sid, _, _, _ = consent_case
    preparation, _, body, ack = queued(consent_case)
    assert case.app.state.codex_turn_worker.run_once() is True
    assert len(case.app.state.synthetic_transport_calls) == 1
    before = case.dump()
    url = 'turns/' + preparation['turn_id'] + '/events'
    events = frames(case.get(url))
    assert [e.seq for e in events] == list(range(1, len(events) + 1))
    assert all(e.turn_id == preparation['turn_id'] and e.run_id == preparation['job']['id'] for e in events)
    assert [e.payload.type for e in events] == ['status', 'status', 'status', 'answer_delta', 'usage', 'terminal']
    assert events[3].payload.text == 'Synthetic exact answer α\n'
    assert events[-1].payload.outcome == 'completed' and events[-1].payload.error_code is None
    result = case.get('turns/' + preparation['turn_id'] + '/result').json()
    assert events[4].payload.usage.model_dump() == result['usage']
    assert result['control']['last_seq'] == len(events)
    assert frames(case.get(url + '?after_seq=3')) == events[3:]
    assert frames(case.client.get('/api/v1/codex/' + url, headers={
        'Last-Event-ID': preparation['job']['id'] + ':3'})) == events[3:]
    assert frames(case.get(url + '?after_seq=' + str(len(events)))) == []
    assert case.post(f'sessions/{sid}/turns', body, 'start').content == ack.content
    assert case.dump() == before and len(case.app.state.synthetic_transport_calls) == 1


@pytest.mark.parametrize('query,header,status,code', [
    ('after_seq=-1', None, 400, 'SCHEMA_INVALID'),
    ('after_seq=1.0', None, 400, 'SCHEMA_INVALID'),
    ('after_seq=1e2', None, 400, 'SCHEMA_INVALID'),
    ('after_seq=١', None, 400, 'SCHEMA_INVALID'),
    ('after_seq=9007199254740992', None, 400, 'SCHEMA_INVALID'),
    ('after_seq=00000000000000000', None, 400, 'SCHEMA_INVALID'),
    ('after_seq=0&after_seq=0', None, 400, 'SCHEMA_INVALID'),
    ('unknown=0', None, 400, 'SCHEMA_INVALID'),
    ('after_seq=999', None, 409, 'CURSOR_AHEAD'),
    ('', 'other_run:0', 400, 'SCHEMA_INVALID'),
    ('', 'TURN:0', 400, 'SCHEMA_INVALID'),
    ('after_seq=1', 'RUN:2', 400, 'SCHEMA_INVALID'),
    ('', 'RUN:-1', 400, 'SCHEMA_INVALID'),
])
def test_event_cursor_rejection_is_read_only(consent_case, query, header, status, code):
    case, _, _, _, _, _ = consent_case
    prepared, _, _, _ = queued(consent_case)
    assert case.app.state.codex_turn_worker.run_once() is True
    if header:
        header = header.replace('TURN', prepared['turn_id']).replace('RUN', prepared['job']['id'])
    before = case.dump()
    response = case.client.get('/api/v1/codex/turns/' + prepared['turn_id'] + '/events?' + query,
        headers={'Last-Event-ID':header} if header else {})
    assert response.status_code == status and response.json()['error']['code'] == code
    assert case.dump() == before and len(case.app.state.synthetic_transport_calls) == 1


def test_duplicate_cursor_header_and_missing_ownership_are_read_only(consent_case):
    case, _, _, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    assert case.app.state.codex_turn_worker.run_once() is True
    url = '/api/v1/codex/turns/' + prep['turn_id'] + '/events'
    before = case.dump()
    cursor = prep['job']['id'] + ':0'
    response = case.client.get(url, headers=[('Last-Event-ID',cursor),('Last-Event-ID',cursor)])
    assert response.status_code == 400 and response.json()['error']['code'] == 'SCHEMA_INVALID'
    response = case.get('turns/turn_missing/events?after_seq=not-decimal')
    assert response.status_code == 404 and response.json()['error']['code'] == 'REFERENCE_MISSING'
    assert case.dump() == before and len(case.app.state.synthetic_transport_calls) == 1


def test_pre_execution_cancel_and_later_stop_cannot_append_an_old_terminal(consent_case):
    case, _, sid, _, _, _ = consent_case
    _, preparation, _, _, _, _ = grant_fixture(consent_case)
    prep = preparation.json()
    ack = case.client.post('/api/v1/jobs/' + prep['job']['id'] + '/cancel',
        json={'expected_revision':1}, headers={**case.headers,'Idempotency-Key':'cancel-original'})
    assert ack.status_code == 200
    url = 'turns/' + prep['turn_id'] + '/events'
    original = frames(case.get(url))
    assert [e.payload.type for e in original] == ['status', 'terminal']
    assert original[-1].payload.outcome == 'cancelled'
    assert case.get('turns/' + prep['turn_id']).json()['last_seq'] == 2
    revision = case.get('sessions/' + sid).json()['revision']
    _, following = consent_preparation(case, sid, revision, key='explicit-following')
    assert following.status_code == 202
    current = case.get('sessions/' + sid).json()
    stopped = case.post('sessions/' + sid + '/interrupt', {
        'turn_id':prep['turn_id'], 'expected_session_revision':current['revision']}, 'old-stop')
    assert stopped.status_code == 200 and stopped.json()['status'] == 'already_terminal'
    before = case.dump()
    assert frames(case.get(url)) == original
    assert case.get('sessions/' + sid).json()['active_turn_id'] == following.json()['turn_id']
    assert case.client.post('/api/v1/jobs/' + prep['job']['id'] + '/cancel',
        json={'expected_revision':1}, headers={**case.headers,'Idempotency-Key':'cancel-original'}).content == ack.content
    assert case.dump() == before and case.app.state.synthetic_transport_calls == []


def test_manifest_event_precedes_unique_terminal_without_new_scan_or_request(consent_case):
    case, sid, prep, _, _, _ = execute(consent_case)
    before = case.dump()
    events = frames(case.get('turns/' + prep['turn_id'] + '/events'))
    types = [e.payload.type for e in events]
    assert types.count('manifest_ready') == types.count('terminal') == 1
    assert types.index('manifest_ready') < types.index('terminal') == len(events) - 1
    manifest = case.get(f'sessions/{sid}/turns/{prep["turn_id"]}/artifacts').json()
    payload = next(e.payload for e in events if e.payload.type == 'manifest_ready')
    assert payload.manifest_id == manifest['manifest']['id']
    assert payload.manifest_sha256 == manifest['manifest_sha256']
    assert case.dump() == before and len(case.app.state.synthetic_transport_calls) == 1


@pytest.mark.parametrize('change', ['role', 'logout'])
def test_real_access_loss_between_deliveries_closes_without_body_or_new_facts(consent_case, change):
    case, _, _, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    assert case.app.state.codex_turn_worker.run_once() is True
    endpoint = next(context.original_route.endpoint for context in iter_route_contexts(case.app.routes)
        if isinstance(context.original_route, APIRoute) and context.path == '/api/v1/codex/turns/{id}/events')

    async def observe():
        async def receive():
            return {'type':'http.request', 'body':b'', 'more_body':False}
        request = Request({'type':'http','method':'GET','path':'/api/v1/codex/turns/' + prep['turn_id'] + '/events',
            'app':case.app,'query_string':b'', 'headers':[(b'cookie',
                (COOKIE_NAME + '=' + case.client.cookies.get(COOKIE_NAME)).encode())]}, receive=receive)
        identity = authenticate(case.app.state.database, request)
        request.state.identity = identity
        response = await endpoint(prep['turn_id'], request)
        iterator = response.body_iterator
        first = await anext(iterator)
        assert b'event: status\n' in first and b'Synthetic exact answer' not in first
        sessions = SessionService(case.app.state.database)
        if change == 'role':
            sessions.switch_role(identity, RoleRequest(role='learner'), 'lose-role')
        else:
            sessions.logout(identity)
        before = case.dump()
        with pytest.raises(StopAsyncIteration):
            await anext(iterator)
        assert case.dump() == before
    asyncio.run(observe())
    assert len(case.app.state.synthetic_transport_calls) == 1


def test_full_owner_damage_precedes_cursor_and_never_repairs(consent_case):
    case, _, _, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    assert case.app.state.codex_turn_worker.run_once() is True
    with case.app.state.database.transaction() as conn:
        conn.execute('DROP TRIGGER codex_turn_events_delete')
        conn.execute('DELETE FROM codex_turn_events WHERE seq=(SELECT MAX(seq) FROM codex_turn_events)')
    before = case.dump()
    response = case.get('turns/' + prep['turn_id'] + '/events?after_seq=not-decimal')
    assert response.status_code == 409 and response.json()['error']['code'] == 'CODEX_HISTORY_DAMAGED'
    assert case.dump() == before and len(case.app.state.synthetic_transport_calls) == 1


def test_approval_required_is_original_member_once_before_terminal(consent_case):
    from tests.integration.test_codex_generic_approval_http import callback_turn
    case, prep, request, frame = callback_turn(consent_case)
    recorded = []
    def peer(gate):
        gate.request(request.body, endpoint=request.endpoint, max_output_tokens=64)
        identifier = case.app.state.codex_turn_worker.receive_operation(frame)
        view = case.client.get('/api/v1/approvals/' + identifier).json()
        body = {'expected_revision':view['revision'], 'operation_sha256':view['operation_sha256'],
            'decision':'decline'}
        response = case.client.post('/api/v1/approvals/' + identifier + '/decision', json=body,
            headers={**case.headers,'Idempotency-Key':'decline-original'})
        assert response.status_code == 200
        recorded.append((identifier,body,response.content))
    case.app.state.synthetic_executor.peer = peer
    assert case.app.state.codex_turn_worker.run_once() is True and len(recorded) == 1
    before = case.dump()
    events = frames(case.get('turns/' + prep['turn_id'] + '/events'))
    approvals = [e for e in events if e.payload.type == 'approval_required']
    assert len(approvals) == 1 and approvals[0].payload.approval_id == recorded[0][0]
    assert approvals[0].seq < events[-1].seq and events[-1].payload.type == 'terminal'
    assert events[-1].payload.outcome == 'cancelled'
    assert case.client.post('/api/v1/approvals/' + recorded[0][0] + '/decision',json=recorded[0][1],
        headers={**case.headers,'Idempotency-Key':'decline-original'}).content == recorded[0][2]
    assert frames(case.get('turns/' + prep['turn_id'] + '/events')) == events
    assert case.dump() == before and len(case.app.state.synthetic_transport_calls) == 1


def test_failed_turn_replays_original_completed_answer_and_usage(consent_case):
    from services.api.app.application.errors import ApiError
    case, _, _, _, _, _ = consent_case
    prep, _, _, _ = queued(consent_case)
    owner = case.app.state.codex_turn_service.outbound_owner
    with case.app.state.database.transaction(immediate=False) as conn:
        state = owner.owned_states(conn, case.app.state.database.workspace_id())[0][prep['turn_id']]
        request = owner.prepared_request(state)
    def peer(gate):
        gate.request(request.body, endpoint=request.endpoint, max_output_tokens=64)
        with pytest.raises(ApiError):
            gate.request(request.body, endpoint=request.endpoint, max_output_tokens=64)
    case.app.state.synthetic_executor.peer = peer
    assert case.app.state.codex_turn_worker.run_once() is True
    before = case.dump()
    events = frames(case.get('turns/' + prep['turn_id'] + '/events'))
    assert next(e.payload.text for e in events if e.payload.type == 'answer_delta') == 'Synthetic exact answer α\n'
    assert next(e.payload.usage for e in events if e.payload.type == 'usage').output_tokens is not None
    assert events[-1].payload.outcome == 'failed'
    assert events[-1].payload.error_code == 'CODEX_NEW_OUTBOUND_CONSENT_REQUIRED'
    assert case.dump() == before and len(case.app.state.synthetic_transport_calls) == 1


@pytest.mark.parametrize('mode', ['independent','open_book'])
def test_real_policy_entry_between_frames_closes_subject_stream(assessment_state, mode):
    from tests.integration.test_assessment_policy import start
    from tests.integration.test_codex_turn_preparation_http import identity
    database, _, fixture, assessment = assessment_state
    for original in make_consent_case(database.settings.data_dir):
        for values in make_dispatch_case(original):
            case, _, _, _, _, _ = values
            prep, _, _, _ = queued(values)
            assert case.app.state.codex_turn_worker.run_once() is True
            endpoint = next(context.original_route.endpoint for context in iter_route_contexts(case.app.routes)
                if isinstance(context.original_route, APIRoute) and context.path == '/api/v1/codex/turns/{id}/events')
            async def observe():
                async def receive():
                    return {'type':'http.request', 'body':b'', 'more_body':False}
                request = Request({'type':'http','method':'GET','path':'/api/v1/codex/turns/' + prep['turn_id'] + '/events',
                    'app':case.app,'query_string':b'', 'headers':[(b'cookie',
                        (COOKIE_NAME + '=' + case.client.cookies.get(COOKIE_NAME)).encode())]}, receive=receive)
                request.state.identity = authenticate(case.app.state.database, request)
                response = await endpoint(prep['turn_id'], request)
                iterator = response.body_iterator
                assert b'event: status\n' in await anext(iterator)
                start((database,identity(case),fixture,assessment), mode=mode)
                before = case.dump()
                with pytest.raises(StopAsyncIteration):
                    await anext(iterator)
                assert case.dump() == before
            asyncio.run(observe())
            assert len(case.app.state.synthetic_transport_calls) == 1
