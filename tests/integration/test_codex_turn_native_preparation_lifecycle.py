"""Actual HTTP/SQLite lifetime for a private, unqualified native-resource port.

The observable resource has only close(), supplies no runtime or InputProof,
and cannot send. This suite checks resource lifetime alongside committed server
facts; the synthetic bootstrap and resource are not native-owner qualification.
"""
from contextlib import contextmanager
import json

from fastapi.testclient import TestClient
import pytest

from services.api.app.application.codex_native_preparation import NativePreparationSources
from services.api.app.application.errors import ApiError
from services.api.app.application.provider_budget import ProofRegistry
from services.api.app.main import create_app
from tests.integration.test_codex_bootstrap_http import approve
from tests.integration.test_codex_turn_preparation_http import (
    cancel,
    identity,
    turn_body,
    turn_case as base_turn_case,
)

turn_case = base_turn_case


class ObservedResource:
    """A close-only test observation; never an SDK owner or sender."""

    def __init__(self, close_error=False):
        self.close_calls = 0
        self.close_error = close_error
        self.on_close = lambda: None

    def close(self):
        self.close_calls += 1
        self.on_close()
        if self.close_error:
            raise RuntimeError('private-cleanup-marker-must-not-be-delivered')


class ObservedPreparer:
    def __init__(self):
        self.sources = []
        self.resources = []
        self.create_resource = True
        self.close_error = False
        self.additional_sid = None

    def prepare(self, sources):
        assert isinstance(sources, NativePreparationSources)
        self.sources.append(sources)
        if not self.create_resource:
            return None
        resource = ObservedResource(self.close_error)
        self.resources.append(resource)
        return resource


@pytest.fixture
def closed_authority_case(turn_case, monkeypatch, request):
    case, runtime, _, _, _ = turn_case
    owner = ObservedPreparer()
    if getattr(request, 'param', None) == 'two_sessions':
        _, _, second_body = approve(case, key='second-lifetime')
        second = case.post('sessions', second_body, 'second-bootstrap-session')
        assert second.status_code == 201, second.text
        owner.additional_sid = second.json()['id']
    app = create_app(case.app.state.settings, codex_bootstrap_runtime=runtime,
                     codex_proofs=ProofRegistry(), codex_native_preparer=owner)
    client = TestClient(app, base_url=app.state.settings.origin)
    client.cookies.update(case.client.cookies)
    case.client.close()
    case.app, case.client = app, client
    service = app.state.codex_turn_service
    actual_freeze = service.proofs.freeze
    observations = []

    def observe(*args, **kwargs):
        result = actual_freeze(*args, **kwargs)
        observations.append(result)
        return result

    def forbidden(*args, **kwargs):
        pytest.fail('pregrant control or replay attempted execution')

    monkeypatch.setattr(service.proofs, 'freeze', observe)
    monkeypatch.setattr(runtime, 'execute', forbidden)
    try:
        yield turn_case, observations, owner
    finally:
        service.native_preparations.close_all()


def _prepare(case, sid, key):
    response = case.post(f'sessions/{sid}/turn-preparations', turn_body(), key)
    assert response.status_code == 202, response.text
    return response


