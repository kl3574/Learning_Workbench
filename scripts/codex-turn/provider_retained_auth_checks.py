"""Owned SQLite/SecretStore + fixed genuine Rust memory tests, zero transport.

Run explicitly with pytest and LW_OWNED_RETAINED_LIBRARY plus
LW_OWNED_RETAINED_LIBRARY_SHA256 pointing to an owned sealed build.
Existing compiled sealed Rust SO is reused; this is NOT a fresh Rust build.
This manual filename is intentionally outside default full-suite discovery.
Synthetic proof/resolver composition never qualifies a genuine InputProof.
"""
from contextlib import ExitStack
from dataclasses import FrozenInstanceError, replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import uuid

from fastapi.testclient import TestClient
import pytest

from services.api.app.application.codex_turn_worker import SyntheticCodexExecutor
from services.api.app.application.errors import ApiError
from services.api.app.application.provider_budget import ProofRegistry
from services.api.app.application.provider_codex_profile import CodexProofRegistry, SyntheticCodexProof
from services.api.app.application.provider_codex_retained_request import _RetainedCoreRequestOwner, _ResolvedCoreConstruction
from services.api.app.infrastructure.security import author_execution_identity
from services.api.app.main import create_app
from services.api.app.provider_dto import ProviderConfigView, ProviderConfigWrite, ProviderSecretAck, ProviderSecretWrite
from services.api.app.infrastructure.provider_repository import ProviderRepository
from services.api.app.application.providers import command_id
from services.api.app.serialization import content_sha256
from tests.integration.test_codex_bootstrap_http import Case, ControlledRuntime, approve, make_case
from tests.integration.test_codex_turn_consent_http import grant_fixture, full_preview_body
from packages.contracts import domain_models as dm

BUNDLE = Path(__file__).resolve().parents[2] / 'scripts' / 'codex-turn'


def load_module(name, file):
    spec = importlib.util.spec_from_file_location(name, file)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class _ObservedForeign:
    def __init__(self, foreign):
        self.foreign = foreign
        self.calls = 0

    def create(self, facts, bearer):
        self.calls += 1
        return self.foreign.create(facts, bearer)


class _SecretAdapter:
    """Explicit test system-adapter drift; initial bytes come from real FileStore."""
    def __init__(self, store):
        self.store = store
        self.override = None

    def read(self, locator):
        return self.store.read(locator) if self.override is None else self.override

    def __getattr__(self, name):
        return getattr(self.store, name)


class _TestResolver:
    """Fixture-only metadata; no production metadata or InputProof claim."""
    def __init__(self):
        self.callback = lambda conn, current, material, config: None
        self.mutate = lambda facts: None

    def resolve(self, conn, current, material, config, binding):
        fixture = load_module('_owned_foreign_fixtures', BUNDLE / 'retained_request_foreign_tests.py')
        facts = fixture.materials()
        facts['provider']['base_url'] = config.base_url
        facts['provider']['name'] = config.id
        facts['maximum'] = self.budget['max_output_tokens']
        facts['timeout_ms'] = material.input.runtime.tools.wall_seconds * 1000
        facts['response_body_limit_bytes'] = material.input.runtime.protocol_output_bytes
        facts['model_info']['slug'] = config.model
        facts['model_info']['display_name'] = config.model
        # Explicit fixture projection, not a claimed native AppServer mapping.
        native_thread = str(uuid.uuid5(uuid.NAMESPACE_URL, 'owned-test/' + material.preparation.session_id))
        facts['policy']['thread_id'] = native_thread
        facts['http_facts']['thread_id'] = native_thread
        facts['metadata']['thread_id'] = native_thread
        facts['metadata']['session_id'] = material.preparation.session_id
        facts['metadata']['turn_id'] = material.preparation.turn_id
        messages = material.context.messages
        assert messages[0].role == 'system' and not material.context.evidence
        facts['prompt']['base_instructions']['text'] = messages[0].content
        facts['prompt']['input'] = [{'type': 'message', 'role': item.role,
            'content': [{'type': 'input_text', 'text': item.content}]} for item in messages[1:]]
        self.callback(conn, current, material, config)
        self.mutate(facts)
        return _ResolvedCoreConstruction(binding, facts)


