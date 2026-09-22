"""Real generated candidate and SQLite numeric ledger; explicit runtime test double.

Generation uses a controlled loopback provider with its exact endpoint proof.
LedgerRuntime never launches processes: these cases do not claim sandbox passes.
"""
import asyncio
from dataclasses import replace
from datetime import datetime, timedelta

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.authoring_numeric_service import NumericService
from services.api.app.application.errors import ApiError
from services.api.app.authoring_dto import NumericCheckPreviewWrite, NumericCheckResult, NumericRuntimeProfile, numeric_result_sha256
from services.api.app.import_dto import JobCancelRequest
from services.api.app.infrastructure.authoring_numeric_runtime import NumericRuntimeError
from services.api.app.infrastructure.authoring_numeric_repository import NumericRepository
from services.api.app.infrastructure.database import utc_now
from tests.integration.test_authoring_provider import approved, configured, payload
from tests.integration.test_retrieval import all_rows
from tests.provider_protocol_fixture import local_provider


class LedgerRuntime:
    """A clearly labelled frozen test runtime; no physical isolation assertion."""
    def __init__(self):
        self.changed = False
        self.prepares = 0
        self.checks = 0

    def prepare(self):
        self.prepares += 1
        return NumericRuntimeProfile(evaluator_version='finite-arithmetic-v1', evaluator_sha256='b'*64,
            runtime_manifest_sha256=sha256_bytes(self.manifest_document()), python_version='synthetic-ledger-only',
            sandbox_version='not-executed', wall_seconds=5, cpu_seconds=2, memory_bytes=268435456,
            output_bytes=65536, evaluator_process_limit=1)

    def manifest_document(self):
        return canonical_bytes({'format':'synthetic-ledger-manifest-v1','execution':'never'})

    def check(self, profile):
        self.checks += 1
        if self.changed:
            raise NumericRuntimeError('NUMERIC_RUNTIME_CHANGED')


class Generated(tuple):
    def __repr__(self):
        return '<controlled fixture: actual candidate and SQLite; no identity repr>'


@pytest.fixture
def generated(tmp_path):
    async def build():
        async with local_provider(text=canonical_bytes(payload()).decode()) as server:
            state = configured(tmp_path, server.base_url)
            database, identity, authoring, worker, _, _ = state
            original, _, _ = await asyncio.to_thread(approved, state)
            assert await asyncio.to_thread(worker.run_once)
            candidate = authoring.read(identity, original.id).summary.candidate
            assert candidate is not None and len(server.requests) == 1
            runtime = LedgerRuntime()
            return Generated((database, identity, authoring, NumericService(database, authoring.context, runtime, authoring=authoring), candidate, runtime))
    return asyncio.run(build())


def decision(view, action='approve_once', revision=1):
    return dm.ApprovalDecision(operation_sha256=view.operation_sha256, decision=action, expected_revision=revision)


def test_preview_is_no_execution_and_decline_replay_is_original_after_expiry(generated, monkeypatch):
    database, identity, authoring, service, candidate, runtime = generated
    before = all_rows(database)
    view = service.preview(identity, candidate.draft_id, NumericCheckPreviewWrite(candidate=candidate), 'preview')
    with database.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM jobs WHERE kind='authoring_numeric_check'").fetchone()[0] == 0
        assert conn.execute('SELECT COUNT(*) FROM authoring_numeric_executions').fetchone()[0] == 0
    stable = all_rows(database)
    assert service.read(identity, view.id) == view
    assert all_rows(database) == stable and stable != before
    from services.api.app.application import authoring_numeric_service as mod
    from services.api.app.infrastructure import authoring_numeric_repository as repo_mod
    monkeypatch.setattr(mod, 'utc_now', lambda: '2099-01-01T00:00:00Z')
    monkeypatch.setattr(repo_mod, 'utc_now', lambda: '2099-01-01T00:00:00Z')
    expired = service.read(identity, view.id)
    assert expired.expired and expired.revision == 1 and expired.job is None
    with pytest.raises(ApiError) as caught:
        service.decide(identity, view.id, decision(view), 'expired-approve')
    assert caught.value.code == 'NUMERIC_APPROVAL_EXPIRED'
    declined = service.decide(identity, view.id, decision(view, 'decline'), 'decline')
    assert declined.job is None and declined.revision == 2
    runtime.changed = True
    assert service.decide(identity, view.id, decision(view, 'decline'), 'decline') == declined
    assert service.preview(identity, candidate.draft_id, NumericCheckPreviewWrite(candidate=candidate), 'preview') == view
    assert runtime.prepares == 1 and runtime.checks == 0
    assert authoring.draft(identity, candidate.draft_id).state == 'draft'


