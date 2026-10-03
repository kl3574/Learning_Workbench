"""Actual SQLite owners; synthetic human and numeric ledger facts, no publication.

Generated fixtures use controlled loopback output. Synthetic terminal numeric
records test admission of recorded facts, never physical sandbox success.
"""
import pytest
from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.draft_candidates import DraftCandidates
from services.api.app.application.errors import ApiError
from services.api.app.application.publication_admission import PublicationAdmissionService
from services.api.app.application.publication_admission_models import DraftPublishWrite
from services.api.app.application.review_numeric import ReviewNumeric
from services.api.app.application.review_service import ReviewService
from services.api.app.application.review_worker import ReviewWorker
from services.api.app.authoring_dto import NumericCheckResult, numeric_result_sha256
from services.api.app.authoring_group_dto import AuthoringGroupNumericPreviewWrite
from services.api.app.infrastructure.authoring_numeric_repository import NumericRepository
from services.api.app.infrastructure.authoring_group_numeric_repository import GroupNumericRepository
from services.api.app.infrastructure.database import utc_now
from tests.integration.test_authoring_numeric_provider_history import ProviderHistoryCase, table_hashes
from tests.integration.test_authoring_numeric_service import generated as single_fixture, decision as numeric_decision
from tests.integration.test_authoring_group_numeric_service import generated_group
from tests.integration.test_review_workflow import workflow as workflow_fixture, request, decision


@pytest.fixture
def workflow(tmp_path):
    yield from workflow_fixture.__wrapped__(tmp_path)


def reviewed(database, identity, candidate, reviews, *, key='review', checks=None, math='APPROVED', sources='APPROVED'):
    body = request(candidate)
    if checks is not None:
        body = body.model_copy(update={'checks': checks})
    ack = reviews.create(identity, candidate.draft_id, body, key)
    assert ReviewWorker(reviews).run_once()
    receipt = reviews.read(identity, ack.id)
    return reviews.decide(identity, ack.id, decision(receipt, mathematical=math, sources=sources), key+'-human')


def publish_request(database, identity, candidate, reviews, receipt, **changes):
    with database.transaction(immediate=False) as conn:
        history, material = reviews.read_publication_basis(conn, identity, receipt.id)
        warnings = [*material.warnings, *(w for c in history.records[0].numeric.checks for w in c.view.warnings)]
    return DraftPublishWrite(**(dict(expected_revision=candidate.draft_revision,
        expected_content_sha256=candidate.candidate_sha256, review_receipt_id=receipt.id,
        acknowledged_warning_codes=sorted({w.code for w in warnings})) | changes))


def admit(database, identity, candidate, reviews, body):
    with database.transaction(immediate=False) as conn:
        conn.execute('PRAGMA query_only=ON')
        return PublicationAdmissionService(reviews).check(conn, identity, candidate.draft_id, body)


def test_plain_import_admission_is_same_transaction_readonly_and_not_publication(workflow, monkeypatch):
    database, identity, candidate, reviews, _ = workflow
    receipt = reviewed(database, identity, candidate, reviews, math='NOT_APPLICABLE')
    body = publish_request(database, identity, candidate, reviews, receipt)
    before = table_hashes(database)
    with database.transaction(immediate=False) as conn:
        conn.execute('PRAGMA query_only=ON')
        monkeypatch.setattr(database, 'connect', lambda **kwargs: pytest.fail('admission opened another connection'))
        result = PublicationAdmissionService(reviews).check(conn, identity, candidate.draft_id, body)
        assert result.publication == 'NOT_RUN' and result.numeric_coverage == 'not_required_by_material'
        assert result.numeric_check_ids == [] and result.review_revision == 2
    monkeypatch.undo()
    assert table_hashes(database) == before
    assert reviews.read(identity, receipt.id).independent_pedagogy == 'NOT_RUN'


@pytest.mark.parametrize('change', [dict(expected_revision=2), dict(expected_content_sha256='0'*64), dict(review_receipt_id='missing_review')])
def test_exact_publish_binding_and_no_mutation(workflow, change):
    database, identity, candidate, reviews, _ = workflow
    receipt = reviewed(database, identity, candidate, reviews, math='NOT_APPLICABLE')
    body = publish_request(database, identity, candidate, reviews, receipt, **change)
    before = table_hashes(database)
    with pytest.raises(ApiError):
        admit(database, identity, candidate, reviews, body)
    assert table_hashes(database) == before


