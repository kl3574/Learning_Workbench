"""Synthetic human intent exercises persistence only; no application approval."""
import json
import warnings

import pytest

from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes
from services.api.app.application.errors import ApiError
from services.api.app.application.review_history_models import (
    ReviewDecisionCommand, ReviewDecisionRecord, ReviewMachineRecord,
)
from services.api.app.infrastructure.database import utc_now
from services.api.app.infrastructure.review_repository import ReviewRepository
from tests.integration.test_review_repository import (
    prepared, artifact_fixture, complete_machine, create_job,
)

__all__ = ['prepared']


TABLES = ('review_jobs', 'reviews', 'review_revisions', 'review_artifact_bindings', 'review_commands')


def quality_bytes(connection):
    return {table: canonical_bytes([dict(row) for row in connection.execute(f'SELECT * FROM {table} ORDER BY rowid')])
            for table in TABLES}


def decision_fixture(prepared, connection, machine, previous, *, attachments=2):
    database, identity, value = prepared
    revision = previous.receipt.revision + 1
    evidence = [artifact_fixture(database, connection, value, f'artifact_human_{revision}_{index}',
                                purpose='human_decision_evidence') for index in range(attachments)]
    request = {'expected_revision': revision - 1, 'candidate_sha256': value.candidate.candidate_sha256,
               'mathematical': 'REJECTED', 'sources': 'NOT_APPLICABLE',
               'reason': f'Synthetic persistence fixture r{revision}; no content was reviewed.',
               'evidence_artifact_ids': [item.artifact.artifact_id for item in evidence]}
    receipt = machine.receipt.model_dump() | {'revision': revision, 'reviewer': identity.id,
        'mathematical': request['mathematical'], 'sources': request['sources'],
        'decision_reason': request['reason'], 'evidence_paths': [machine.report.artifact.download_path,
                                                                *[item.artifact.download_path for item in evidence]]}
    record = ReviewDecisionRecord(version='review-decision-record-v1', workspace_id=identity.workspace_id,
        review_id=value.review_id, candidate=value.candidate, previous_receipt_sha256=metadata_sha256(previous.receipt),
        machine_record_sha256=metadata_sha256(machine), material_descriptor_sha256=machine.material.descriptor_sha256,
        request=request, request_sha256=metadata_sha256(request), actor_session_id=identity.id,
        actor_role_at_decision='author', evidence=evidence, receipt=receipt, decided_at=utc_now())
    command = ReviewDecisionCommand(workspace_id=identity.workspace_id, actor_id=identity.id,
        route=f'POST /reviews/{value.review_id}/decision', command_key=f'synthetic_decision_{revision}',
        review_id=value.review_id, basis_revision=revision - 1, resulting_revision=revision,
        recorded_at=record.decided_at, command_kind='decision', request=record.request, ack=record.receipt)
    return record, command


def test_adjacent_decisions_retain_old_receipts_attachments_and_original_ack(prepared):
    database, identity, value = prepared
    with database.transaction() as connection:
        repo, machine, create = complete_machine(prepared, connection)
        repo.append_machine(machine)
        first, first_command = decision_fixture(prepared, connection, machine, machine)
        repo.append_decision(first, first_command)
        saved = connection.execute('SELECT * FROM review_revisions WHERE revision=2').fetchone()
        second, second_command = decision_fixture(prepared, connection, machine, first, attachments=0)
        repo.append_decision(second, second_command)
        history = repo.load(value.review_id)
        assert history.records == [machine, first, second] and history.receipt == second.receipt
        assert dict(connection.execute('SELECT * FROM review_revisions WHERE revision=2').fetchone()) == dict(saved)
        assert history.records[1].receipt.evidence_paths == first.receipt.evidence_paths
        assert history.receipt.evidence_paths == [machine.report.artifact.download_path]
        assert history.receipt.structural == machine.receipt.structural
        assert history.receipt.independent_pedagogy == 'NOT_RUN'
        for original in (create, first_command, second_command):
            assert repo.replay(original.actor_id, original.route, original.command_key, original.request) == original
        before = quality_bytes(connection)
        with pytest.raises(ApiError) as caught:
            repo.append_decision(first, first_command)
        assert caught.value.code == 'REVIEW_REVISION_MISMATCH' and quality_bytes(connection) == before
        with pytest.raises(ApiError) as caught:
            repo.replay(first_command.actor_id, first_command.route, first_command.command_key,
                        first.request.model_copy(update={'reason': 'different synthetic body'}))
        assert caught.value.code == 'IDEMPOTENCY_CONFLICT' and quality_bytes(connection) == before
    with database.transaction(immediate=False) as connection:
        connection.execute('PRAGMA query_only=ON')
        assert ReviewRepository(connection, identity.workspace_id).load(value.review_id).records == [machine, first, second]