def test_approve_exact_operation_runtime_original_ack_and_safe_queued_cancel(generated):
    database, identity, _, service, candidate, runtime = generated
    body = NumericCheckPreviewWrite(candidate=candidate)
    view = service.preview(identity, candidate.draft_id, body, 'preview')
    with pytest.raises(ApiError) as caught:
        service.decide(identity, view.id, decision(view, revision=2), 'bad-revision')
    assert caught.value.status == 412
    runtime.changed = True
    with pytest.raises(ApiError) as caught:
        service.decide(identity, view.id, decision(view), 'changed-runtime')
    assert caught.value.code == 'NUMERIC_RUNTIME_CHANGED'
    runtime.changed = False
    ack = service.decide(identity, view.id, decision(view), 'approve')
    assert ack.job.status == 'queued'
    original_cancel = JobCancelRequest(expected_revision=1)
    learner = replace(identity, role='learner')
    with pytest.raises(ApiError) as caught:
        service.read(learner, view.id)
    assert caught.value.status == 403
    control = service.job(learner, ack.job.id)
    assert control.kind == 'authoring_numeric_check' and control.progress.label == 'queued'
    assert control.result_refs == control.warnings == [] and control.error is None
    cancelled = service.cancel_job(learner, ack.job.id, original_cancel, 'cancel')
    assert cancelled.status == 'cancelled' and cancelled.revision == 2
    stable = all_rows(database)
    assert service.cancel_job(learner, ack.job.id, original_cancel, 'cancel') == cancelled
    runtime.changed = True
    assert service.decide(identity, view.id, decision(view), 'approve') == ack
    actual = service.read(identity, view.id)
    assert actual.job.status == 'cancelled' and actual.result.outcome == 'cancelled'
    assert actual.result.started_at is None and actual.result.assertions == []
    assert actual.revision == 2 and actual.job_revision == 2
    assert all_rows(database) == stable


def test_missing_preview_membership_cannot_free_a_slot_for_new_preview(generated):
    database, identity, _, service, candidate, _ = generated
    body = NumericCheckPreviewWrite(candidate=candidate)
    original = service.preview(identity, candidate.draft_id, body, 'preview-one')
    with database.transaction() as conn:
        conn.execute('DELETE FROM authoring_numeric_checks WHERE check_id=?', (original.id,))
    before = all_rows(database)
    with pytest.raises(ApiError) as caught:
        service.preview(identity, candidate.draft_id, body, 'preview-two')
    assert caught.value.code == 'AUTHORING_INTEGRITY_ERROR'
    assert all_rows(database) == before


def blocked_result(job, outcome, started_at=None):
    value = dict(job_id=job.job_id, input_sha256=sha256_bytes(canonical_bytes(job)),
        operation_sha256=job.operation_sha256, outcome=outcome, verdict='BLOCKED',
        started_at=started_at, finished_at=utc_now(), exit_code=None, assertions=[],
        output_sha256=None, result_sha256='0'*64)
    value['result_sha256'] = numeric_result_sha256(value)
    return NumericCheckResult.model_validate(value)


def test_committed_launch_permission_survives_restart_without_claiming_process_start(generated, monkeypatch):
    database, identity, _, service, candidate, _ = generated
    view = service.preview(identity, candidate.draft_id, NumericCheckPreviewWrite(candidate=candidate), 'preview')
    ack = service.decide(identity, view.id, decision(view), 'approve')
    with database.transaction() as conn:
        repo = NumericRepository(conn, identity.workspace_id)
        lease, job, actor = repo.claim(ack.job.id)
        assert actor == identity.id
        assert repo.execution_state(job.job_id) == (None, None)
        assert repo.begin(lease, utc_now())
    # A fresh owner instance sees durable permission, with no fabricated Popen fact.
    with database.transaction() as conn:
        repo = NumericRepository(conn, identity.workspace_id)
        start, end = repo.execution_state(job.job_id)
        assert start.admitted_at is not None and start.actual_started_at is None and end is None
        assert not repo.begin(lease, utc_now())
    future = datetime.fromisoformat(lease.expires_at.replace('Z', '+00:00')) + timedelta(seconds=1)
    from services.api.app.infrastructure import authoring_job_repository as jobs_module
    monkeypatch.setattr(jobs_module, 'utc_now', lambda: future.isoformat().replace('+00:00', 'Z'))
    monkeypatch.setattr(jobs_module, 'expires_after', lambda seconds: (future + timedelta(seconds=seconds)).isoformat().replace('+00:00', 'Z'))
    with database.transaction() as conn:
        repo = NumericRepository(conn, identity.workspace_id)
        recovery, same_job, _ = repo.claim(job.job_id)
        assert same_job == job and recovery.owner != lease.owner
        assert not repo.begin(recovery, jobs_module.utc_now())
        result = blocked_result(job, 'outcome_unknown')
        terminal = repo.finish(recovery, result)
        assert terminal.job.status == 'failed' and terminal.result.started_at is None
    original = all_rows(database)
    assert service.decide(identity, view.id, decision(view), 'approve') == ack
    assert service.read(identity, view.id).result == result
    with database.transaction() as conn:
        repo = NumericRepository(conn, identity.workspace_id)
        with pytest.raises(ApiError):
            repo.finish(lease, result)
    assert all_rows(database) == original


