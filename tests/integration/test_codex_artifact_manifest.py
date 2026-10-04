"""Real synthetic dispatch, local files, copied BlobStore and owner HTTP reads."""
import json

import pytest

from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.infrastructure.codex_answer_materializer import CheckedAnswerMaterializer
from tests.integration.test_codex_turn_dispatch_http import queued, consent_case, base_consent_case

__all__ = ['consent_case', 'base_consent_case']


def execute(values):
    case, _, sid, _, _, _ = values
    case.app.state.codex_turn_service.artifacts.producer = CheckedAnswerMaterializer(case.app.state.settings.data_dir)
    prep, consent, body, ack = queued(values)
    assert case.app.state.codex_turn_worker.run_once() is True
    return case, sid, prep, consent, body, ack


def manifest_path(sid, prep):
    return f'sessions/{sid}/turns/{prep["turn_id"]}/artifacts'


def test_real_answer_file_is_copied_before_manifest_and_unique_terminal(consent_case):
    case, sid, prep, consent, body, ack = execute(consent_case)
    before = case.dump()
    response = case.get(manifest_path(sid, prep))
    assert response.status_code == 200
    view = response.json()
    manifest = view['manifest']
    assert view['manifest_sha256'] == sha256_bytes(canonical_bytes(manifest))
    assert manifest['source_outcome'] == 'completed'
    assert [manifest[key] for key in ['mathematical', 'sources', 'independent_pedagogy']] == ['NOT_RUN']*3
    assert len(manifest['entries']) == 1 and manifest['excluded'] == []
    entry = manifest['entries'][0]
    expected = 'Synthetic exact answer α\n'.encode()
    assert entry['logical_path'] == 'answer.md' and entry['sha256'] == sha256_bytes(expected)
    assert entry['scan'] == 'PASS' and entry['import_kind'] == 'markdown'
    download = case.client.get(f'/api/v1/artifacts/{entry["artifact_id"]}/download')
    assert download.status_code == 200 and download.content == expected
    control = case.get('turns/'+prep['turn_id']).json()
    assert control['manifest_id'] == manifest['id'] and control['outcome'] == 'completed'
    assert case.get('sessions/'+sid).json()['revision'] == 5
    assert case.post(f'sessions/{sid}/turns', body, 'start').content == ack.content
    assert case.dump() == before
    with case.app.state.database.transaction(immediate=False) as conn:
        events = [json.loads(row[0])['event'] for row in conn.execute('SELECT record_json FROM codex_turn_events ORDER BY seq')]
        assert events[-1]['kind'] == 'lifecycle' and events[-1]['phase'] == 'terminal'
        assert [event['kind'] for event in events].count('manifest_ready') == 1
        record = json.loads(conn.execute('SELECT record_json FROM codex_artifact_records').fetchone()[0])
        assert record['receipt']['collection']['source']['answer_sha256'] == sha256_bytes(expected)
        assert 'manifest_sha256' not in record['receipt']
    assert len(case.app.state.synthetic_transport_calls) == 1
    assert case.app.state.codex_turn_worker.run_once() is False
    # Later sandbox mutation cannot change the immutable, checked copy.
    for path in (case.app.state.settings.data_dir/'codex-answer-outputs').glob('*/answer.md'):
        path.write_bytes(b'changed after terminal')
    assert case.get(manifest_path(sid, prep)).content == response.content
    assert case.client.get(f'/api/v1/artifacts/{entry["artifact_id"]}/download').content == expected


def test_scan_rejection_retains_actual_model_result_and_never_repeats(consent_case, monkeypatch):
    from services.api.app.infrastructure import codex_answer_materializer as materializer
    from services.api.app.application.errors import ApiError
    case, _, sid, _, _, _ = consent_case
    case.app.state.codex_turn_service.artifacts.producer = CheckedAnswerMaterializer(case.app.state.settings.data_dir)
    prep, _, _, _ = queued(consent_case)
    def reject(*args):
        raise ApiError(409, 'CODEX_ARTIFACT_REJECTED', '受控测试拒绝。')
    monkeypatch.setattr(materializer, '_scan', reject)
    assert case.app.state.codex_turn_worker.run_once() is True
    control = case.get('turns/'+prep['turn_id']).json()
    assert control['outcome'] == 'failed' and control['error_code'] == 'CODEX_ARTIFACT_REJECTED'
    assert case.get(manifest_path(sid, prep)).status_code == 404
    with case.app.state.database.transaction(immediate=False) as conn:
        states, _ = case.app.state.codex_turn_service.outbound_owner.owned_states(conn, case.app.state.database.workspace_id())
        actual = states[prep['turn_id']].finished.execution_result
        assert actual.outcome == 'completed' and actual.answer == 'Synthetic exact answer α\n'
        assert actual.usage.output_tokens == len(actual.answer.encode())
        assert conn.execute('SELECT count(*) FROM codex_artifact_records').fetchone()[0] == 0
    assert case.app.state.codex_turn_worker.run_once() is False
    assert len(case.app.state.synthetic_transport_calls) == 1


@pytest.mark.parametrize('table', ['codex_artifact_records', 'codex_artifact_members'])
def test_loss_of_any_artifact_owner_family_fails_control_and_manifest_reads(consent_case, table):
    case, sid, prep, _, _, _ = execute(consent_case)
    with case.app.state.database.transaction() as conn:
        conn.execute(f'DROP TRIGGER {table}_delete')
        conn.execute(f'DELETE FROM {table}')
    assert case.get(manifest_path(sid, prep)).status_code == 409
    assert case.get('turns/'+prep['turn_id']).status_code == 409


def test_late_actor_loss_keeps_files_but_refuses_subject_delivery(consent_case):
    case, _, sid, _, _, _ = consent_case
    original = case.app.state.synthetic_executor.transport
    def transport(*args):
        assert case.client.post('/api/v1/session/role', json={'role':'learner'},
            headers={**case.headers, 'Idempotency-Key':'lose-author'}).status_code == 200
        return original(*args)
    case.app.state.synthetic_executor.transport = transport
    case, sid, prep, _, _, _ = execute(consent_case)
    control = case.get('turns/'+prep['turn_id'])
    assert control.status_code == 200 and control.json()['manifest_id'] is not None
    assert case.get(manifest_path(sid, prep)).status_code == 403
    assert case.client.post('/api/v1/session/role', json={'role':'author'},
        headers={**case.headers, 'Idempotency-Key':'author-again'}).status_code == 200
    manifest = case.get(manifest_path(sid, prep)).json()['manifest']
    assert manifest['source_outcome'] == 'failed'
    assert manifest['entries'][0]['sha256'] == sha256_bytes('Synthetic exact answer α\n'.encode())
