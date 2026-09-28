"""Real local review workflow; all human intent in these tests is synthetic."""
import pytest
from dataclasses import replace
import json

from packages.contracts.canonical import canonical_bytes
from services.api.app.application.artifacts import ArtifactsService
from services.api.app.application.errors import ApiError
from services.api.app.application.draft_candidates import DraftCandidates
from services.api.app.application.imports import ImportService, IMPORT_ARTIFACT_PROFILES
from services.api.app.application.review_numeric import ReviewNumeric
from services.api.app.application.review_service import ReviewService
from services.api.app.application.review_worker import ReviewWorker
from services.api.app.review_dto import DraftReviewWrite
from services.api.app.review_dto import ReviewDecisionWrite
from services.api.app.import_dto import JobCancelRequest
from services.api.app.infrastructure.review_repository import ReviewRepository
from tests.integration.test_draft_candidate_owners import imported_candidate as imported_fixture
from tests.integration.test_authoring_numeric_provider_history import ProviderHistoryCase, table_hashes


class Workflow(tuple):
    def __repr__(self):
        return 'SyntheticReviewWorkflow()'


@pytest.fixture
def workflow(tmp_path):
    for database, identity, _, _, _, candidate in imported_fixture.__wrapped__(tmp_path):
        imports = ImportService(database)
        candidates = DraftCandidates({'import': imports})
        service = ReviewService(database, candidates, ReviewNumeric(candidates, {}),
            {(profile, 'import'): imports for profile in IMPORT_ARTIFACT_PROFILES})
        yield Workflow((database, identity, candidate, service, ReviewWorker(service)))


def request(candidate):
    return DraftReviewWrite(expected_revision=candidate.draft_revision,
        checks=['structure', 'sources', 'mathematics', 'numerical_examples'], reviewer_note='Synthetic fixture intent')


def test_real_create_worker_receipt_and_registered_report_reader(workflow):
    database, identity, candidate, service, worker = workflow
    ack = service.create(identity, candidate.draft_id, request(candidate), 'create')
    assert ack.status == 'queued'
    assert worker.run_once()
    receipt = service.read(identity, ack.id)
    assert receipt.candidate == candidate
    assert receipt.mathematical == receipt.sources == receipt.independent_pedagogy == 'NOT_RUN'
    assert receipt.structural == 'PASS'
    assert service.create(identity, candidate.draft_id, request(candidate), 'create') == ack
    assert service.read_job(identity, ack.id).status == 'completed'
    with database.transaction(immediate=False) as conn:
        raw, artifact = service.read_artifact(conn, identity, receipt.evidence_paths[0].split('/')[-2])
    assert artifact.media_type == 'application/json'
    assert b'no_numeric_owner_pipeline' in raw and b'NOT_RUN' in raw
    assert worker.run_once() is False


def completed(workflow, key='create'):
    _, identity, candidate, service, worker = workflow
    ack = service.create(identity, candidate.draft_id, request(candidate), key)
    assert worker.run_once()
    return ack, service.read(identity, ack.id)


def decision(receipt, artifacts=(), **changes):
    return ReviewDecisionWrite(**dict(expected_revision=receipt.revision,
        candidate_sha256=receipt.candidate.candidate_sha256, mathematical='APPROVED', sources='REJECTED',
        reason='Synthetic explicit human decision fixture; not real content approval', evidence_artifact_ids=list(artifacts)) | changes)


def test_synthetic_explicit_decisions_keep_original_actor_history_and_replay(workflow):
    database, identity, candidate, service, _ = workflow
    ack, original = completed(workflow)
    with database.connect() as conn:
        evidence = conn.execute("SELECT id FROM artifacts WHERE profile='import_original'").fetchone()[0]
    body = decision(original, [evidence])
    accepted = service.decide(identity, ack.id, body, 'human-first')
    assert accepted.revision == 2 and accepted.reviewer == identity.id
    assert accepted.created_at == original.created_at and accepted.structural == original.structural
    assert accepted.evidence_paths == [*original.evidence_paths, f'/api/v1/artifacts/{evidence}/download']
    refused = service.decide(identity, ack.id, decision(accepted, mathematical='REJECTED'), 'human-second')
    assert refused.revision == 3 and refused.mathematical == 'REJECTED'
    assert service.decide(identity, ack.id, body, 'human-first') == accepted
    assert service.read(identity, ack.id) == refused
    assert service.create(identity, candidate.draft_id, request(candidate), 'create') == ack
    with database.transaction() as conn:
        history = ReviewRepository(conn, identity.workspace_id).load(ack.id)
        assert [record.receipt for record in history.records] == [original, accepted, refused]


