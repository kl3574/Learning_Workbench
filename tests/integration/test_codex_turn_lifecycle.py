"""Synthetic persistence/access races, restart and forward migration oracles."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Event
import shutil

from fastapi.testclient import TestClient
import pytest

from services.api.app.application.codex_turn_models import EventEnvelope
from services.api.app.infrastructure.database import Database
from services.api.app.serialization import canonical_json, content_sha256
from services.api.app.main import create_app
from tests.integration.test_codex_turn_preparation_http import turn_case as fixture, prepared, turn_body, cancel
from tests.integration.test_codex_bootstrap_http import ControlledRuntime, approve, make_case
from tests.integration.test_authoring_numeric_provider_history import table_hashes

turn_case = fixture


@pytest.mark.parametrize('change,expected', [('learner', 200), ('logout', 401), ('workspace', 401)])
def test_safe_get_fresh_delivery_retains_learner_but_rejects_invalid_identity(turn_case, monkeypatch, change, expected):
    case, _, _, _, _ = turn_case
    value = prepared(turn_case).json()
    service = case.app.state.codex_turn_service
    original = service._state
    entered, release = Event(), Event()
    def held(*args, **kwargs):
        result = original(*args, **kwargs)
        entered.set()
        assert release.wait(10)
        return result
    monkeypatch.setattr(service, '_state', held)
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(case.get, 'turns/' + value['turn_id'])
        try:
            assert entered.wait(10)
            if change == 'learner':
                response = case.client.post('/api/v1/session/role', json={'role': 'learner'},
                    headers={**case.headers, 'Idempotency-Key': 'control-role'})
                assert response.status_code == 200
            else:
                # Session-owned storage corruption/revocation fixture only.
                with case.app.state.database.transaction() as conn:
                    if change == 'logout':
                        conn.execute("UPDATE local_sessions SET revoked_at='2026-01-01T00:00:00Z' WHERE id=?", (case.actor_id,))
                    else:
                        conn.execute("INSERT INTO workspace(id,title,created_at) VALUES('other_workspace','Synthetic','2026-01-01T00:00:00Z')")
                        conn.execute("UPDATE local_sessions SET workspace_id='other_workspace' WHERE id=?", (case.actor_id,))
            before = case.dump()
        finally:
            release.set()
        response = future.result(timeout=10)
    assert response.status_code == expected
    assert turn_body()['message'] not in response.text and 'context_refs' not in response.text
    if response.status_code == 200:
        assert 'message' not in response.json()
    assert case.dump() == before


def test_restart_preserves_original_ack_current_revision_and_never_runs_cli(turn_case, monkeypatch):
    import subprocess
    case, runtime, sid, bootstrap_body, bootstrap_ack = turn_case
    response = prepared(turn_case)
    value = response.json()
    stopped = cancel(case, value['job']['id'])
    assert stopped.status_code == 200
    def forbidden(*args, **kwargs):
        pytest.fail('restart/control launched an external process')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    new = create_app(case.app.state.settings, codex_bootstrap_runtime=runtime)
    client = TestClient(new, base_url=case.app.state.settings.origin)
    client.cookies.update(case.client.cookies)
    try:
        before = case.dump()
        current = client.get('/api/v1/codex/sessions/' + sid)
        assert current.status_code == 200 and current.json()['revision'] == 5 and current.json()['active_turn_id'] is None
        replay = client.post(f'/api/v1/codex/sessions/{sid}/turn-preparations', json=turn_body(),
            headers={**case.headers, 'Idempotency-Key': 'turn'})
        assert replay.content == response.content
        original = client.post('/api/v1/codex/sessions', json=bootstrap_body,
            headers={**case.headers, 'Idempotency-Key': 'bootstrap-session'})
        assert original.content == bootstrap_ack
        replay = client.post('/api/v1/jobs/' + value['job']['id'] + '/cancel', json={'expected_revision': 1},
            headers={**case.headers, 'Idempotency-Key': 'cancel'})
        assert replay.content == stopped.content
        assert client.get('/api/v1/runs/' + value['job']['id']).status_code == 404
        assert len(runtime.calls) == 1 and case.dump() == before
    finally:
        client.close()


def test_provider_tail_loss_rejects_frozen_original_even_when_its_revision_survives(turn_case):
    case, _, sid, _, _ = turn_case
    value = prepared(turn_case).json()
    response = case.client.put('/api/v1/providers/codex_local/config', json={
        'expected_revision': 1, 'adapter': 'compatible_chat', 'base_url': 'https://example.invalid',
        'model': 'synthetic-model-r2', 'embedding_model': None, 'endpoint_policy': 'public_https', 'pricing': None,
    }, headers={**case.headers, 'Idempotency-Key': 'config-two'})
    assert response.status_code == 200
    # Use explicit synthetic corruption with FK enforcement suspended only for
    # this deliberately invalid fixture; the application connections keep FK ON.
    with case.app.state.database.connect() as conn:
        conn.execute('PRAGMA foreign_keys=OFF')
        conn.execute('DROP TRIGGER provider_config_history_no_delete')
        conn.execute("DELETE FROM provider_config_history WHERE provider_id='codex_local' AND revision=2")
    before = case.dump()
    response = case.get('turns/' + value['turn_id'])
    assert response.status_code == 409
    response = case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'turn')
    assert response.status_code == 409
    assert case.dump() == before


@pytest.mark.parametrize('field', ['requested_session_revision', 'terminal_session_revision'])
def test_cancel_each_revision_fact_is_checked_even_with_rehashed_owner_chain(turn_case, field):
    case, _, sid, _, _ = turn_case
    value = prepared(turn_case).json()
    assert cancel(case, value['job']['id']).status_code == 200
    with case.app.state.database.transaction() as conn:
        row = conn.execute('SELECT record_json FROM codex_turn_events WHERE session_id=? AND seq=2', (sid,)).fetchone()
        event = EventEnvelope.model_validate_json(row[0])
        setattr(event.event, field, getattr(event.event, field) + 1)
        digest = content_sha256(event)
        conn.execute('DROP TRIGGER codex_turn_events_update')
        conn.execute('DROP TRIGGER codex_turn_event_members_update')
        conn.execute('UPDATE codex_turn_events SET record_json=?,record_sha256=? WHERE session_id=? AND seq=2',
            (canonical_json(event), digest, sid))
        conn.execute('UPDATE codex_turn_event_members SET record_sha256=? WHERE session_id=? AND seq=2', (digest, sid))
        conn.execute('UPDATE codex_turn_heads SET head_sha256=? WHERE session_id=?', (digest, sid))
    before = case.dump()
    response = case.get('sessions/' + sid)
    assert response.status_code == 409
    response = cancel(case, value['job']['id'])
    assert response.status_code == 409
    assert case.dump() == before


def test_forward_migration_preserves_original_bootstrap_and_all_existing_rows(tmp_path):
    # Populate genuine old owner facts using the exact pre-0028 schema.
    runtime = ControlledRuntime()
    case = make_case(tmp_path / 'seed', codex_bootstrap_runtime=runtime)
    prior = tmp_path / 'prior_migrations'
    prior.mkdir()
    for path in case.app.state.settings.migrations_dir.glob('*.sql'):
        if path.name < '0028':
            shutil.copyfile(path, prior / path.name)
    settings = replace(case.app.state.settings, data_dir=tmp_path / 'old', migrations_dir=prior)
    old = Database(settings)
    old.initialize()
    # Existing bootstrap APIs do not require new turn tables to prepare/create.
    app = create_app(settings, codex_bootstrap_runtime=runtime)
    from tests.integration.test_codex_bootstrap_http import Case
    from services.api.app.security import issue_bootstrap_code
    client = TestClient(app, base_url=settings.origin)
    grant = client.post('/api/v1/session/bootstrap', json={'one_time_code': issue_bootstrap_code(old)}, headers={'Origin': settings.origin})
    headers = {'Origin': settings.origin, 'X-CSRF-Token': grant.json()['csrf_token']}
    role = client.post('/api/v1/session/role', json={'role': 'author'}, headers={**headers, 'Idempotency-Key': 'role'})
    assert role.status_code == 200
    actor = client.get('/api/v1/session').json()['actor_session_id']
    legacy = Case(app, client, headers, actor)
    _, _, body = approve(legacy)
    response = legacy.post('sessions', body, 'legacy-session')
    assert response.status_code == 201
    before = table_hashes(old)
    upgraded = Database(replace(settings, migrations_dir=Path(case.app.state.settings.migrations_dir)))
    upgraded.initialize()
    after = table_hashes(upgraded)
    assert {key: after[key] for key in before if key != 'schema_migrations'} == {key: item for key, item in before.items() if key != 'schema_migrations'}
    with upgraded.connect() as conn:
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
    current_app = create_app(upgraded.settings, codex_bootstrap_runtime=runtime)
    current = TestClient(current_app, base_url=settings.origin)
    current.cookies.update(client.cookies)
    try:
        replay = current.post('/api/v1/codex/sessions', json=body, headers={**headers, 'Idempotency-Key': 'legacy-session'})
        assert replay.content == response.content
        read = current.get('/api/v1/codex/sessions/' + response.json()['id'])
        assert read.status_code == 200 and read.json() == {**response.json(), 'active_turn_id': None}
        assert len(runtime.calls) == 1
    finally:
        current.close()
        client.close()
        case.client.close()


def test_current_cross_workspace_actor_cannot_read_or_cancel_known_turn_ids(turn_case):
    from services.api.app.security import issue_bootstrap_code
    case, _, sid, _, _ = turn_case
    value = prepared(turn_case).json()
    fresh = case.client.post('/api/v1/session/bootstrap', json={'one_time_code': issue_bootstrap_code(case.app.state.database)},
        headers={'Origin': case.headers['Origin']})
    case.headers['X-CSRF-Token'] = fresh.json()['csrf_token']
    actor = case.client.get('/api/v1/session').json()['actor_session_id']
    with case.app.state.database.transaction() as conn:
        conn.execute("INSERT INTO workspace(id,title,created_at) VALUES('other_workspace','Synthetic','2026-01-01T00:00:00Z')")
        conn.execute("UPDATE local_sessions SET workspace_id='other_workspace',role='author' WHERE id=?", (actor,))
    before = case.dump()
    for path in ['sessions/' + sid, f'sessions/{sid}/turns', 'turns/' + value['turn_id'],
                 'turn-preparations/' + value['id']]:
        response = case.get(path)
        assert response.status_code == 404
    response = cancel(case, value['job']['id'])
    assert response.status_code == 404
    response = case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'foreign')
    assert response.status_code == 404
    assert case.dump() == before