def test_unqualified_prepare_cannot_consume_or_claim_complete_input_proof(closed_authority_case):
    values, observations, owner = closed_authority_case
    case, runtime, sid, _, _ = values
    response = _prepare(case, sid, 'unqualified')
    preparation = response.json()
    assert observations == [None] and len(owner.resources) == 1
    assert owner.resources[0].close_calls == 0
    sources = owner.sources[0]
    frozen_turn = json.loads(sources.turn_json)
    assert sources.actor_session_id == case.actor_id
    assert sources.job_id == preparation['job']['id']
    assert frozen_turn['workspace_id'] == sources.workspace_id
    assert frozen_turn['actor_session_id'] == case.actor_id
    assert frozen_turn['session_id'] == sid and frozen_turn['job_id'] == sources.job_id
    assert frozen_turn['request'] == turn_body()
    assert frozen_turn['runtime']['implemented'] is False
    assert json.loads(sources.bootstrap_json)['session']['id'] == sid
    assert isinstance(json.loads(sources.context_json), dict)
    assert all(isinstance(value, bytes) and value for value in (
        sources.bootstrap_json, sources.turn_json, sources.context_json,
    ))
    assert preparation['validity'] == 'unavailable'
    assert preparation['job']['status'] == 'awaiting_approval'
    assert preparation['proposal_id'] is None and preparation['consent_id'] is None
    control = case.get('turns/' + preparation['turn_id']).json()
    assert control['execution'] == 'not_started'
    assert control['approval_controls'] == [] and control['consent_control'] is None
    before = case.dump()
    started = case.post(f'sessions/{sid}/turns', {
        'preparation_id': preparation['id'],
        'preparation_sha256': preparation['preparation_sha256'],
        'consent_id': 'consent_unresolved',
        'expected_session_revision': preparation['session_revision'],
    }, 'unqualified-start')
    assert started.status_code == 503, started.text
    assert started.json()['error']['code'] == 'CODEX_INPUT_PROOF_UNAVAILABLE'
    assert case.app.state.codex_turn_worker.run_once() is False
    assert case.dump() == before and observations == [None]
    assert len(owner.sources) == 1 and owner.resources[0].close_calls == 0
    assert len(runtime.calls) == 1


def test_missing_csrf_refuses_before_proof_freeze_and_any_turn_write(closed_authority_case):
    values, observations, owner = closed_authority_case
    case, runtime, sid, _, _ = values
    before = case.dump()
    response = case.client.post(f'/api/v1/codex/sessions/{sid}/turn-preparations',
        json=turn_body(), headers={'Origin': case.headers['Origin'],
                                  'Idempotency-Key': 'missing-csrf'})
    assert response.status_code == 403, response.text
    assert observations == [] and case.dump() == before
    assert owner.sources == [] and owner.resources == []
    assert len(runtime.calls) == 1


def test_revoked_subject_permission_refuses_before_proof_freeze(closed_authority_case):
    values, observations, owner = closed_authority_case
    case, runtime, sid, _, _ = values
    role = case.client.post('/api/v1/session/role', json={'role': 'learner'},
        headers={**case.headers, 'Idempotency-Key': 'revoke-subject-role'})
    assert role.status_code == 200, role.text
    before = case.dump()
    response = case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'denied-role')
    assert response.status_code == 403, response.text
    assert observations == [] and case.dump() == before
    assert owner.sources == [] and owner.resources == []
    assert len(runtime.calls) == 1


@pytest.mark.parametrize('failure_stage', ['context_summary', 'prepared_event', 'final_access', 'transaction_exit'])
def test_failure_after_real_context_freeze_rolls_back_whole_owned_graph(
    closed_authority_case, monkeypatch, failure_stage,
):
    from services.api.app.infrastructure.codex_turn_repository import CodexTurnRepository

    values, observations, owner = closed_authority_case
    case, runtime, sid, _, _ = values
    before = case.dump()
    with monkeypatch.context() as patch:
        if failure_stage == 'context_summary':
            def summary(*args, **kwargs):
                raise RuntimeError('synthetic post-context transaction failure')
            patch.setattr(case.app.state.codex_turn_service.context, 'summary', summary)
        elif failure_stage == 'prepared_event':
            original = CodexTurnRepository.append
            def append(self, state, event, now):
                if event.kind == 'prepared':
                    raise RuntimeError('synthetic prepared-event transaction failure')
                return original(self, state, event, now)
            patch.setattr(CodexTurnRepository, 'append', append)
        elif failure_stage == 'final_access':
            from services.api.app.application import codex_turn
            original_access = codex_turn.current_control_access

            def fail_after_allocation(*args, **kwargs):
                if owner.resources:
                    raise RuntimeError('synthetic final checked-access failure')
                return original_access(*args, **kwargs)

            patch.setattr(codex_turn, 'current_control_access', fail_after_allocation)
        else:
            actual_transaction = case.app.state.database.transaction

            @contextmanager
            def fail_before_commit(**kwargs):
                with actual_transaction(**kwargs) as conn:
                    yield conn
                    if owner.resources:
                        raise RuntimeError('synthetic transaction-exit failure before commit')

            patch.setattr(case.app.state.database, 'transaction', fail_before_commit)
        response = case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'rollback')
    assert response.status_code == 500, response.text
    assert response.json()['error']['code'] == 'INTERNAL_ERROR'
    assert observations == [None] and case.dump() == before
    assert len(owner.resources) == 1 and owner.resources[0].close_calls == 1
    assert case.get('sessions/' + sid).json()['revision'] == 2
    assert case.app.state.codex_turn_worker.run_once() is False
    retried = _prepare(case, sid, 'rollback')
    assert retried.json()['session_revision'] == 3 and observations == [None, None]
    assert len(case.get(f'sessions/{sid}/turns').json()['items']) == 1
    assert len(owner.resources) == 2
    assert [resource.close_calls for resource in owner.resources] == [1, 0]
    assert owner.sources[0].job_id != owner.sources[1].job_id
    assert len(runtime.calls) == 1


