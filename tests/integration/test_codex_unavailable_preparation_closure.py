"""Approved seams: real HTTP/SQLite and checked owner ports; no CLI/model/tool."""
from fastapi.testclient import TestClient
import pytest

from packages.contracts.canonical import canonical_bytes
from pydantic import ValidationError
from services.api.app.application.codex_bootstrap_models import BootstrapFreeze
from services.api.app.application.codex_turn_preparation_models import UnavailablePreparationContext
from services.api.app.application.codex_turn_worker import SyntheticCodexExecutor
from services.api.app.application.codex_operation_profile import CodexOperationRegistry
from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.security import author_execution_identity
from services.api.app.infrastructure.provider_transport import ProviderTransport
from services.api.app.infrastructure.codex_probe import LocalCodexProbe
from services.api.app.main import create_app
from services.api.app.serialization import canonical_json, content_sha256
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
def closure_case(tmp_path, request):
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
    case.app.state.closure_bootstrap_body = body
    case.app.state.closure_bootstrap_ack = response.content
    try:
        yield case, runtime, response.json()['id']
    finally:
        case.client.close()
        # Optional private evidence records only named counts; no cookies,
        # messages, SQL, paths, credentials, request/response bodies or IDs.
        import os
        import json
        from pathlib import Path
        target = os.environ.get('LWB_CLOSURE_CASE_RECEIPTS')
        counts = getattr(case.app.state, 'closure_observed_execution_seams', None)
        if target and counts is not None:
            with Path(target).open('a') as stream:
                stream.write(json.dumps({'test': request.node.nodeid, 'counts': counts,
                    'scope': 'new unavailable phase after separately declared synthetic setup',
                    'synthetic_bootstrap_setup_calls': len(runtime.calls)})+'\n')


def owned_material(case, value):
    with case.app.state.database.transaction(immediate=False) as conn:
        identity = author_execution_identity(conn, case.app.state.database.workspace_id(), case.actor_id)
        return case.app.state.codex_turn_service.read_outbound_preparation(conn, identity, value['id'], 1)


def freeze_execution_seams(case, runtime, monkeypatch):
    """Only the new preparation phase is observed; bootstrap setup already ran."""
    calls = {name: 0 for name in ('freeze', 'validity', 'bootstrap', 'process', 'probe',
                                 'secret_read', 'model_executor', 'model_transport', 'tool')}
    def forbidden(name):
        def call(*args, **kwargs):
            calls[name] += 1
            raise AssertionError('Unavailable preparation crossed forbidden '+name+' boundary')
        return call
    for name in ('freeze', 'validity'):
        monkeypatch.setattr(runtime, name, forbidden(name))
    monkeypatch.setattr(runtime, 'execute', forbidden('bootstrap'))
    import subprocess
    monkeypatch.setattr(subprocess, 'Popen', forbidden('process'))
    monkeypatch.setattr(LocalCodexProbe, 'read', forbidden('probe'))
    monkeypatch.setattr(type(case.app.state.provider_service.secret_store), 'read', forbidden('secret_read'))
    monkeypatch.setattr(SyntheticCodexExecutor, 'execute', forbidden('model_executor'))
    monkeypatch.setattr(ProviderTransport, 'stream', forbidden('model_transport'))
    monkeypatch.setattr(CodexOperationRegistry, 'execute', forbidden('tool'))
    case.app.state.closure_observed_execution_seams = calls
    return calls


def prepare(case, sid, key='closure-turn'):
    response = case.post(f'sessions/{sid}/turn-preparations', turn_body(), key)
    assert response.status_code == 202
    return response


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


def test_new_actor_can_read_known_facts_but_cannot_inherit_original_source_authority(closure_case, tmp_path, monkeypatch):
    case, runtime, sid = closure_case
    calls = freeze_execution_seams(case, runtime, monkeypatch)
    original = prepare(case, sid)
    value = original.json()
    other = make_case(tmp_path, codex_bootstrap_runtime=runtime)
    try:
        assert other.actor_id != case.actor_id
        before = case.dump()
        assert other.get('turn-preparations/'+value['id']).json() == value
        assert other.get('turns/'+value['turn_id']).json()['actor_session_id'] == case.actor_id
        response = other.post('consent-previews', preview_body(value), 'new-actor-preview')
        assert response.status_code == 403 and response.json()['error']['code'] == 'POLICY_DENIED'
        assert case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'closure-turn').content == original.content
        assert case.dump() == before
    finally:
        other.client.close()
    assert not any(calls.values())