@pytest.mark.parametrize('checks,sources,expected', [(['sources'], 'APPROVED', 'PUBLISH_STRUCTURE_REQUIRED'),
    (None, 'REJECTED', 'PUBLISH_HUMAN_REVIEW_REQUIRED'), (None, 'NOT_APPLICABLE', 'PUBLISH_SOURCE_REVIEW_REQUIRED')])
def test_real_review_fields_cannot_bypass_required_checks(workflow, checks, sources, expected):
    database, identity, candidate, reviews, _ = workflow
    receipt = reviewed(database, identity, candidate, reviews, checks=checks, math='NOT_APPLICABLE', sources=sources)
    body = publish_request(database, identity, candidate, reviews, receipt)
    with pytest.raises(ApiError) as caught:
        admit(database, identity, candidate, reviews, body)
    assert caught.value.code == expected


def test_current_latest_human_rejection_invalidates_earlier_admission(workflow):
    database, identity, candidate, reviews, _ = workflow
    receipt = reviewed(database, identity, candidate, reviews, math='NOT_APPLICABLE')
    body = publish_request(database, identity, candidate, reviews, receipt)
    assert admit(database, identity, candidate, reviews, body).review_revision == 2
    reviews.decide(identity, receipt.id, decision(receipt, sources='REJECTED'), 'later-rejection')
    with pytest.raises(ApiError):
        admit(database, identity, candidate, reviews, body)


@pytest.mark.parametrize('damage', ['role', 'revoked', 'report', 'history'])
def test_admission_revalidates_current_access_complete_history_and_bytes(workflow, damage):
    database, identity, candidate, reviews, _ = workflow
    receipt = reviewed(database, identity, candidate, reviews, math='NOT_APPLICABLE')
    body = publish_request(database, identity, candidate, reviews, receipt)
    with database.transaction() as conn:
        if damage == 'role':
            conn.execute("UPDATE local_sessions SET role='learner'")
        elif damage == 'revoked':
            conn.execute("UPDATE local_sessions SET revoked_at='2000-01-01T00:00:00Z'")
        elif damage == 'history':
            conn.execute('DROP TRIGGER review_commands_no_delete')
            conn.execute('DELETE FROM review_commands WHERE review_id=?', (receipt.id,))
        else:
            row = conn.execute("SELECT b.relative_path FROM artifacts a JOIN content_blobs b ON a.blob_sha256=b.sha256 WHERE a.profile='quality_review_report'").fetchone()
            (database.settings.data_dir / row[0]).write_bytes(b'SYNTHETIC_CHANGED_REPORT')
    before = table_hashes(database)
    with pytest.raises(ApiError):
        admit(database, identity, candidate, reviews, body)
    assert table_hashes(database) == before


def generated_case(tmp_path, kind):
    state = single_fixture.__wrapped__(tmp_path) if kind == 'single' else generated_group(tmp_path, kind)
    case = ProviderHistoryCase('single' if kind == 'single' else 'group', state)
    source = 'authoring_single' if kind == 'single' else 'authoring_group'
    candidates = DraftCandidates({source:case.authoring})
    reviews = ReviewService(case.database, candidates, ReviewNumeric(candidates, {source:case.numeric}), {})
    return case, reviews


