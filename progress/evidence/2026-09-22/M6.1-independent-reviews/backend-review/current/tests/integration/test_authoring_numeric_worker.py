"""Actual numeric owner scheduling and crash ledger; no fake execution success."""
from dataclasses import replace

import pytest
from services.api.app.application.authoring_numeric_worker import NumericWorker
from services.api.app.application.sessions import SessionService
from services.api.app.authoring_dto import NumericCheckPreviewWrite
from services.api.app.dto import RoleRequest
from services.api.app.infrastructure.authoring_numeric_repository import NumericRepository
from services.api.app.infrastructure.database import utc_now
from tests.integration.test_authoring_numeric_service import generated as shared_generated, decision
from tests.integration.test_retrieval import all_rows


@pytest.fixture
def generated(tmp_path):
    return shared_generated.__wrapped__(tmp_path)


def approved_numeric(generated):
    _, identity, _, numeric, candidate, _ = generated
    view = numeric.preview(identity, candidate.draft_id, NumericCheckPreviewWrite(candidate=candidate), 'preview')
    return view, numeric.decide(identity, view.id, decision(view), 'approve')


@pytest.mark.parametrize('observed_start', [False, True])
def test_numeric_recovery_of_committed_launch_never_executes_again(generated, monkeypatch, observed_start):
    database, identity, authoring, numeric, _, runtime = generated
    view, ack = approved_numeric(generated)
    worker = NumericWorker(database, authoring.context, runtime, authoring=authoring)
    work = worker.claim()
    assert work is not None
    lease, _, _ = work
    with database.transaction() as conn:
        repo = NumericRepository(conn, identity.workspace_id)
        assert repo.begin(lease, utc_now())
        actual = utc_now() if observed_start else None
        if actual is not None:
            repo.mark_started(lease, actual)
        # A controlled crash fixture expires only the prior owner's lease.
        conn.execute('UPDATE jobs SET lease_until=? WHERE id=?', ('2000-01-01T00:00:00Z', lease.job_id))
    def forbidden(*args, **kwargs):
        pytest.fail('a committed launch permission must not be sent to any new executor')
    monkeypatch.setattr(runtime, 'run_checked', forbidden, raising=False)
    assert worker.run_once()
    result = numeric.read(identity, view.id)
    assert result.job.status == 'failed' and result.result.outcome == 'outcome_unknown'
    assert result.result.started_at == actual and result.result.exit_code is None
    before = all_rows(database)
    assert numeric.decide(identity, view.id, decision(view), 'approve') == ack
    assert not worker.run_once()
    assert all_rows(database) == before


def test_current_grant_actor_demotion_stops_numeric_before_start_permission(generated, monkeypatch):
    database, identity, authoring, numeric, _, runtime = generated
    view, _ = approved_numeric(generated)
    SessionService(database).switch_role(identity, RoleRequest(role='learner'), 'demote')
    def forbidden(*args, **kwargs):
        pytest.fail('a demoted original author cannot begin numerical execution')
    monkeypatch.setattr(runtime, 'run_checked', forbidden, raising=False)
    worker = NumericWorker(database, authoring.context, runtime, authoring=authoring)
    assert worker.run_once()
    with database.transaction(immediate=False) as conn:
        repo = NumericRepository(conn, identity.workspace_id)
        actual = repo.current(view.id)
        start, end = repo.execution_state(actual.job.id)
        assert start.admitted_at is start.actual_started_at is None
        assert end.result.outcome == 'cancelled' and end.result.verdict == 'BLOCKED'
    safe = numeric.job(replace(identity, role='learner'), actual.job.id)
    assert safe.status == 'cancelled' and safe.result_refs == []
