"""Actual group scheduling, durable launch admission and real blocked runtime.

Crash observation timestamps in recovery fixtures are explicit ledger faults;
only the separate real-runtime case claims an observed physical process result.
"""

import base64
from dataclasses import replace
from pathlib import Path

import pytest

from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.authoring_group_numeric_service import GroupNumericService
from services.api.app.application.authoring_group_numeric_worker import GroupNumericWorker
from services.api.app.application.sessions import SessionService
from services.api.app.authoring_group_dto import AuthoringGroupNumericPreviewWrite
from services.api.app.import_dto import JobCancelRequest
from services.api.app.infrastructure.authoring_group_numeric_repository import GroupNumericRepository
from services.api.app.infrastructure.authoring_numeric_runtime import NumericRuntime
from services.api.app.infrastructure.database import Database, utc_now
from tests.integration.test_authoring_group_numeric_service import generated_group, preview
from tests.integration.test_authoring_numeric_service import decision
from tests.integration.test_retrieval import all_rows


@pytest.fixture
def generated(tmp_path):
    return generated_group(tmp_path)


@pytest.mark.parametrize('observed_start', [False, True])
@pytest.mark.parametrize('cancel_requested', [False, True])
def test_restart_after_committed_permission_never_reexecutes_even_with_cancel(generated, monkeypatch, observed_start, cancel_requested):
    database, identity, authoring, numeric, candidate, _, runtime = generated
    generation = authoring.read(identity, authoring.draft(identity, candidate.draft_id).source_job_id)
    view = preview(generated)
    ack = numeric.decide(identity, view.id, decision(view), 'approve')
    worker = GroupNumericWorker(database, authoring.context, runtime, authoring=authoring)
    lease, job, actor = worker.claim()
    assert actor == identity.id
    with database.transaction() as conn:
        repo = GroupNumericRepository(conn, identity.workspace_id)
        assert repo.begin(lease, utc_now())
        actual = utc_now() if observed_start else None
        if actual is not None:
            repo.mark_started(lease, actual)
    learner = replace(identity, role='learner')
    command = JobCancelRequest(expected_revision=lease.revision)
    cancel_ack = numeric.cancel_job(learner, job.job_id, command, 'cancel-after-admission') if cancel_requested else None
    with database.transaction() as conn:
        # Explicit crash fixture expires only the previous owner's real lease.
        conn.execute('UPDATE jobs SET lease_until=? WHERE id=?', ('2000-01-01T00:00:00Z', job.job_id))

    def forbidden(*args, **kwargs):
        pytest.fail('a committed permission cannot be submitted to another executor')

    monkeypatch.setattr(runtime, 'run_checked', forbidden, raising=False)
    restarted = GroupNumericWorker(Database(database.settings), authoring.context, runtime, authoring=authoring)
    assert restarted.run_once()
    current = numeric.read(identity, view.id)
    assert current.job.status == 'failed' and current.result.outcome == 'outcome_unknown'
    assert current.result.verdict == 'BLOCKED' and current.result.started_at == actual
    assert current.result.exit_code is current.result.output_sha256 is None and current.result.assertions == []
    with database.transaction(immediate=False) as conn:
        repo = GroupNumericRepository(conn, identity.workspace_id)
        start, end = repo.execution_state(job.job_id)
        assert start.lease_owner == lease.owner and start.actual_started_at == actual
        assert end.result == current.result
        assert conn.execute('SELECT COUNT(*) FROM authoring_numeric_executions WHERE job_id=?', (job.job_id,)).fetchone()[0] == 1
    before = all_rows(database)
    assert numeric.decide(identity, view.id, decision(view), 'approve') == ack
    if cancel_ack is not None:
        assert numeric.cancel_job(learner, job.job_id, command, 'cancel-after-admission') == cancel_ack
    assert not restarted.run_once() and all_rows(database) == before
    assert authoring.read(identity, generation.summary.id) == generation


def test_revoked_original_approver_cannot_start_member_execution(generated, monkeypatch):
    database, identity, authoring, numeric, _, _, runtime = generated
    view = preview(generated)
    ack = numeric.decide(identity, view.id, decision(view), 'approve')
    SessionService(database).logout(identity)
    monkeypatch.setattr(runtime, 'run_checked', lambda *args, **kwargs: pytest.fail('revoked author started process'), raising=False)
    worker = GroupNumericWorker(database, authoring.context, runtime, authoring=authoring)
    assert worker.run_once()
    with database.transaction(immediate=False) as conn:
        repo = GroupNumericRepository(conn, identity.workspace_id)
        start, end = repo.execution_state(ack.job.id)
        assert start.admitted_at is start.actual_started_at is None
        assert end.result.outcome == 'cancelled' and end.result.verdict == 'BLOCKED'
    safe = numeric.job(replace(identity, role='learner'), ack.job.id)
    assert safe.status == 'cancelled' and safe.result_refs == [] and safe.error is None


def test_real_group_worker_records_actual_environment_block_without_claiming_numeric_pass(generated):
    database, identity, authoring, _, candidate, target, _ = generated
    runtime = NumericRuntime()
    numeric = GroupNumericService(database, authoring.context, runtime, authoring=authoring)
    view = numeric.preview(identity, candidate.draft_id, target.member_key,
        AuthoringGroupNumericPreviewWrite(candidate=candidate, target=target), 'real-environment')
    ack = numeric.decide(identity, view.id, decision(view), 'approve-real-environment')
    worker = GroupNumericWorker(database, authoring.context, runtime, authoring=authoring)
    assert worker.run_once()
    current = numeric.read(identity, view.id)
    assert current.job.status == 'failed' and current.result.outcome == 'environment_unavailable'
    assert current.result.verdict == 'BLOCKED' and current.result.assertions == []
    with database.transaction(immediate=False) as conn:
        repo = GroupNumericRepository(conn, identity.workspace_id)
        start, end = repo.execution_state(ack.job.id)
        assert start.admitted_at is not None and start.actual_started_at == current.result.started_at
        stdout, stderr = base64.b64decode(end.stdout_base64), base64.b64decode(end.stderr_base64)
        assert stderr == b'bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted\n'
        assert Path('/proc/sys/kernel/apparmor_restrict_unprivileged_userns').read_text().strip() == '1'
        assert current.result.started_at is not None and current.result.exit_code != 0
        assert current.result.input_sha256 == sha256_bytes(canonical_bytes(repo.job_input(ack.job.id)))
        assert current.result.output_sha256 == (sha256_bytes(stdout) if end.output_complete and stdout else None)
    before = all_rows(database)
    assert numeric.decide(identity, view.id, decision(view), 'approve-real-environment') == ack
    assert not worker.run_once() and all_rows(database) == before
    assert authoring.draft(identity, candidate.draft_id).candidate == candidate
