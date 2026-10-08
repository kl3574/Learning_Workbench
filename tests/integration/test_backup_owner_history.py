"""Additional real backup/readback owners; numeric fixture never executes a process."""

from services.api.app.application.restore_numeric_worker import RestoreNumericWorker
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_authoring_numeric_service import LedgerRuntime, decision
from tests.integration.test_backup_session_history import cli_backup, fresh_author
from tests.integration.test_content_impact_decisions_http import case as impact_case
from tests.integration.test_evidence_applicability_decisions import (
    case as evidence_case, change, command as evidence_command, storage as storage,
)
from tests.integration.test_restore_numeric_service import restored as numeric_case, preview
from tests.integration.test_learner_profile import request as profile_request

__all__ = ['impact_case', 'evidence_case', 'numeric_case']


def only_authentication_changed(original, copied):
    before, after = table_hashes(original), table_hashes(copied)
    assert {name for name in before if before[name] != after[name]} <= {
        'local_sessions', 'bootstrap_codes', 'idempotency', 'provider_backup_projections',
        'assessment_receipts', 'learner_profile_command_receipts'}


def test_backup_keeps_content_decisions_note_stale_and_route_pins(impact_case, tmp_path):
    case = impact_case
    assert case.decide(case.write()).status_code == 200
    profile = case.client.put('/api/v1/learner/profile', json=profile_request().model_dump(mode='json'),
        headers={**case.headers, 'Idempotency-Key': 'backup-profile'})
    assert profile.status_code == 200
    paths = [case.path + '?target_id=lesson', '/api/v1/notes?ref_id=block', '/api/v1/routes', '/api/v1/learner/profile']
    expected = {}
    for path in paths:
        response = case.client.get(path)
        assert response.status_code == 200
        expected[path] = response.content
    copied, _ = cli_backup(case.database, tmp_path)
    only_authentication_changed(case.database, copied)
    with copied.connect() as conn:
        assert conn.execute('SELECT count(*) FROM learner_profile_history').fetchone()[0] == 1
        assert conn.execute('SELECT count(*) FROM learner_profile_command_receipts').fetchone()[0] == 0
    _, client = fresh_author(copied)
    try:
        for path, body in expected.items():
            response = client.get(path)
            assert response.status_code == 200 and response.content == body
    finally:
        client.close()


def test_backup_keeps_actual_grade_evidence_decision_and_private_solution_history(evidence_case, tmp_path):
    database, author, _, service, evidence, _ = evidence_case
    event = change(evidence_case)
    pending = service.read(author, evidence.id, event)
    receipt = service.decide(author, evidence.id, evidence_command(pending, event), 'backup-evidence')
    expected = service.read(author, evidence.id, event)
    assert expected.decisions == [receipt]
    copied, _ = cli_backup(database, tmp_path)
    only_authentication_changed(database, copied)
    with copied.connect() as conn:
        assert conn.execute('SELECT count(*) FROM assessment_receipts').fetchone()[0] == 0
        assert conn.execute('SELECT count(*) FROM grades').fetchone()[0] > 0
    _, client = fresh_author(copied)
    try:
        response = client.get(f'/api/v1/learning/evidence/{evidence.id}/applicability', params={'event_id': event})
        assert response.status_code == 200 and response.json() == expected.model_dump(mode='json')
    finally:
        client.close()


def test_backup_retains_numeric_approval_without_reusing_its_execution_authority(numeric_case, tmp_path):
    case = numeric_case
    view = preview(case)
    approved = case.service.decide(case.identity, view.id, decision(view), 'backup-numeric-approve')
    expected = case.service.read(case.identity, view.id)
    assert approved.job.status == 'queued' and expected.result is None
    copied, _ = cli_backup(case.database, tmp_path)
    only_authentication_changed(case.database, copied)
    author, client = fresh_author(copied)
    try:
        path = f'/api/v1/content/restore-numeric-checks/{view.id}'
        response = client.get(path)
        assert response.status_code == 200 and response.json() == expected.model_dump(mode='json')
        # No run_checked method exists on LedgerRuntime: accidentally executing
        # would fail the test. Revoked original authority stops before check().
        runtime = LedgerRuntime()
        service = client.app.state.restore_numeric_service
        worker = RestoreNumericWorker(copied, service, runtime)
        assert worker.run_once()
        current = service.read(author, view.id)
        assert runtime.checks == 0 and current.result.outcome == 'cancelled'
        assert current.result.started_at is None and current.result.output_sha256 is None
        assert current.job.status == 'cancelled'
        assert case.service.read(case.identity, view.id) == expected  # source remains queued
    finally:
        client.close()
