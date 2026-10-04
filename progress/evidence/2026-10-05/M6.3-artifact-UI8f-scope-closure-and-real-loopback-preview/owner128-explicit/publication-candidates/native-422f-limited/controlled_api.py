"""Explicit private synthetic fixture, normal HTTP owners and real local parser.
No remote Provider, real CLI, tool command, sandbox probe or public registration.
"""
import json
from dataclasses import replace
from unittest.mock import patch
from services.api.app.config import Settings
from tests.integration.test_codex_turn_consent_http import make_consent_case
from tests.integration.test_codex_turn_dispatch_http import make_dispatch_case
from tests.integration.test_codex_artifact_manifest import execute, manifest_path

_generators = []


def create_app():
    settings = Settings.from_env()
    def configured(**kwargs):
        return replace(settings, **kwargs)
    # Only the existing test constructor's Settings factory is replaced, so its
    # original HTTP fixture uses this dedicated data directory and loopback port.
    with patch('tests.integration.test_codex_bootstrap_http.Settings', configured):
        base = make_consent_case(settings.data_dir)
        _generators.append(base)
        values = next(base)
        dispatch = make_dispatch_case(values)
        _generators.append(dispatch)
        active = next(dispatch)
        case = active[0]
        original = case.app.state.synthetic_executor.transport
        def transport(*args):
            answer = original(*args)
            # Existing normal role HTTP makes the eventual turn fail closed,
            # while preserving the already returned complete synthetic answer.
            r = case.client.post('/api/v1/session/role', json={'role': 'learner'},
                headers={**case.headers, 'Idempotency-Key': 'native-source-lose-role'})
            assert r.status_code == 200
            return answer
        case.app.state.synthetic_executor.transport = transport
        case, sid, prep, _, _, _ = execute(active)
        assert case.client.post('/api/v1/session/role', json={'role': 'author'},
            headers={**case.headers, 'Idempotency-Key': 'native-source-author-again'}).status_code == 200
        result = case.get(manifest_path(sid, prep))
        assert result.status_code == 200
        manifest = result.json()
        assert manifest['manifest']['source_outcome'] == 'failed'
        assert len(case.app.state.synthetic_transport_calls) == 1
        fixture = {'session_id': sid, 'turn_id': prep['turn_id'], 'manifest': manifest,
            'actor': case.actor_id, 'workspace': case.app.state.database.workspace_id(),
            'synthetic_memory_requests': 1, 'synthetic_bootstrap_calls': len(values[1].calls),
            'cookies': [{'name': c.name, 'value': c.value, 'domain': '127.0.0.1', 'path': '/'} for c in case.client.cookies.jar]}
        (settings.data_dir / 'private-fixture.json').write_text(json.dumps(fixture))
        return case.app
