"""Read-only historical numeric observations from real SQLite owners and loopback generation."""
from dataclasses import replace
import json

import pytest

from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.authoring_numeric_repository import NumericRepository
from services.api.app.infrastructure.authoring_group_numeric_repository import GroupNumericRepository
from services.api.app.infrastructure.database import utc_now
from services.api.app.import_dto import JobCancelRequest

from tests.integration.test_authoring_numeric_provider_history import ProviderHistoryCase, table_hashes
from tests.integration.test_authoring_numeric_service import generated as single_fixture, decision
from tests.integration.test_authoring_group_numeric_service import generated_group


@pytest.fixture(params=['single', 'group'])
def generated(request, tmp_path):
    state = single_fixture.__wrapped__(tmp_path) if request.param == 'single' else generated_group(tmp_path, 'assessment')
    return ProviderHistoryCase(request.param, state)


def repository(case, conn):
    cls = NumericRepository if case.variant == 'single' else GroupNumericRepository
    return cls(conn, case.identity.workspace_id)


def read(case):
    with case.database.transaction(immediate=False) as conn:
        conn.execute('PRAGMA query_only=ON')
        return case.numeric.read_review_numeric(conn, case.identity, case.candidate)


def verify(case, observation, identity=None):
    with case.database.transaction(immediate=False) as conn:
        conn.execute('PRAGMA query_only=ON')
        case.numeric.verify_review_numeric(conn, identity or case.identity, observation)


def test_real_numeric_owner_reads_all_checks_without_writes_or_runtime(generated, monkeypatch):
    case = generated
    first = case.preview('first')
    second = case.preview('second')
    before = table_hashes(case.database)
    with case.database.transaction(immediate=False) as conn:
        conn.execute('PRAGMA query_only=ON')
        def forbidden(*args, **kwargs):
            pytest.fail('numeric review must not open another connection or invoke runtime')
        with monkeypatch.context() as patch:
            patch.setattr(case.database, 'connect', forbidden)
            for method in ['prepare', 'check', 'manifest_document', 'run_checked']:
                patch.setattr(case.runtime, method, forbidden, raising=False)
            observation = case.numeric.read_review_numeric(conn, case.identity, case.candidate)
            assert [item.view.id for item in observation.checks] == [first.id, second.id]
            case.numeric.verify_review_numeric(conn, case.identity, observation)
    assert table_hashes(case.database) == before


def test_old_observations_survive_new_checks_decisions_job_progress_recovery_and_expiry(generated, monkeypatch):
    from services.api.app.infrastructure import authoring_numeric_repository as single_repo
    from services.api.app.infrastructure import authoring_group_numeric_repository as group_repo

    case = generated
    empty = read(case)
    first, second = case.preview('pending-first'), case.preview('pending-second')
    pending = read(case)
    assert all(item.view.decision == 'pending' and not item.view.expired for item in pending.checks)
    # Same timestamp and arbitrary UUID order cannot reorder an appended row.
    with monkeypatch.context() as patch:
        patch.setattr(single_repo if case.variant == 'single' else group_repo, 'utc_now', lambda: first.created_at)
        third = case.preview('same-time-later')
    case.numeric.decide(case.identity, second.id, decision(second, 'decline'), 'decline-second')
    ack = case.numeric.decide(case.identity, first.id, decision(first), 'approve-first')
    queued = read(case)
    assert [item.view.id for item in queued.checks] == [first.id, second.id, third.id]
    assert queued.checks[0].job.id == ack.job.id and queued.checks[0].job.status == 'queued'
    worker = case.worker()
    lease, _, _ = worker.claim()
    running = read(case)
    assert running.checks[0].job.status == 'running' and running.checks[0].start is None
    with case.database.transaction() as conn:
        assert repository(case, conn).begin(lease, utc_now())
    admitted = read(case)
    assert admitted.checks[0].start.admitted_at is not None
    assert admitted.checks[0].start.actual_started_at is None
    # Real recovery of a committed permission cannot execute the plan again.
    with case.database.transaction() as conn:
        conn.execute("UPDATE jobs SET lease_until='2000-01-01T00:00:00Z' WHERE id=?", (lease.job_id,))
    def forbidden(*args, **kwargs):
        pytest.fail('recovery of admitted work must not call an executor')
    monkeypatch.setattr(case.runtime, 'run_checked', forbidden, raising=False)
    assert worker.run_once()
    terminal = read(case)
    result = terminal.checks[0].end.result
    assert (result.verdict, result.outcome, result.exit_code) == ('BLOCKED', 'outcome_unknown', None)
    assert terminal.checks[0].view.result == result
    before = table_hashes(case.database)
    monkeypatch.setattr(single_repo, 'utc_now', lambda: '2099-01-01T00:00:00Z')
    monkeypatch.setattr(group_repo, 'utc_now', lambda: '2099-01-01T00:00:00Z')
    for original in [empty, pending, queued, running, admitted, terminal]:
        verify(case, original)
    assert not pending.checks[0].view.expired
    assert table_hashes(case.database) == before