@pytest.mark.parametrize('operation', ['create', 'read', 'decide', 'artifact'])
@pytest.mark.parametrize('change', ['revoked', 'expired', 'role', 'workspace'])
def test_current_session_changes_reject_subject_reads_and_replays(workflow, operation, change):
    database, identity, candidate, service, _ = workflow
    ack, receipt = completed(workflow)
    body = decision(receipt)
    service.decide(identity, ack.id, body, 'human')
    with database.transaction() as conn:
        if change == 'workspace':
            identity = replace(identity, workspace_id='workspace_missing')
        elif change == 'revoked':
            conn.execute("UPDATE local_sessions SET revoked_at='2000-01-01T00:00:00Z'")
        elif change == 'expired':
            conn.execute("UPDATE local_sessions SET expires_at='2000-01-01T00:00:00Z'")
        else:
            conn.execute("UPDATE local_sessions SET role='learner'")
    before = table_hashes(database)
    with pytest.raises(ApiError):
        if operation == 'create':
            service.create(identity, candidate.draft_id, request(candidate), 'create')
        elif operation == 'read':
            service.read(identity, ack.id)
        elif operation == 'decide':
            service.decide(identity, ack.id, body, 'human')
        else:
            ArtifactsService(database, service.readers()).download(identity, receipt.evidence_paths[0].split('/')[-2])
    assert table_hashes(database) == before


@pytest.mark.parametrize('mode', ['independent', 'open_book', 'assisted'])
def test_current_real_assessment_policy_blocks_receipt_decision_and_private_report(workflow, mode):
    from services.api.app.application.assessment import AssessmentService
    from services.api.app.assessment_dto import AssessmentAttemptCreate
    from services.api.app.infrastructure.content_repository import reference
    from tests.assessment_fixtures import assessment_fixture
    from tests.integration.test_assessment_attempts import import_fixture
    database, identity, _, service, _ = workflow
    ack, receipt = completed(workflow)
    fixture = assessment_fixture('reviewworkflow')
    import_fixture(database, identity, fixture, 'assessment-material')
    AssessmentService(database).create_attempt(identity, fixture.assessment.id,
        AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode=mode), 'attempt')
    before = table_hashes(database)
    for call in [lambda: service.read(identity, ack.id), lambda: service.decide(identity, ack.id, decision(receipt), 'human'),
                 lambda: ArtifactsService(database, service.readers()).download(identity, receipt.evidence_paths[0].split('/')[-2])]:
        with pytest.raises(ApiError):
            call()
    assert service.read_job(identity, ack.id).status == 'completed'
    assert table_hashes(database) == before


@pytest.mark.parametrize('running', [False, True])
def test_role_reduction_keeps_safe_control_and_single_cancel_terminal(workflow, running):
    database, identity, candidate, service, worker = workflow
    ack = service.create(identity, candidate.draft_id, request(candidate), 'create')
    lease = worker.claim() if running else None
    with database.transaction() as conn:
        conn.execute("UPDATE local_sessions SET role='learner'")
    current = service.read_job(identity, ack.id)
    body = JobCancelRequest(expected_revision=current.revision)
    cancelled = service.cancel(identity, ack.id, body, 'cancel')
    if lease:
        worker.finish(lease)
    assert service.read_job(identity, ack.id).status == 'cancelled'
    assert service.cancel(identity, ack.id, body, 'cancel') == cancelled
    assert 'Synthetic fixture intent' not in canonical_bytes(cancelled).decode()
    with database.connect() as conn:
        assert conn.execute('SELECT count(*) FROM reviews').fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM artifacts WHERE profile='quality_review_report'").fetchone()[0] == 0