def test_restart_reads_same_v4_without_current_runtime_secret_or_execution(closure_case, monkeypatch):
    case, runtime, sid = closure_case
    calls = freeze_execution_seams(case, runtime, monkeypatch)
    original = prepare(case, sid)
    value = original.json()
    expected = canonical_bytes(owned_material(case, value).context)
    app = create_app(case.app.state.settings, codex_bootstrap_runtime=runtime)
    # This bounded reader does not enter lifespan or claim background recovery.
    client = TestClient(app, base_url=app.state.settings.origin)
    client.cookies.update(case.client.cookies)
    try:
        before = case.dump()
        assert client.get('/api/v1/codex/turn-preparations/'+value['id']).json() == value
        with app.state.database.transaction(immediate=False) as conn:
            identity = author_execution_identity(conn, app.state.database.workspace_id(), case.actor_id)
            actual = app.state.codex_turn_service.read_outbound_preparation(conn, identity, value['id'], 1)
        assert canonical_bytes(actual.context) == expected
        assert app.state.codex_turn_worker.executor is None
        assert case.dump() == before
    finally:
        client.close()
    assert not any(calls.values())


@pytest.mark.parametrize('bad', ['true', 'zero', 'float_zero', 'missing_item', 'duplicate_item',
                               'unknown_item', 'extra', 'provider', 'bootstrap_digest'])
def test_v4_private_contract_rejects_false_aliases_unknown_qualifications_and_bad_binding(closure_case, bad):
    case, _, sid = closure_case
    value = prepare(case, sid).json()
    data = owned_material(case, value).context.model_dump(mode='json')
    if bad in {'true', 'zero', 'float_zero'}:
        data['closure']['implemented'] = {'true': True, 'zero': 0, 'float_zero': 0.0}[bad]
    elif bad == 'missing_item':
        data['closure']['missing'].pop()
    elif bad == 'duplicate_item':
        data['closure']['missing'][1] = data['closure']['missing'][0]
    elif bad == 'unknown_item':
        data['closure']['missing'][0] = 'manual_trusted_proof'
    elif bad == 'extra':
        data['closure']['final_model_request_sha256'] = '0'*64
    elif bad == 'provider':
        data['closure']['provider']['model'] = 'borrowed-model'
    else:
        data['closure']['bootstrap_sha256'] = '0'*64
    with pytest.raises(ValidationError):
        UnavailablePreparationContext.model_validate(data)


@pytest.mark.parametrize('damage', ['closure', 'bootstrap_copy', 'context', 'provider_original',
                                  'bootstrap_member', 'turn_member', 'turn_tail'])
def test_damaged_known_originals_fail_closed_without_get_repair_or_command_replay(closure_case, damage, monkeypatch):
    import json
    case, runtime, sid = closure_case
    calls = freeze_execution_seams(case, runtime, monkeypatch)
    value = prepare(case, sid).json()
    with case.app.state.database.transaction() as conn:
        if damage in {'closure', 'bootstrap_copy', 'context'}:
            row = conn.execute('SELECT envelope_json FROM context_snapshots WHERE id=?',
                (value['summary']['context_snapshot_id'],)).fetchone()
            data = json.loads(row[0])
            if damage == 'closure':
                data['closure']['implemented'] = 0
            elif damage == 'bootstrap_copy':
                data['closure']['bootstrap']['finished']['outcome']['thread_id'] = 'borrowed-thread'
                data['closure']['bootstrap_sha256'] = content_sha256(data['closure']['bootstrap'])
            else:
                data['messages'][-1]['content'] = 'changed-original-task'
            conn.execute('UPDATE context_snapshots SET envelope_json=? WHERE id=?',
                (canonical_json(data), value['summary']['context_snapshot_id']))
        elif damage == 'provider_original':
            conn.execute('DROP TRIGGER provider_config_history_no_update')
            conn.execute("UPDATE provider_config_history SET config_json='{}' WHERE provider_id='codex_local'")
        else:
            table = {'bootstrap_member': 'codex_bootstrap_session_memberships', 'turn_member': 'codex_turn_event_members',
                     'turn_tail': 'codex_turn_events'}[damage]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (table,)):
                conn.execute('DROP TRIGGER '+row[0])
            conn.execute('DELETE FROM '+table)
    before = case.dump()
    for path in ['turn-preparations/'+value['id'], 'turns/'+value['turn_id'], 'sessions/'+sid]:
        response = case.get(path)
        assert response.status_code == 409
    assert case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'closure-turn').status_code == 409
    assert case.post('consent-previews', preview_body(value), 'damaged-preview').status_code == 409
    assert case.dump() == before and not any(calls.values())


