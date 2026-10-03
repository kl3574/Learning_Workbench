"""Actual HTTP/SQLite boundaries with synthetic workspace and control runtime."""
from dataclasses import dataclass

from fastapi.testclient import TestClient
import pytest

from services.api.app.config import Settings
from services.api.app.main import create_app
from services.api.app.security import issue_bootstrap_code
from services.api.app.application.codex_bootstrap_models import BootstrapFreeze, BootstrapOutcome
from services.api.app.codex_bootstrap_dto import CodexBootstrapScope
from services.api.app.serialization import canonical_json, content_sha256
from packages.contracts.canonical import strict_json
from tests.integration.test_assessment_learning_port import assessment_learning_state

assessment_state = assessment_learning_state


@dataclass
class Case:
    app: object
    client: TestClient
    headers: dict
    actor_id: str

    def post(self, path, body, key):
        return self.client.post('/api/v1/codex/' + path, json=body,
                                headers={**self.headers, 'Idempotency-Key': key})

    def get(self, path):
        return self.client.get('/api/v1/codex/' + path)

    def dump(self):
        with self.app.state.database.connect() as connection:
            return tuple(connection.iterdump())


def make_case(tmp_path, **options):
    settings = Settings(data_dir=tmp_path, codex_executable=tmp_path / 'missing-controlled-cli')
    app = create_app(settings, **options)
    app.state.database.initialize()
    client = TestClient(app, base_url=settings.origin)
    bootstrap = client.post('/api/v1/session/bootstrap', json={'one_time_code': issue_bootstrap_code(app.state.database)},
                            headers={'Origin': settings.origin})
    headers = {'Origin': settings.origin, 'X-CSRF-Token': bootstrap.json()['csrf_token']}
    response = client.post('/api/v1/session/role', json={'role': 'author'}, headers={**headers, 'Idempotency-Key': 'author'})
    assert response.status_code == 200
    actor = client.get('/api/v1/session').json()['actor_session_id']
    return Case(app, client, headers, actor)


def test_unavailable_prepare_read_and_decline_never_start_cli_or_write_on_get(tmp_path, monkeypatch):
    import subprocess
    def forbidden(*args, **kwargs):
        pytest.fail('prepare, GET or decision started a process')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    case = make_case(tmp_path)
    body = {'sandbox_root_id': 'workspace_default', 'allowed_actions': []}
    created = case.post('session-preparations', body, 'prepare-original')
    assert created.status_code == 201, created.text
    original = created.json()
    assert original['status'] == 'pending' and original['revision'] == 1 and original['validity'] == 'unavailable'
    assert original['actor_session_id'] == case.actor_id and original['consent_id'] is None
    path = 'session-preparations/' + original['id']
    before = case.dump()
    read = case.get(path)
    assert read.status_code == 200 and read.json() == original
    assert read.headers['cache-control'] == 'no-store'
    assert case.dump() == before
    decision = {'expected_revision': 1, 'operation_sha256': original['operation_sha256'], 'decision': 'approve_once'}
    assert case.post(path + '/decision', decision, 'not-available').status_code == 409
    declined = case.post(path + '/decision', {**decision, 'decision': 'decline'}, 'decline-original')
    assert declined.status_code == 200 and declined.json()['revision'] == 2 and declined.json()['consent_id'] is None
    current = case.get(path).json()
    assert (current['status'], current['revision'], current['validity']) == ('declined', 2, 'closed')
    before = case.dump()
    assert case.post('session-preparations', body, 'prepare-original').json() == original
    assert case.post(path + '/decision', {**decision, 'decision': 'decline'}, 'decline-original').json() == declined.json()
    assert case.dump() == before


