"""Synthetic backup startup: retain history, never inherit the old actor's grant.

This enters the real application lifespan and worker loop, not the M7 restore
preview/commit workflow. No actual model, Codex CLI or tool execution is allowed.
"""
from dataclasses import replace
import hashlib
import json
import os
import subprocess
from threading import Event
import zipfile

from fastapi.testclient import TestClient
import pytest

from scripts.backup import create_backup
from services.api.app.application.codex_operation_profile import CodexOperationRegistry
from services.api.app.application.codex_turn_worker import SyntheticCodexExecutor
from services.api.app.infrastructure.blobs import BlobStore
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.provider_transport import ProviderTransport
from services.api.app.infrastructure.security import issue_bootstrap_code
from services.api.app.main import create_app
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_backup_codex_turn_history import TURN_TABLES, PROVIDER_TABLES
from tests.integration.test_backup_session_history import file_hashes
from tests.integration.test_codex_bootstrap_http import Case, ControlledRuntime
from tests.integration.test_codex_turn_dispatch_http import base_consent_case, consent_case, queued

__all__ = ['base_consent_case', 'consent_case']


def checked_copy(source, target):
    """Use the existing backup writer; expand only its checked synthetic payloads."""
    database = source.app.state.database
    before = table_hashes(database)
    files = file_hashes(database.settings.data_dir)
    with database.connect() as conn:
        assert all(conn.execute(f'SELECT count(*) FROM {name}').fetchone()[0]
                   for name in TURN_TABLES + PROVIDER_TABLES)
    archive = create_backup(database.settings)
    target.mkdir(mode=0o700)
    with zipfile.ZipFile(archive) as reader:
        manifest = json.loads(reader.read('manifest.json'))
        assert manifest['restore_acceptance'] == 'NOT_RUN'
        assert manifest['consent_dispatch_disabled'] is True
        assert manifest['session_backup']['authentication_disabled'] is True
        assert set(reader.namelist()) == {'manifest.json', *(item['path'] for item in manifest['files'])}
        for item in manifest['files']:
            data = reader.read(item['path'])
            assert len(data) == item['size'] and hashlib.sha256(data).hexdigest() == item['sha256']
            if item['path'] == 'workspace.sqlite3':
                (target / item['path']).write_bytes(data)
                os.chmod(target / item['path'], 0o600)
            else:
                assert item['path'] == 'blobs/' + item['sha256']
                BlobStore(target).write(data, expected_sha256=item['sha256'])
    copied = Database(replace(database.settings, data_dir=target))
    preserved = table_hashes(copied)
    assert all(preserved[name] == before[name] for name in before
               if name.startswith(('codex_', 'provider_codex_')))
    assert table_hashes(database) == before and file_hashes(database.settings.data_dir) == files
    return copied, before, files