@pytest.mark.parametrize('change, expected', [('learner', 403), ('revoke', 401)])
@pytest.mark.parametrize('close_error', [False, True])
def test_fresh_delivery_revocation_preserves_commit_without_rebuilding(
    closed_authority_case, monkeypatch, change, expected, close_error,
):
    values, observations, owner = closed_authority_case
    case, runtime, sid, _, _ = values
    service = case.app.state.codex_turn_service
    original_deliver = service._deliver
    owner.close_error = close_error
    committed_acks = []

    def revoke_before_delivery(identity, value, *, subject):
        assert subject is True
        committed_acks.append(value.model_dump(mode='json'))
        with case.app.state.database.transaction() as conn:
            if change == 'learner':
                conn.execute("UPDATE local_sessions SET role='learner' WHERE id=?", (case.actor_id,))
            else:
                conn.execute("UPDATE local_sessions SET revoked_at='2026-01-01T00:00:00Z' WHERE id=?",
                             (case.actor_id,))
        return original_deliver(identity, value, subject=subject)

    with monkeypatch.context() as patch:
        patch.setattr(service, '_deliver', revoke_before_delivery)
        refused = case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'revoked-delivery')
    assert refused.status_code == expected, refused.text
    assert len(committed_acks) == 1 and observations == [None]
    assert len(owner.resources) == 1 and owner.resources[0].close_calls == 1
    assert 'private-cleanup-marker' not in refused.text
    with case.app.state.database.transaction() as conn:
        conn.execute("UPDATE local_sessions SET role='author', revoked_at=NULL WHERE id=?", (case.actor_id,))
    preparation = committed_acks[0]
    current = case.get('sessions/' + sid).json()
    assert current['revision'] == 3 and current['active_turn_id'] == preparation['turn_id']
    before = case.dump()
    replay = case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'revoked-delivery')
    assert replay.status_code == 202 and replay.json() == preparation
    assert observations == [None] and case.dump() == before
    assert len(owner.sources) == 1 and owner.resources[0].close_calls == 1
    assert len(runtime.calls) == 1


