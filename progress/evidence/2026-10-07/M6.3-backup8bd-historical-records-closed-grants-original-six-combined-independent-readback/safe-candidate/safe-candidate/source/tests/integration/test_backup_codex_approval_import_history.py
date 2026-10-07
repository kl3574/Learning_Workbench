"""Nonempty approval/import backup histories; no restored lifecycle or parser."""
from contextlib import contextmanager
import json
import subprocess

import pytest

from packages.contracts.canonical import canonical_bytes
from services.api.app.application.codex_operation_profile import (
    CodexOperationRegistry, LiteralCommand, LiteralOperationProfile,
)
from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.provider_transport import ProviderTransport
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_backup_codex_lifespan import checked_copy
from tests.integration.test_backup_codex_turn_history import fresh_reader
from tests.integration.test_codex_artifact_import_http import selected
from tests.integration.test_codex_generic_approval_http import callback_turn
from tests.integration.test_codex_turn_dispatch_http import base_consent_case, consent_case

__all__ = ['base_consent_case', 'consent_case']

APPROVAL_TABLES = ('approvals', 'codex_approval_heads', 'codex_approval_events',
                   'codex_approval_members', 'codex_approval_commands')
IMPORT_TABLES = ('codex_artifact_import_heads', 'codex_artifact_import_events',
                 'codex_artifact_import_members', 'codex_artifact_import_commands',
                 'codex_import_batches', 'codex_import_bindings', 'ingestion_imports', 'sources')


def nonempty_owner_hashes(database, names):
    with database.connect() as conn:
        assert all(conn.execute(f'SELECT count(*) FROM {name}').fetchone()[0] for name in names)
    hashes = table_hashes(database)
    return {name: hashes[name] for name in names}


@contextmanager
def execution_free_reader(copied, source, proofs, monkeypatch):
    """Observe only known application seams after the synthetic copy is made."""
    calls = {'process': 0, 'provider': 0, 'operation_start': 0}

    def forbidden(name):
        def refuse(*args, **kwargs):
            calls[name] += 1
            pytest.fail('Restored history crossed the forbidden ' + name + ' seam')
        return refuse

    monkeypatch.setattr(subprocess, 'Popen', forbidden('process'))
    monkeypatch.setattr(ProviderTransport, 'stream', forbidden('provider'))
    with fresh_reader(copied, source, proofs, monkeypatch) as (case, runtime, transport_calls):
        # The literal runtime freezes its actual execute code. Replacing that
        # function would invalidate the profile before original authority is
        # checked. Observe the separate owner start boundary instead.
        monkeypatch.setattr(case.app.state.codex_turn_service.approvals, '_append', forbidden('operation_start'))
        yield case
        assert runtime.calls == [] and transport_calls == []
    assert calls == {'process': 0, 'provider': 0, 'operation_start': 0}


def test_backup_keeps_unstarted_approved_operation_and_refuses_its_original_execution(
        consent_case, tmp_path_factory, monkeypatch):
    source, _, sid, proofs, _, _ = consent_case
    source, prep, request, original_frame = callback_turn(consent_case)
    registry = CodexOperationRegistry([LiteralOperationProfile.current()])
    source.app.state.codex_turn_service.approvals.operations = registry
    command = LiteralCommand(version='codex-synthetic-literal-command-v1', text='Synthetic unapplied operation')
    frame = canonical_bytes({**json.loads(original_frame), 'request_text': canonical_bytes(command).decode()})
    worker = source.app.state.codex_turn_worker
    captured, errors = {}, []
    target = tmp_path_factory.mktemp('approved-operation-backup') / 'copied'

    def peer(gate):
        try:
            gate.request(request.body, endpoint=request.endpoint, max_output_tokens=64)
            identifier = worker.receive_operation(frame)
            view = source.client.get('/api/v1/approvals/' + identifier).json()
            body = {'operation_sha256': view['operation_sha256'], 'expected_revision': 1,
                    'decision': 'approve_once'}
            ack = source.client.post('/api/v1/approvals/' + identifier + '/decision', json=body,
                headers={**source.headers, 'Idempotency-Key': 'approved-before-backup'})
            assert ack.status_code == 200
            current = source.client.get('/api/v1/approvals/' + identifier).json()
            assert current['decision'] == 'approve_once' and current['execution'] == 'not_started'
            original_hashes = nonempty_owner_hashes(source.app.state.database, APPROVAL_TABLES)
            copied, _, _ = checked_copy(source, target)
            assert nonempty_owner_hashes(copied, APPROVAL_TABLES) == original_hashes
            captured.update(copied=copied, identifier=identifier, body=body, ack=ack.json(), view=current)
        except BaseException as error:
            errors.append(error)
            raise

    source.app.state.synthetic_executor.peer = peer
    assert worker.run_once() is True
    if errors:
        raise errors[0]
    copied, identifier = captured['copied'], captured['identifier']
    source_after = table_hashes(source.app.state.database)
    with execution_free_reader(copied, source, proofs, monkeypatch) as case:
        # The restored fresh learner has the safe control basis, not the full operation.
        before = table_hashes(copied)
        control = case.get('turns/' + prep['turn_id'])
        assert control.status_code == 200 and control.json()['execution'] == 'active'
        assert control.json()['approval_controls'][0]['decision'] == 'approve_once'
        assert case.client.get('/api/v1/approvals/' + identifier).status_code == 403
        assert table_hashes(copied) == before
        # This is the same explicit test-only interpreter, not production registration.
        case.app.state.codex_turn_service.approvals.operations = registry
        role = case.client.post('/api/v1/session/role', json={'role': 'author'},
            headers={**case.headers, 'Idempotency-Key': 'read-approved-backup'})
        assert role.status_code == 200
        before = table_hashes(copied)
        view = case.client.get('/api/v1/approvals/' + identifier)
        assert view.status_code == 200
        for name in ('actor_session_id', 'operation', 'operation_sha256', 'decision', 'revision',
                     'decided_at', 'execution', 'started_at', 'finished_at'):
            assert view.json()[name] == captured['view'][name]
        assert view.json()['actor_session_id'] == source.actor_id != case.actor_id
        owner = case.app.state.codex_turn_service.approvals
        with copied.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            workspace = copied.workspace_id()
            _, _, history = case.app.state.codex_turn_service._owned_state(conn, workspace)
            state = owner.verify_history(conn, workspace, history)[identifier]
            assert state.decided.command.ack.model_dump(mode='json') == captured['ack']
            assert state.decided.command.actor_session_id == source.actor_id
            execution_owner = state.operation.execution_owner_id
            assert registry.available(state.operation.closure.profile)
        # A matching current CAS still cannot transfer the original approve_once.
        denied = case.client.post('/api/v1/approvals/' + identifier + '/decision',
            json={**captured['body'], 'expected_revision': view.json()['revision']},
            headers={**case.headers, 'Idempotency-Key': 'fresh-actor-approve'})
        assert denied.status_code == 403 and denied.json()['error']['code'] == 'POLICY_DENIED'
        # The private original execution port independently refuses the retained grant.
        with pytest.raises(ApiError) as refused:
            owner.execute_owned_operation(workspace, prep['turn_id'], execution_owner, identifier)
        assert refused.value.code in {'POLICY_DENIED', 'PROVIDER_BACKUP_DISABLED'}
        assert table_hashes(copied) == before
    assert table_hashes(source.app.state.database) == source_after
    assert len(source.app.state.synthetic_transport_calls) == 1