@pytest.mark.parametrize('registration', ['production_empty', 'trusted_memory_sentinel'])
def test_backup_lifespan_rejects_old_queued_turn_without_inheriting_actor_or_permission(
        consent_case, tmp_path_factory, monkeypatch, registration):
    source, _, sid, proofs, _, _ = consent_case
    preparation, consent, start_body, start_ack = queued(consent_case)
    assert source.app.state.synthetic_transport_calls == []
    temporary = tmp_path_factory.mktemp('codex-lifespan-copy')
    copied, original_tables, original_files = checked_copy(source, temporary / 'restored')
    copied_before = table_hashes(copied)
    original_control = source.get('turns/' + preparation['turn_id']).json()
    original_job = source.client.get('/api/v1/jobs/' + preparation['job']['id']).json()
    calls = {'codex_model': 0, 'ordinary_provider': 0, 'tool': 0, 'process': 0, 'bootstrap': 0}

    def forbidden(name):
        def refuse(*args, **kwargs):
            calls[name] += 1
            raise AssertionError('Synthetic restore crossed a forbidden execution seam: ' + name)
        return refuse

    # These sentinels prevent execution rather than diagnosing the host or network.
    monkeypatch.setattr(ProviderTransport, 'stream', forbidden('ordinary_provider'))
    monkeypatch.setattr(CodexOperationRegistry, 'execute', forbidden('tool'))
    monkeypatch.setattr(subprocess, 'Popen', forbidden('process'))
    runtime = ControlledRuntime()
    monkeypatch.setattr(runtime, 'execute', forbidden('bootstrap'))
    options = {} if registration == 'production_empty' else {
        'codex_proofs': proofs,
        'codex_executor': SyntheticCodexExecutor(forbidden('codex_model')),
    }
    app = create_app(copied.settings, codex_bootstrap_runtime=runtime, **options)
    worker = app.state.codex_turn_worker
    original_run_once = worker.run_once
    retried = Event()
    observations = []
    entered_lifespan = assertions_completed = False
    alive_before_shutdown = False

    def observe_run_once():
        # The real lifespan thread calls the unchanged public worker method.
        # An Event observes its completion; no fake terminal or manual run_once.
        try:
            worked = original_run_once()
        except Exception as error:
            observations.append({'error': type(error).__name__, 'code': getattr(error, 'code', None),
                                 'prior_loop_error': worker.last_error_code})
            if len(observations) >= 2:
                retried.set()
            raise  # The original loop, not this observer, handles the refusal.
        observations.append({'worked': worked})
        return worked

    monkeypatch.setattr(worker, 'run_once', observe_run_once)
    try:
        with TestClient(app, base_url=copied.settings.origin) as client:
            # A returned context has run actual initialize/recover/start, not merely factory.
            entered_lifespan = True
            assert app.state.codex_turn_recovered == 0
            assert retried.wait(5), 'Expected two real backup-disabled worker refusals'
            assert all(item.get('code') == 'PROVIDER_BACKUP_DISABLED' for item in observations), observations
            assert observations[1]['prior_loop_error'] == 'PROVIDER_BACKUP_DISABLED'
            assert worker.last_error_code == 'PROVIDER_BACKUP_DISABLED'
            alive_before_shutdown = worker._thread is not None and worker._thread.is_alive()
            assert alive_before_shutdown
            # This is a refused queued item, not a fabricated failed/completed terminal.
            for name in (*TURN_TABLES, *PROVIDER_TABLES, 'jobs', 'runs', 'job_events'):
                assert table_hashes(copied)[name] == copied_before[name]
            client.cookies.update(source.client.cookies)
            assert client.get('/api/v1/session').status_code == 401
            client.cookies.clear()
            bootstrap = client.post('/api/v1/session/bootstrap',
                json={'one_time_code': issue_bootstrap_code(copied)}, headers={'Origin': copied.settings.origin})
            assert bootstrap.status_code == 200
            session = client.get('/api/v1/session').json()
            assert session['role'] == 'learner' and session['actor_session_id'] != source.actor_id
            headers = {'Origin': copied.settings.origin, 'X-CSRF-Token': bootstrap.json()['csrf_token']}
            case = Case(app, client, headers, session['actor_session_id'])
            before_gets = table_hashes(copied)
            control_response = case.get('turns/' + preparation['turn_id'])
            assert control_response.status_code == 200
            control = control_response.json()
            assert control == original_control
            assert control['job']['status'] == 'queued' and control['outcome'] is None
            assert control['error_code'] is None
            assert control['execution'] == 'not_started' and control['started_at'] is None
            assert control['job_revision'] == 2
            assert client.get('/api/v1/jobs/' + preparation['job']['id']).json() == original_job
            current_session = case.get('sessions/' + sid).json()
            assert current_session['active_turn_id'] == preparation['turn_id'] and current_session['revision'] == 4
            assert case.get('turns/' + preparation['turn_id'] + '/result').status_code == 403
            assert table_hashes(copied) == before_gets
            role = client.post('/api/v1/session/role', json={'role': 'author'},
                               headers={**headers, 'Idempotency-Key': 'restored-current-author'})
            assert role.status_code == 200
            before_reads = table_hashes(copied)
            current = case.get('consents/' + consent['id']).json()
            assert current['actor_session_id'] == source.actor_id != case.actor_id
            assert current['summary'] == consent['summary']
            dispatch = current['dispatch']
            assert dispatch['started_at'] is None and dispatch['consumed_provider_calls'] == 0
            assert dispatch['outcome'] is None and dispatch['error_code'] is None
            assert dispatch['finished_at'] is None and dispatch['input_tokens'] is None
            assert dispatch['output_tokens'] is None
            result = case.get('turns/' + preparation['turn_id'] + '/result')
            assert result.status_code == 200
            assert result.json()['output_state'] == 'none' and result.json()['answer_markdown'] == ''
            assert [result.json()[name] for name in ('mathematical', 'sources', 'independent_pedagogy')] == ['NOT_RUN'] * 3
            # Read the existing checked owner's immutable original ACK separately from current.
            with copied.transaction(immediate=False) as conn:
                conn.execute('PRAGMA query_only=ON')
                workspace = copied.workspace_id()
                _, _, history = app.state.codex_turn_service._owned_state(conn, workspace)
                turn = history[sid].turns[preparation['turn_id']]
                assert turn.start.command.ack.model_dump(mode='json') == start_ack.json()
                states, _ = app.state.codex_turn_service.outbound_owner.owned_states(conn, workspace)
                assert states[preparation['turn_id']].granted.command.ack.model_dump(mode='json') == consent
            # Neither the original key nor a new key transfers another actor's authority.
            for key in ('start', 'new-restored-start'):
                denied = case.post(f'sessions/{sid}/turns', start_body, key)
                assert denied.status_code == 403 and denied.json()['error']['code'] == 'POLICY_DENIED'
            for key in ('grant', 'new-restored-grant'):
                denied = case.post('consents', {'proposal_id': consent['proposal_id'],
                    'proposal_sha256': consent['proposal_sha256']}, key)
                assert denied.status_code == 403 and denied.json()['error']['code'] == 'POLICY_DENIED'
            assert table_hashes(copied) == before_reads
            assert case.get('turns/' + preparation['turn_id']).json() == control
            assert calls == {'codex_model': 0, 'ordinary_provider': 0, 'tool': 0, 'process': 0, 'bootstrap': 0}
            assert runtime.calls == []
        assertions_completed = True
    finally:
        # Safe counts are actually read after normal context shutdown, even on failure.
        (temporary / "lifespan-observation.json").write_text(json.dumps({
            "registration": registration, "entered_lifespan": entered_lifespan,
            "worker_observations": observations, "last_error_code": worker.last_error_code,
            "alive_before_shutdown": alive_before_shutdown,
            "alive_after_context": worker._thread is not None and worker._thread.is_alive(),
            "forbidden_calls": calls, "fresh_bootstrap_calls": len(runtime.calls),
            "source_synthetic_model_calls": len(source.app.state.synthetic_transport_calls),
            "contract_assertions_completed": assertions_completed,
            "boundary": "Refusal and history retention only; no general convergence or M7 acceptance",
        }, indent=2) + "\n")
    # Actual lifespan shutdown completes before these final invariants are read.
    assert calls == {'codex_model': 0, 'ordinary_provider': 0, 'tool': 0, 'process': 0, 'bootstrap': 0}
    assert runtime.calls == []
    assert worker._thread is not None and not worker._thread.is_alive()
    assert source.app.state.synthetic_transport_calls == []
    assert table_hashes(source.app.state.database) == original_tables
    assert file_hashes(source.app.state.settings.data_dir) == original_files