@pytest.mark.parametrize('table', ['review_revisions', 'review_artifact_bindings', 'review_commands'])
def test_decision_failure_rolls_back_projection_history_and_command_when_outer_commits(prepared, table):
    database, identity, value = prepared
    with database.transaction() as connection:
        repo, machine, _ = complete_machine(prepared, connection)
        repo.append_machine(machine)
        record, command = decision_fixture(prepared, connection, machine, machine)
        before = quality_bytes(connection)
        connection.execute(f"CREATE TEMP TRIGGER injected_failure BEFORE INSERT ON {table} "
                           "BEGIN SELECT RAISE(ABORT,'synthetic later insert failed'); END")
        with pytest.raises(ApiError) as caught:
            repo.append_decision(record, command)
        assert caught.value.code == 'REVIEW_INTEGRITY_ERROR'
        assert connection.in_transaction and quality_bytes(connection) == before
        connection.execute("UPDATE workspace SET title='outer commit survives' WHERE id=?", (identity.workspace_id,))
    with database.transaction() as connection:
        assert quality_bytes(connection) == before
        assert ReviewRepository(connection, identity.workspace_id).load(value.review_id).records == [machine]
        assert connection.execute('SELECT title FROM workspace').fetchone()[0] == 'outer commit survives'


@pytest.mark.parametrize('table', ['reviews', 'review_revisions', 'review_artifact_bindings'])
def test_machine_failure_does_not_partially_create_a_receipt_or_undo_prior_jobs(prepared, table):
    database, identity, value = prepared
    with database.transaction() as connection:
        repo, machine, _ = complete_machine(prepared, connection)
        before = quality_bytes(connection)
        connection.execute(f"CREATE TEMP TRIGGER injected_failure BEFORE INSERT ON {table} "
                           "BEGIN SELECT RAISE(ABORT,'synthetic later insert failed'); END")
        with pytest.raises(ApiError) as caught:
            repo.append_machine(machine)
        assert caught.value.code == 'REVIEW_INTEGRITY_ERROR' and quality_bytes(connection) == before
    with database.transaction() as connection:
        assert quality_bytes(connection) == before
        assert connection.execute('SELECT status FROM jobs WHERE id=?', (value.review_id,)).fetchone()[0] == 'completed'
        # The caller failed to wrap Jobs + Quality together: never disguise this as pending/ready.
        with pytest.raises(ApiError) as caught:
            ReviewRepository(connection, identity.workspace_id).load(value.review_id)
        assert caught.value.code == 'REVIEW_INTEGRITY_ERROR'


@pytest.mark.parametrize('alteration', ['previous_hash', 'machine_hash', 'material_hash', 'structural', 'attachment_order',
                                     'workspace', 'command_actor', 'command_body', 'command_ack', 'command_time'])
def test_bad_decision_is_rejected_without_mutation(prepared, alteration):
    database, identity, value = prepared
    with database.transaction() as connection:
        repo, machine, _ = complete_machine(prepared, connection)
        repo.append_machine(machine)
        record, command = decision_fixture(prepared, connection, machine, machine)
        if alteration in ('previous_hash', 'machine_hash', 'material_hash'):
            field = {'previous_hash': 'previous_receipt_sha256', 'machine_hash': 'machine_record_sha256',
                     'material_hash': 'material_descriptor_sha256'}[alteration]
            record = record.model_copy(update={field: 'f' * 64})
        elif alteration == 'structural':
            record = record.model_copy(update={'receipt': record.receipt.model_copy(update={'structural': 'FAIL'})})
        elif alteration == 'attachment_order':
            record = record.model_copy(update={'evidence': list(reversed(record.evidence))})
        elif alteration == 'workspace':
            record = record.model_copy(update={'workspace_id': 'other_workspace'})
        elif alteration == 'command_actor':
            command = command.model_copy(update={'actor_id': 'other_actor'})
        elif alteration == 'command_body':
            command = command.model_copy(update={'request': command.request.model_copy(update={'reason': 'other'})})
        elif alteration == 'command_ack':
            command = command.model_copy(update={'ack': machine.receipt})
        else:
            command = command.model_copy(update={'recorded_at': '2099-01-01T00:00:00Z'})
        before = quality_bytes(connection)
        with pytest.raises(ApiError) as caught:
            repo.append_decision(record, command)
        assert caught.value.code == 'REVIEW_INTEGRITY_ERROR' and quality_bytes(connection) == before


