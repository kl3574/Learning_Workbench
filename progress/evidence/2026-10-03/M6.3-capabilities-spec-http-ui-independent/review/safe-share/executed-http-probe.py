"""Independent actual HTTP control-boundary probes; no CLI or external process."""
from contextlib import contextmanager
from dataclasses import replace

from fastapi.testclient import TestClient
import pytest

from services.api.app.application.codex_capabilities import CodexCapabilitiesService
from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.security import consume_bootstrap, issue_bootstrap_code
from services.api.app.main import create_app
from tests.integration.test_assessment_learning_port import assessment_learning_state
from tests.integration.test_assessment_policy import start

state = assessment_learning_state
VIEW = {'available': True, 'authorized': False, 'adapter_version': 'codex-cli/0.160.0',
        'sandbox_roots': [{'id': 'workspace_default', 'label': '此工作区的隔离 Broker 目录'}],
        'capabilities': {'approvals': False, 'interrupt': False, 'artifacts': False}}


def dump(database):
    with database.connect() as connection:
        return tuple(connection.iterdump())


def runtime(state, probe):
    database, *_ = state
    app = create_app(database.settings, codex_probe=probe)
    client = TestClient(app, base_url=database.settings.origin)
    response = client.post('/api/v1/session/bootstrap', json={'one_time_code': issue_bootstrap_code(database)},
                          headers={'Origin': database.settings.origin})
    assert response.status_code == 200
    return client, {'Origin': database.settings.origin, 'X-CSRF-Token': response.json()['csrf_token']}


@pytest.mark.parametrize('role,mode,status', [('learner', None, 200), ('author', None, 200),
    ('learner', 'open_book', 200), ('author', 'open_book', 200), ('author', 'independent', 409)])
def test_control_metadata_role_and_workspace_policy_are_real_http_and_query_only(state, monkeypatch, role, mode, status):
    database, *_ = state
    calls = []
    class Probe:
        def read(self):
            calls.append('read')
            return VIEW
    client, headers = runtime(state, Probe())
    if role == 'author':
        assert client.post('/api/v1/session/role', json={'role': 'author'},
            headers={**headers, 'Idempotency-Key': 'independent-probe-author'}).status_code == 200
    if mode:
        start(state, mode)
    before = dump(database)
    connect = Database.connect
    @contextmanager
    def readonly(self, **kwargs):
        with connect(self, **kwargs) as connection:
            connection.execute('PRAGMA query_only=ON')
            yield connection
    monkeypatch.setattr(Database, 'connect', readonly)
    response = client.get('/api/v1/codex/capabilities')
    assert response.status_code == status
    assert response.headers['cache-control'] == 'no-store'
    if status == 200:
        assert response.json() == VIEW
        assert calls == ['read']
    else:
        assert response.json()['error']['code'] == 'ASSESSMENT_ACTIVE'
        assert calls == []
    assert dump(database) == before


@pytest.mark.parametrize('change', ['revoke', 'expire', 'independent'])
def test_late_actual_http_response_rechecks_session_or_new_workspace_guard(state, change):
    database, *_ = state
    post_change = []
    class Probe:
        def read(self):
            if change == 'independent':
                start(state)
            else:
                with database.transaction() as connection:
                    if change == 'revoke':
                        connection.execute("UPDATE local_sessions SET revoked_at='2000-01-01T00:00:00Z'")
                    else:
                        connection.execute("UPDATE local_sessions SET expires_at='2000-01-01T00:00:00Z'")
            post_change.append(dump(database))
            return VIEW
    client, _ = runtime(state, Probe())
    response = client.get('/api/v1/codex/capabilities')
    assert response.status_code == (409 if change == 'independent' else 401)
    assert 'adapter_version' not in response.json()
    assert dump(database) == post_change[0]  # Exclude the explicit test-owner transition; GET itself adds no writes.


def test_wrong_workspace_identity_and_independent_workspace_do_not_borrow_a_live_session(state):
    database, *_ = state
    _, identity = consume_bootstrap(database, issue_bootstrap_code(database))
    calls = []
    class Probe:
        def read(self):
            calls.append('read')
            return VIEW
    service = CodexCapabilitiesService(database, Probe())
    before = dump(database)
    with pytest.raises(ApiError) as caught:
        service.read(replace(identity, workspace_id='workspace_not_the_actor_workspace'))
    assert caught.value.code == 'SESSION_REQUIRED' and not calls and dump(database) == before


def test_unknown_http_control_error_is_not_forged_unauthorized_and_has_no_new_state(state):
    database, *_ = state
    class Probe:
        def read(self):
            raise ApiError(503, 'CODEX_PROBE_TIMEOUT', '授权状态未知；未启动生成。')
    client, _ = runtime(state, Probe());before = dump(database)
    response = client.get('/api/v1/codex/capabilities')
    assert response.status_code == 503 and response.json()['error']['code'] == 'CODEX_PROBE_TIMEOUT'
    assert 'authorized' not in response.json() and dump(database) == before
