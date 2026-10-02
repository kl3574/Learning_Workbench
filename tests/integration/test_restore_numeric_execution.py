"""Real worker/ledger state machine with clearly synthetic runtime outcomes.

A separate physical probe records this host's actual sealed evaluator outcome.
"""
from dataclasses import asdict
import pytest
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.authoring_numeric import evaluate_plan
from services.api.app.application.restore_numeric_worker import RestoreNumericWorker
from services.api.app.authoring_dto import NumericCheckResult, numeric_result_sha256
from services.api.app.infrastructure.authoring_numeric_runtime import NumericExecution
from services.api.app.infrastructure.restore_numeric_repository import RestoreNumericRepository
from services.api.app.infrastructure.database import utc_now
from tests.integration.test_restore_numeric_service import restored as restored, preview, BODY
from tests.integration.test_authoring_numeric_service import LedgerRuntime, decision
from tests.integration.test_authoring_http import command
from tests.integration.test_content_restore_http import approve
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from services.api.app.application.content import ContentService


class SyntheticExecution(LedgerRuntime):
    """Protocol test double, not a sandbox or academic approval claim."""
    calls = 0
    after_start = None

    def run_checked(self, value, cancellation, *, on_started=None):
        self.calls += 1
        assert not cancellation()
        start = utc_now()
        on_started(start)
        if self.after_start:
            self.after_start()
        assert not cancellation()
        assertions = [asdict(item) for item in evaluate_plan(value.plan.model_dump(mode='json'))]
        stdout = canonical_bytes(dict(version='numeric-output-v1', isolation=dict(uid=1000, gid=1000,
            network_denied=True, fork_denied=True, exec_denied=True, host_paths_absent=True,
            cpu_limit=2, memory_limit=268435456, output_limit=65536), assertions=assertions))
        raw = dict(job_id=value.job_id, input_sha256=sha256_bytes(canonical_bytes(value)), operation_sha256=value.operation_sha256,
            outcome='passed', verdict='PASS', started_at=start, finished_at=utc_now(), exit_code=0,
            assertions=assertions, output_sha256=sha256_bytes(stdout))
        raw['result_sha256'] = numeric_result_sha256(raw)
        return NumericExecution(NumericCheckResult.model_validate(raw), stdout, b'', True, (), self.manifest_document())


def executed(case):
    runtime = SyntheticExecution()
    case.service.runtime = runtime
    view = preview(case)
    ack = case.service.decide(case.identity, view.id, decision(view), 'approve')
    worker = RestoreNumericWorker(case.database, case.service, runtime)
    assert worker.run_once()
    read = case.service.read(case.identity, view.id)
    assert read.result.verdict == 'PASS' and read.job.status == 'completed'
    assert runtime.calls == 1
    return view, ack, worker, runtime


def test_actual_worker_protocol_fresh_review_and_cas_publication(restored):
    case = restored
    view, ack, worker, runtime = executed(case)
    stale = case.snapshot
    snapshot = case.client.get('/api/v1/content/restore-drafts/' + case.identifier).json()
    assert snapshot['candidate'] == stale['candidate']
    lesson = __import__('packages.contracts.domain_models', fromlist=['Lesson']).Lesson(
        id='pinned_numeric_parent', revision=1, title='Pinned original', objectives=[], block_refs=[case.current])
    content = ContentService(case.database)
    parent = content.publish(case.identity.workspace_id, [lesson], {})[0]
    publish = approve(case, case.identifier, snapshot)
    response = case.client.post(f'/api/v1/drafts/{case.identifier}/publish', json=publish, headers=command(case.headers, 'publish'))
    assert response.status_code == 201, response.text
    assert response.json()['revision'] == 3
    assert content.body(case.identity.workspace_id, case.block.id, 3)[0] == BODY.encode()
    assert content.current(case.identity.workspace_id, parent.id) == parent
    with case.database.connect() as conn:
        row = conn.execute("SELECT record_json FROM draft_publication_results").fetchone()[0]
        assert 'restore-numeric-publication-v1' in row and snapshot['numeric_material']['numeric_material_sha256'] in row
    before = table_hashes(case.database)
    assert case.service.decide(case.identity, view.id, decision(view), 'approve') == ack
    assert preview(case) == view
    assert not worker.run_once() and runtime.calls == 1
    assert case.client.post(f'/api/v1/drafts/{case.identifier}/publish', json=publish, headers=command(case.headers, 'publish')).json() == response.json()
    assert table_hashes(case.database) == before


def test_new_pending_blocks_old_review_but_original_review_stays_readable(restored):
    case = restored
    executed(case)
    publish = approve(case, case.identifier, case.snapshot)
    old = case.client.get('/api/v1/reviews/' + publish['review_receipt_id'])
    assert old.status_code == 200
    preview(case, 'new-pending')
    assert case.client.get('/api/v1/reviews/' + publish['review_receipt_id']).json() == old.json()
    response = case.client.post(f'/api/v1/drafts/{case.identifier}/publish', json=publish, headers=command(case.headers, 'publish'))
    assert response.status_code == 409 and response.json()['error']['code'] == 'PUBLISH_NUMERIC_OBSERVATION_STALE'


@pytest.mark.parametrize('observed', [False, True])
def test_committed_start_recovery_never_reexecutes(restored, observed):
    case = restored
    runtime = SyntheticExecution()
    case.service.runtime = runtime
    view = preview(case)
    case.service.decide(case.identity, view.id, decision(view), 'approve')
    worker = RestoreNumericWorker(case.database, case.service, runtime)
    lease, value, actor = worker.claim()
    with case.database.transaction() as conn:
        repo = RestoreNumericRepository(conn, case.identity.workspace_id)
        assert repo.begin(lease, utc_now())
        if observed:
            repo.mark_started(lease, utc_now())
        conn.execute('UPDATE jobs SET lease_until=? WHERE id=?', ('2000-01-01T00:00:00Z', lease.job_id))
    assert worker.run_once()
    result = case.service.read(case.identity, view.id)
    assert result.result.outcome == 'outcome_unknown' and runtime.calls == 0
    assert bool(result.result.started_at) == observed


@pytest.mark.parametrize('before_start', [True, False])
def test_base_changes_gate_start_but_preserve_actual_terminal_after_start(restored, before_start):
    case = restored
    runtime = SyntheticExecution()
    case.service.runtime = runtime
    view = preview(case)
    case.service.decide(case.identity, view.id, decision(view), 'approve')
    def advance():
        ContentService(case.database).publish(case.identity.workspace_id,
            [case.block.model_copy(update={'revision': 3})], {case.block.body_path: BODY.encode()})
    if before_start:
        advance()
    else:
        runtime.after_start = advance
    worker = RestoreNumericWorker(case.database, case.service, runtime)
    assert worker.run_once()
    result = case.service.read(case.identity, view.id)
    assert result.result.outcome == ('cancelled' if before_start else 'passed')
    assert bool(result.result.started_at) != before_start
    assert runtime.calls == (0 if before_start else 1)