@pytest.mark.parametrize('alteration', ['request_flag', 'input_hash', 'material_body', 'numeric_hash',
                                     'job_revision', 'artifact_manifest', 'artifact_size', 'machine_approval'])
def test_bad_machine_is_rejected_without_mutation(prepared, alteration):
    database, identity, value = prepared
    with database.transaction() as connection:
        repo, machine, _ = complete_machine(prepared, connection)
        if alteration == 'request_flag':
            from services.api.app.application.review_checks import review_structure
            report = review_structure(machine.material, requested=not machine.structural_report.requested)
            machine = machine.model_copy(update={'structural_report': report,
                'receipt': machine.receipt.model_copy(update={'structural': report.structural})})
        elif alteration == 'input_hash':
            machine = machine.model_copy(update={'input_sha256': 'f' * 64})
        elif alteration == 'material_body':
            raw = machine.model_dump()
            raw['material']['descriptor_sha256'] = 'f' * 64
            machine = ReviewMachineRecord.model_construct(**raw)
        elif alteration == 'numeric_hash':
            machine = machine.model_copy(update={'numeric': machine.numeric.model_copy(update={'descriptor_sha256': 'f' * 64})})
        elif alteration == 'job_revision':
            machine = machine.model_copy(update={'job_revision': 2})
        elif alteration == 'artifact_manifest':
            machine = machine.model_copy(update={'report': machine.report.model_copy(update={'manifest_sha256': 'f' * 64})})
        elif alteration == 'artifact_size':
            machine = machine.model_copy(update={'report': machine.report.model_copy(update={
                'artifact': machine.report.artifact.model_copy(update={'size': 999999})})})
        else:
            machine = machine.model_copy(update={'receipt': machine.receipt.model_copy(update={'mathematical': 'APPROVED'})})
        before = quality_bytes(connection)
        with pytest.raises(ApiError):
            repo.append_machine(machine)
        assert quality_bytes(connection) == before


def test_legacy_projection_is_retained_but_not_authenticated_or_backfilled(prepared):
    database, identity, value = prepared
    with database.transaction() as connection:
        command = create_job(connection, identity.workspace_id, value)
        raw = '{"legacy":"synthetic original bytes, not an authenticated receipt"}'
        connection.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?,?,?,?,?,?)',
            (value.review_id, value.candidate.draft_id, value.candidate.draft_revision,
             value.candidate.candidate_sha256, 1, raw, None, value.created_at,
             identity.workspace_id, 'import', value.candidate.entity))
        before = quality_bytes(connection)
        repo = ReviewRepository(connection, identity.workspace_id)
        with pytest.raises(ApiError) as caught:
            repo.load(value.review_id)
        assert caught.value.code == 'REVIEW_LEGACY_HISTORY_UNVERIFIABLE'
        with pytest.raises(ApiError):
            repo.bind(value, command)
        assert quality_bytes(connection) == before


@pytest.mark.parametrize('damage', ['old_record_hash', 'old_record_rehashed', 'old_receipt_hash', 'command_body_hash',
    'command_body_rehashed', 'missing_create', 'missing_decision_command', 'attachment_binding_hash',
    'attachment_ordinal', 'projection_json', 'projection_revision', 'artifact_manifest'])