def test_terminal_cancel_observation_keeps_original_input_runtime_and_all_output_facts(generated):
    case = generated
    preview = case.preview()
    ack = case.numeric.decide(case.identity, preview.id, decision(preview), 'approve')
    case.numeric.cancel_job(case.identity, ack.job.id, JobCancelRequest(expected_revision=1), 'cancel')
    original = read(case)
    entry = original.checks[0]
    assert entry.view.result.verdict == 'BLOCKED' and entry.view.result.outcome == 'cancelled'
    assert entry.start.admitted_at is entry.start.actual_started_at is None
    assert entry.view.result.exit_code is None
    assert entry.record.runtime_manifest_json == case.runtime.manifest_document().decode()
    assert entry.input.plan == preview.plan and entry.input.runtime == preview.runtime
    assert sha256_bytes(canonical_bytes(entry.input)) == entry.end.result.input_sha256
    assert entry.end.stdout_base64 == entry.end.stderr_base64 == '' and not entry.end.output_complete
    if case.variant == 'group':
        assert entry.input.target == case.state[5]
        material = case.authoring.draft(case.identity, case.candidate.draft_id)
        private = case.authoring.solution(case.identity, case.candidate.draft_id, entry.view.target.member_key)
        assert private.payload.answer.numeric_plan == entry.view.plan
        assert material.candidate.candidate_sha256 == original.candidate.candidate_sha256
    # A later terminal no-op cancel command may be appended; old original ACK,
    # command/event prefixes and result remain exact.
    case.numeric.cancel_job(case.identity, ack.job.id, JobCancelRequest(expected_revision=1), 'cancel-again')
    before = table_hashes(case.database)
    verify(case, original)
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('damage', ['check_missing', 'preview_command', 'runtime_manifest', 'job_event', 'execution_missing', 'output_bytes'])
def test_original_numeric_ledger_loss_or_tampering_is_rejected(generated, damage):
    case = generated
    preview = case.preview()
    ack = case.numeric.decide(case.identity, preview.id, decision(preview), 'approve')
    case.numeric.cancel_job(case.identity, ack.job.id, JobCancelRequest(expected_revision=1), 'cancel')
    original = read(case)
    table = 'authoring_numeric_checks' if case.variant == 'single' else 'authoring_group_numeric_checks'
    with case.database.transaction() as conn:
        if damage == 'check_missing':
            conn.execute(f'DELETE FROM {table} WHERE check_id=?', (preview.id,))
        elif damage == 'preview_command':
            # Current repository validation accepts any legitimate nonblank key;
            # the observed original command prefix must still detect replacement.
            conn.execute("UPDATE authoring_commands SET key='changed-key' WHERE owner_id=? AND job_revision IS NULL", (preview.id,))
        elif damage == 'runtime_manifest':
            row = conn.execute(f'SELECT record_json FROM {table} WHERE check_id=?', (preview.id,)).fetchone()
            raw = json.loads(row['record_json'])
            raw['runtime_manifest_json'] = '{}'
            encoded = canonical_bytes(raw)
            conn.execute(f'UPDATE {table} SET record_json=?,record_sha256=? WHERE check_id=?',
                         (encoded.decode(), sha256_bytes(encoded), preview.id))
        elif damage == 'job_event':
            conn.execute('DELETE FROM job_events WHERE job_id=? AND seq=1', (ack.job.id,))
        elif damage == 'execution_missing':
            conn.execute('DELETE FROM authoring_numeric_executions WHERE job_id=?', (ack.job.id,))
        else:
            row = conn.execute('SELECT end_json FROM authoring_numeric_executions WHERE job_id=?', (ack.job.id,)).fetchone()
            raw = json.loads(row['end_json'])
            raw['stderr_base64'] = 'Y2hhbmdlZA=='
            encoded = canonical_bytes(raw)
            conn.execute('UPDATE authoring_numeric_executions SET end_json=?,end_sha256=? WHERE job_id=?',
                         (encoded.decode(), sha256_bytes(encoded), ack.job.id))
    before = table_hashes(case.database)
    with pytest.raises(ApiError):
        verify(case, original)
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('damage', ['role', 'revoked', 'workspace', 'provider'])
def test_observation_and_history_verification_require_current_access_and_provider(generated, damage):
    case = generated
    case.preview()
    original = read(case)
    identity = case.identity
    if damage == 'provider':
        case.damage_original_artifact()
    elif damage == 'workspace':
        identity = replace(identity, workspace_id='workspace_other')
    else:
        with case.database.transaction() as conn:
            if damage == 'role':
                conn.execute("UPDATE local_sessions SET role='learner' WHERE id=?", (identity.id,))
            else:
                conn.execute("UPDATE local_sessions SET revoked_at='2026-01-01T00:00:00Z' WHERE id=?", (identity.id,))
    before = table_hashes(case.database)
    with pytest.raises(ApiError):
        verify(case, original, identity)
    with case.database.transaction(immediate=False) as conn, pytest.raises(ApiError):
        case.numeric.read_review_numeric(conn, identity, case.candidate)
    assert table_hashes(case.database) == before