def test_original_replay_and_restart_get_never_recapture_proof(closed_authority_case, monkeypatch):
    values, observations, owner = closed_authority_case
    case, runtime, sid, _, _ = values
    original = _prepare(case, sid, 'original')
    preparation = original.json()

    def forbidden(*args, **kwargs):
        pytest.fail('original replay or control GET recaptured preparation proof')

    monkeypatch.setattr(case.app.state.codex_turn_service.proofs, 'freeze', forbidden)
    before = case.dump()
    assert case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'original').content == original.content
    assert case.get('turn-preparations/' + preparation['id']).json() == preparation
    restarted_owner = ObservedPreparer()
    new = create_app(case.app.state.settings, codex_bootstrap_runtime=runtime,
                     codex_proofs=ProofRegistry(), codex_native_preparer=restarted_owner)
    monkeypatch.setattr(new.state.codex_turn_service.proofs, 'freeze', forbidden)
    client = TestClient(new, base_url=new.state.settings.origin)
    client.cookies.update(case.client.cookies)
    try:
        current = client.get('/api/v1/codex/sessions/' + sid)
        assert current.status_code == 200 and current.json()['revision'] == 3
        read = client.get('/api/v1/codex/turn-preparations/' + preparation['id'])
        assert read.status_code == 200 and read.json() == preparation
        control = client.get('/api/v1/codex/turns/' + preparation['turn_id'])
        assert control.status_code == 200 and control.json()['execution'] == 'not_started'
        replay = client.post(f'/api/v1/codex/sessions/{sid}/turn-preparations', json=turn_body(),
            headers={**case.headers, 'Idempotency-Key': 'original'})
        assert replay.content == original.content
    finally:
        client.close()
    assert observations == [None] and case.dump() == before
    assert len(owner.resources) == 1 and owner.resources[0].close_calls == 0
    assert restarted_owner.sources == [] and restarted_owner.resources == []
    assert len(runtime.calls) == 1


def test_cancel_original_ack_and_prepare_replay_never_freeze_again(closed_authority_case, monkeypatch):
    values, observations, owner = closed_authority_case
    case, runtime, sid, _, _ = values
    original = _prepare(case, sid, 'original')
    preparation = original.json()

    def forbidden(*args, **kwargs):
        pytest.fail('cancel or historical acknowledgement rebuilt preparation')

    monkeypatch.setattr(case.app.state.codex_turn_service.proofs, 'freeze', forbidden)
    durable_at_close = []
    owner.resources[0].on_close = lambda: durable_at_close.append(case.dump())
    stopped = cancel(case, preparation['job']['id'])
    assert stopped.status_code == 200, stopped.text
    assert owner.resources[0].close_calls == 1
    assert durable_at_close == [case.dump()]
    current = case.get('sessions/' + sid).json()
    assert current['revision'] == 5 and current['active_turn_id'] is None
    assert case.get('turn-preparations/' + preparation['id']).json()['validity'] == 'closed'
    before = case.dump()
    assert cancel(case, preparation['job']['id']).content == stopped.content
    assert case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'original').content == original.content
    assert observations == [None] and case.dump() == before
    assert len(runtime.calls) == 1


def test_public_prepare_body_cannot_supply_private_source_authority(closed_authority_case):
    values, observations, owner = closed_authority_case
    case, _, sid, _, _ = values
    before = case.dump()
    response = case.post(f'sessions/{sid}/turn-preparations', {
        **turn_body(),
        'workspace_id': 'workspace_intruder',
        'actor_session_id': 'actor_intruder',
        'job_id': 'job_intruder',
        'bootstrap_json': '{}',
        'turn_json': '{}',
        'context_json': '{}',
    }, 'caller-cannot-supply-sources')
    assert response.status_code == 422, response.text
    assert owner.sources == [] and owner.resources == [] and observations == []
    assert case.dump() == before


def test_preparer_returning_none_cannot_admit_input_proof(closed_authority_case):
    values, observations, owner = closed_authority_case
    case, _, sid, _, _ = values
    owner.create_resource = False
    original = _prepare(case, sid, 'no-native-resource')
    value = original.json()
    assert value['validity'] == 'unavailable' and value['consent_id'] is None
    assert len(owner.sources) == 1 and owner.resources == [] and observations == [None]
    before = case.dump()
    assert case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'no-native-resource').content == original.content
    assert case.get('turn-preparations/' + value['id']).json() == value
    assert case.dump() == before and len(owner.sources) == 1


