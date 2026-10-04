"""Real answer artifact -> ordinary Import parser/preview; never commit/publish."""
import pytest
from fastapi.testclient import TestClient

from services.api.app.infrastructure.import_worker import ImportWorker
from services.api.app.main import create_app
from tests.integration.test_codex_artifact_manifest import execute
from tests.integration.test_codex_turn_dispatch_http import consent_case, base_consent_case

__all__ = ['consent_case', 'base_consent_case']


def selected(values):
    case, sid, prep, _, _, _ = execute(values)
    view = case.get(f'sessions/{sid}/turns/{prep["turn_id"]}/artifacts').json()
    body = {'turn_id':prep['turn_id'], 'artifact_ids':[view['manifest']['entries'][0]['artifact_id']],
        'expected_manifest_sha256':view['manifest_sha256']}
    return case, sid, view, body


def test_real_ordinary_preview_completes_aggregate_and_original_ack_survives_rebuild(consent_case):
    case, sid, manifest, body = selected(consent_case)
    before_calls = len(case.app.state.synthetic_transport_calls)
    ack = case.post(f'sessions/{sid}/artifacts/import', body, 'select-original')
    assert ack.status_code == 202 and ack.json()['status'] == 'queued'
    identifier = ack.json()['id']
    before = case.dump()
    view = case.get('artifact-imports/'+identifier)
    assert view.status_code == 200 and view.json()['job'] == ack.json()
    item = view.json()['items'][0]
    assert item['artifact_id'] == body['artifact_ids'][0]
    assert item['source_sha256'] == manifest['manifest']['entries'][0]['sha256']
    assert case.client.get('/api/v1/imports/'+item['import_id']).json()['status'] == 'staged'
    assert case.app.state.codex_artifact_imports.run_once() is False
    assert case.dump() == before
    assert ImportWorker(case.app.state.database).run_once() is True
    preview = case.client.get('/api/v1/imports/'+item['import_id'])
    assert preview.status_code == 200 and preview.json()['status'] == 'preview_ready'
    assert 'CODEX_IMPORTED_MATERIAL_UNREVIEWED' in [warning['code'] for warning in preview.json()['warnings']]
    # GET is only an observation: it does not perform the aggregate transition.
    assert case.get('artifact-imports/'+identifier).json()['job']['status'] == 'queued'
    assert case.app.state.codex_artifact_imports.run_once() is True
    current = case.get('artifact-imports/'+identifier).json()
    assert current['job']['status'] == 'completed'
    assert current['items'][0]['job']['status'] == 'awaiting_approval'
    job = case.client.get('/api/v1/jobs/'+identifier)
    assert job.status_code == 200 and job.json()['result_refs'] == [] and job.json()['kind'] == 'codex_artifact_import'
    before = case.dump()
    assert case.post(f'sessions/{sid}/artifacts/import', body, 'select-original').content == ack.content
    assert case.app.state.codex_artifact_imports.run_once() is False
    assert len(case.app.state.synthetic_transport_calls) == before_calls == 1
    assert case.dump() == before
    rebuilt = create_app(case.app.state.settings, codex_bootstrap_runtime=consent_case[1], codex_proofs=consent_case[3])
    with TestClient(rebuilt, base_url=case.app.state.settings.origin) as client:
        client.cookies.update(case.client.cookies)
        assert client.get('/api/v1/codex/artifact-imports/'+identifier).json() == current
        assert client.post(f'/api/v1/codex/sessions/{sid}/artifacts/import', json=body,
            headers={**case.headers, 'Idempotency-Key':'select-original'}).content == ack.content


@pytest.mark.parametrize('change,status', [('hash',412), ('foreign',409), ('duplicate',409), ('session',409)])
def test_invalid_selection_creates_no_job_stage_or_consumption(consent_case, change, status):
    case, sid, _, body = selected(consent_case)
    if change == 'hash':
        body['expected_manifest_sha256'] = '0'*64
    elif change == 'foreign':
        body['artifact_ids'] = ['artifact_other']
    elif change == 'duplicate':
        body['artifact_ids'] *= 2
    else:
        sid = 'session_other'
    before = case.dump()
    response = case.post(f'sessions/{sid}/artifacts/import', body, 'bad-selection')
    assert response.status_code == status
    assert case.dump() == before
    assert len(case.app.state.synthetic_transport_calls) == 1


