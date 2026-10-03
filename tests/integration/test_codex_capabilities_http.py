"""M6.3 local control projection; controlled probe never executes a model."""
from fastapi.testclient import TestClient
import pytest

from services.api.app.application.errors import ApiError
from services.api.app.application.codex_capabilities import CodexCapabilitiesService
from services.api.app.config import Settings
from services.api.app.main import create_app
from services.api.app.security import issue_bootstrap_code
from services.api.app.infrastructure.security import consume_bootstrap
from tests.integration.test_assessment_policy import start
from tests.integration.test_assessment_learning_port import assessment_learning_state

state = assessment_learning_state


def test_capabilities_are_a_real_authenticated_read_only_projection(tmp_path):
    calls = []
    class ControlledProbe:
        def read(self):
            calls.append('bounded-local-protocol')
            return {'available': True, 'authorized': False, 'adapter_version': 'codex-cli/0.160.0',
                    'sandbox_roots': [{'id': 'workspace_default', 'label': '工作区隔离目录'}],
                    'capabilities': {'approvals': False, 'interrupt': False, 'artifacts': False}}
    settings = Settings(data_dir=tmp_path)
    application = create_app(settings, codex_probe=ControlledProbe())
    application.state.database.initialize()
    client = TestClient(application, base_url=settings.origin)
    assert client.get('/api/v1/codex/capabilities').status_code == 401
    assert calls == []
    response = client.post('/api/v1/session/bootstrap', json={'one_time_code': issue_bootstrap_code(application.state.database)}, headers={'Origin': settings.origin})
    assert response.status_code == 200
    with application.state.database.connect() as connection:
        before = tuple(connection.iterdump())
    result = client.get('/api/v1/codex/capabilities')
    assert result.status_code == 200
    assert result.json() == {'available': True, 'authorized': False, 'adapter_version': 'codex-cli/0.160.0',
        'sandbox_roots': [{'id': 'workspace_default', 'label': '工作区隔离目录'}],
        'capabilities': {'approvals': False, 'interrupt': False, 'artifacts': False}}
    assert 'no-store' in result.headers['cache-control']
    assert calls == ['bounded-local-protocol']
    assert client.request('GET', '/api/v1/codex/capabilities', content=b'{}').status_code == 422
    assert calls == ['bounded-local-protocol']
    with application.state.database.connect() as connection:
        assert tuple(connection.iterdump()) == before
    assert client.get('/api/v1/codex/capabilities?path=/outside').status_code == 422
    assert calls == ['bounded-local-protocol']


@pytest.mark.parametrize('result,status', [(ApiError(503, 'CODEX_PROBE_TIMEOUT', '授权状态未知。'), 503),
    ({'available':True, 'authorized':False, 'codexHome':'synthetic_private'}, 502)])
def test_unknown_or_malformed_probe_cannot_be_rendered_as_unauthorized(tmp_path, result, status):
    class Probe:
        def read(self):
            if isinstance(result, Exception):
                raise result
            return result
    settings = Settings(data_dir=tmp_path)
    application = create_app(settings, codex_probe=Probe())
    application.state.database.initialize()
    client = TestClient(application, base_url=settings.origin)
    client.post('/api/v1/session/bootstrap', json={'one_time_code':issue_bootstrap_code(application.state.database)}, headers={'Origin':settings.origin})
    with application.state.database.connect() as connection:
        before = tuple(connection.iterdump())
    response = client.get('/api/v1/codex/capabilities')
    assert response.status_code == status
    assert 'authorized' not in response.json() and 'synthetic_private' not in response.text
    with application.state.database.connect() as connection:
        assert tuple(connection.iterdump()) == before


@pytest.mark.parametrize('change', ['revoke', 'independent'])
def test_late_probe_projection_is_rejected_after_current_access_changes(state, change):
    database, _, fixture, assessment = state
    _, identity = consume_bootstrap(database, issue_bootstrap_code(database))
    current_state = (database, identity, fixture, assessment)
    calls = []
    class Probe:
        def read(self):
            calls.append('read')
            if change == 'revoke':
                with database.transaction() as connection:
                    connection.execute("UPDATE local_sessions SET revoked_at='2026-01-01T00:00:00Z' WHERE id=?", (identity.id,))
            else:
                start(current_state)
            return {'available':False,'authorized':False,'adapter_version':None,'sandbox_roots':[],
                    'capabilities':{'approvals':False,'interrupt':False,'artifacts':False}}
    service = CodexCapabilitiesService(database, Probe())
    with pytest.raises(ApiError) as error:
        service.read(identity)
    assert error.value.code == ('SESSION_REQUIRED' if change == 'revoke' else 'ASSESSMENT_ACTIVE')
    assert calls == ['read']
    with database.connect() as connection:
        before = tuple(connection.iterdump())
    with pytest.raises(ApiError):
        service.read(identity)
    assert calls == ['read']
    with database.connect() as connection:
        assert tuple(connection.iterdump()) == before


def test_factory_and_openapi_never_observe_cli_or_create_broker_directory(tmp_path):
    class Probe:
        def read(self):
            pytest.fail('factory or OpenAPI started a control probe')
    data = tmp_path / 'not-created'
    application = create_app(Settings(data_dir=data), codex_probe=Probe())
    operation = application.openapi()['paths']['/api/v1/codex/capabilities']['get']
    assert 'requestBody' not in operation and not data.exists()