@pytest.fixture
def retained_case(tmp_path, request):
    runtime = ControlledRuntime()
    original = make_case(tmp_path, codex_bootstrap_runtime=runtime)
    original.app.state.provider_service.secret_store.initialize()
    response = original.client.put('/api/v1/providers/codex_peer/config', json={
        'expected_revision': 0, 'adapter': 'official_responses', 'base_url': 'https://127.0.0.1:43871',
        'model': 'synthetic-peer', 'embedding_model': None, 'endpoint_policy': 'explicit_loopback', 'pricing': None,
    }, headers={**original.headers, 'Idempotency-Key': 'peer-config'})
    assert response.status_code == 200
    response = original.client.post('/api/v1/providers/codex_peer/secret',
        json={'expected_revision': 1, 'secret': 'synthetic-codex-peer-value'},
        headers={**original.headers, 'Idempotency-Key': 'peer-secret'})
    assert response.status_code == 200
    config = ProviderConfigView.model_validate(original.client.get('/api/v1/providers/codex_peer/config').json())
    _, _, bootstrap_body = approve(original)
    bootstrap_ack = original.post('sessions', bootstrap_body, 'bootstrap-session')
    assert bootstrap_ack.status_code == 201
    sid = bootstrap_ack.json()['id']
    with original.app.state.database.transaction() as conn:
        identity = author_execution_identity(conn, original.app.state.database.workspace_id(), original.actor_id)
        bootstrap = original.app.state.codex_bootstrap_service.checked_sessions(conn, identity)[sid]
    proof = SyntheticCodexProof.create(registration_id='synthetic_https_memory', config=config,
        bootstrap_sha256=content_sha256(bootstrap), model_versions=['synthetic-peer'], kind='local_exact',
        max_input_tokens=1000000, max_output_tokens=1024, shared_context_tokens=2000000, valid_until=None)
    proofs = ProofRegistry(codex=CodexProofRegistry([proof]))
    def forbidden_transport(*args):
        pytest.fail('memory preparation attempted transport')
    app = create_app(original.app.state.settings, codex_bootstrap_runtime=runtime, codex_proofs=proofs,
        codex_executor=SyntheticCodexExecutor(forbidden_transport))
    client = TestClient(app, base_url=app.state.settings.origin)
    client.cookies.update(original.client.cookies)
    case = Case(app, client, original.headers, original.actor_id)
    values = (case, runtime, sid, proofs, bootstrap_body, bootstrap_ack.content)
    if getattr(request, 'param', False):
        from tests.integration.test_retrieval import publish_small
        from services.api.app.infrastructure.content_repository import reference
        with app.state.database.transaction() as conn:
            actor = author_execution_identity(conn, app.state.database.workspace_id(), case.actor_id)
        blocks, _, _ = publish_small(app.state.database, actor, 'owned-memory-reference', ['Owned exact public reference\n'])
        preparation = case.post(f'sessions/{sid}/turn-preparations', {
            'message': 'Owned reference request', 'context_refs': [reference(blocks[0]).model_dump()],
            'expected_session_revision': 2, 'provider_id': 'codex_peer',
            'tools': {'max_tool_calls': 0, 'wall_seconds': 30}}, 'refs-turn')
        assert preparation.status_code == 202
        proposal = case.post('consent-previews', full_preview_body(preparation.json()), 'refs-preview')
        assert proposal.status_code == 201
        consent = case.post('consents', {'proposal_id': proposal.json()['id'],
            'proposal_sha256': proposal.json()['proposal_sha256']}, 'refs-grant')
        assert consent.status_code == 201
    else:
        _, preparation, _, _, _, consent = grant_fixture(values)
    prep = preparation.json()
    response = case.post(f'sessions/{sid}/turns', {'preparation_id': prep['id'],
        'preparation_sha256': prep['preparation_sha256'], 'consent_id': consent.json()['id'],
        'expected_session_revision': prep['session_revision']}, 'start')
    assert response.status_code == 202
    provider = app.state.codex_turn_worker.provider
    with provider.database.transaction() as conn:
        identity = author_execution_identity(conn, provider.database.workspace_id(), case.actor_id)
    native = load_module('_owned_retained_native', BUNDLE / '_rust_retained_request.py')
    foreign = _ObservedForeign(native._RetainedRequestOwner(Path(os.environ['LW_OWNED_RETAINED_LIBRARY']),
        os.environ['LW_OWNED_RETAINED_LIBRARY_SHA256']))
    resolver = _TestResolver()
    resolver.budget = consent.json()['summary']['budget']
    owner = _RetainedCoreRequestOwner._for_local_test(provider, resolver, foreign)
    try:
        yield case, provider, identity, prep['turn_id'], resolver, foreign, owner
    finally:
        client.close()
        original.client.close()