def test_backup_keeps_nonempty_staged_import_bindings_and_original_ack_without_get_work(
        consent_case, tmp_path_factory, monkeypatch):
    source, _, _, proofs, _, _ = consent_case
    source, sid, manifest, body = selected(consent_case)
    ack = source.post(f'sessions/{sid}/artifacts/import', body, 'selected-before-backup')
    assert ack.status_code == 202
    aggregate_id = ack.json()['id']
    aggregate = source.get('artifact-imports/' + aggregate_id)
    assert aggregate.status_code == 200
    item, = aggregate.json()['items']
    original_import = source.client.get('/api/v1/imports/' + item['import_id'])
    assert original_import.status_code == 200 and original_import.json()['status'] == 'staged'
    original_hashes = nonempty_owner_hashes(source.app.state.database, IMPORT_TABLES)
    copied, source_before, _ = checked_copy(source, tmp_path_factory.mktemp('staged-import-backup') / 'copied')
    assert nonempty_owner_hashes(copied, IMPORT_TABLES) == original_hashes
    prep = {'turn_id': body['turn_id']}
    with execution_free_reader(copied, source, proofs, monkeypatch) as case:
        before = table_hashes(copied)
        assert case.get('turns/' + body['turn_id']).status_code == 200
        assert case.get('artifact-imports/' + aggregate_id).status_code == 403
        assert table_hashes(copied) == before
        role = case.client.post('/api/v1/session/role', json={'role': 'author'},
            headers={**case.headers, 'Idempotency-Key': 'read-staged-backup'})
        assert role.status_code == 200
        before = table_hashes(copied)
        current = case.get('artifact-imports/' + aggregate_id)
        assert current.status_code == 200 and current.content == aggregate.content
        assert current.json()['actor_session_id'] == source.actor_id != case.actor_id
        restored_import = case.client.get('/api/v1/imports/' + item['import_id'])
        assert restored_import.status_code == 200 and restored_import.content == original_import.content
        assert case.get(f'sessions/{sid}/turns/{prep["turn_id"]}/artifacts').json() == manifest
        with copied.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            workspace = copied.workspace_id()
            _, records, stages = case.app.state.codex_artifact_imports._checked(conn, workspace)
            original = records[aggregate_id].created
            assert original.ack.model_dump(mode='json') == ack.json()
            assert original.input.actor_session_id == source.actor_id
            binding, = original.bindings
            assert binding.actor_session_id == source.actor_id
            assert binding.artifact_sha256 == item['source_sha256'] == manifest['manifest']['entries'][0]['sha256']
            assert stages[aggregate_id][0].binding == binding
            assert stages[aggregate_id][0].status == 'staged'
        # Reading a selected local source is distinct from replaying a model/tool grant.
        assert table_hashes(copied) == before
    assert table_hashes(source.app.state.database) == source_before
    assert len(source.app.state.synthetic_transport_calls) == 1