def test_rollback_cleanup_error_keeps_transaction_failure_primary(closed_authority_case, monkeypatch):
    values, observations, owner = closed_authority_case
    case, _, sid, _, _ = values
    owner.close_error = True
    before = case.dump()

    def fail_summary(*args, **kwargs):
        raise RuntimeError('synthetic post-allocation transaction failure')

    with monkeypatch.context() as patch:
        patch.setattr(case.app.state.codex_turn_service.context, 'summary', fail_summary)
        failed = case.post(f'sessions/{sid}/turn-preparations', turn_body(), 'failed-cleanup')
    assert failed.status_code == 500, failed.text
    assert failed.json()['error']['code'] == 'INTERNAL_ERROR'
    assert 'private-cleanup-marker' not in failed.text
    assert case.dump() == before and observations == [None]
    assert len(owner.resources) == 1 and owner.resources[0].close_calls == 1
    owner.close_error = False
    assert _prepare(case, sid, 'failed-cleanup').json()['session_revision'] == 3
    assert [resource.close_calls for resource in owner.resources] == [1, 0]


def test_cancel_transaction_rollback_keeps_resource_live_until_successful_commit(closed_authority_case):
    values, _, owner = closed_authority_case
    case, _, sid, _, _ = values
    preparation = _prepare(case, sid, 'cancel-rollback').json()
    resource = owner.resources[0]
    with case.app.state.database.transaction() as conn:
        conn.execute("CREATE TRIGGER native_cancel_failure BEFORE UPDATE ON codex_turn_heads "
                     "BEGIN SELECT RAISE(ABORT,'synthetic native cancel rollback'); END;")
    before = case.dump()
    failed = cancel(case, preparation['job']['id'], key='cancel-rollback')
    assert failed.status_code == 500, failed.text
    assert case.dump() == before and resource.close_calls == 0
    current = case.get('sessions/' + sid).json()
    assert current['revision'] == 3 and current['active_turn_id'] == preparation['turn_id']
    assert case.get('turns/' + preparation['turn_id']).json()['execution'] == 'not_started'
    with case.app.state.database.transaction() as conn:
        conn.execute('DROP TRIGGER native_cancel_failure')
    durable_at_close = []
    resource.on_close = lambda: durable_at_close.append(case.dump())
    stopped = cancel(case, preparation['job']['id'], key='cancel-rollback')
    assert stopped.status_code == 200, stopped.text
    assert resource.close_calls == 1 and durable_at_close == [case.dump()]
    assert case.get('sessions/' + sid).json()['active_turn_id'] is None
    before = case.dump()
    assert cancel(case, preparation['job']['id'], key='cancel-rollback').content == stopped.content
    assert case.dump() == before and resource.close_calls == 1 and len(owner.sources) == 1


def test_missing_cancel_csrf_preserves_existing_resource_and_waiting_slot(closed_authority_case):
    values, _, owner = closed_authority_case
    case, _, sid, _, _ = values
    preparation = _prepare(case, sid, 'cancel-csrf').json()
    before = case.dump()
    denied = case.client.post('/api/v1/jobs/' + preparation['job']['id'] + '/cancel',
        json={'expected_revision': 1}, headers={'Origin': case.headers['Origin'],
                                              'Idempotency-Key': 'missing-cancel-csrf'})
    assert denied.status_code == 403, denied.text
    assert case.dump() == before and owner.resources[0].close_calls == 0
    assert case.get('sessions/' + sid).json()['active_turn_id'] == preparation['turn_id']
    assert cancel(case, preparation['job']['id']).status_code == 200
    assert owner.resources[0].close_calls == 1 and len(owner.sources) == 1


def test_cancel_cleanup_error_preserves_committed_original_ack(closed_authority_case):
    values, _, owner = closed_authority_case
    case, _, sid, _, _ = values
    owner.close_error = True
    preparation = _prepare(case, sid, 'cancel-close-error').json()
    resource = owner.resources[0]
    durable_at_close = []
    resource.on_close = lambda: durable_at_close.append(case.dump())
    failed_delivery = cancel(case, preparation['job']['id'])
    assert failed_delivery.status_code == 409, failed_delivery.text
    assert failed_delivery.json()['error']['code'] == 'CODEX_INPUT_PROOF_UNAVAILABLE'
    assert 'private-cleanup-marker' not in failed_delivery.text
    assert resource.close_calls == 1 and durable_at_close == [case.dump()]
    current = case.get('sessions/' + sid).json()
    assert current['revision'] == 5 and current['active_turn_id'] is None
    assert case.get('turn-preparations/' + preparation['id']).json()['validity'] == 'closed'
    before = case.dump()
    replay = cancel(case, preparation['job']['id'])
    assert replay.status_code == 200 and replay.json()['status'] == 'cancelled'
    assert case.dump() == before and resource.close_calls == 1
    assert cancel(case, preparation['job']['id'], revision=2, key='terminal-observe').status_code == 200
    assert resource.close_calls == 1 and len(owner.sources) == 1