def test_pending_receipt_and_stale_or_different_commands_do_not_change_history(workflow):
    database, identity, candidate, service, worker = workflow
    ack = service.create(identity, candidate.draft_id, request(candidate), 'create')
    with pytest.raises(ApiError) as pending:
        service.read(identity, ack.id)
    assert pending.value.code == 'REVIEW_NOT_READY'
    changed = request(candidate).model_copy(update={'reviewer_note':'different explicit intent'})
    before = table_hashes(database)
    with pytest.raises(ApiError) as conflict:
        service.create(identity, candidate.draft_id, changed, 'create')
    assert conflict.value.code == 'IDEMPOTENCY_CONFLICT' and table_hashes(database) == before
    assert worker.run_once()
    receipt = service.read(identity, ack.id)
    service.decide(identity, ack.id, decision(receipt), 'first')
    before = table_hashes(database)
    with pytest.raises(ApiError) as stale:
        service.decide(identity, ack.id, decision(receipt), 'second')
    assert stale.value.status == 412 and table_hashes(database) == before


def test_plain_nonmathematical_content_allows_explicit_human_na_with_original_reason(workflow):
    database, identity, _, service, _ = workflow
    ack, receipt = completed(workflow)
    reason = 'Synthetic explicit judgment: this candidate is only a source heading, not mathematical content.'
    body = decision(receipt, mathematical='NOT_APPLICABLE', reason=reason)
    result = service.decide(identity, ack.id, body, 'not-applicable')
    assert result.mathematical == 'NOT_APPLICABLE' and result.reviewer == identity.id
    assert result.decision_reason == reason and result.candidate == receipt.candidate
    with database.transaction() as conn:
        history = ReviewRepository(conn, identity.workspace_id).load(ack.id)
        assert history.records[0].receipt.mathematical == 'NOT_RUN'
        assert history.records[1].request == body
    assert service.decide(identity, ack.id, body, 'not-applicable') == result


@pytest.mark.parametrize('fault', ['blob_write', 'append_machine', 'final_read'])
def test_complete_operation_rolls_back_artifact_job_terminal_and_receipt(workflow, monkeypatch, fault):
    database, identity, candidate, service, worker = workflow
    ack = service.create(identity, candidate.draft_id, request(candidate), 'create')
    lease = worker.claim()
    before = table_hashes(database)
    def fail(*args, **kwargs):
        raise RuntimeError('SYNTHETIC_TRANSACTION_FAILURE')
    if fault == 'blob_write':
        monkeypatch.setattr(service.artifacts.store, 'write', fail)
    elif fault == 'append_machine':
        original = ReviewRepository.append_machine
        def written(*args, **kwargs):
            original(*args, **kwargs)
            fail()
        monkeypatch.setattr(ReviewRepository, 'append_machine', written)
    else:
        original = service._history
        def checked(conn, current, identifier, *args):
            result = original(conn, current, identifier, *args)
            if result[0].state == 'ready':
                fail()
            return result
        monkeypatch.setattr(service, '_history', checked)
    with pytest.raises(RuntimeError, match='SYNTHETIC_TRANSACTION_FAILURE'):
        worker.finish(lease)
    assert table_hashes(database) == before
    assert service.read_job(identity, ack.id).status == 'running'


def test_expired_lease_recovery_rejects_previous_owner_and_creates_only_one_report(workflow):
    database, identity, candidate, service, worker = workflow
    ack = service.create(identity, candidate.draft_id, request(candidate), 'create')
    first = worker.claim()
    with database.transaction() as conn:
        conn.execute("UPDATE jobs SET lease_until='2000-01-01T00:00:00Z' WHERE id=?", (ack.id,))
    second = ReviewWorker(service).claim()
    before = table_hashes(database)
    worker.finish(first)
    assert table_hashes(database) == before
    worker.finish(second)
    assert service.read(identity, ack.id).revision == 1
    with database.connect() as conn:
        assert conn.execute("SELECT count(*) FROM artifacts WHERE profile='quality_review_report'").fetchone()[0] == 1


