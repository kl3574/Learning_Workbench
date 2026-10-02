"""Single-sided physical corruption, rollback and concurrent author intent."""
from concurrent.futures import ThreadPoolExecutor
import sqlite3
import pytest
from services.api.app.application.errors import ApiError
from services.api.app.restore_numeric_dto import RestoreNumericCheckPreviewWrite
from services.api.app.infrastructure.restore_numeric_repository import RestoreNumericRepository
from tests.integration.test_restore_numeric_service import restored as restored, preview
from tests.integration.test_restore_numeric_execution import executed
from tests.integration.test_authoring_numeric_service import decision
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_authoring_http import command


def corrupt(database, action):
    """Out-of-band damage fixture; product DB constraints remain enabled normally."""
    conn = sqlite3.connect(database.path)
    try:
        for name, in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND (name LIKE 'restore_numeric_%' OR name LIKE 'authoring_records_%')").fetchall():
            conn.execute(f'DROP TRIGGER {name}')
        action(conn)
        conn.commit()
    finally:
        conn.close()


@pytest.mark.parametrize('fault', ['events_tail', 'events_all', 'head_missing', 'head_smaller', 'check_tail', 'check_all',
    'command_tail', 'command_all', 'material_body', 'material_hash', 'actor_workspace', 'job_member', 'job_input',
    'runtime_manifest', 'terminal_bytes', 'job_event_tail', 'job_terminal'])
def test_corrupt_history_rejected_by_subject_snapshot_and_original_replay_without_writes(restored, fault):
    case = restored
    view, ack, _, _ = executed(case)
    preview(case, 'second')
    def damage(conn):
        if fault in {'events_tail', 'events_all'}:
            conn.execute('DELETE FROM restore_numeric_events' + (' WHERE sequence=(SELECT max(sequence) FROM restore_numeric_events)' if fault.endswith('tail') else ''))
        elif fault == 'head_missing':
            conn.execute('DELETE FROM restore_numeric_heads')
        elif fault == 'head_smaller':
            conn.execute('UPDATE restore_numeric_heads SET sequence=sequence-1')
        elif fault in {'check_tail', 'check_all'}:
            conn.execute('DELETE FROM restore_numeric_checks' + (' WHERE ordinal=2' if fault.endswith('tail') else ''))
        elif fault in {'command_tail', 'command_all'}:
            conn.execute('DELETE FROM restore_numeric_commands' + (' WHERE sequence=(SELECT max(sequence) FROM restore_numeric_commands)' if fault.endswith('tail') else ''))
        elif fault == 'material_body':
            conn.execute("UPDATE restore_numeric_materials SET material_json=json_set(material_json,'$.body_sha256',?)", ('a' * 64,))
        elif fault == 'material_hash':
            conn.execute('UPDATE restore_numeric_materials SET material_sha256=?', ('a' * 64,))
        elif fault == 'actor_workspace':
            conn.execute('UPDATE local_sessions SET workspace_id=? WHERE id=?', ('workspace_foreign', case.identity.id))
        elif fault == 'job_member':
            conn.execute('DELETE FROM restore_numeric_jobs')
        elif fault == 'job_input':
            conn.execute("UPDATE jobs SET input_json=json_set(input_json,'$.version','authoring-numeric-job-v1') WHERE id=?", (ack.job.id,))
        elif fault in {'runtime_manifest', 'terminal_bytes'}:
            # A lone stored event column is damaged, without rewriting its head or original command.
            kind = 'preview' if fault == 'runtime_manifest' else 'terminal'
            conn.execute("UPDATE restore_numeric_events SET event_json=json_set(event_json,'$.payload_json','{}') WHERE json_extract(event_json,'$.kind')=?", (kind,))
        elif fault == 'job_event_tail':
            conn.execute('DELETE FROM job_events WHERE job_id=? AND seq=(SELECT max(seq) FROM job_events WHERE job_id=?)', (ack.job.id, ack.job.id))
        else:
            conn.execute('UPDATE jobs SET result_json=? WHERE id=?', ('{}', ack.job.id))
    corrupt(case.database, damage)
    before = table_hashes(case.database)
    if fault == 'actor_workspace':
        # Current identity fails authorization, with no payload or repair.
        response = case.client.get('/api/v1/content/restore-drafts/' + case.identifier)
        assert response.status_code == 404
    else:
        with pytest.raises(ApiError) as error:
            case.service.read(case.identity, view.id)
        assert error.value.status == 409
        response = case.client.get('/api/v1/content/restore-drafts/' + case.identifier)
        assert response.status_code == 409, response.text
        with pytest.raises(ApiError) as error:
            case.service.decide(case.identity, view.id, decision(view), 'approve')
        assert error.value.status == 409
    assert table_hashes(case.database) == before


