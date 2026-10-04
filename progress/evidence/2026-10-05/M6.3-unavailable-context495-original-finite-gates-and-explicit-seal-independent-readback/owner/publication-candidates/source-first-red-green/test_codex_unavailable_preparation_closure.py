"""Approved seams: real HTTP/SQLite and checked owner ports; no CLI/model/tool."""
from fastapi.testclient import TestClient
import pytest

from packages.contracts.canonical import canonical_bytes
from services.api.app.application.codex_bootstrap_models import BootstrapFreeze
from services.api.app.infrastructure.security import author_execution_identity
from tests.integration.test_codex_bootstrap_http import ControlledRuntime, approve, make_case
from tests.integration.test_codex_turn_preparation_http import turn_body
from tests.integration.test_codex_turn_consent_http import preview_body


class HistoricalOnlyRuntime(ControlledRuntime):
    """Explicit synthetic bootstrap fixture; validation never inspects current host."""
    def __init__(self):
        super().__init__()
        self.original = None

    def freeze(self, sandbox_root_id):
        frozen = super().freeze(sandbox_root_id)
        self.original = frozen.model_copy(deep=True)
        return frozen

    def validate_frozen(self, frozen):
        BootstrapFreeze.model_validate(frozen.model_dump())
        assert self.original is not None
        assert canonical_bytes(frozen) == canonical_bytes(self.original)


@pytest.fixture
def closure_case(tmp_path):
    runtime = HistoricalOnlyRuntime()
    case = make_case(tmp_path, codex_bootstrap_runtime=runtime)
    case.app.state.provider_service.secret_store.initialize()
    response = case.client.put('/api/v1/providers/codex_local/config', json={
        'expected_revision': 0, 'adapter': 'compatible_chat', 'base_url': 'https://example.invalid',
        'model': 'unregistered-model', 'embedding_model': None, 'endpoint_policy': 'public_https', 'pricing': None,
    }, headers={**case.headers, 'Idempotency-Key': 'closure-config'})
    assert response.status_code == 200
    _, _, body = approve(case)
    response = case.post('sessions', body, 'closure-session')
    assert response.status_code == 201
    try:
        yield case, runtime, response.json()['id']
    finally:
        case.client.close()


def owned_material(case, value):
    with case.app.state.database.transaction(immediate=False) as conn:
        identity = author_execution_identity(conn, case.app.state.database.workspace_id(), case.actor_id)
        return case.app.state.codex_turn_service.read_outbound_preparation(conn, identity, value['id'], 1)


def test_real_prepare_freezes_known_owner_facts_and_pure_read_stays_unavailable(closure_case, monkeypatch):
    case, runtime, sid = closure_case
    calls = []
    def forbidden(*args, **kwargs):
        calls.append('forbidden')
        raise AssertionError('local unavailable preparation crossed an execution/current-runtime boundary')
    for name in ('freeze', 'validity', 'execute'):
        monkeypatch.setattr(runtime, name, forbidden)
    import subprocess
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    response = case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'closure-turn')
    assert response.status_code == 202
    value = response.json()
    material = owned_material(case, value)
    assert material.context.version == 'codex-turn-context-v4'
    assert material.context.closure.implemented is False
    assert material.context.closure.bootstrap.session.id == sid
    assert material.context.closure.bootstrap.finished.outcome.thread_id == 'synthetic-thread'
    before = case.dump()
    assert case.get('turn-preparations/'+value['id']).json() == value
    assert case.get('turns/'+value['turn_id']).json()['execution'] == 'not_started'
    assert owned_material(case, value) == material
    refused = case.post('consent-previews', preview_body(value), 'closure-preview')
    assert refused.status_code == 503
    assert refused.json()['error']['code'] == 'CODEX_INPUT_PROOF_UNAVAILABLE'
    assert case.dump() == before
    assert value['validity'] == 'unavailable' and value['proposal_id'] is None and value['consent_id'] is None
    assert case.app.state.codex_turn_worker.executor is None
    assert calls == [] and len(runtime.calls) == 1