def synthetic_numeric(case, key, *, target=None, outcome='passed', complete=True, exit_code=0):
    """Populate an explicit synthetic execution through actual Jobs/Numeric owners."""
    if target is None:
        preview = case.preview(key)
    else:
        preview = case.numeric.preview(case.identity, case.candidate.draft_id, target.member_key,
            AuthoringGroupNumericPreviewWrite(candidate=case.candidate, target=target), key)
    ack = case.numeric.decide(case.identity, preview.id, numeric_decision(preview), key+'-approve')
    cls = NumericRepository if case.variant == 'single' else GroupNumericRepository
    with case.database.transaction() as conn:
        repo = cls(conn, case.identity.workspace_id)
        lease, job, _ = repo.claim(ack.job.id)
        assert repo.begin(lease, utc_now())
        started = utc_now()
        repo.mark_started(lease, started)
        assertions = [dict(id=x.id, actual=x.expected, passed=True, error_code=None) for x in job.plan.assertions]
        stdout = canonical_bytes(dict(synthetic_ledger_only=True, assertions=assertions))
        raw = dict(job_id=job.job_id, input_sha256=sha256_bytes(canonical_bytes(job)),
            operation_sha256=job.operation_sha256, outcome=outcome, verdict='PASS' if outcome == 'passed' else 'BLOCKED',
            started_at=started, finished_at=utc_now(), exit_code=exit_code if outcome == 'passed' else None,
            assertions=assertions if outcome == 'passed' else [], output_sha256=sha256_bytes(stdout) if complete else None, result_sha256='0'*64)
        raw['result_sha256'] = numeric_result_sha256(raw)
        repo.finish(lease, NumericCheckResult.model_validate(raw), stdout, b'', complete, case.runtime.manifest_document())
    return preview


@pytest.mark.parametrize('kind', ['single', 'lesson', 'practice_set', 'assessment'])
def test_two_human_approvals_and_empty_numeric_history_do_not_admit_generated_candidates(tmp_path, kind):
    case, reviews = generated_case(tmp_path, kind)
    receipt = reviewed(case.database, case.identity, case.candidate, reviews)
    body = publish_request(case.database, case.identity, case.candidate, reviews, receipt)
    before = table_hashes(case.database)
    with pytest.raises(ApiError) as caught:
        admit(case.database, case.identity, case.candidate, reviews, body)
    expected = 'PUBLISH_NUMERIC_REQUIRED' if kind in {'single','lesson'} else 'PUBLISH_QUESTION_QUALITY_UNCHECKED'
    assert caught.value.code == expected
    assert table_hashes(case.database) == before


def test_last_frozen_numeric_check_controls_recovery_without_upgrading_old_review(tmp_path):
    case, reviews = generated_case(tmp_path, 'single')
    synthetic_numeric(case, 'blocked', outcome='environment_unavailable')
    old = reviewed(case.database, case.identity, case.candidate, reviews, key='old')
    old_body = publish_request(case.database, case.identity, case.candidate, reviews, old)
    good = synthetic_numeric(case, 'recovery')
    with pytest.raises(ApiError):
        admit(case.database, case.identity, case.candidate, reviews, old_body)
    fresh = reviewed(case.database, case.identity, case.candidate, reviews, key='fresh')
    fresh_body = publish_request(case.database, case.identity, case.candidate, reviews, fresh)
    result = admit(case.database, case.identity, case.candidate, reviews, fresh_body)
    assert result.numeric_check_ids == [good.id] and result.publication == 'NOT_RUN'
    synthetic_numeric(case, 'last-blocked', outcome='cancelled')
    latest = reviewed(case.database, case.identity, case.candidate, reviews, key='latest')
    with pytest.raises(ApiError):
        admit(case.database, case.identity, case.candidate, reviews,
              publish_request(case.database, case.identity, case.candidate, reviews, latest))


def test_complete_lesson_requires_every_exact_numeric_member(tmp_path):
    case, reviews = generated_case(tmp_path, 'lesson')
    draft = case.authoring.draft(case.identity, case.candidate.draft_id)
    first, second = [target for target in draft.root.blocks if target.member_key != 'lesson_text']
    one = synthetic_numeric(case, 'first', target=first)
    partial = reviewed(case.database, case.identity, case.candidate, reviews, key='partial')
    with pytest.raises(ApiError):
        admit(case.database, case.identity, case.candidate, reviews,
              publish_request(case.database, case.identity, case.candidate, reviews, partial))
    two = synthetic_numeric(case, 'second', target=second)
    full = reviewed(case.database, case.identity, case.candidate, reviews, key='full')
    result = admit(case.database, case.identity, case.candidate, reviews,
        publish_request(case.database, case.identity, case.candidate, reviews, full))
    assert result.numeric_check_ids == [one.id, two.id]
    assert case.authoring.draft(case.identity, case.candidate.draft_id).state == 'draft'