class ControlledRuntime:
    """A named synthetic test port, never proof of actual CLI or isolation."""
    def __init__(self):
        self.calls = []
        self.current = 'current'
        self.after_start = lambda: None
        self.outcome = 'ready'

    def freeze(self, sandbox_root_id):
        if sandbox_root_id != 'workspace_default':
            from services.api.app.application.errors import ApiError
            raise ApiError(409, 'CODEX_BOOTSTRAP_BINDING', 'Synthetic root mismatch')
        description = {'version': 'synthetic-owner-test-v1', 'methods': ['initialize', 'initialized', 'thread/start']}
        return BootstrapFreeze(version='codex-bootstrap-freeze-v1', scope=CodexBootstrapScope(
            version='codex-local-session-bootstrap-v1', sandbox_root_id=sandbox_root_id,
            sandbox_label='Synthetic owner test', allowed_actions=[], adapter_version='synthetic-control-v1',
            bootstrap_profile_sha256=content_sha256(description)), description_json=canonical_json(description), available=True)

    def validate_frozen(self, frozen):
        assert frozen == self.freeze(frozen.scope.sandbox_root_id)

    def validity(self, frozen):
        self.validate_frozen(frozen)
        return self.current

    def execute(self, frozen, permit_id):
        self.calls.append(permit_id)
        self.after_start()
        if self.outcome == 'exception':
            raise ValueError('synthetic_private_runtime_diagnostic')
        if self.outcome == 'ready':
            return BootstrapOutcome(status='ready', thread_id='synthetic-thread', receipt_json=canonical_json({
                'permit_id': permit_id, 'profile': frozen.scope.bootstrap_profile_sha256, 'thread_id': 'synthetic-thread'}),
                error_code=None, thread_start_attempted=True)
        return BootstrapOutcome(status=self.outcome, thread_id=None, receipt_json=None,
            error_code='CODEX_BOOTSTRAP_UNAVAILABLE' if self.outcome == 'failed' else 'CODEX_SESSION_OUTCOME_UNKNOWN',
            thread_start_attempted=self.outcome != 'failed')

    def validate_outcome(self, frozen, permit_id, outcome):
        BootstrapOutcome.model_validate(outcome.model_dump())
        if outcome.status == 'ready':
            assert strict_json(outcome.receipt_json) == {'permit_id': permit_id,
                'profile': frozen.scope.bootstrap_profile_sha256, 'thread_id': outcome.thread_id}


@pytest.fixture
def controlled_case(tmp_path):
    runtime = ControlledRuntime()
    return make_case(tmp_path, codex_bootstrap_runtime=runtime), runtime


def approve(case, key='one'):
    created = case.post('session-preparations', {'sandbox_root_id': 'workspace_default', 'allowed_actions': []}, 'prepare-' + key)
    assert created.status_code == 201, created.text
    original = created.json()
    path = 'session-preparations/' + original['id']
    decision = {'expected_revision': 1, 'operation_sha256': original['operation_sha256'], 'decision': 'approve_once'}
    response = case.post(path + '/decision', decision, 'decision-' + key)
    assert response.status_code == 200, response.text
    return original, response.json(), {'sandbox_root_id': 'workspace_default',
                                     'consent_id': response.json()['consent_id'], 'allowed_actions': []}