def completed_result(job, started_at, stdout, *, actual=42.0):
    value = dict(job_id=job.job_id, input_sha256=sha256_bytes(canonical_bytes(job)),
        operation_sha256=job.operation_sha256, outcome='passed', verdict='PASS',
        started_at=started_at, finished_at=utc_now(), exit_code=0,
        assertions=[dict(id='sum_check', actual=actual, passed=True, error_code=None)],
        output_sha256=sha256_bytes(stdout), result_sha256='0'*64)
    value['result_sha256'] = numeric_result_sha256(value)
    return NumericCheckResult.model_validate(value)


def test_rejected_result_cannot_leave_terminal_bytes_when_caller_handles_error(generated):
    database, identity, _, service, candidate, runtime = generated
    view = service.preview(identity, candidate.draft_id, NumericCheckPreviewWrite(candidate=candidate), 'preview')
    ack = service.decide(identity, view.id, decision(view), 'approve')
    with database.transaction() as conn:
        repo = NumericRepository(conn, identity.workspace_id)
        lease, job, _ = repo.claim(ack.job.id)
        assert repo.begin(lease, utc_now())
        actual_start = utc_now()
        repo.mark_started(lease, actual_start)
    before = all_rows(database)
    stdout = b'{"synthetic_ledger_result":42}\n'
    wrong = completed_result(job, actual_start, stdout, actual=41.0)
    with database.transaction() as conn:
        repo = NumericRepository(conn, identity.workspace_id)
        with pytest.raises((ApiError, ValueError)):
            repo.finish(lease, wrong, stdout, b'', True, runtime.manifest_document())
    assert all_rows(database) == before
    right = completed_result(job, actual_start, stdout)
    with database.transaction() as conn:
        repo = NumericRepository(conn, identity.workspace_id)
        result = repo.finish(lease, right, stdout, b'controlled private stderr', True, runtime.manifest_document())
        assert result.job.status == 'completed' and result.result == right
    assert service.read(identity, view.id).result.assertions[0].actual == 42.0


def test_running_cancel_keeps_launch_owner_and_original_ack_after_terminal(generated):
    database, identity, _, service, candidate, runtime = generated
    view = service.preview(identity, candidate.draft_id, NumericCheckPreviewWrite(candidate=candidate), 'preview')
    ack = service.decide(identity, view.id, decision(view), 'approve')
    with database.transaction() as conn:
        repo = NumericRepository(conn, identity.workspace_id)
        lease, job, _ = repo.claim(ack.job.id)
        assert repo.begin(lease, utc_now())
    learner = replace(identity, role='learner')
    command = JobCancelRequest(expected_revision=lease.revision)
    cancelling = service.cancel_job(learner, job.job_id, command, 'running-cancel')
    assert cancelling.status == 'running' and cancelling.revision == lease.revision + 1
    with database.transaction() as conn:
        repo = NumericRepository(conn, identity.workspace_id)
        actual = utc_now()
        repo.mark_started(lease, actual)  # Popen may already have happened when cancel arrived.
        result = blocked_result(job, 'cancelled', actual)
        done = repo.finish(lease, result, manifest_json=runtime.manifest_document())
        assert done.job.status == 'cancelled' and done.result.started_at == actual
    before = all_rows(database)
    assert service.cancel_job(learner, job.job_id, command, 'running-cancel') == cancelling
    assert service.job(learner, job.job_id).revision == cancelling.revision + 1
    assert all_rows(database) == before
    noop = service.cancel_job(learner, job.job_id, command, 'terminal-noop')
    assert noop.status == 'cancelled'
    assert service.cancel_job(learner, job.job_id, command, 'terminal-noop') == noop


