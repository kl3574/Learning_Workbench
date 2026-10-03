"""Real backup CLI keeps synthetic Codex history, never old execution authority."""

from dataclasses import replace

from fastapi.testclient import TestClient
import pytest

from services.api.app.application.sessions import SessionService
from services.api.app.dto import RoleRequest
from services.api.app.infrastructure.security import COOKIE_NAME, consume_bootstrap, issue_bootstrap_code
from services.api.app.main import create_app
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_backup_session_history import cli_backup
from tests.integration.test_codex_bootstrap_http import ControlledRuntime, approve, make_case


@pytest.mark.parametrize('state', ['approved', 'declined', 'ready', 'unknown'])
def test_backup_retains_codex_control_facts_and_rejects_old_authority(tmp_path, monkeypatch, state):
    runtime = ControlledRuntime()
    case = make_case(tmp_path / 'source', codex_bootstrap_runtime=runtime)
    original, decision, body = approve(case, 'backup-control')
    if state == 'declined':
        # Keep a separately declined preparation beside the approved original.
        pending = case.post('session-preparations', {
            'sandbox_root_id': 'workspace_default', 'allowed_actions': []}, 'declined-prepare').json()
        declined = case.post('session-preparations/' + pending['id'] + '/decision', {
            'expected_revision': 1, 'operation_sha256': pending['operation_sha256'],
            'decision': 'decline'}, 'declined-decision')
        assert declined.status_code == 200
        identifier = pending['id']
    else:
        identifier = original['id']
    if state in {'ready', 'unknown'}:
        runtime.outcome = state
        created = case.post('sessions', body, 'backup-consume')
        assert created.status_code == (201 if state == 'ready' else 503)
        assert len(runtime.calls) == 1
    preparation_path = '/api/v1/codex/session-preparations/' + identifier
    preparation = case.client.get(preparation_path)
    assert preparation.status_code == 200
    expected = {preparation_path: preparation.content}
    session_id = preparation.json()['session_id']
    if session_id is not None:
        session_path = '/api/v1/codex/sessions/' + session_id
        expected[session_path] = case.client.get(session_path).content

    before = table_hashes(case.app.state.database)
    copied, manifest = cli_backup(case.app.state.database, tmp_path)
    copied_hashes = table_hashes(copied)
    codex_tables = {name for name in before if name.startswith('codex_')}
    assert len(codex_tables) >= 8
    assert all(before[name] == copied_hashes[name] for name in codex_tables)
    assert manifest['consent_dispatch_disabled'] is True

    copied_runtime = ControlledRuntime()
    app = create_app(copied.settings, codex_bootstrap_runtime=copied_runtime)
    client = TestClient(app, base_url=copied.settings.origin)
    client.cookies.update(case.client.cookies)
    assert client.get('/api/v1/session').status_code == 401
    token, identity = consume_bootstrap(copied, issue_bootstrap_code(copied))
    SessionService(copied).switch_role(identity, RoleRequest(role='author'), 'backup-control-reader')
    identity = replace(identity, role='author')
    assert identity.id != case.actor_id
    client.cookies.clear()
    client.cookies.set(COOKIE_NAME, token)
    headers = {'Origin': copied.settings.origin, 'X-CSRF-Token': identity.csrf_token}

    def forbidden_process(*args, **kwargs):
        pytest.fail('backup control readback or rejected authority launched a process')

    import subprocess
    monkeypatch.setattr(subprocess, 'Popen', forbidden_process)
    try:
        read_before = table_hashes(copied)
        for path, raw in expected.items():
            response = client.get(path)
            assert response.status_code == 200 and response.content == raw
            assert response.headers['cache-control'] == 'no-store'
        assert table_hashes(copied) == read_before
        # The same public consent and original key are not inherited by a new actor.
        rejected = client.post('/api/v1/codex/sessions', json=body,
            headers={**headers, 'Idempotency-Key': 'backup-consume'})
        assert rejected.status_code == 409
        denied_decision = client.post('/api/v1/codex/session-preparations/' + original['id'] + '/decision', json={
            'expected_revision': 1, 'operation_sha256': original['operation_sha256'],
            'decision': decision['decision']}, headers={**headers, 'Idempotency-Key': 'decision-backup-control'})
        assert denied_decision.status_code == 409
        assert copied_runtime.calls == []
        assert table_hashes(copied) == read_before
        assert table_hashes(case.app.state.database) == before
    finally:
        client.close()
        case.client.close()