@pytest.mark.parametrize('phase', ['context', 'run', 'command'])
def test_prepare_rolls_back_entire_known_material_and_original_slot(closure_case, phase, monkeypatch):
    case, runtime, sid = closure_case
    calls = freeze_execution_seams(case, runtime, monkeypatch)
    table = {'context': 'context_snapshots', 'run': 'runs', 'command': 'codex_turn_commands'}[phase]
    with case.app.state.database.transaction() as conn:
        conn.execute('CREATE TRIGGER unavailable_fixture_failure BEFORE INSERT ON '+table+
            " BEGIN SELECT RAISE(ABORT,'controlled unavailable preparation rollback'); END;")
    before = case.dump()
    response = case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'rollback-'+phase)
    assert response.status_code == 500 and response.json()['error']['code'] == 'INTERNAL_ERROR'
    assert case.dump() == before
    assert case.get('sessions/'+sid).json()['revision'] == 2
    assert not any(calls.values())


@pytest.mark.parametrize('change', ['config', 'secret'])
def test_provider_current_advance_changes_qualification_not_original_known_facts_or_ack(closure_case, change, monkeypatch):
    case, runtime, sid = closure_case
    calls = freeze_execution_seams(case, runtime, monkeypatch)
    original = prepare(case, sid)
    value = original.json()
    frozen = canonical_bytes(owned_material(case, value).context)
    if change == 'config':
        response = case.client.put('/api/v1/providers/codex_local/config', json={
            'expected_revision': 1, 'adapter': 'compatible_chat', 'base_url': 'https://example.invalid',
            'model': 'changed-unregistered-model', 'embedding_model': None, 'endpoint_policy': 'public_https', 'pricing': None,
        }, headers={**case.headers, 'Idempotency-Key': 'config-advance'})
    else:
        response = case.client.post('/api/v1/providers/codex_local/secret', json={
            'expected_revision': 1, 'secret': 'synthetic-not-a-model-credential'},
            headers={**case.headers, 'Idempotency-Key': 'secret-advance'})
    assert response.status_code == 200
    before = case.dump()
    read = case.get('turn-preparations/'+value['id'])
    assert read.status_code == 200 and read.json()['validity'] == 'changed'
    assert read.json()['summary'] == value['summary']
    assert case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'closure-turn').content == original.content
    with case.app.state.database.transaction(immediate=False) as conn:
        source = case.app.state.codex_turn_service.owned_outbound_sources(conn, case.app.state.database.workspace_id())
        assert canonical_bytes(source[value['turn_id']].material.context) == frozen
    assert case.dump() == before and not any(calls.values())


def test_learner_reads_safe_control_but_not_private_preparation_and_cannot_change_source(closure_case, monkeypatch):
    case, runtime, sid = closure_case
    calls = freeze_execution_seams(case, runtime, monkeypatch)
    value = prepare(case, sid).json()
    assert case.client.post('/api/v1/session/role', json={'role': 'learner'},
        headers={**case.headers, 'Idempotency-Key': 'closure-learner'}).status_code == 200
    before = case.dump()
    assert case.get('turn-preparations/'+value['id']).status_code == 403
    control = case.get('turns/'+value['turn_id'])
    assert control.status_code == 200
    assert 'closure' not in control.text and 'synthetic-thread' not in control.text
    assert case.post('consent-previews', preview_body(value), 'learner-preview').status_code == 403
    with case.app.state.database.transaction(immediate=False) as conn:
        with pytest.raises(ApiError):
            author_execution_identity(conn, case.app.state.database.workspace_id(), case.actor_id)
    assert case.dump() == before and not any(calls.values())