def test_raw_secret_rotation_during_resolution_rejects_before_genuine_construction(retained_case):
    _, provider, identity, turn_id, resolver, foreign, owner = retained_case
    adapter = _SecretAdapter(provider.secrets)
    provider.secrets = adapter
    resolver.callback = lambda *args: setattr(adapter, 'override', 'synthetic-rotated-secret-value')
    code, memory = None, None
    try:
        request = owner.prepare(identity, turn_id)
        state = request.borrow_state()
        memory = {'encoded_frozen_same': state.encoded_frozen_same, 'auth_sensitive': state.auth_sensitive}
        request.release()
    except ApiError as error:
        code = error.code
    diagnostic = os.environ.get('LW_RETAINED_AUTH_TEST_DIAGNOSTIC')
    if diagnostic:
        Path(diagnostic).write_text(json.dumps({'safe_code': code, 'foreign_create_calls': foreign.calls,
            'actual_memory': memory}) + '\n')
    assert code == 'PROVIDER_SECRET_UNAVAILABLE'
    assert foreign.calls == 0


def test_genuine_memory_uses_real_source_capture_and_does_not_record_start(retained_case, caplog):
    _, provider, identity, turn_id, _, foreign, owner = retained_case
    with provider.database.transaction(immediate=False) as conn:
        state = provider.owned_states(conn, identity.workspace_id)[0][turn_id]
        synthetic_body = provider.prepared_request(state).body
        material = state.proposed.material
        secret = provider.auth_snapshot(conn, identity, state).secret
    request = owner.prepare(identity, turn_id)
    info = request.borrow_state()
    assert info.encoded_frozen_same and info.cloned_body_same and info.auth_sensitive
    body = request._copy_body_for_owned_verification()
    actual = json.loads(body)
    assert body != synthetic_body and secret.encode() not in body
    assert actual['model'] == material.input.provider.model
    assert actual['instructions'] == material.context.messages[0].content
    assert [item['content'][0]['text'] for item in actual['input']] == [m.content for m in material.context.messages[1:]]
    assert actual['max_output_tokens'] == 64 and actual['truncation'] == 'disabled'
    assert foreign.calls == 1
    owner.verify(identity, request)
    with pytest.raises(FrozenInstanceError):
        request._snapshot.secret = 'synthetic-mutation'
    assert secret not in repr(request) and request._snapshot.locator not in repr(request)
    assert secret not in repr(request._snapshot) and secret not in caplog.text
    with provider.database.transaction(immediate=False) as conn:
        current = provider.owned_states(conn, identity.workspace_id)[0][turn_id]
        assert current.started is None and current.finished is None
    request.release()
    with pytest.raises(ApiError, match='CODEX_BINDING_INVALID'):
        request.borrow_state()