@pytest.mark.parametrize('fault', ['file', 'bytes', 'visibility', 'manifest', 'profile', 'job', 'history', 'created_at'])
def test_report_reads_reject_damaged_ownership_history_and_physical_bytes(workflow, fault):
    database, identity, _, service, _ = workflow
    ack, receipt = completed(workflow)
    artifact_id = receipt.evidence_paths[0].split('/')[-2]
    with database.transaction() as conn:
        row = conn.execute('SELECT * FROM artifacts WHERE id=?', (artifact_id,)).fetchone()
        if fault in {'file', 'bytes'}:
            path = database.settings.data_dir / conn.execute('SELECT relative_path FROM content_blobs WHERE sha256=?', (row['blob_sha256'],)).fetchone()[0]
            if fault == 'file':
                path.unlink()
            else:
                path.write_bytes(b'SYNTHETIC_DAMAGED_REPORT')
        elif fault == 'history':
            conn.execute('DROP TRIGGER review_commands_no_delete')
            conn.execute('DELETE FROM review_commands WHERE review_id=?', (ack.id,))
        else:
            field, value = {'visibility':('visibility','learner'), 'manifest':('manifest_json','{}'),
                            'profile':('profile','unregistered'), 'job':('job_id',None),
                            'created_at':('created_at','2000-01-01T00:00:00Z')}[fault]
            conn.execute(f'UPDATE artifacts SET {field}=? WHERE id=?', (value, artifact_id))
    before = table_hashes(database)
    for call in [lambda: service.read(identity, ack.id),
                 lambda: ArtifactsService(database, service.readers()).download(identity, artifact_id)]:
        with pytest.raises(ApiError):
            call()
    assert table_hashes(database) == before


def test_quality_evidence_cycle_rejected_and_original_decision_kept(workflow):
    database, identity, _, service, _ = workflow
    first, first_receipt = completed(workflow, 'first')
    second, second_receipt = completed(workflow, 'second')
    first_artifact, second_artifact = (item.evidence_paths[0].split('/')[-2] for item in [first_receipt, second_receipt])
    accepted = service.decide(identity, first.id, decision(first_receipt, [second_artifact]), 'first-decision')
    before = table_hashes(database)
    with pytest.raises(ApiError) as caught:
        service.decide(identity, second.id, decision(second_receipt, [first_artifact]), 'would-cycle')
    assert caught.value.code == 'REVIEW_EVIDENCE_CYCLE'
    assert table_hashes(database) == before and service.read(identity, first.id) == accepted


@pytest.mark.parametrize('kind', ['single', 'lesson', 'practice_set', 'assessment'])
def test_actual_generated_owners_numeric_prefix_and_private_group_coverage(tmp_path, monkeypatch, kind):
    from tests.integration.test_authoring_numeric_service import generated as single_fixture
    from tests.integration.test_authoring_group_numeric_service import generated_group
    state = single_fixture.__wrapped__(tmp_path) if kind == 'single' else generated_group(tmp_path, kind)
    case = ProviderHistoryCase('single' if kind == 'single' else 'group', state)
    source = 'authoring_single' if kind == 'single' else 'authoring_group'
    candidates = DraftCandidates({source:case.authoring})
    service = ReviewService(case.database, candidates, ReviewNumeric(candidates, {source:case.numeric}), {})
    worker = ReviewWorker(service)
    first = case.preview('before-review')
    def forbidden(*args, **kwargs):
        pytest.fail('Review must never prepare or execute numeric runtime or call Provider')
    with monkeypatch.context() as patch:
        for method in ['prepare', 'check', 'run_checked', 'manifest_document']:
            patch.setattr(case.runtime, method, forbidden, raising=False)
        ack = service.create(case.identity, case.candidate.draft_id, request(case.candidate), 'review')
        assert worker.run_once()
        receipt = service.read(case.identity, ack.id)
        raw, _ = ArtifactsService(case.database, service.readers()).download(case.identity, receipt.evidence_paths[0].split('/')[-2])
        report = json.loads(raw)
        assert [item['view']['id'] for item in report['numeric_observation']['checks']] == [first.id]
        assert report['mathematical'] == report['sources'] == 'NOT_RUN'
        with pytest.raises(ApiError) as caught:
            service.decide(case.identity, ack.id, decision(receipt, mathematical='NOT_APPLICABLE'), 'bypass')
        assert caught.value.code == 'MATHEMATICAL_REVIEW_REQUIRED'
    case.preview('later-does-not-rewrite-report')
    assert service.read(case.identity, ack.id) == receipt
    later_raw, _ = ArtifactsService(case.database, service.readers()).download(case.identity, receipt.evidence_paths[0].split('/')[-2])
    assert later_raw == raw