@pytest.mark.parametrize('damage', ['cancel_command', 'context', 'manifest'])
def test_safe_control_and_original_ack_fail_closed_on_owned_history_damage(generated, damage):
    database, identity, _, service, candidate, _ = generated
    view = service.preview(identity, candidate.draft_id, NumericCheckPreviewWrite(candidate=candidate), 'preview')
    ack = service.decide(identity, view.id, decision(view), 'approve')
    cancel = JobCancelRequest(expected_revision=1)
    service.cancel_job(identity, ack.job.id, cancel, 'cancel')
    import json
    with database.transaction() as conn:
        if damage == 'cancel_command':
            row = conn.execute("SELECT request_json FROM authoring_commands WHERE owner_id=? AND key='cancel'", (view.id,)).fetchone()
            value = json.loads(row[0])
            value['expected_revision'] = 19
            raw = canonical_bytes(value).decode()
            conn.execute("UPDATE authoring_commands SET request_json=?,request_sha256=? WHERE owner_id=? AND key='cancel'", (raw, sha256_bytes(raw.encode()), view.id))
        elif damage == 'context':
            conn.execute("UPDATE context_snapshots SET snapshot_sha256=?", ('e'*64,))
        else:
            row = conn.execute('SELECT record_json FROM authoring_numeric_checks WHERE check_id=?', (view.id,)).fetchone()
            value = json.loads(row[0])
            value['runtime_manifest_json'] = canonical_bytes({'format':'tampered-but-canonical'}).decode()
            raw = canonical_bytes(value).decode()
            conn.execute('UPDATE authoring_numeric_checks SET record_json=?,record_sha256=? WHERE check_id=?', (raw, sha256_bytes(raw.encode()), view.id))
    before = all_rows(database)
    learner = replace(identity, role='learner')
    with pytest.raises(ApiError) as caught:
        service.job(learner, ack.job.id)
    assert caught.value.code == 'AUTHORING_INTEGRITY_ERROR'
    with pytest.raises(ApiError):
        service.cancel_job(learner, ack.job.id, cancel, 'cancel')
    assert all_rows(database) == before


def test_actual_runtime_manifest_preview_approval_without_process_execution(generated, monkeypatch):
    from services.api.app.infrastructure.authoring_numeric_runtime import NumericRuntime
    database, identity, authoring, _, candidate, _ = generated
    import subprocess
    def forbidden(*args, **kwargs):
        pytest.fail('numeric preview and approval must not spawn a process')
    monkeypatch.setattr(subprocess, 'Popen', forbidden)
    runtime = NumericRuntime()
    service = NumericService(database, authoring.context, runtime, authoring=authoring)
    view = service.preview(identity, candidate.draft_id, NumericCheckPreviewWrite(candidate=candidate), 'actual-manifest')
    manifest = runtime.manifest_document()
    assert sha256_bytes(manifest) == view.runtime.runtime_manifest_sha256
    ack = service.decide(identity, view.id, decision(view), 'approve-actual-manifest')
    with database.transaction(immediate=False) as conn:
        repo = NumericRepository(conn, identity.workspace_id)
        assert repo.load(view.id).runtime_manifest_json.encode() == manifest
        assert repo.execution_state(ack.job.id) == (None, None)
    assert service.job(identity, ack.job.id).status == 'queued'


def test_one_hundred_previews_include_expired_and_declined_without_deleting_history(generated, monkeypatch):
    database, identity, _, service, candidate, _ = generated
    body = NumericCheckPreviewWrite(candidate=candidate)
    previews = [service.preview(identity, candidate.draft_id, body, f'preview-{index}') for index in range(100)]
    from services.api.app.application import authoring_numeric_service as service_module
    from services.api.app.infrastructure import authoring_numeric_repository as repo_module
    monkeypatch.setattr(service_module, 'utc_now', lambda: '2099-01-01T00:00:00Z')
    monkeypatch.setattr(repo_module, 'utc_now', lambda: '2099-01-01T00:00:00Z')
    declined = service.decide(identity, previews[0].id, decision(previews[0], 'decline'), 'decline-first')
    before = all_rows(database)
    with pytest.raises(ApiError) as caught:
        service.preview(identity, candidate.draft_id, body, 'preview-101')
    assert caught.value.code == 'NUMERIC_PREVIEW_LIMIT'
    assert service.preview(identity, candidate.draft_id, body, 'preview-0') == previews[0]
    assert service.decide(identity, previews[0].id, decision(previews[0], 'decline'), 'decline-first') == declined
    assert service.read(identity, previews[-1].id).expired
    assert all_rows(database) == before