def test_secret_locator_revision_changed_inside_resolver_rejects_zero_ffi(retained_case):
    case, provider, identity, turn_id, resolver, foreign, owner = retained_case
    revisions = []
    def rotate(conn, current, material, config):
        service = case.app.state.provider_service
        repo = ProviderRepository(conn, current.workspace_id)
        request = ProviderSecretWrite(expected_revision=config.revision, secret='synthetic-resolver-new-version')
        locator = service.secret_store.put(request.secret)
        cid = command_id()
        value = repo.append_config(config.id, ProviderConfigWrite(expected_revision=config.revision,
            **config.model_dump(exclude={'id', 'revision', 'config_sha256', 'configured', 'secret_present'})),
            cid, locator=locator)
        key, route = 'owned-resolver-rotation', f'POST /providers/{config.id}/secret'
        ack = ProviderSecretAck(id=value.id, revision=value.revision, config_sha256=value.config_sha256, secret_present=True)
        repo.record_command(cid, route, key, {'expected_revision': config.revision, 'operation': 'replace_secret'},
            service._fingerprint(current, route, key, request), ack)
        assert repo.secret_locator(config.id, value.revision) == locator
        revisions.extend([config.revision, value.revision])
    resolver.callback = rotate
    with pytest.raises(ApiError) as caught:
        owner.prepare(identity, turn_id)
    assert caught.value.code == 'CODEX_SOURCE_CHANGED' and foreign.calls == 0
    assert revisions[1] == revisions[0] + 1
    # The owner transaction refused; it did not silently refresh the capture.
    with provider.database.transaction(immediate=False) as conn:
        assert ProviderRepository(conn, identity.workspace_id).config('codex_peer').revision == revisions[0]


@pytest.mark.parametrize('field,value', [
    ('base_url', 'https://example.org/v1'), ('model', 'wrong-model'), ('name', 'wrong-provider'),
    ('message', 'dropped-original-input'), ('maximum', 65), ('timeout_ms', 1), ('response_body_limit_bytes', 1),
    ('session_id', 'wrong-session'), ('turn_id', 'wrong-turn'), ('instructions', 'replacement-instructions'),
])
def test_resolver_source_config_budget_material_changes_reject_zero_ffi(retained_case, field, value):
    _, _, identity, turn_id, resolver, foreign, owner = retained_case
    def mutate(facts):
        if field in {'base_url', 'name'}:
            facts['provider'][field] = value
        elif field == 'model':
            facts['model_info']['slug'] = value
        elif field == 'message':
            facts['prompt']['input'][0]['content'][0]['text'] = value
        elif field == 'instructions':
            facts['prompt']['base_instructions']['text'] = value
        elif field in {'session_id', 'turn_id'}:
            facts['metadata'][field] = value
        else:
            facts[field] = value
    resolver.mutate = mutate
    with pytest.raises(ApiError) as caught:
        owner.prepare(identity, turn_id)
    assert caught.value.code == 'CODEX_BINDING_INVALID' and foreign.calls == 0


def test_caller_dictionary_cannot_become_internal_resolved_owner(retained_case):
    _, _, identity, turn_id, resolver, foreign, owner = retained_case
    resolve = resolver.resolve
    resolver.resolve = lambda *args: {'binding': resolve(*args).binding, 'facts': {}}
    with pytest.raises(ApiError) as caught:
        owner.prepare(identity, turn_id)
    assert caught.value.code == 'CODEX_BINDING_INVALID' and foreign.calls == 0


def test_resolver_wrong_owner_binding_rejects_before_foreign(retained_case):
    _, _, identity, turn_id, resolver, foreign, owner = retained_case
    resolve = resolver.resolve
    def wrong(*args):
        result = resolve(*args)
        return _ResolvedCoreConstruction(replace(result.binding, dispatch_id='wrong-dispatch'), result.facts)
    resolver.resolve = wrong
    with pytest.raises(ApiError) as caught:
        owner.prepare(identity, turn_id)
    assert caught.value.code == 'CODEX_BINDING_INVALID' and foreign.calls == 0


