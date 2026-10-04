"""Real Provider/Codex local consent seams; never an external model request."""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest

from services.api.app.application.provider_budget import ProofRegistry
from services.api.app.application.provider_codex_profile import CodexProofRegistry, SyntheticCodexProof
from services.api.app.infrastructure.security import author_execution_identity
from services.api.app.main import create_app
from services.api.app.provider_dto import ProviderConfigView
from services.api.app.serialization import content_sha256
from tests.integration.test_codex_bootstrap_http import Case, ControlledRuntime, approve, make_case
from tests.integration.test_codex_turn_preparation_http import prepared, turn_case
from tests.integration.test_assessment_learning_port import assessment_learning_state

assessment_state = assessment_learning_state

__all__ = ['turn_case']


def preview_body(value, provider_revision=1):
    return {'preparation_id': value['id'], 'preparation_sha256': value['preparation_sha256'],
        'expected_job_revision': 1, 'expected_provider_revision': provider_revision,
        'budget': {'max_input_tokens': 4096, 'max_output_tokens': 64, 'max_provider_calls': 1,
                   'max_search_calls': 0, 'max_cost_usd': None},
        'expires_at': (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat().replace('+00:00', 'Z')}


def test_unregistered_codex_complete_input_proof_refuses_real_preview_without_mutation(turn_case, monkeypatch):
    case, runtime, _, _, _ = turn_case
    value = prepared(turn_case).json()
    def forbidden(*args, **kwargs):
        raise AssertionError('local preview attempted bootstrap or external execution')
    monkeypatch.setattr(runtime, 'execute', forbidden)
    before = case.dump()
    response = case.post('consent-previews', preview_body(value), 'preview-original')
    assert response.status_code == 503
    assert response.json()['error']['code'] == 'CODEX_INPUT_PROOF_UNAVAILABLE'
    assert case.dump() == before
    assert case.get('turn-preparations/' + value['id']).json() == value


@pytest.fixture
def consent_case(tmp_path):
    yield from make_consent_case(tmp_path)


def make_consent_case(tmp_path):
    """Explicit trusted synthetic profile; all product records use actual owners."""
    runtime = ControlledRuntime()
    original = make_case(tmp_path, codex_bootstrap_runtime=runtime)
    original.app.state.provider_service.secret_store.initialize()
    response = original.client.put('/api/v1/providers/codex_peer/config', json={
        'expected_revision': 0, 'adapter': 'official_responses', 'base_url': 'http://127.0.0.1:43871',
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
    with original.app.state.database.transaction(immediate=False) as conn:
        identity = author_execution_identity(conn, original.app.state.database.workspace_id(), original.actor_id)
        bootstrap = original.app.state.codex_bootstrap_service.checked_sessions(conn, identity)[sid]
    proof = SyntheticCodexProof.create(registration_id='synthetic_http_peer', config=config,
        bootstrap_sha256=content_sha256(bootstrap), model_versions=['synthetic-peer'], kind='local_exact',
        max_input_tokens=1000000, max_output_tokens=1024, shared_context_tokens=2000000, valid_until=None)
    proofs = ProofRegistry(codex=CodexProofRegistry([proof]))
    app = create_app(original.app.state.settings, codex_bootstrap_runtime=runtime, codex_proofs=proofs)
    client = TestClient(app, base_url=app.state.settings.origin)
    client.cookies.update(original.client.cookies)
    case = Case(app, client, original.headers, original.actor_id)
    try:
        yield case, runtime, sid, proofs, bootstrap_body, bootstrap_ack.content
    finally:
        client.close()
        original.client.close()


def consent_preparation(case, sid, revision=2, key='turn'):
    body = {'message': 'Synthetic exact Unicode α\nOnly an explicit request.', 'context_refs': [],
        'expected_session_revision': revision, 'provider_id': 'codex_peer',
        'tools': {'max_tool_calls': 0, 'wall_seconds': 30}}
    response = case.post(f'sessions/{sid}/turn-preparations', body, key)
    assert response.status_code == 202
    assert response.json()['validity'] == 'current'
    return body, response


def full_preview_body(preparation):
    body = preview_body(preparation, 2)
    body['budget']['max_input_tokens'] = 1000000
    return body


def test_real_preview_grant_safe_revoke_original_acks_and_current_get(consent_case, monkeypatch):
    case, runtime, sid, _, bootstrap_body, bootstrap_ack = consent_case
    def forbidden(*args, **kwargs):
        pytest.fail('preview/grant/revoke attempted execution')
    monkeypatch.setattr(runtime, 'execute', forbidden)
    body, prepared_ack = consent_preparation(case, sid)
    preparation = prepared_ack.json()
    preview = full_preview_body(preparation)
    proposal_ack = case.post('consent-previews', preview, 'preview-original')
    assert proposal_ack.status_code == 201
    proposal = proposal_ack.json()
    assert proposal['summary']['adapter'] == 'codex_app_server'
    assert proposal['summary']['input_token_assurance']['kind'] == 'local_exact'
    grant = {'proposal_id': proposal['id'], 'proposal_sha256': proposal['proposal_sha256']}
    grant_ack = case.post('consents', grant, 'grant-original')
    assert grant_ack.status_code == 201
    consent = grant_ack.json()
    before = case.dump()
    assert case.get('consent-proposals/' + proposal['id']).json()['consent_id'] == consent['id']
    assert case.get('consents/' + consent['id']).json()['dispatch'] is None
    current = case.get('turn-preparations/' + preparation['id']).json()
    assert (current['proposal_id'], current['consent_id']) == (proposal['id'], consent['id'])
    assert current['preparation_sha256'] == preparation['preparation_sha256']
    control = case.get('turns/' + preparation['turn_id']).json()
    assert control['consent_control'] == {'id': consent['id'], 'revision': 1, 'status': 'active'}
    assert case.get('sessions/' + sid).json()['revision'] == 3 and case.dump() == before
    assert case.client.post('/api/v1/session/role', json={'role': 'learner'},
        headers={**case.headers, 'Idempotency-Key': 'learner'}).status_code == 200
    before = case.dump()
    assert case.get('consent-proposals/' + proposal['id']).status_code == 403
    assert case.get('consents/' + consent['id']).status_code == 403
    assert case.get('turns/' + preparation['turn_id']).json()['consent_control']['revision'] == 1
    assert case.dump() == before
    revoked = case.post('consents/' + consent['id'] + '/revoke', {'expected_revision': 1}, 'revoke-original')
    assert revoked.status_code == 200 and revoked.json() == {'id': consent['id'], 'revision': 2, 'applied': True}
    assert case.get('turns/' + preparation['turn_id']).json()['consent_control']['status'] == 'revoked'
    assert case.client.post('/api/v1/session/role', json={'role': 'author'},
        headers={**case.headers, 'Idempotency-Key': 'author-again'}).status_code == 200
    before = case.dump()
    assert case.post(f'sessions/{sid}/turn-preparations', body, 'turn').content == prepared_ack.content
    assert case.post('consent-previews', preview, 'preview-original').content == proposal_ack.content
    assert case.post('consents', grant, 'grant-original').content == grant_ack.content
    assert case.post('consents/' + consent['id'] + '/revoke', {'expected_revision': 1}, 'revoke-original').content == revoked.content
    assert case.post('sessions', bootstrap_body, 'bootstrap-session').content == bootstrap_ack
    assert case.dump() == before and len(runtime.calls) == 1


def grant_fixture(consent_case):
    case, _, sid, _, _, _ = consent_case
    body, preparation = consent_preparation(case, sid)
    preview = full_preview_body(preparation.json())
    proposal = case.post('consent-previews', preview, 'preview')
    assert proposal.status_code == 201
    grant = {'proposal_id': proposal.json()['id'], 'proposal_sha256': proposal.json()['proposal_sha256']}
    consent = case.post('consents', grant, 'grant')
    assert consent.status_code == 201
    return body, preparation, preview, proposal, grant, consent


@pytest.mark.parametrize('variant,status', [('job_cas', 412), ('provider_cas', 412), ('preparation_sha', 409),
    ('input_budget', 409), ('output_budget', 409), ('expired', 422), ('too_long', 422), ('unknown_field', 422)])
def test_preview_admission_rejects_without_any_partial_record(consent_case, variant, status):
    case, _, sid, _, _, _ = consent_case
    _, value = consent_preparation(case, sid)
    body = full_preview_body(value.json())
    if variant == 'job_cas':
        body['expected_job_revision'] = 2
    elif variant == 'provider_cas':
        body['expected_provider_revision'] = 1
    elif variant == 'preparation_sha':
        body['preparation_sha256'] = '0' * 64
    elif variant == 'input_budget':
        body['budget']['max_input_tokens'] = 1
    elif variant == 'output_budget':
        body['budget']['max_output_tokens'] = 1025
    elif variant in {'expired', 'too_long'}:
        body['expires_at'] = (datetime.now(timezone.utc) + timedelta(minutes=-1 if variant == 'expired' else 11)).isoformat()
    else:
        body['proof'] = 'untrusted-http-proof'
    before = case.dump()
    result = case.post('consent-previews', body, 'invalid-preview')
    assert result.status_code == status
    assert case.dump() == before


def test_immutable_full_key_body_one_proposal_one_grant_and_strong_cas(consent_case):
    case, _, _, _, _, _ = consent_case
    _, preparation, preview, proposal, grant, consent = grant_fixture(consent_case)
    before = case.dump()
    for body, key in [(preview, 'other-preview'), ({**preview, 'expected_job_revision': 2}, 'preview')]:
        assert case.post('consent-previews', body, key).status_code == 409
    assert case.post('consents', grant, 'other-grant').status_code == 409
    assert case.post('consents', {**grant, 'proposal_sha256': '0' * 64}, 'grant').status_code == 409
    assert case.post('consents', {**grant, 'proposal_sha256': '0' * 64}, 'fresh-bad-grant').status_code == 412
    assert case.post('consents/' + consent.json()['id'] + '/revoke', {'expected_revision': 2}, 'bad-cas').status_code == 412
    assert case.dump() == before
    assert case.get('turns/' + preparation.json()['turn_id']).json()['consent_control']['id'] == consent.json()['id']
    assert case.get('consent-proposals/' + proposal.json()['id']).json()['consent_id'] == consent.json()['id']


@pytest.mark.parametrize('table,mutation', [('heads', 'all'), ('events', 'tail'), ('members', 'tail'),
    ('commands', 'tail'), ('commands', 'key'), ('events', 'hash'), ('family', 'all')])
def test_complete_owner_history_loss_or_tampering_blocks_reads_and_original_ack(consent_case, table, mutation):
    case, _, sid, _, _, _ = consent_case
    _, preparation, preview, proposal, grant, consent = grant_fixture(consent_case)
    with case.app.state.database.transaction() as conn:
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name LIKE 'provider_codex_%'").fetchall():
            conn.execute('DROP TRIGGER ' + row[0])
        if table == 'family':
            for name in ['heads', 'events', 'members', 'commands']:
                conn.execute('DELETE FROM provider_codex_' + name)
        elif mutation == 'all':
            conn.execute('DELETE FROM provider_codex_' + table)
        elif mutation == 'tail':
            conn.execute('DELETE FROM provider_codex_' + table + ' WHERE seq=2')
        elif mutation == 'key':
            conn.execute("UPDATE provider_codex_commands SET command_key='damaged-command' WHERE seq=2")
        else:
            conn.execute("UPDATE provider_codex_events SET record_sha256=? WHERE seq=2", ('0' * 64,))
    before = case.dump()
    for path in ['consent-proposals/' + proposal.json()['id'], 'consents/' + consent.json()['id'],
        'turn-preparations/' + preparation.json()['id'], 'turns/' + preparation.json()['turn_id'], 'sessions/' + sid]:
        result = case.get(path)
        assert result.status_code == 409 and result.json()['error']['code'] == 'CODEX_HISTORY_DAMAGED'
    assert case.post('consent-previews', preview, 'preview').status_code == 409
    assert case.post('consents', grant, 'grant').status_code == 409
    assert case.dump() == before


@pytest.mark.parametrize('operation', ['preview', 'grant', 'revoke'])
def test_provider_and_codex_witness_commit_atomically(consent_case, operation):
    case, _, sid, _, _, _ = consent_case
    _, prep = consent_preparation(case, sid)
    path, body, key = 'consent-previews', full_preview_body(prep.json()), 'preview'
    if operation in {'grant', 'revoke'}:
        proposal = case.post(path, body, key)
        assert proposal.status_code == 201
        path, body, key = 'consents', {'proposal_id': proposal.json()['id'], 'proposal_sha256': proposal.json()['proposal_sha256']}, 'grant'
    if operation == 'revoke':
        consent = case.post(path, body, key)
        assert consent.status_code == 201
        path, body, key = 'consents/' + consent.json()['id'] + '/revoke', {'expected_revision': 1}, 'revoke'
    with case.app.state.database.transaction() as conn:
        conn.execute("CREATE TRIGGER paired_owner_failure BEFORE INSERT ON codex_turn_events BEGIN SELECT RAISE(ABORT,'synthetic paired rollback'); END;")
    before = case.dump()
    assert case.post(path, body, key).status_code == 500
    assert case.dump() == before


def test_current_expiry_and_proof_withdrawal_do_not_rewrite_original_ack(consent_case, monkeypatch):
    from services.api.app.application import provider_codex_consents
    case, runtime, sid, proofs, _, _ = consent_case
    _, prep, preview, proposal, grant, consent = grant_fixture(consent_case)
    before = case.dump()
    monkeypatch.setattr(provider_codex_consents, 'utc_now', lambda: proposal.json()['summary']['expires_at'])
    assert case.get('consent-proposals/' + proposal.json()['id']).json()['validity'] == 'expired'
    assert case.get('consents/' + consent.json()['id']).json()['status'] == 'expired'
    assert case.get('turns/' + prep.json()['turn_id']).json()['consent_control']['status'] == 'expired'
    assert case.post('consent-previews', preview, 'preview').content == proposal.content
    assert case.post('consents', grant, 'grant').content == consent.content
    assert case.dump() == before
    monkeypatch.undo()
    restarted = create_app(case.app.state.settings, codex_bootstrap_runtime=runtime, codex_proofs=ProofRegistry())
    client = TestClient(restarted, base_url=restarted.state.settings.origin)
    try:
        client.cookies.update(case.client.cookies)
        other = Case(restarted, client, case.headers, case.actor_id)
        assert other.get('consent-proposals/' + proposal.json()['id']).json()['validity'] == 'unavailable'
        assert other.get('turn-preparations/' + prep.json()['id']).json()['validity'] == 'unavailable'
        assert other.post('consents', grant, 'grant').content == consent.content
        assert other.get('sessions/' + sid).json()['revision'] == 3
        assert other.dump() == before
    finally:
        client.close()
    assert proofs.codex is not None and len(runtime.calls) == 1


def test_concurrent_same_key_preview_and_grant_create_only_original_facts(consent_case):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    case, _, sid, _, _, _ = consent_case
    _, prep = consent_preparation(case, sid)
    for path, body in [('consent-previews', full_preview_body(prep.json()))]:
        barrier = Barrier(2)
        def preview_request(_):
            barrier.wait()
            return case.post(path, body, 'same-preview')
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(preview_request, range(2)))
        assert [result.status_code for result in results] == [201, 201]
        assert results[0].content == results[1].content
        proposal = results[0].json()
    barrier = Barrier(2)
    def grant_request(_):
        barrier.wait()
        return case.post('consents', {'proposal_id': proposal['id'], 'proposal_sha256': proposal['proposal_sha256']}, 'same-grant')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(grant_request, range(2)))
    assert [result.status_code for result in results] == [201, 201]
    assert results[0].content == results[1].content
    with case.app.state.database.transaction(immediate=False) as conn:
        assert conn.execute('SELECT COUNT(*) FROM provider_codex_events').fetchone()[0] == 2
    assert case.get('sessions/' + sid).json()['revision'] == 3


def test_new_actor_can_revoke_but_cannot_take_original_grant_or_preview(consent_case, tmp_path):
    case, runtime, sid, _, _, _ = consent_case
    _, preparation = consent_preparation(case, sid)
    preview = full_preview_body(preparation.json())
    other = make_case(tmp_path, codex_bootstrap_runtime=runtime)
    try:
        before = case.dump()
        assert other.post('consent-previews', preview, 'takeover-preview').status_code == 403
        assert case.dump() == before
        proposal = case.post('consent-previews', preview, 'preview')
        assert proposal.status_code == 201
        grant = {'proposal_id': proposal.json()['id'], 'proposal_sha256': proposal.json()['proposal_sha256']}
        before = case.dump()
        assert other.post('consents', grant, 'takeover-grant').status_code == 403
        assert case.dump() == before
        consent = case.post('consents', grant, 'grant')
        assert consent.status_code == 201
        assert other.client.post('/api/v1/session/role', json={'role': 'learner'},
            headers={**other.headers, 'Idempotency-Key': 'other-learner'}).status_code == 200
        control = other.get('turns/' + preparation.json()['turn_id']).json()
        assert control['actor_session_id'] == case.actor_id
        assert control['consent_control']['id'] == consent.json()['id']
        revoked = other.post('consents/' + consent.json()['id'] + '/revoke', {'expected_revision': 1}, 'safe-revoke')
        assert revoked.status_code == 200
        assert case.get('consents/' + consent.json()['id']).json()['actor_session_id'] == case.actor_id
    finally:
        other.client.close()


@pytest.mark.parametrize('path_kind,change,expected', [('proposal', 'learner', 403), ('consent', 'learner', 403),
    ('proposal', 'logout', 401), ('consent', 'workspace', 401)])
def test_subject_delivery_rechecks_new_transaction_after_concurrent_access_loss(consent_case, monkeypatch, path_kind, change, expected):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event
    case, _, _, _, _, _ = consent_case
    _, _, _, proposal, _, consent = grant_fixture(consent_case)
    owner = case.app.state.codex_turn_service.outbound_owner
    actual = owner._states
    entered, release = Event(), Event()
    def held(*args):
        result = actual(*args)
        entered.set()
        assert release.wait(10)
        return result
    monkeypatch.setattr(owner, '_states', held)
    path = 'consent-proposals/' + proposal.json()['id'] if path_kind == 'proposal' else 'consents/' + consent.json()['id']
    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(case.get, path)
        try:
            assert entered.wait(10)
            if change == 'learner':
                assert case.client.post('/api/v1/session/role', json={'role': 'learner'},
                    headers={**case.headers, 'Idempotency-Key': 'delivery-learner'}).status_code == 200
            else:
                with case.app.state.database.transaction() as conn:
                    if change == 'logout':
                        conn.execute("UPDATE local_sessions SET revoked_at='2026-01-01T00:00:00Z' WHERE id=?", (case.actor_id,))
                    else:
                        conn.execute("INSERT INTO workspace(id,title,created_at) VALUES('other_workspace','Synthetic','2026-01-01T00:00:00Z')")
                        conn.execute("UPDATE local_sessions SET workspace_id='other_workspace' WHERE id=?", (case.actor_id,))
            before = case.dump()
        finally:
            release.set()
        response = future.result(timeout=10)
    assert response.status_code == expected
    assert 'summary' not in response.json() and case.dump() == before


@pytest.mark.parametrize('mode', ['independent', 'open_book'])
def test_assessment_policy_blocks_subject_and_grant_but_keeps_revoke(assessment_state, mode):
    from tests.integration.test_assessment_policy import start
    from tests.integration.test_codex_turn_preparation_http import identity, cancel
    from services.api.app.application.errors import ApiError
    database, _, fixture, assessment = assessment_state
    for values in make_consent_case(database.settings.data_dir):
        case, _, sid, _, _, _ = values
        _, preparation, preview, proposal, grant, consent = grant_fixture(values)
        owner_state = database, identity(case), fixture, assessment
        if mode == 'independent':
            before = case.dump()
            with pytest.raises(ApiError) as refused:
                start(owner_state, mode=mode)
            assert refused.value.code == 'SUBJECT_WORK_ACTIVE' and case.dump() == before
            assert cancel(case, preparation.json()['job']['id']).status_code == 200
        start(owner_state, mode=mode)
        before = case.dump()
        assert case.get('consent-proposals/' + proposal.json()['id']).status_code == 409
        assert case.get('consents/' + consent.json()['id']).status_code == 409
        assert case.post('consent-previews', preview, 'preview').status_code == 409
        assert case.post('consents', grant, 'grant').status_code == 409
        control = case.get('turns/' + preparation.json()['turn_id']).json()
        assert control['consent_control']['id'] == consent.json()['id']
        assert case.get('sessions/' + sid).status_code == 200 and case.dump() == before
        assert case.post('consents/' + consent.json()['id'] + '/revoke', {'expected_revision': 1}, 'assessment-revoke').status_code == 200


def test_expired_projection_never_rewrites_durable_run_when_cancelling(consent_case, monkeypatch):
    from services.api.app.application import provider_codex_consents
    from tests.integration.test_codex_turn_preparation_http import cancel
    case, _, sid, _, _, _ = consent_case
    _, prep, _, proposal, _, consent = grant_fixture(consent_case)
    monkeypatch.setattr(provider_codex_consents, 'utc_now', lambda: proposal.json()['summary']['expires_at'])
    assert case.get('turns/' + prep.json()['turn_id']).json()['consent_control']['status'] == 'expired'
    result = cancel(case, prep.json()['job']['id'])
    assert result.status_code == 200
    current = case.get('turns/' + prep.json()['turn_id']).json()
    assert current['outcome'] == 'cancelled' and current['consent_control']['status'] == 'expired'
    assert case.get('sessions/' + sid).json()['revision'] == 5
    with case.app.state.database.transaction(immediate=False) as conn:
        from services.api.app.infrastructure.codex_turn_repository import CodexTurnRepository
        from tests.integration.test_codex_turn_preparation_http import identity
        actor = identity(case)
        original = case.app.state.codex_bootstrap_service.checked_sessions(conn, actor)
        repo = CodexTurnRepository(conn, actor, case.app.state.codex_turn_service.context)
        retained = repo.checked(original)[sid].turns[prep.json()['turn_id']]
        assert retained.control.consent_control.model_dump() == {'id': consent.json()['id'], 'revision': 1, 'status': 'active'}