@pytest.mark.parametrize('operation', ['create', 'decision'])
def test_command_receipt_failure_rolls_back_entire_application_operation(workflow, monkeypatch, operation):
    database, identity, candidate, service, _ = workflow
    if operation == 'decision':
        ack, receipt = completed(workflow)
    name = 'bind' if operation == 'create' else 'append_decision'
    original = getattr(ReviewRepository, name)
    def failed(*args, **kwargs):
        original(*args, **kwargs)
        raise RuntimeError('SYNTHETIC_AFTER_DURABLE_WRITE')
    monkeypatch.setattr(ReviewRepository, name, failed)
    before = table_hashes(database)
    with pytest.raises(RuntimeError, match='SYNTHETIC_AFTER_DURABLE_WRITE'):
        if operation == 'create':
            service.create(identity, candidate.draft_id, request(candidate), 'create')
        else:
            service.decide(identity, ack.id, decision(receipt), 'human')
    assert table_hashes(database) == before


def test_report_reader_uses_original_readonly_transaction_and_safe_registry(workflow, monkeypatch):
    database, identity, _, service, _ = workflow
    _, receipt = completed(workflow)
    artifact = receipt.evidence_paths[0].split('/')[-2]
    expected, descriptor = ArtifactsService(database, service.readers()).download(identity, artifact)
    with database.transaction(immediate=False) as conn:
        conn.execute('PRAGMA query_only=ON')
        before = list(conn.iterdump())
        def forbidden(*args, **kwargs):
            pytest.fail('Owner must use the same current transaction')
        monkeypatch.setattr(database, 'connect', forbidden)
        assert service.read_artifact(conn, identity, artifact) == (expected, descriptor)
        assert list(conn.iterdump()) == before


def test_creator_revocation_fails_actual_job_without_fake_report(workflow):
    database, identity, candidate, service, worker = workflow
    ack = service.create(identity, candidate.draft_id, request(candidate), 'create')
    with database.transaction() as conn:
        conn.execute("UPDATE local_sessions SET role='learner'")
    assert worker.run_once()
    snapshot = service.read_job(identity, ack.id)
    assert snapshot.status == 'failed'
    with database.transaction() as conn:
        history = ReviewRepository(conn, identity.workspace_id).load(ack.id)
        assert history.records == [] and history.receipt is None
        assert conn.execute("SELECT count(*) FROM artifacts WHERE profile='quality_review_report'").fetchone()[0] == 0


def test_lease_expiry_after_actual_blob_write_rolls_back_terminal_and_references(workflow, monkeypatch):
    database, identity, candidate, service, worker = workflow
    ack = service.create(identity, candidate.draft_id, request(candidate), 'create')
    lease = worker.claim()
    before = table_hashes(database)
    original = service.artifacts.write
    def expired(conn, value, raw):
        result = original(conn, value, raw)
        conn.execute("UPDATE jobs SET lease_until='2000-01-01T00:00:00Z' WHERE id=?", (ack.id,))
        return result
    monkeypatch.setattr(service.artifacts, 'write', expired)
    with pytest.raises(ApiError) as caught:
        worker.finish(lease)
    assert caught.value.code == 'REVIEW_LEASE_LOST' and table_hashes(database) == before


def test_unrequested_structure_stays_not_run_and_read_never_advances_numeric_ledger(workflow):
    database, identity, candidate, service, worker = workflow
    body = request(candidate).model_copy(update={'checks':['sources']})
    ack = service.create(identity, candidate.draft_id, body, 'source-only')
    assert worker.run_once()
    receipt = service.read(identity, ack.id)
    assert receipt.structural == receipt.mathematical == receipt.sources == 'NOT_RUN'
    before = table_hashes(database)
    raw, _ = ArtifactsService(database, service.readers()).download(identity, receipt.evidence_paths[0].split('/')[-2])
    value = json.loads(raw)
    assert value['numerical_examples_requested'] is False
    assert value['numeric_observation']['checks'] == []
    assert all(item['status'] == 'NOT_RUN' for item in value['structure']['checks'])
    assert table_hashes(database) == before