def completed_pair_setup(case, runtime, sid, large):
    """Two explicit memory protocol-peer calls in setup, never production proof."""
    from services.api.app.application.provider_budget import ProofRegistry
    from services.api.app.application.provider_codex_profile import CodexProofRegistry, SyntheticCodexProof
    from services.api.app.provider_dto import ProviderConfigView
    from tests.integration.test_codex_turn_dispatch_http import make_dispatch_case, start_body
    from tests.integration.test_codex_turn_consent_http import full_preview_body
    response = case.client.put('/api/v1/providers/codex_peer/config', json={
        'expected_revision': 0, 'adapter': 'official_responses', 'base_url': 'http://127.0.0.1:43871',
        'model': 'synthetic-peer', 'embedding_model': None, 'endpoint_policy': 'explicit_loopback', 'pricing': None,
    }, headers={**case.headers, 'Idempotency-Key': 'peer-config'})
    assert response.status_code == 200
    assert case.client.post('/api/v1/providers/codex_peer/secret', json={
        'expected_revision': 1, 'secret': 'synthetic-memory-peer-only'},
        headers={**case.headers, 'Idempotency-Key': 'peer-secret'}).status_code == 200
    config = ProviderConfigView.model_validate(case.client.get('/api/v1/providers/codex_peer/config').json())
    with case.app.state.database.transaction(immediate=False) as conn:
        identity = author_execution_identity(conn, case.app.state.database.workspace_id(), case.actor_id)
        original = case.app.state.codex_bootstrap_service.checked_sessions(conn, identity)[sid]
    proof = SyntheticCodexProof.create(registration_id='synthetic_closure_history_setup', config=config,
        bootstrap_sha256=content_sha256(original), model_versions=['synthetic-peer'], kind='local_exact',
        max_input_tokens=1000000, max_output_tokens=1024, shared_context_tokens=2000000, valid_until=None)
    factory = make_dispatch_case((case, runtime, sid, ProofRegistry(codex=CodexProofRegistry([proof])), None, b''))
    peer, _, _, _, _, _ = next(factory)
    expected = []
    try:
        for number in range(2):
            message = (str(number)*7000) if large else 'Completed memory peer task '+str(number)
            body = {'message': message, 'context_refs': [], 'expected_session_revision': 2+3*number,
                    'provider_id': 'codex_peer', 'tools': {'max_tool_calls': 0, 'wall_seconds': 30}}
            preparation = peer.post(f'sessions/{sid}/turn-preparations', body, 'history-prepare-'+str(number))
            assert preparation.status_code == 202
            value = preparation.json()
            proposal = peer.post('consent-previews', full_preview_body(value), 'history-preview-'+str(number))
            assert proposal.status_code == 201
            consent = peer.post('consents', {'proposal_id': proposal.json()['id'],
                'proposal_sha256': proposal.json()['proposal_sha256']}, 'history-grant-'+str(number))
            assert consent.status_code == 201
            assert peer.post(f'sessions/{sid}/turns', start_body(value, consent.json()),
                'history-start-'+str(number)).status_code == 202
            assert peer.app.state.codex_turn_worker.run_once() is True
            assert peer.get('turns/'+value['turn_id']).json()['outcome'] == 'completed'
            with peer.app.state.database.transaction(immediate=False) as conn:
                owner = peer.app.state.codex_turn_service.outbound_owner
                states, _ = owner.owned_states(conn, peer.app.state.database.workspace_id())
                receipt = states[value['turn_id']].finished
            expected.append((value['turn_id'], message, receipt.answer))
        assert len(peer.app.state.synthetic_transport_calls) == 2
        return expected
    finally:
        factory.close()


