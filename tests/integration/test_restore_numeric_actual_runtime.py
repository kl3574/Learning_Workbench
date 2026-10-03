"""One real sealed Restore execution probe. Host denial is BLOCKED, never fake PASS."""
import json
from services.api.app.infrastructure.authoring_numeric_runtime import NumericRuntime
from services.api.app.application.restore_numeric_worker import RestoreNumericWorker
from services.api.app.infrastructure.restore_numeric_repository import RestoreNumericRepository
from tests.integration.test_restore_numeric_service import restored as restored
from tests.integration.test_authoring_http import command
import pytest


def test_actual_restore_numeric_sealed_execution(restored, tmp_path):
    case = restored
    runtime = NumericRuntime()
    case.service.runtime = runtime
    response = case.client.post(f'/api/v1/content/restore-drafts/{case.identifier}/numeric-checks',
        json=case.request.model_dump(mode='json'), headers=command(case.headers, 'physical-preview'))
    assert response.status_code == 201, response.text
    view = response.json()
    approved = case.client.post(f'/api/v1/content/restore-numeric-checks/{view["id"]}/decision',
        json={'expected_revision': 1, 'operation_sha256': view['operation_sha256'], 'decision': 'approve_once'},
        headers=command(case.headers, 'physical-approve'))
    assert approved.status_code == 202, approved.text
    worker = RestoreNumericWorker(case.database, case.service, runtime)
    assert worker.run_once()
    result = case.client.get('/api/v1/content/restore-numeric-checks/' + view['id'])
    assert result.status_code == 200, result.text
    with case.database.transaction(immediate=False) as conn:
        repo = RestoreNumericRepository(conn, case.identity.workspace_id)
        start, end = repo.execution_state(approved.json()['job']['id'])
        value = repo.job_input(approved.json()['job']['id'])
        record = repo.load(view['id'])
        probe = dict(result=result.json(), input=value.model_dump(mode='json'), start=start.model_dump(mode='json'),
                     end=end.model_dump(mode='json'), runtime_manifest=json.loads(record.runtime_manifest_json))
    (tmp_path / 'physical-probe.json').write_text(json.dumps(probe, ensure_ascii=False, indent=2) + '\n')
    assert value.version == 'restore-numeric-job-v1'
    assert end.result.outcome in {'passed', 'environment_unavailable'}
    assert end.result.started_at == start.actual_started_at
    assert not worker.run_once()
    if end.result.outcome == 'environment_unavailable':
        assert end.result.verdict == 'BLOCKED' and not end.result.assertions
        assert result.json()['job']['status'] == 'failed'
        pytest.skip('BLOCKED_ENVIRONMENT: actual sealed Restore evaluator did not return a numeric PASS; no fallback')
    assert end.result.verdict == 'PASS' and end.result.exit_code == 0
    assert end.result.assertions[0].actual == 4.0
    assert end.output_complete and end.stdout_base64 and end.result.output_sha256