@pytest.mark.parametrize('outcome', ['ready', 'failed', 'unknown', 'exception'])
def test_one_consumption_original_acks_current_reads_and_restart_never_repeat(controlled_case, outcome):
    case, runtime = controlled_case
    original, decision, body = approve(case)
    assert runtime.calls == []
    runtime.outcome = outcome
    response = case.post('sessions', body, 'session-original')
    assert response.status_code == (201 if outcome == 'ready' else 503), response.text
    assert len(runtime.calls) == 1
    if outcome == 'exception':
        assert 'synthetic_private' not in response.text
    current = case.get('session-preparations/' + original['id']).json()
    assert (current['revision'], current['status'], current['validity']) == (3, 'consumed', 'closed')
    assert current['actor_session_id'] == original['actor_session_id'] and current['consent_id'] == decision['consent_id']
    session = case.get('sessions/' + current['session_id'])
    assert session.status_code == 200, session.text
    assert session.json()['status'] == ('unknown' if outcome == 'exception' else outcome)
    assert session.json()['active_turn_id'] is None and all(value is False for value in session.json()['capabilities'].values())
    assert 'thread' not in session.text and 'receipt' not in session.text
    before = case.dump()
    owners = case.app.state.settings.data_dir / 'codex-control-owners'
    owner_files = {path.name for path in owners.iterdir()}
    replay = case.post('sessions', body, 'session-original')
    assert replay.status_code == response.status_code
    if outcome == 'ready':
        assert replay.content == response.content
    else:
        assert replay.json()['error']['code'] == response.json()['error']['code']
    assert case.post('sessions', body, 'session-other').status_code == 409
    assert case.post('sessions', {**body, 'sandbox_root_id': 'other'}, 'session-original').status_code == 409
    assert len(runtime.calls) == 1 and case.dump() == before
    assert {path.name for path in owners.iterdir()} == owner_files
    # A new application/owner on the same database reads persisted facts only.
    restarted = create_app(case.app.state.settings, codex_bootstrap_runtime=runtime)
    assert restarted.state.codex_bootstrap_service.recover(case.app.state.database.workspace_id()) == 0
    from services.api.app.infrastructure.security import SessionIdentity
    with case.app.state.database.connect() as connection:
        row = connection.execute('SELECT expires_at FROM local_sessions WHERE id=?', (case.actor_id,)).fetchone()
    identity = SessionIdentity(case.actor_id, case.app.state.database.workspace_id(), 'author', '', row['expires_at'])
    assert restarted.state.codex_bootstrap_service.read_session(identity, current['session_id']).model_dump() == session.json()
    assert len(runtime.calls) == 1 and case.dump() == before


@pytest.mark.parametrize('change', ['learner', 'revoke'])
def test_post_start_access_loss_preserves_actual_fact_without_delivering_201(controlled_case, change):
    case, runtime = controlled_case
    original, _, body = approve(case)
    def changed():
        with case.app.state.database.transaction() as connection:
            if change == 'learner':
                connection.execute("UPDATE local_sessions SET role='learner' WHERE id=?", (case.actor_id,))
            else:
                connection.execute("UPDATE local_sessions SET revoked_at='2026-01-01T00:00:00Z' WHERE id=?", (case.actor_id,))
    runtime.after_start = changed
    response = case.post('sessions', body, 'one-start')
    assert response.status_code == (403 if change == 'learner' else 401), response.text
    with case.app.state.database.transaction() as connection:
        row = connection.execute('SELECT status,revision,external_thread_id FROM codex_sessions').fetchone()
        assert tuple(row) == ('ready', 2, 'synthetic-thread')
        connection.execute("UPDATE local_sessions SET role='author',revoked_at=NULL WHERE id=?", (case.actor_id,))
    current = case.get('session-preparations/' + original['id']).json()
    assert current['session_id'] is not None and current['status'] == 'consumed'
    assert case.post('sessions', body, 'one-start').status_code == 201
    assert len(runtime.calls) == 1


@pytest.mark.parametrize('bad', ['expected_revision', 'operation_sha256', 'extra', 'bool_revision', 'actions', 'duplicate_key', 'missing_csrf'])
def test_strict_cas_transport_and_empty_permissions_do_not_write(controlled_case, bad):
    case, runtime = controlled_case
    created = case.post('session-preparations', {'sandbox_root_id': 'workspace_default', 'allowed_actions': []}, 'prepare').json()
    body = {'expected_revision': 1, 'operation_sha256': created['operation_sha256'], 'decision': 'approve_once'}
    path = 'session-preparations/' + created['id'] + '/decision'
    expected = 422
    if bad == 'expected_revision':
        body['expected_revision'] = 2
        expected = 412
    elif bad == 'operation_sha256':
        body['operation_sha256'] = 'f' * 64
        expected = 409
    elif bad == 'extra':
        body['actor_session_id'] = case.actor_id
    elif bad == 'bool_revision':
        body['expected_revision'] = True
    elif bad == 'actions':
        path, body = 'session-preparations', {'sandbox_root_id': 'workspace_default', 'allowed_actions': ['read']}
    before = case.dump()
    if bad == 'duplicate_key':
        response = case.client.post('/api/v1/codex/' + path, json=body,
            headers=[*case.headers.items(), ('Idempotency-Key', 'one'), ('Idempotency-Key', 'two')])
        expected = 400
    elif bad == 'missing_csrf':
        expected = 403
        response = case.client.post('/api/v1/codex/' + path, json=body, headers={'Origin': case.headers['Origin'], 'Idempotency-Key': 'one'})
    else:
        response = case.post(path, body, 'bad')
    assert response.status_code == expected, response.text
    assert case.dump() == before and runtime.calls == []