@pytest.mark.parametrize('large', [False, True])
def test_default_v4_keeps_verified_complete_pairs_or_omits_whole_pairs_without_new_execution(closure_case, large, monkeypatch):
    case, runtime, sid = closure_case
    expected = completed_pair_setup(case, runtime, sid, large)
    calls = freeze_execution_seams(case, runtime, monkeypatch)
    body = turn_body(8)
    response = case.post(f'sessions/{sid}/turn-preparations', body, 'after-history')
    assert response.status_code == 202
    value = response.json()
    material = owned_material(case, value)
    context = material.context
    assert context.version == 'codex-turn-context-v4'
    retained = [expected[-1]] if large else expected
    omitted = expected[:1] if large else []
    assert [(item.turn_id, item.user, item.answer) for item in context.history] == retained
    assert [(item.turn_id, item.user, item.answer) for item in context.omitted_history] == omitted
    assert value['summary']['history_turn_ids'] == [item[0] for item in retained]
    assert context.input.version == 'codex-turn-input-v1' and context.input.runtime.implemented is False
    assert case.app.state.codex_turn_worker.executor is None
    before = case.dump()
    assert case.get('turn-preparations/'+value['id']).json() == value
    assert case.post(f'sessions/{sid}/turn-preparations', body, 'after-history').content == response.content
    assert case.post('sessions', case.app.state.closure_bootstrap_body, 'closure-session').content == case.app.state.closure_bootstrap_ack
    refused = case.post('consent-previews', preview_body(value), 'history-refuse')
    assert refused.status_code == 503 and refused.json()['error']['code'] == 'CODEX_INPUT_PROOF_UNAVAILABLE'
    assert case.dump() == before and not any(calls.values())


@pytest.mark.parametrize('with_history', [False, True])
def test_explicit_legacy_context_factory_and_original_decoder_bytes_remain_readable(closure_case, with_history):
    """New codec fixture via unchanged legacy factory, never rewriting old facts."""
    from services.api.app.application.codex_turn_context import CodexTurnContext
    from services.api.app.application.codex_turn_execution_models import CodexCompletedHistory
    case, _, sid = closure_case
    value = prepare(case, sid).json()
    material = owned_material(case, value)
    legacy = CodexTurnContext(case.app.state.database)
    # These are declared manual codec test data, not a claimed Provider receipt.
    history = [CodexCompletedHistory(turn_id='legacy_codec_pair', user='Prior user', answer='Prior answer',
        receipt_sha256='a'*64, output_sha256=None)] if with_history else []
    with case.app.state.database.transaction() as conn:
        identity = author_execution_identity(conn, case.app.state.database.workspace_id(), case.actor_id)
        context = legacy.prepare_turn(conn, identity, material.input, '2026-10-01T00:00:00Z', history)
        summary = legacy.summary(context)
    expected_version = 'codex-turn-context-v3' if with_history else 'codex-turn-context-v1'
    assert context.version == expected_version
    expected = canonical_bytes(context)
    before = case.dump()
    with case.app.state.database.transaction(immediate=False) as conn:
        identity = author_execution_identity(conn, case.app.state.database.workspace_id(), case.actor_id)
        assert canonical_bytes(legacy.verify_turn(conn, identity, material.input, summary)) == expected
    assert case.dump() == before


def test_unavailable_context_full_reference_source_survives_metadata_advance_as_original_fact(closure_case, monkeypatch):
    from tests.integration.test_codex_turn_preparation_http import identity
    from tests.integration.test_retrieval import publish_small
    from services.api.app.infrastructure.content_repository import reference
    from services.api.app.application.content import ContentService
    case, runtime, sid = closure_case
    blocks, _, _ = publish_small(case.app.state.database, identity(case), 'known-v4-source', ['Exact public source α\n'])
    calls = freeze_execution_seams(case, runtime, monkeypatch)
    body = {**turn_body(), 'context_refs': [reference(blocks[0]).model_dump()]}
    response = case.post(f'sessions/{sid}/turn-preparations', body, 'v4-source')
    assert response.status_code == 202
    value = response.json()
    context = owned_material(case, value).context
    assert context.evidence[0].text == 'Exact public source α\n'
    original = canonical_bytes(context)
    changed = blocks[0].model_copy(update={'revision': 2, 'title': 'Later public metadata'})
    ContentService(case.app.state.database).publish(identity(case).workspace_id, [changed], {changed.body_path: b'Exact public source \xce\xb1\n'})
    before = case.dump()
    read = case.get('turn-preparations/'+value['id'])
    assert read.status_code == 200 and read.json()['validity'] == 'changed'
    assert read.json()['summary'] == value['summary']
    assert case.post(f'sessions/{sid}/turn-preparations', body, 'v4-source').content == response.content
    with case.app.state.database.transaction(immediate=False) as conn:
        sources = case.app.state.codex_turn_service.owned_outbound_sources(conn, case.app.state.database.workspace_id())
        assert canonical_bytes(sources[value['turn_id']].material.context) == original
    assert case.dump() == before and not any(calls.values())