def test_request_has_only_the_four_specified_fields_and_serialization_failure_is_private(workflow):
    import warnings
    from pydantic import ValidationError
    database, identity, candidate, reviews, _ = workflow
    receipt = reviewed(database, identity, candidate, reviews, math='NOT_APPLICABLE')
    body = publish_request(database, identity, candidate, reviews, receipt)
    assert set(DraftPublishWrite.model_fields) == {'expected_revision', 'expected_content_sha256', 'review_receipt_id', 'acknowledged_warning_codes'}
    with pytest.raises(ValidationError):
        DraftPublishWrite.model_validate({**body.model_dump(), 'publish_now': True})
    invalid = body.model_copy(update={'acknowledged_warning_codes': [{'secret': 'synthetic-private-admission-marker'}]})
    before = table_hashes(database)
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter('always')
        with pytest.raises(ApiError) as caught:
            admit(database, identity, candidate, reviews, invalid)
    assert observed == [] and 'synthetic-private-admission-marker' not in str(caught.value)
    assert table_hashes(database) == before


def test_machine_only_and_no_transaction_do_not_produce_admission(workflow):
    database, identity, candidate, reviews, worker = workflow
    ack = reviews.create(identity, candidate.draft_id, request(candidate), 'machine-only')
    assert worker.run_once()
    receipt = reviews.read(identity, ack.id)
    body = publish_request(database, identity, candidate, reviews, receipt)
    with database.connect() as conn:
        with pytest.raises(ApiError) as caught:
            PublicationAdmissionService(reviews).check(conn, identity, candidate.draft_id, body)
        assert caught.value.code == 'TRANSACTION_REQUIRED'
    with pytest.raises(ApiError) as caught:
        admit(database, identity, candidate, reviews, body)
    assert caught.value.code == 'PUBLISH_HUMAN_REVIEW_REQUIRED'


def test_actual_import_warnings_require_exact_acknowledgment(workflow):
    from services.api.app.application.imports import ImportService
    from services.api.app.infrastructure.import_worker import ImportWorker
    database, identity, _, reviews, _ = workflow
    imports = ImportService(database)
    staged = imports.stage(identity, data=b'<h1>Plain heading</h1><script>alert(1)</script>',
        filename='warning.html', kind='html', key='warning-source')
    worker = ImportWorker(database)
    try:
        assert worker.run_once()
    finally:
        worker.stop()
    preview = imports.preview(identity, staged.import_id)
    draft = next(d for d in (imports.draft(identity, item) for item in preview.preview_refs) if d.kind == 'block')
    candidate = dm.DraftCandidate(draft_id=draft.id, draft_revision=draft.revision, entity=draft.kind, candidate_sha256=draft.candidate_sha256)
    receipt = reviewed(database, identity, candidate, reviews, math='NOT_APPLICABLE')
    body = publish_request(database, identity, candidate, reviews, receipt)
    assert body.acknowledged_warning_codes
    with pytest.raises(ApiError) as caught:
        admit(database, identity, candidate, reviews, body.model_copy(update={'acknowledged_warning_codes': []}))
    assert caught.value.code == 'PUBLISH_WARNINGS_UNACKNOWLEDGED'
    with pytest.raises(ApiError) as caught:
        admit(database, identity, candidate, reviews, body.model_copy(update={'acknowledged_warning_codes': ['invented-code']}))
    assert caught.value.code == 'PUBLISH_WARNING_CODES_INVALID'
    assert admit(database, identity, candidate, reviews, body).publication == 'NOT_RUN'


@pytest.mark.parametrize('entity,code', [('question','PUBLISH_PRIVATE_COVERAGE_UNAVAILABLE'),
    ('lesson','PUBLISH_MEMBER_COVERAGE_UNAVAILABLE')])