@pytest.mark.parametrize('table,mode', [('codex_bootstrap_events', 'tail'), ('codex_bootstrap_events', 'all'),
    ('codex_bootstrap_heads', 'all'), ('codex_bootstrap_memberships', 'all'), ('codex_bootstrap_event_memberships', 'all'),
    ('codex_bootstrap_commands', 'all'), ('codex_bootstrap_session_memberships', 'all'), ('codex_sessions', 'all')])
def test_incomplete_history_cannot_replay_or_repair(controlled_case, table, mode):
    case, runtime = controlled_case
    original, _, body = approve(case)
    assert case.post('sessions', body, 'one').status_code == 201
    with case.app.state.database.transaction() as connection:
        for row in connection.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (table,)).fetchall():
            connection.execute('DROP TRIGGER ' + row[0])
        connection.execute('DELETE FROM ' + table + (' WHERE sequence=4' if mode == 'tail' else ''))
    before = case.dump()
    assert case.get('session-preparations/' + original['id']).status_code == 409
    assert case.post('sessions', body, 'one').status_code == 409
    assert case.dump() == before and len(runtime.calls) == 1


def test_concurrent_original_command_and_recovery_observe_one_live_instance(controlled_case):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    case, runtime = controlled_case
    original, _, body = approve(case)
    entered, release = Event(), Event()
    def hold():
        entered.set()
        assert release.wait(5)
    runtime.after_start = hold
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(case.post, 'sessions', body, 'original')
        try:
            assert entered.wait(3)
            current = case.get('session-preparations/' + original['id']).json()
            assert current['status'] == 'consumed'
            assert case.get('sessions/' + current['session_id']).json()['status'] == 'initializing'
            before = case.dump()
            locks = sorted((case.app.state.settings.data_dir / 'codex-control-owners').iterdir())
            assert case.post('sessions', body, 'original').json()['error']['code'] == 'CODEX_SESSION_INITIALIZING'
            assert case.post('sessions', body, 'different').status_code == 409
            assert sorted((case.app.state.settings.data_dir / 'codex-control-owners').iterdir()) == locks
            restarted = create_app(case.app.state.settings, codex_bootstrap_runtime=runtime)
            assert restarted.state.codex_bootstrap_service.recover(case.app.state.database.workspace_id()) == 0
            assert case.dump() == before and len(runtime.calls) == 1
        finally:
            release.set()
        assert pending.result().status_code == 201
    assert case.post('sessions', body, 'original').status_code == 201 and len(runtime.calls) == 1