def test_two_first_materials_and_one_decision_are_atomic(restored):
    case = restored
    changed = case.request.model_dump(mode='json')
    changed['material']['reason'] += ' second author intent'
    requests = [case.request, RestoreNumericCheckPreviewWrite.model_validate(changed)]
    def create(index):
        try:
            return case.service.preview(case.identity, case.identifier, requests[index], f'parallel_{index}')
        except ApiError as error:
            return error
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(create, range(2)))
    assert sum(isinstance(item, ApiError) for item in outcomes) == 1
    assert next(item for item in outcomes if isinstance(item, ApiError)).code == 'RESTORE_NUMERIC_MATERIAL_CONFLICT'
    view = next(item for item in outcomes if not isinstance(item, ApiError))
    def approve(index):
        try:
            return case.service.decide(case.identity, view.id, decision(view), f'approval_{index}')
        except ApiError as error:
            return error
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(approve, range(2)))
    assert sum(isinstance(item, ApiError) for item in outcomes) == 1
    assert next(item for item in outcomes if isinstance(item, ApiError)).code == 'NUMERIC_DECISION_EXISTS'
    with case.database.connect() as conn:
        assert conn.execute('SELECT count(*) FROM restore_numeric_jobs').fetchone()[0] == 1


def test_preview_and_approval_failure_roll_back_every_new_fact(restored, monkeypatch):
    case = restored
    original = RestoreNumericRepository.command
    def fail(*args, **kwargs):
        raise ApiError(409, 'INJECTED_COMMAND_FAILURE', 'Synthetic transaction failure')
    before = table_hashes(case.database)
    monkeypatch.setattr(RestoreNumericRepository, 'command', fail)
    with pytest.raises(ApiError):
        preview(case)
    assert table_hashes(case.database) == before
    monkeypatch.setattr(RestoreNumericRepository, 'command', original)
    view = preview(case)
    before = table_hashes(case.database)
    monkeypatch.setattr(RestoreNumericRepository, 'command', fail)
    with pytest.raises(ApiError):
        case.service.decide(case.identity, view.id, decision(view), 'approve')
    assert table_hashes(case.database) == before


def test_role_cycle_safe_cancel_never_returns_subject_payload(restored):
    case = restored
    view = preview(case)
    ack = case.service.decide(case.identity, view.id, decision(view), 'approve')
    response = case.client.post('/api/v1/session/role', json={'role': 'learner'}, headers=command(case.headers, 'learner'))
    assert response.status_code == 200
    before = table_hashes(case.database)
    assert case.client.get('/api/v1/content/restore-numeric-checks/' + view.id).status_code == 403
    safe = case.client.get('/api/v1/authoring/jobs')
    assert safe.status_code == 200 and ack.job.id in [item['id'] for item in safe.json()['items']]
    assert 'plan' not in safe.text and 'assertions' not in safe.text and 'restore_numbers' not in safe.text
    assert table_hashes(case.database) == before
    cancel = case.client.post(f'/api/v1/jobs/{ack.job.id}/cancel', json={'expected_revision': 1}, headers=command(case.headers, 'cancel'))
    assert cancel.status_code == 200, cancel.text
    assert case.client.post('/api/v1/session/role', json={'role': 'author'}, headers=command(case.headers, 'author-again')).status_code == 200
    read = case.client.get('/api/v1/content/restore-numeric-checks/' + view.id)
    assert read.status_code == 200 and read.json()['result']['outcome'] == 'cancelled'


def test_numeric_historical_actor_workspace_is_verified_with_another_current_author(restored):
    case = restored
    from dataclasses import replace
    from services.api.app.infrastructure.security import consume_bootstrap, issue_bootstrap_code
    from services.api.app.application.sessions import SessionService
    from services.api.app.dto import RoleRequest
    _, learner = consume_bootstrap(case.database, issue_bootstrap_code(case.database))
    SessionService(case.database).switch_role(learner, RoleRequest(role='author'), 'second-author')
    other = replace(learner, role='author')
    view = case.service.preview(other, case.identifier, case.request, 'second-actor-preview')
    corrupt(case.database, lambda conn: conn.execute('UPDATE local_sessions SET workspace_id=? WHERE id=?',
                                                   ('foreign_workspace', other.id)))
    before = table_hashes(case.database)
    with pytest.raises(ApiError) as error:
        case.service.read(case.identity, view.id)
    assert error.value.status == 409 and error.value.code == 'RESTORE_NUMERIC_INTEGRITY_ERROR'
    assert table_hashes(case.database) == before