def test_resolver_secret_exception_is_converted_to_static_safe_code(retained_case):
    _, _, identity, turn_id, resolver, foreign, owner = retained_case
    raw = 'synthetic-private-exception-bearer'
    def fail(*args):
        raise RuntimeError(raw)
    resolver.resolve = fail
    with pytest.raises(ApiError) as caught:
        owner.prepare(identity, turn_id)
    assert caught.value.code == 'CODEX_BINDING_INVALID' and raw not in str(caught.value)
    assert caught.value.__suppress_context__ and foreign.calls == 0


def test_live_author_permission_loss_inside_resolver_rejects_zero_ffi(retained_case):
    _, _, identity, turn_id, resolver, foreign, owner = retained_case
    resolver.callback = lambda conn, current, *args: conn.execute(
        "UPDATE local_sessions SET role='learner' WHERE id=?", (current.id,))
    with pytest.raises(ApiError) as caught:
        owner.prepare(identity, turn_id)
    assert caught.value.code in {'POLICY_DENIED', 'SESSION_REQUIRED'} and foreign.calls == 0


def test_raw_secret_change_after_freeze_releases_and_never_refreshes(retained_case):
    _, provider, identity, turn_id, _, foreign, owner = retained_case
    adapter = _SecretAdapter(provider.secrets)
    provider.secrets = adapter
    create, made = foreign.create, []
    def create_then_rotate(*args):
        request = create(*args)
        made.append(request)
        adapter.override = 'synthetic-post-freeze-rotation'
        return request
    foreign.create = create_then_rotate
    with pytest.raises(ApiError) as caught:
        owner.prepare(identity, turn_id)
    assert caught.value.code == 'PROVIDER_SECRET_UNAVAILABLE' and foreign.calls == 1
    with pytest.raises(RuntimeError):
        made[0].borrow_state()
    adapter.override = None
    with pytest.raises(ApiError) as duplicate:
        owner.prepare(identity, turn_id)
    assert duplicate.value.code == 'CODEX_NEW_OUTBOUND_CONSENT_REQUIRED'


def test_default_owner_is_unavailable_without_registered_test_resolver(retained_case):
    _, provider, identity, turn_id, _, foreign, _ = retained_case
    with pytest.raises(ApiError) as caught:
        _RetainedCoreRequestOwner(provider).prepare(identity, turn_id)
    assert caught.value.code == 'CODEX_INPUT_PROOF_UNAVAILABLE' and foreign.calls == 0


@pytest.mark.parametrize('started', [False, True])
def test_live_permission_checked_before_and_after_real_durable_start(retained_case, started):
    case, provider, identity, turn_id, _, _, owner = retained_case
    request = owner.prepare(identity, turn_id)
    try:
        if started:
            with ExitStack() as stack:
                claim = case.app.state.codex_turn_worker._claim(stack)
                assert claim and claim[1] == turn_id
                owner.verify(identity, request)
                # Existing real ledger remains tied to synthetic proposal bytes;
                # this test does not register our different genuine body for send.
                with provider.database.transaction(immediate=False) as conn:
                    state = provider.owned_states(conn, identity.workspace_id)[0][turn_id]
                    assert state.started is not None
                    assert state.started.request_body_sha256 != hashlib.sha256(request._copy_body_for_owned_verification()).hexdigest()
        else:
            owner.verify(identity, request)
        with provider.database.transaction() as conn:
            conn.execute("UPDATE local_sessions SET role='learner' WHERE id=?", (identity.id,))
        with pytest.raises(ApiError) as caught:
            owner.verify(identity, request)
        assert caught.value.code in {'POLICY_DENIED', 'SESSION_REQUIRED'}
    finally:
        request.release()


def test_private_capture_pre_and_post_start_ports_keep_separate_preconditions(retained_case):
    case, provider, identity, turn_id, _, _, _ = retained_case
    with provider.database.transaction() as conn:
        state = provider.owned_states(conn, identity.workspace_id)[0][turn_id]
        snapshot = provider.auth_snapshot(conn, identity, state)
        provider.verify_prepared_auth_snapshot(conn, identity, state, snapshot)
        with pytest.raises(ApiError):
            provider.verify_auth_snapshot(conn, identity, state, snapshot)
    with ExitStack() as stack:
        assert case.app.state.codex_turn_worker._claim(stack)
        with provider.database.transaction() as conn:
            state = provider.owned_states(conn, identity.workspace_id)[0][turn_id]
            provider.verify_auth_snapshot(conn, identity, state, snapshot)
            with pytest.raises(ApiError):
                provider.verify_prepared_auth_snapshot(conn, identity, state, snapshot)


