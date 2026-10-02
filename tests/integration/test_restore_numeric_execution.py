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


class SyntheticFailure(SyntheticExecution):
    outcome = 'mismatch'

    def run_checked(self, value, cancellation, *, on_started=None):
        execution = super().run_checked(value, cancellation, on_started=on_started)
        from packages.contracts.canonical import strict_json
        raw = execution.result.model_dump(mode='json')
        raw.update(outcome=self.outcome, verdict='FAIL' if self.outcome == 'mismatch' else 'BLOCKED')
        if self.outcome == 'mismatch':
            raw['assertions'][0].update(actual=5.0, passed=False)
            output = strict_json(execution.stdout)
            output['assertions'] = raw['assertions']
            stdout = canonical_bytes(output)
        else:
            raw.update(assertions=[], exit_code=-9)
            stdout = b''
        raw['output_sha256'] = sha256_bytes(stdout) if stdout else None
        raw['result_sha256'] = numeric_result_sha256(raw)
        return NumericExecution(NumericCheckResult.model_validate(raw), stdout, b'', True, (), self.manifest_document())


def fresh_publish(case, key='fresh', math='APPROVED'):
    from packages.contracts import domain_models as dm
    from tests.integration.test_publication_admission import reviewed, publish_request
    candidate = dm.DraftCandidate.model_validate(case.snapshot['candidate'])
    receipt = reviewed(case.database, case.identity, candidate, case.app.state.review_service, key=key, math=math)
    return publish_request(case.database, case.identity, candidate, case.app.state.review_service, receipt).model_dump(mode='json')


@pytest.mark.parametrize('newest', ['pending', 'decline', 'mismatch', 'timeout'])
def test_new_review_cannot_skip_newer_nonpass_check(restored, newest):
    case = restored
    executed(case)
    latest = preview(case, 'latest')
    if newest == 'decline':
        case.service.decide(case.identity, latest.id, decision(latest, 'decline'), 'latest-decline')
    elif newest in {'mismatch', 'timeout'}:
        runtime = SyntheticFailure()
        runtime.outcome = newest
        case.service.runtime = runtime
        case.service.decide(case.identity, latest.id, decision(latest), 'latest-approve')
        assert RestoreNumericWorker(case.database, case.service, runtime).run_once()
        assert case.service.read(case.identity, latest.id).result.outcome == newest
    publish = fresh_publish(case)
    before = table_hashes(case.database)
    response = case.client.post(f'/api/v1/drafts/{case.identifier}/publish', json=publish, headers=command(case.headers, 'publish'))
    assert response.status_code == 409 and response.json()['error']['code'] == 'PUBLISH_NUMERIC_REQUIRED'
    assert table_hashes(case.database) == before


def test_published_ack_uses_original_observation_after_later_decline_fact(restored):
    case = restored
    pending = preview(case, 'older-pending')
    executed(case)
    publish = fresh_publish(case)
    path = f'/api/v1/drafts/{case.identifier}/publish'
    published = case.client.post(path, json=publish, headers=command(case.headers, 'publish'))
    assert published.status_code == 201, published.text
    old_review = case.client.get('/api/v1/reviews/' + publish['review_receipt_id']).json()
    case.service.decide(case.identity, pending.id, decision(pending, 'decline'), 'after-publish-decline')
    before = table_hashes(case.database)
    assert case.client.get('/api/v1/reviews/' + publish['review_receipt_id']).json() == old_review
    assert case.client.post(path, json=publish, headers=command(case.headers, 'publish')).json() == published.json()
    assert case.app.state.content_restore_service.read(case.identity, case.identifier).state == 'published'
    assert table_hashes(case.database) == before


@pytest.mark.parametrize('fault', ['math_rejected', 'base_race', 'rollback'])
def test_numeric_pass_cannot_bypass_human_cas_or_atomic_publication(restored, monkeypatch, fault):
    case = restored
    executed(case)
    publish = fresh_publish(case, math='REJECTED' if fault == 'math_rejected' else 'APPROVED')
    if fault == 'base_race':
        ContentService(case.database).publish(case.identity.workspace_id,
            [case.block.model_copy(update={'revision': 3})], {case.block.body_path: BODY.encode()})
    elif fault == 'rollback':
        from services.api.app.application.restore_publication import RestoreBlockPublication
        from services.api.app.application.errors import ApiError
        def fail(*args):
            raise ApiError(409, 'INJECTED_AFTER_CONTENT', 'Synthetic failure after content publication')
        monkeypatch.setattr(RestoreBlockPublication, 'freeze', fail)
    before = table_hashes(case.database)
    response = case.client.post(f'/api/v1/drafts/{case.identifier}/publish', json=publish, headers=command(case.headers, 'publish'))
    assert response.status_code == (412 if fault == 'base_race' else 409), response.text
    assert table_hashes(case.database) == before


def test_bad_complete_output_cannot_commit_pass_or_terminal(restored):
    case = restored
    runtime = SyntheticExecution()
    case.service.runtime = runtime
    view = preview(case)
    case.service.decide(case.identity, view.id, decision(view), 'approve')
    worker = RestoreNumericWorker(case.database, case.service, runtime)
    lease, value, actor = worker.claim()
    with case.database.transaction() as conn:
        RestoreNumericRepository(conn, case.identity.workspace_id).begin(lease, utc_now())
    execution = runtime.run_checked(value, lambda: False, on_started=lambda actual: worker._started(lease, actual))
    raw = execution.result.model_dump(mode='json')
    wrong = b'{}'
    raw['output_sha256'] = sha256_bytes(wrong)
    raw['result_sha256'] = numeric_result_sha256(raw)
    before = table_hashes(case.database)
    from services.api.app.application.errors import ApiError
    with case.database.transaction() as conn:
        with pytest.raises(ApiError) as error:
            RestoreNumericRepository(conn, case.identity.workspace_id).finish(lease,
                NumericCheckResult.model_validate(raw), wrong, b'', True, runtime.manifest_document())
        assert error.value.status == 409
    assert table_hashes(case.database) == before
    worker._finish(lease, execution)
    assert case.service.read(case.identity, view.id).result.verdict == 'PASS'
