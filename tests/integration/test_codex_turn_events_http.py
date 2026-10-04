"""Original Codex HTTP SSE replay observes one checked local synthetic request."""
import json

from services.api.app.codex_turn_dto import CodexTurnEvent
from tests.integration.test_codex_turn_dispatch_http import (
    base_consent_case, consent_case, queued,
)

__all__ = ['base_consent_case', 'consent_case']


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