@pytest.mark.parametrize('phase', ['consume', 'result'])
def test_transaction_failure_never_partially_consumes_or_repeats_started_operation(controlled_case, monkeypatch, phase):
    import sqlite3
    from services.api.app.infrastructure.codex_bootstrap_repository import CodexBootstrapRepository
    case, runtime = controlled_case
    original, _, body = approve(case)
    real = CodexBootstrapRepository.project_session
    def failing(self, snapshot, consumed, finished):
        real(self, snapshot, consumed, finished)
        if (phase == 'consume') == (finished is None):
            raise sqlite3.OperationalError('synthetic fault after owner projection')
    before = case.dump()
    monkeypatch.setattr(CodexBootstrapRepository, 'project_session', failing)
    response = case.post('sessions', body, 'original')
    assert response.status_code == 503
    monkeypatch.setattr(CodexBootstrapRepository, 'project_session', real)
    if phase == 'consume':
        assert runtime.calls == [] and case.dump() == before
        assert case.post('sessions', body, 'original').status_code == 201 and len(runtime.calls) == 1
    else:
        assert len(runtime.calls) == 1
        current = case.get('session-preparations/' + original['id']).json()
        assert current['status'] == 'consumed' and current['session_id'] is not None
        before_get = case.dump()
        assert case.get('sessions/' + current['session_id']).json()['status'] == 'initializing'
        assert case.dump() == before_get
        # Explicit lifecycle recovery, never a read side effect or second CLI.
        restarted = create_app(case.app.state.settings, codex_bootstrap_runtime=runtime)
        assert restarted.state.codex_bootstrap_service.recover(case.app.state.database.workspace_id()) == 1
        assert case.get('sessions/' + current['session_id']).json()['status'] == 'unknown'
        assert case.post('sessions', body, 'original').json()['error']['code'] == 'CODEX_SESSION_OUTCOME_UNKNOWN'
        assert restarted.state.codex_bootstrap_service.recover(case.app.state.database.workspace_id()) == 0
        assert len(runtime.calls) == 1


@pytest.mark.parametrize('validity', ['changed', 'unavailable', 'expired'])
def test_derived_current_validity_never_rewrites_original_approval(controlled_case, monkeypatch, validity):
    from datetime import datetime, timedelta
    from services.api.app.application import codex_bootstrap
    from services.api.app.infrastructure import codex_bootstrap_repository
    case, runtime = controlled_case
    original, decision, body = approve(case)
    if validity == 'expired':
        later = (datetime.fromisoformat(original['expires_at']) + timedelta(seconds=1)).isoformat().replace('+00:00', 'Z')
        monkeypatch.setattr(codex_bootstrap, 'utc_now', lambda: later)
        monkeypatch.setattr(codex_bootstrap_repository, 'utc_now', lambda: later)
    else:
        runtime.current = validity
    before = case.dump()
    path = 'session-preparations/' + original['id']
    assert case.get(path).json()['validity'] == validity
    replay = case.post(path + '/decision', {'expected_revision': 1, 'operation_sha256': original['operation_sha256'],
                                          'decision': 'approve_once'}, 'decision-one')
    assert replay.status_code == 200 and replay.json() == decision
    assert case.post('session-preparations', {'sandbox_root_id': 'workspace_default', 'allowed_actions': []}, 'prepare-one').json() == original
    assert case.post('sessions', body, 'not-current').status_code == 409
    assert case.dump() == before and runtime.calls == []
    assert not (case.app.state.settings.data_dir / 'codex-control-owners').exists()


def test_new_actor_can_read_metadata_but_cannot_take_over_an_old_grant(controlled_case):
    case, runtime = controlled_case
    original, _, body = approve(case)
    bootstrap = case.client.post('/api/v1/session/bootstrap', json={'one_time_code': issue_bootstrap_code(case.app.state.database)},
                                headers={'Origin': case.headers['Origin']})
    case.headers['X-CSRF-Token'] = bootstrap.json()['csrf_token']
    assert case.client.post('/api/v1/session/role', json={'role': 'author'},
        headers={**case.headers, 'Idempotency-Key': 'new-actor-author'}).status_code == 200
    current_actor = case.client.get('/api/v1/session').json()['actor_session_id']
    assert current_actor != original['actor_session_id']
    path = 'session-preparations/' + original['id']
    before = case.dump()
    assert case.get(path).json()['actor_session_id'] == original['actor_session_id']
    assert case.post(path + '/decision', {'expected_revision': 1, 'operation_sha256': original['operation_sha256'],
        'decision': 'approve_once'}, 'decision-one').status_code == 409
    assert case.post('sessions', body, 'new-actor').status_code == 409
    assert case.dump() == before and runtime.calls == []