def test_actual_import_package_does_not_claim_private_or_member_coverage(workflow, entity, code):
    from tests.assessment_fixtures import assessment_fixture
    from services.api.app.application.imports import ImportService
    from services.api.app.infrastructure.import_worker import ImportWorker
    database, identity, _, reviews, _ = workflow
    imports = ImportService(database)
    fixture = assessment_fixture('unreviewed')
    staged = imports.stage(identity, data=fixture.archive, filename='synthetic.learnpack.zip', kind='learnpack', key='package')
    worker = ImportWorker(database)
    try:
        assert worker.run_once()
    finally:
        worker.stop()
    preview = imports.preview(identity, staged.import_id)
    draft = next(d for d in (imports.draft(identity, item) for item in preview.preview_refs) if d.kind == entity)
    candidate = dm.DraftCandidate(draft_id=draft.id, draft_revision=draft.revision, entity=draft.kind, candidate_sha256=draft.candidate_sha256)
    receipt = reviewed(database, identity, candidate, reviews)
    body = publish_request(database, identity, candidate, reviews, receipt)
    before = table_hashes(database)
    with pytest.raises(ApiError) as caught:
        admit(database, identity, candidate, reviews, body)
    assert caught.value.code == code and table_hashes(database) == before


@pytest.mark.parametrize('mode', ['independent', 'open_book', 'assisted'])
def test_current_real_assessment_policy_still_blocks_admission(workflow, mode):
    from services.api.app.application.assessment import AssessmentService
    from services.api.app.assessment_dto import AssessmentAttemptCreate
    from services.api.app.infrastructure.content_repository import reference
    from tests.assessment_fixtures import assessment_fixture
    from tests.integration.test_assessment_attempts import import_fixture
    database, identity, candidate, reviews, _ = workflow
    receipt = reviewed(database, identity, candidate, reviews, math='NOT_APPLICABLE')
    body = publish_request(database, identity, candidate, reviews, receipt)
    fixture = assessment_fixture('admissionpolicy')
    import_fixture(database, identity, fixture, 'assessment-material')
    AssessmentService(database).create_attempt(identity, fixture.assessment.id,
        AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode=mode), 'attempt')
    before = table_hashes(database)
    with pytest.raises(ApiError):
        admit(database, identity, candidate, reviews, body)
    assert table_hashes(database) == before


@pytest.mark.parametrize('last', ['pending', 'queued', 'running'])
def test_last_unfinished_numeric_check_cannot_reuse_earlier_pass(tmp_path, last):
    case, reviews = generated_case(tmp_path, 'single')
    synthetic_numeric(case, 'earlier-pass')
    preview = case.preview('latest-unfinished')
    if last != 'pending':
        ack = case.numeric.decide(case.identity, preview.id, numeric_decision(preview), 'latest-approve')
        if last == 'running':
            with case.database.transaction() as conn:
                NumericRepository(conn, case.identity.workspace_id).claim(ack.job.id)
    receipt = reviewed(case.database, case.identity, case.candidate, reviews)
    body = publish_request(case.database, case.identity, case.candidate, reviews, receipt)
    before = table_hashes(case.database)
    with pytest.raises(ApiError) as caught:
        admit(case.database, case.identity, case.candidate, reviews, body)
    assert caught.value.code == 'PUBLISH_NUMERIC_REQUIRED' and table_hashes(case.database) == before


@pytest.mark.parametrize('changes', [dict(complete=False), dict(exit_code=None)])
def test_declared_numeric_pass_without_complete_output_or_known_exit_is_not_admitted(tmp_path, changes):
    case, reviews = generated_case(tmp_path, 'single')
    synthetic_numeric(case, 'incomplete-proof', **changes)
    receipt = reviewed(case.database, case.identity, case.candidate, reviews)
    with pytest.raises(ApiError) as caught:
        admit(case.database, case.identity, case.candidate, reviews,
            publish_request(case.database, case.identity, case.candidate, reviews, receipt))
    assert caught.value.code == 'PUBLISH_NUMERIC_REQUIRED'


def test_numeric_original_output_corruption_cannot_reuse_accepted_admission(tmp_path):
    case, reviews = generated_case(tmp_path, 'single')
    synthetic_numeric(case, 'original')
    receipt = reviewed(case.database, case.identity, case.candidate, reviews)
    body = publish_request(case.database, case.identity, case.candidate, reviews, receipt)
    assert admit(case.database, case.identity, case.candidate, reviews, body).publication == 'NOT_RUN'
    with case.database.transaction() as conn:
        conn.execute("UPDATE authoring_numeric_executions SET end_json='{}'")
    before = table_hashes(case.database)
    with pytest.raises(ApiError):
        admit(case.database, case.identity, case.candidate, reviews, body)
    assert table_hashes(case.database) == before