@pytest.mark.parametrize('retained_case', [True], indirect=True)
def test_real_selected_sqlite_reference_refuses_unsupported_conversion(retained_case):
    _, provider, identity, turn_id, resolver, foreign, owner = retained_case
    with provider.database.transaction(immediate=False) as conn:
        material = provider.owned_states(conn, identity.workspace_id)[0][turn_id].proposed.material
        assert material.input.request.context_refs and material.context.evidence
    def forbidden(*args):
        pytest.fail('unsupported reference entered test-only resolver')
    resolver.resolve = forbidden
    with pytest.raises(ApiError) as caught:
        owner.prepare(identity, turn_id)
    assert caught.value.code == 'CODEX_INPUT_PROOF_UNAVAILABLE' and foreign.calls == 0


def test_complete_history_message_projection_is_ordered_and_never_dropped(retained_case):
    # Mechanically tests the pure projection with an explicit complete-history
    # fixture. This does not forge an owned completed SQLite turn or authority.
    _, provider, identity, turn_id, resolver, _, owner = retained_case
    with provider.database.transaction() as conn:
        _, state, material, config, binding = owner._read(conn, identity, turn_id)
        original = material.context.messages
        messages = [original[0], dm.GenerationMessage(role='user', content='Owned previous user α'),
            dm.GenerationMessage(role='assistant', content='Owned previous complete answer'), original[-1]]
        material = material.model_copy(update={'context': material.context.model_copy(update={'messages': messages})})
        facts = resolver.resolve(conn, identity, material, config, binding).facts
        owner._check_construction(facts, material, config, state.proposed.command.ack.summary.budget)
        original_input = facts['prompt']['input'][:]
        for changed in [original_input[2:], list(reversed(original_input))]:
            facts['prompt']['input'] = changed
            with pytest.raises(ApiError) as caught:
                owner._check_construction(facts, material, config, state.proposed.command.ack.summary.budget)
            assert caught.value.code == 'CODEX_BINDING_INVALID'


@pytest.mark.parametrize('started', [False, True])
def test_real_secret_version_rotation_after_capture_refuses_without_refresh(retained_case, started):
    case, provider, identity, turn_id, _, foreign, owner = retained_case
    request = owner.prepare(identity, turn_id)
    snapshot = request._snapshot
    try:
        if started:
            with ExitStack() as stack:
                assert case.app.state.codex_turn_worker._claim(stack)
        response = case.client.post('/api/v1/providers/codex_peer/secret', json={
            'expected_revision': snapshot.provider_revision, 'secret': 'synthetic-owned-next-version'},
            headers={**case.headers, 'Idempotency-Key': 'owned-rotate-after-capture'})
        assert response.status_code == 200
        assert response.json()['revision'] == snapshot.provider_revision + 1
        with pytest.raises(ApiError) as caught:
            owner.verify(identity, request)
        assert caught.value.code == 'CODEX_SOURCE_CHANGED'
        assert request._snapshot is snapshot and foreign.calls == 1
        assert request.borrow_state().encoded_frozen_same
    finally:
        request.release()


def test_safe_error_does_not_echo_resolver_status_or_message(retained_case):
    _, _, identity, turn_id, resolver, foreign, owner = retained_case
    raw = 'synthetic-private-status-text'
    def fail(*args):
        raise ApiError(raw, 'POLICY_DENIED', raw)
    resolver.resolve = fail
    with pytest.raises(ApiError) as caught:
        owner.prepare(identity, turn_id)
    assert caught.value.status == 403 and caught.value.code == 'POLICY_DENIED'
    assert raw not in str(caught.value) and foreign.calls == 0