@pytest.mark.parametrize('closed_authority_case', ['two_sessions'], indirect=True)
def test_close_all_attempts_every_resource_and_never_rebuilds_after_failure(closed_authority_case):
    values, _, owner = closed_authority_case
    case, runtime, sid, _, _ = values
    first = _prepare(case, sid, 'first-live-resource').json()
    assert owner.additional_sid is not None
    second = _prepare(case, owner.additional_sid, 'second-live-resource').json()
    assert len(owner.resources) == 2 and len(runtime.calls) == 2
    owner.resources[0].close_error = True
    service = case.app.state.codex_turn_service
    before = case.dump()
    with pytest.raises(ApiError) as failed:
        service.native_preparations.close_all()
    assert failed.value.code == 'CODEX_INPUT_PROOF_UNAVAILABLE'
    assert 'private-cleanup-marker' not in str(failed.value)
    assert [resource.close_calls for resource in owner.resources] == [1, 1]
    assert case.dump() == before
    service.native_preparations.close_all()
    assert [resource.close_calls for resource in owner.resources] == [1, 1]
    assert cancel(case, first['job']['id'], key='close-first').status_code == 200
    assert cancel(case, second['job']['id'], key='close-second').status_code == 200
    before = case.dump()
    denied = case.post(f'sessions/{sid}/turn-preparations', turn_body(5), 'closed-store')
    assert denied.status_code == 409, denied.text
    assert denied.json()['error']['code'] == 'CODEX_INPUT_PROOF_UNAVAILABLE'
    assert len(owner.sources) == 2 and case.dump() == before
    assert [resource.close_calls for resource in owner.resources] == [1, 1]


@pytest.mark.parametrize('closed_authority_case', ['two_sessions'], indirect=True)
def test_one_committed_transaction_attempts_both_real_cancel_cleanups(closed_authority_case):
    from services.api.app.import_dto import JobCancelRequest

    values, _, owner = closed_authority_case
    case, _, sid, _, _ = values
    first = _prepare(case, sid, 'multi-cancel-first').json()
    assert owner.additional_sid is not None
    second = _prepare(case, owner.additional_sid, 'multi-cancel-second').json()
    service, actor = case.app.state.codex_turn_service, identity(case)
    owner.resources[0].close_error = True
    durable_at_close = []
    for resource in owner.resources:
        resource.on_close = lambda: durable_at_close.append(case.dump())
    with pytest.raises(ApiError) as failed_cleanup:
        with case.app.state.database.transaction() as conn:
            service.request_stop(conn, actor, first['job']['id'],
                                 JobCancelRequest(expected_revision=1), 'multi-first')
            service.request_stop(conn, actor, second['job']['id'],
                                 JobCancelRequest(expected_revision=1), 'multi-second')
            assert [resource.close_calls for resource in owner.resources] == [0, 0]
    assert failed_cleanup.value.code == 'CODEX_INPUT_PROOF_UNAVAILABLE'
    assert [resource.close_calls for resource in owner.resources] == [1, 1]
    assert durable_at_close == [case.dump(), case.dump()]
    for session_id in (sid, owner.additional_sid):
        current = case.get('sessions/' + session_id).json()
        assert current['revision'] == 5 and current['active_turn_id'] is None
    before = case.dump()
    assert cancel(case, first['job']['id'], key='multi-first').status_code == 200
    assert cancel(case, second['job']['id'], key='multi-second').status_code == 200
    assert case.dump() == before and len(owner.sources) == 2
    assert [resource.close_calls for resource in owner.resources] == [1, 1]