def test_import_facade_explicitly_has_no_numeric_pipeline_and_does_not_repair_catalog(tmp_path):
    from services.api.app.application.draft_candidates import DraftCandidates
    from services.api.app.application.review_numeric import ReviewNumeric
    from tests.integration.test_draft_candidate_owners import imported_candidate, remove_catalog_fixture

    for database, identity, owner, _, _, candidate in imported_candidate.__wrapped__(tmp_path):
        facade = ReviewNumeric(DraftCandidates({'import': owner}), {})
        before = table_hashes(database)
        with database.transaction(immediate=False) as conn:
            conn.execute('PRAGMA query_only=ON')
            original = facade.read_review_numeric(conn, identity, candidate.draft_id, candidate.draft_revision)
            assert original.coverage == 'no_numeric_owner_pipeline' and original.checks == []
            assert original.candidate_record_sha256 is None
            facade.verify_review_numeric(conn, identity, original)
        assert table_hashes(database) == before
        remove_catalog_fixture(database, candidate.draft_id)
        before = table_hashes(database)
        with database.transaction(immediate=False) as conn, pytest.raises(ApiError) as caught:
            facade.verify_review_numeric(conn, identity, original)
        assert caught.value.code == 'DRAFT_CANDIDATE_UNREGISTERED'
        assert table_hashes(database) == before


def test_observation_facade_and_private_representations_are_bound_to_real_owner(generated):
    from pydantic import ValidationError
    from services.api.app.application.draft_candidates import DraftCandidates
    from services.api.app.application.review_numeric import ReviewNumeric

    case = generated
    case.preview()
    kind = 'authoring_' + case.variant
    facade = ReviewNumeric(DraftCandidates({kind: case.authoring}), {kind: case.numeric})
    before = table_hashes(case.database)
    with case.database.transaction(immediate=False) as conn:
        conn.execute('PRAGMA query_only=ON')
        original = facade.read_review_numeric(conn, case.identity, case.candidate.draft_id, case.candidate.draft_revision)
        facade.verify_review_numeric(conn, case.identity, original)
    assert table_hashes(case.database) == before
    for item in [original, original.checks[0], original.checks[0].commands[0]]:
        assert repr(item) == type(item).__name__ + '()' and str(item) == ''
        raw = item.model_dump(mode='json')
        raw['unexpected'] = 'zz_numeric_review_private_sentinel'
        with pytest.raises(ValidationError) as caught:
            type(item).model_validate(raw)
        assert 'zz_numeric_review_private_sentinel' not in str(caught.value)