def test_any_historical_damage_blocks_read_and_original_replay_without_repair(prepared, damage):
    database, identity, value = prepared
    with database.transaction() as connection:
        repo, machine, create = complete_machine(prepared, connection)
        repo.append_machine(machine)
        record, command = decision_fixture(prepared, connection, machine, machine)
        repo.append_decision(record, command)
        # Explicit adversarial fixture: disable only guards needed to introduce damaged storage.
        for trigger in ('review_revisions_no_update', 'review_commands_no_update',
                        'review_commands_no_delete', 'review_artifacts_no_update'):
            connection.execute(f'DROP TRIGGER {trigger}')
        if damage == 'old_record_hash':
            connection.execute("UPDATE review_revisions SET record_sha256=? WHERE revision=1", ('f' * 64,))
        elif damage == 'old_record_rehashed':
            changed = machine.model_dump()
            changed['input_sha256'] = 'f' * 64
            raw = canonical_bytes(changed).decode()
            connection.execute('UPDATE review_revisions SET record_json=?,record_sha256=? WHERE revision=1',
                               (raw, sha256_bytes(raw.encode())))
        elif damage == 'old_receipt_hash':
            connection.execute('UPDATE review_revisions SET receipt_sha256=? WHERE revision=2', ('f' * 64,))
        elif damage in ('command_body_hash', 'command_body_rehashed'):
            raw = canonical_bytes(command.request.model_dump() | {'reason': 'tampered old intent'}).decode()
            digest = sha256_bytes(raw.encode()) if damage.endswith('rehashed') else 'f' * 64
            connection.execute("UPDATE review_commands SET request_json=?,request_sha256=? WHERE command_kind='decision'",
                               (raw, digest))
        elif damage in ('missing_create', 'missing_decision_command'):
            connection.execute('DELETE FROM review_commands WHERE command_kind=?',
                               ('create' if damage == 'missing_create' else 'decision',))
        elif damage == 'attachment_binding_hash':
            connection.execute('UPDATE review_artifact_bindings SET binding_sha256=? WHERE review_revision=1', ('f' * 64,))
        elif damage == 'attachment_ordinal':
            connection.execute('UPDATE review_artifact_bindings SET ordinal=9 WHERE review_revision=1')
        elif damage == 'projection_json':
            connection.execute('UPDATE reviews SET receipt_json=?', (json.dumps(record.receipt.model_dump()),))
        elif damage == 'projection_revision':
            connection.execute('UPDATE reviews SET revision=3')
        else:
            connection.execute("UPDATE artifacts SET manifest_json='{}' WHERE id=?", (machine.report.artifact.artifact_id,))
        before = quality_bytes(connection)
        replayed = command if damage == 'missing_create' else create
        for read in (lambda: repo.load(value.review_id),
                     lambda: repo.replay(replayed.actor_id, replayed.route, replayed.command_key, replayed.request)):
            with pytest.raises(ApiError) as caught:
                read()
            assert caught.value.code == 'REVIEW_INTEGRITY_ERROR'
        assert quality_bytes(connection) == before


def test_sanitized_backup_session_null_preserves_closed_human_history(prepared):
    database, identity, value = prepared
    with database.transaction() as connection:
        repo, machine, _ = complete_machine(prepared, connection)
        repo.append_machine(machine)
        record, command = decision_fixture(prepared, connection, machine, machine)
        repo.append_decision(record, command)
        connection.execute('UPDATE reviews SET reviewer_session_id=NULL WHERE id=?', (value.review_id,))
        assert repo.load(value.review_id).records == [machine, record]
        assert repo.replay(command.actor_id, command.route, command.command_key, command.request) == command


def test_revalidation_of_constructed_values_never_warns_private_input(prepared):
    database, _, _ = prepared
    with database.transaction() as connection:
        repo, machine, _ = complete_machine(prepared, connection)
        private = 'SYNTHETIC_PRIVATE_REVIEW_REVALIDATION_INPUT'
        malformed = machine.model_copy(update={'material': {'private_synthetic_marker': private}})
        before = quality_bytes(connection)
        with warnings.catch_warnings(record=True) as emitted:
            warnings.simplefilter('always')
            with pytest.raises(ApiError) as caught:
                repo.append_machine(malformed)
        assert private not in str(caught.value) and private not in repr(caught.value)
        assert not emitted, 'Revalidation must not emit serializer warnings containing private input'
        assert quality_bytes(connection) == before
