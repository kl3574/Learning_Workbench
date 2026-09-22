"""Synthetic human intent exercises persistence only; no application approval."""
import json
import warnings

import pytest

from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes
from services.api.app.application.errors import ApiError
from services.api.app.application.review_history_models import (
    ReviewCancelCommand, ReviewDecisionCommand, ReviewDecisionRecord, ReviewMachineRecord,
)
from services.api.app.application.review_models import ReviewJobInput
from services.api.app.infrastructure.database import utc_now
from services.api.app.infrastructure.review_job_repository import ReviewJobRepository
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


@pytest.mark.parametrize('kind', ['single', 'assessment'])
def test_generated_owner_history_preserves_exact_numeric_observation_without_running_it(tmp_path, kind, monkeypatch):
    from tests.integration.test_authoring_numeric_service import generated as single_fixture
    from tests.integration.test_authoring_group_numeric_service import generated_group
    from tests.integration.test_review_job_lifecycle import PreparedReviewFixture

    # Existing producers use explicit controlled loopback model bytes. This is
    # neither a vendor request nor mathematical review or numeric execution.
    state = single_fixture.__wrapped__(tmp_path) if kind == 'single' else generated_group(tmp_path, kind)
    database, identity, owner, numeric, candidate, runtime = state
    source_kind = 'authoring_single' if kind == 'single' else 'authoring_group'
    value = ReviewJobInput(version='draft-review-job-v1', workspace_id=identity.workspace_id,
        review_id='synthetic_generated_review', source_kind=source_kind, candidate=candidate.model_dump(),
        request={'expected_revision': candidate.draft_revision, 'checks': ['structure', 'numerical_examples'],
                 'reviewer_note': 'Synthetic persistence fixture; no actual review decision'},
        creator_session_id=identity.id, rules_version='draft-review-rules-v1', created_at=utc_now())
    safe = PreparedReviewFixture(database, identity, value)
    def forbidden(*args, **kwargs):
        pytest.fail('Persistence must not prepare or execute numeric work')
    for method in ('prepare', 'check', 'manifest_document', 'run_checked'):
        monkeypatch.setattr(runtime, method, forbidden, raising=False)
    with database.transaction() as connection:
        repo, machine, _ = complete_machine(safe, connection, owner=owner, numeric_owner=numeric)
        repo.append_machine(machine)
        record, command = decision_fixture(safe, connection, machine, machine, attachments=0)
        repo.append_decision(record, command)
        read = repo.load(value.review_id)
        assert read.records[0].material.payload.record == machine.material.payload.record
        assert read.records[0].numeric == machine.numeric and machine.numeric.checks == []
        assert machine.numeric.coverage == 'authoring_numeric_ledger'
        assert machine.numeric.candidate_record_sha256 == machine.material.owner_record_sha256
        assert read.receipt.independent_pedagogy == 'NOT_RUN'


def test_running_cancel_original_ack_survives_later_terminal_and_terminal_noop(prepared):
    database, identity, value = prepared
    with database.transaction() as connection:
        create = create_job(connection, identity.workspace_id, value)
        repo = ReviewRepository(connection, identity.workspace_id)
        repo.bind(value, create)
        jobs = ReviewJobRepository(connection, identity.workspace_id)
        jobs.claim(value.review_id)
        ack = jobs.cancel(value.review_id, 2)
        original = ReviewCancelCommand(workspace_id=identity.workspace_id, actor_id=identity.id,
            route=f'POST /jobs/{value.review_id}/cancel', command_key='synthetic_running_cancel',
            review_id=value.review_id, basis_revision=2, resulting_revision=3, recorded_at=utc_now(),
            command_kind='cancel', request={'expected_revision': 2}, ack=ack.model_dump())
        repo.record_cancel(original)
        jobs.transition(jobs.load(value.review_id), 'cancelled')
        terminal_ack = jobs.cancel(value.review_id, 1)
        terminal = original.model_copy(update={'command_key': 'synthetic_terminal_cancel', 'basis_revision': 4,
            'resulting_revision': 4, 'request': original.request.model_copy(update={'expected_revision': 1}),
            'ack': type(original.ack).model_validate(terminal_ack.model_dump()), 'recorded_at': utc_now()})
        repo.record_cancel(terminal)
        assert repo.load(value.review_id).state == 'pending'
        assert repo.load(value.review_id).receipt is None
        assert repo.replay(original.actor_id, original.route, original.command_key, original.request) == original
        assert repo.replay(terminal.actor_id, terminal.route, terminal.command_key, terminal.request) == terminal
        assert original.ack.status == 'running' and original.ack.revision == 3
        assert terminal.ack.status == 'cancelled' and terminal.ack.revision == 4


@pytest.mark.parametrize('model_name', ['machine', 'decision', 'command', 'history', 'artifact', 'receipt'])
def test_closed_persistence_values_hide_private_diagnostics(prepared, model_name):
    from pydantic import ValidationError

    database, _, value = prepared
    with database.transaction() as connection:
        repo, machine, _ = complete_machine(prepared, connection)
        repo.append_machine(machine)
        decision, command = decision_fixture(prepared, connection, machine, machine)
        values = {'machine': machine, 'decision': decision, 'command': command,
                  'history': repo.load(value.review_id), 'artifact': machine.report, 'receipt': machine.receipt}
        model = values[model_name]
        assert repr(model) == type(model).__name__ + '()' and str(model) == ''
        marker = 'SYNTHETIC_PRIVATE_REVIEW_VALIDATION_BODY'
        malformed = model.model_dump() | {'unexpected_private_body': marker}
        with pytest.raises(ValidationError) as caught:
            type(model).model_validate(malformed)
        assert marker not in str(caught.value) and marker not in repr(caught.value)
        assert 'input_value' not in str(caught.value)