@pytest.mark.parametrize('query', ['?x=1', '?x=1&x=2'])
def test_both_control_gets_reject_queries_and_body_without_side_effects(controlled_case, query):
    case, runtime = controlled_case
    original, _, body = approve(case)
    session = case.post('sessions', body, 'one').json()
    before = case.dump()
    for path in ('session-preparations/' + original['id'], 'sessions/' + session['id']):
        assert case.get(path + query).status_code == 422
        assert case.client.request('GET', '/api/v1/codex/' + path, content='{}').status_code == 422
    assert case.dump() == before and len(runtime.calls) == 1


@pytest.mark.parametrize('mode', ['independent', 'open_book'])
def test_real_workspace_policy_change_after_start_preserves_fact_but_gates_every_write(assessment_state, mode):
    from tests.integration.test_assessment_policy import start
    from services.api.app.infrastructure.security import SessionIdentity
    database, _, fixture, assessment = assessment_state
    runtime = ControlledRuntime()
    case = make_case(database.settings.data_dir, codex_bootstrap_runtime=runtime)
    original, decision, body = approve(case)
    pending = case.post('session-preparations', {'sandbox_root_id': 'workspace_default', 'allowed_actions': []}, 'pending').json()
    identity = SessionIdentity(case.actor_id, database.workspace_id(), 'author', '', '2099-01-01T00:00:00Z')
    runtime.after_start = lambda: start((database, identity, fixture, assessment), mode=mode)
    denied = case.post('sessions', body, 'session-original')
    assert denied.status_code == 409 and denied.json()['error']['code'] == 'ASSESSMENT_ACTIVE'
    assert len(runtime.calls) == 1
    before = case.dump()
    path = 'session-preparations/' + original['id']
    current = case.get(path)
    assert current.status_code == 200 and current.json()['status'] == 'consumed'
    read = case.get('sessions/' + current.json()['session_id'])
    assert read.status_code == 200 and read.json()['status'] == 'ready'
    assert case.post('sessions', body, 'session-original').status_code == 409
    assert case.post('session-preparations', {'sandbox_root_id': 'workspace_default', 'allowed_actions': []}, 'blocked').status_code == 409
    assert case.post('session-preparations/' + pending['id'] + '/decision', {
        'expected_revision': 1, 'operation_sha256': pending['operation_sha256'], 'decision': 'decline'}, 'blocked-decline').status_code == 409
    assert case.post(path + '/decision', {'expected_revision': 1, 'operation_sha256': decision['operation_sha256'],
        'decision': 'approve_once'}, 'decision-one').status_code == 409
    assert case.dump() == before and len(runtime.calls) == 1


def test_cross_workspace_control_ids_and_grants_never_establish_authority(controlled_case):
    case, runtime = controlled_case
    original, _, body = approve(case)
    assert case.post('sessions', body, 'first').status_code == 201
    session = case.get('session-preparations/' + original['id']).json()['session_id']
    # A second synthetic local actor is assigned to a distinct synthetic
    # workspace. No real workspace or credential is accessed by this fixture.
    bootstrap = case.client.post('/api/v1/session/bootstrap', json={'one_time_code': issue_bootstrap_code(case.app.state.database)},
        headers={'Origin': case.headers['Origin']})
    case.headers['X-CSRF-Token'] = bootstrap.json()['csrf_token']
    other_actor = case.client.get('/api/v1/session').json()['actor_session_id']
    with case.app.state.database.transaction() as connection:
        connection.execute("INSERT INTO workspace(id,title,created_at) VALUES('workspace_other','Synthetic other','2026-01-01T00:00:00Z')")
        connection.execute("UPDATE local_sessions SET workspace_id='workspace_other',role='author' WHERE id=?", (other_actor,))
    before = case.dump()
    assert case.get('session-preparations/' + original['id']).status_code == 404
    assert case.get('sessions/' + session).status_code == 404
    assert case.post('sessions', body, 'cross-workspace').status_code == 409
    assert case.post('session-preparations/' + original['id'] + '/decision', {
        'expected_revision': 1, 'operation_sha256': original['operation_sha256'], 'decision': 'approve_once'}, 'cross-workspace').status_code == 404
    assert case.dump() == before and len(runtime.calls) == 1