def test_aggregate_cancel_is_safe_permanent_and_stops_children_without_parse(consent_case):
    case, sid, _, body = selected(consent_case)
    ack = case.post(f'sessions/{sid}/artifacts/import', body, 'select')
    assert ack.status_code == 202
    identifier = ack.json()['id']
    assert case.client.post('/api/v1/session/role', json={'role':'learner'},
        headers={**case.headers, 'Idempotency-Key':'lose-author'}).status_code == 200
    assert case.get('artifact-imports/'+identifier).status_code == 403
    cancel_body = {'expected_revision':1}
    cancel = case.client.post('/api/v1/jobs/'+identifier+'/cancel', json=cancel_body,
        headers={**case.headers, 'Idempotency-Key':'cancel-original'})
    assert cancel.status_code == 200 and cancel.json()['status'] == 'cancelled'
    assert cancel.json()['result_refs'] == []
    before = case.dump()
    assert case.client.post('/api/v1/jobs/'+identifier+'/cancel', json=cancel_body,
        headers={**case.headers, 'Idempotency-Key':'cancel-original'}).content == cancel.content
    assert case.app.state.codex_artifact_imports.run_once() is False
    assert ImportWorker(case.app.state.database).claim() is None
    assert case.dump() == before


@pytest.mark.parametrize('table', ['codex_artifact_import_events', 'codex_artifact_import_members', 'codex_artifact_import_commands'])
def test_aggregate_history_loss_is_not_repaired_by_get_or_original_ack(consent_case, table):
    case, sid, _, body = selected(consent_case)
    ack = case.post(f'sessions/{sid}/artifacts/import', body, 'select')
    assert ack.status_code == 202
    with case.app.state.database.transaction() as conn:
        conn.execute(f'DROP TRIGGER {table}_delete')
        conn.execute(f'DELETE FROM {table}')
    before = case.dump()
    assert case.get('artifact-imports/'+ack.json()['id']).status_code == 409
    assert case.post(f'sessions/{sid}/artifacts/import', body, 'select').status_code == 409
    assert case.dump() == before


def test_aggregate_and_all_child_stages_rollback_when_permanent_command_cannot_commit(consent_case):
    case, sid, _, body = selected(consent_case)
    with case.app.state.database.transaction() as conn:
        conn.execute("CREATE TRIGGER reject_synthetic_aggregate BEFORE INSERT ON codex_artifact_import_events BEGIN SELECT RAISE(ABORT, 'synthetic aggregate rollback'); END")
    before = case.dump()
    response = case.post(f'sessions/{sid}/artifacts/import', body, 'rollback')
    assert response.status_code == 500 and response.json()['error']['code'] == 'INTERNAL_ERROR'
    assert case.dump() == before
    assert len(case.app.state.synthetic_transport_calls) == 1


def test_concurrent_same_original_command_creates_one_real_aggregate_and_child(consent_case):
    from concurrent.futures import ThreadPoolExecutor
    case, sid, _, body = selected(consent_case)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(case.post, f'sessions/{sid}/artifacts/import', body, 'concurrent') for _ in range(2)]
        responses = [future.result(timeout=10) for future in futures]
    assert [response.status_code for response in responses] == [202, 202]
    assert responses[0].content == responses[1].content
    with case.app.state.database.transaction(immediate=False) as conn:
        assert conn.execute("SELECT count(*) FROM jobs WHERE kind='codex_artifact_import'").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM jobs WHERE kind='import'").fetchone()[0] == 1
    assert len(case.app.state.synthetic_transport_calls) == 1


def test_subject_get_rechecks_role_after_leaving_original_read_snapshot(consent_case, monkeypatch):
    import threading
    from concurrent.futures import ThreadPoolExecutor
    case, sid, _, body = selected(consent_case)
    ack = case.post(f'sessions/{sid}/artifacts/import', body, 'select')
    assert ack.status_code == 202
    owner = case.app.state.codex_artifact_imports
    checked = owner._checked
    entered, release = threading.Event(), threading.Event()
    def held(*args):
        value = checked(*args)
        entered.set()
        assert release.wait(10)
        return value
    monkeypatch.setattr(owner, '_checked', held)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(case.get, 'artifact-imports/'+ack.json()['id'])
        try:
            assert entered.wait(10)
            changed = case.client.post('/api/v1/session/role', json={'role':'learner'},
                headers={**case.headers, 'Idempotency-Key':'late-loss'})
            assert changed.status_code == 200
            before = case.dump()
        finally:
            release.set()
        response = future.result(timeout=10)
    assert response.status_code == 403
    assert case.dump() == before
    assert len(case.app.state.synthetic_transport_calls) == 1