@pytest.mark.parametrize('formula', ['$x^2+1$', r'\(x+1\)', r'\[x=2\]',
    r'\begin{equation*}x=2\end{equation*}', r'\begin{align*}x&=2\end{align*}'])
def test_explicit_formula_in_real_import_body_cannot_claim_na(tmp_path, formula):
    from services.api.app.infrastructure.config import Settings
    from services.api.app.infrastructure.database import Database
    from services.api.app.infrastructure.import_worker import ImportWorker
    from services.api.app.infrastructure.security import consume_bootstrap, issue_bootstrap_code
    from services.api.app.application.sessions import SessionService
    from services.api.app.dto import RoleRequest
    from packages.contracts import domain_models as dm
    database = Database(Settings(data_dir=tmp_path / 'data'))
    database.initialize()
    _, identity = consume_bootstrap(database, issue_bootstrap_code(database))
    SessionService(database).switch_role(identity, RoleRequest(role='author'), 'author')
    identity = replace(identity, role='author')
    owner = ImportService(database)
    staged = owner.stage(identity, data=(formula+'\n').encode(), filename='math.md', kind='markdown', key='upload')
    importer = ImportWorker(database)
    try:
        assert importer.run_once()
    finally:
        importer.stop()
    preview = owner.preview(identity, staged.import_id)
    draft = next(value for value in (owner.draft(identity, item) for item in preview.preview_refs) if value.kind == 'block')
    candidate = dm.DraftCandidate(draft_id=draft.id, draft_revision=draft.revision,
        entity=draft.kind, candidate_sha256=draft.candidate_sha256)
    candidates = DraftCandidates({'import':owner})
    service = ReviewService(database, candidates, ReviewNumeric(candidates, {}), {})
    ack = service.create(identity, candidate.draft_id, request(candidate), 'create')
    assert ReviewWorker(service).run_once()
    receipt = service.read(identity, ack.id)
    with pytest.raises(ApiError) as caught:
        service.decide(identity, ack.id, decision(receipt, mathematical='NOT_APPLICABLE'), 'human')
    assert caught.value.code == 'MATHEMATICAL_REVIEW_REQUIRED'


@pytest.mark.parametrize('owner_kind', ['import', 'quality'])
@pytest.mark.parametrize('damage', ['bytes', 'membership'])
def test_accepted_external_evidence_corruption_rejects_receipt_original_ack_and_download(workflow, owner_kind, damage):
    from services.api.app.infrastructure.import_worker import ImportWorker
    database, identity, candidate, service, _ = workflow
    first, receipt = completed(workflow, 'first')
    if owner_kind == 'quality':
        _, other = completed(workflow, 'other-quality')
        artifact_id = other.evidence_paths[0].split('/')[-2]
    else:
        imports = ImportService(database)
        staged = imports.stage(identity, data=b'# Independent synthetic evidence\n', filename='evidence.md',
                               kind='markdown', key='independent-evidence')
        worker = ImportWorker(database)
        try:
            assert worker.run_once()
        finally:
            worker.stop()
        with database.connect() as conn:
            artifact_id = conn.execute("SELECT id FROM artifacts WHERE job_id=? AND profile='import_original'",
                                       (staged.job.id,)).fetchone()[0]
    body = decision(receipt, [artifact_id])
    accepted = service.decide(identity, first.id, body, 'human')
    assert service.read(identity, first.id) == accepted
    with database.transaction() as conn:
        if damage == 'membership':
            conn.execute("UPDATE artifacts SET profile='unregistered' WHERE id=?", (artifact_id,))
        else:
            path = conn.execute('SELECT b.relative_path FROM artifacts a JOIN content_blobs b '
                                'ON a.blob_sha256=b.sha256 WHERE a.id=?', (artifact_id,)).fetchone()[0]
            (database.settings.data_dir / path).write_bytes(b'SYNTHETIC_CORRUPT_EXTERNAL_EVIDENCE')
    before = table_hashes(database)
    for call in [lambda: service.read(identity, first.id),
                 lambda: service.decide(identity, first.id, body, 'human'),
                 lambda: service.create(identity, candidate.draft_id, request(candidate), 'first'),
                 lambda: ArtifactsService(database, service.readers()).download(identity, receipt.evidence_paths[0].split('/')[-2])]:
        with pytest.raises(ApiError):
            call()
    assert table_hashes(database) == before


