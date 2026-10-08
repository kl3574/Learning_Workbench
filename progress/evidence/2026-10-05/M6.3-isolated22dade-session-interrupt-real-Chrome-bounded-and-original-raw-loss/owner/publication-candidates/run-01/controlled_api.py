"""Private synthetic bootstrap only; real HTTP/SQLite interrupt owners.

No injected model executor, no proof registration, no provider secret, no tool.
The startup wrapper retains the complete original application lifespan.
"""
import json
import os
from contextlib import asynccontextmanager
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from services.api.app.config import Settings
from services.api.app.security import issue_bootstrap_code
from tests.integration.test_codex_bootstrap_http import ControlledRuntime, approve, make_case
from tests.integration.test_codex_turn_preparation_http import turn_body

_patches = []


def create_app():
    settings = replace(Settings.from_env(), static_dir=Path(os.environ['NATIVE_STATIC_DIR']))
    runtime = ControlledRuntime()
    counters = dict(codex_executor=0, provider_transport=0, literal_operation=0, later_bootstrap=0)
    def save(phase):
        (settings.data_dir / 'sentinels.json').write_text(json.dumps({
            'counts': counters, 'synthetic_bootstrap_calls': len(runtime.calls),
            'executor_none': case.app.state.codex_turn_worker.executor is None, 'phase': phase}))
    def forbidden(name):
        def reject(*args, **kwargs):
            counters[name] += 1
            save('forbidden')
            raise AssertionError('Forbidden synthetic test seam: ' + name)
        return reject
    with patch('tests.integration.test_codex_bootstrap_http.Settings', lambda **kw: replace(settings, **kw)):
        case = make_case(settings.data_dir, codex_bootstrap_runtime=runtime)
    config = case.client.put('/api/v1/providers/codex_local/config', json={
        'expected_revision': 0, 'adapter': 'compatible_chat', 'base_url': 'https://example.invalid',
        'model': 'synthetic-model', 'embedding_model': None, 'endpoint_policy': 'public_https', 'pricing': None,
    }, headers={**case.headers, 'Idempotency-Key': 'synthetic-config'})
    assert config.status_code == 200
    _, _, body = approve(case)
    created = case.post('sessions', body, 'native-bootstrap')
    assert created.status_code == 201 and len(runtime.calls) == 1
    sid = created.json()['id']
    prepared = case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'native-preparation')
    assert prepared.status_code == 202
    value = prepared.json()
    assert value['validity'] == 'unavailable' and value['job']['status'] == 'awaiting_approval'
    assert value['consent_id'] is None and value['proposal_id'] is None
    switched = case.client.post('/api/v1/session/role', json={'role': 'learner'},
        headers={**case.headers, 'Idempotency-Key': 'native-learner'})
    assert switched.status_code == 200
    other = TestClient(case.app, base_url=settings.origin)
    login = other.post('/api/v1/session/bootstrap', json={'one_time_code': issue_bootstrap_code(case.app.state.database)},
        headers={'Origin': settings.origin})
    assert login.status_code == 200
    actor_b = other.get('/api/v1/session').json()
    assert actor_b['role'] == 'learner' and actor_b['actor_session_id'] != case.actor_id
    cookies = lambda client: [{'name': c.name, 'value': c.value, 'domain': '127.0.0.1', 'path': '/'} for c in client.cookies.jar]
    (settings.data_dir / 'private-fixture.json').write_text(json.dumps({
        'session_id': sid, 'turn_id': value['turn_id'], 'job_id': value['job']['id'],
        'actor': case.actor_id, 'workspace': actor_b['workspace_id'], 'actor_b': actor_b['actor_session_id'],
        'cookies': cookies(case.client), 'cookies_b': cookies(other)}))
    runtime.execute = forbidden('later_bootstrap')
    for target, name in [
        ('services.api.app.application.codex_turn_worker.SyntheticCodexExecutor.execute', 'codex_executor'),
        ('services.api.app.infrastructure.provider_transport.ProviderTransport.stream', 'provider_transport'),
        ('services.api.app.application.codex_operation_profile.CodexOperationRegistry.execute', 'literal_operation'),
    ]:
        active = patch(target, forbidden(name)); active.start(); _patches.append(active)
    original = case.app.router.lifespan_context
    @asynccontextmanager
    async def observed(app):
        async with original(app):
            save('lifespan-entered')
            try:
                yield
            finally:
                save('lifespan-exiting')
        save('lifespan-exited')
    case.app.router.lifespan_context = observed
    other.close(); case.client.close()
    return case.app
