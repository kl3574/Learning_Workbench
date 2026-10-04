"""M6.3 local control projection; controlled probe never executes a model."""
from fastapi.testclient import TestClient

from services.api.app.config import Settings
from services.api.app.main import create_app
from services.api.app.security import issue_bootstrap_code


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