def test_jobs_owned_candidates_are_readonly_and_a_damaged_first_job_does_not_hide_valid_work(workflow):
    from services.api.app.infrastructure.review_job_repository import ReviewJobRepository
    from services.api.app.infrastructure.database import utc_now
    database, identity, candidate, service, worker = workflow
    first = service.create(identity, candidate.draft_id, request(candidate), 'first')
    second = service.create(identity, candidate.draft_id, request(candidate), 'second')
    before = table_hashes(database)
    with database.transaction(immediate=False) as conn:
        conn.execute('PRAGMA query_only=ON')
        scan = ReviewJobRepository(conn, identity.workspace_id).claimable_candidates(utc_now())
        assert [item.job_id for item in scan.candidates] == [first.id, second.id]
        assert scan.invalid_rows == 0
    assert table_hashes(database) == before
    with database.transaction() as conn:
        conn.execute("UPDATE jobs SET input_json='{}' WHERE id=?", (first.id,))
    lease = worker.claim()
    assert lease.job_id == second.id
    worker.finish(lease)
    assert service.read(identity, second.id).revision == 1
    with pytest.raises(ApiError):
        service.read_job(identity, first.id)


def test_artifacts_owned_manifest_rejects_a_forged_reader_descriptor_without_writes(workflow):
    from services.api.app.infrastructure.artifact_repository import ArtifactRepository
    from packages.contracts.canonical import sha256_bytes
    database, identity, _, service, _ = workflow
    _, receipt = completed(workflow)
    artifact_id = receipt.evidence_paths[0].split('/')[-2]
    _, artifact = ArtifactsService(database, service.readers()).download(identity, artifact_id)
    before = table_hashes(database)
    with database.transaction(immediate=False) as conn:
        conn.execute('PRAGMA query_only=ON')
        repo = ArtifactRepository(conn, identity.workspace_id)
        manifest = conn.execute('SELECT manifest_json FROM artifacts WHERE id=?', (artifact_id,)).fetchone()[0]
        assert repo.manifest_sha256(artifact_id, artifact) == sha256_bytes(manifest.encode())
        with pytest.raises(ApiError):
            repo.manifest_sha256(artifact_id, artifact.model_copy(update={'filename':'forged.json'}))
    assert table_hashes(database) == before


@pytest.mark.parametrize('field', ['created_at', 'id'])
def test_bad_queue_scheduling_row_does_not_starve_a_healthy_review(workflow, field):
    database, identity, candidate, service, worker = workflow
    first = service.create(identity, candidate.draft_id, request(candidate), 'damaged')
    second = service.create(identity, candidate.draft_id, request(candidate), 'healthy')
    # Simulate offline database damage, including broken FK membership. These
    # values must never become a claimed lease or be repaired into valid input.
    with database.connect() as conn:
        conn.execute('PRAGMA foreign_keys=OFF')
        if field == 'created_at':
            conn.execute("UPDATE jobs SET created_at='invalid-time' WHERE id=?", (first.id,))
        else:
            conn.execute("UPDATE jobs SET id='!invalid-id' WHERE id=?", (first.id,))
    lease = worker.claim()
    assert lease is not None and lease.job_id == second.id
    worker.finish(lease)
    assert service.read(identity, second.id).revision == 1
    assert worker.last_queue_error_code == 'AUTHORING_INTEGRITY_ERROR'
    before = table_hashes(database)
    with pytest.raises(ApiError):
        worker.claim()
    with pytest.raises(ApiError):
        service.read_job(identity, first.id)
    assert table_hashes(database) == before
