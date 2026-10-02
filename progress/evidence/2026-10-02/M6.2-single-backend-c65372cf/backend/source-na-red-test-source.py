"""Migration and ongoing execution continuity; all numeric outputs are synthetic."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.assessment import AssessmentService
from services.api.app.application.draft_publication import DraftPublicationService
from services.api.app.application.errors import ApiError
from services.api.app.application.imports import ImportService
from services.api.app.assessment_dto import AssessmentAttemptCreate
from services.api.app.authoring_dto import NumericCheckResult, numeric_result_sha256
from services.api.app.infrastructure.authoring_numeric_runtime import NumericExecution
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database, utc_now
from tests.assessment_fixtures import assessment_fixture
from tests.integration.test_assessment_attempts import import_fixture
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_authoring_numeric_service import decision
from tests.integration.test_publication_admission import generated_case, publish_request, reviewed, synthetic_numeric
from tests.integration.test_single_publication import ready_single


def test_forward_migration_preserves_original_generated_candidate_and_provider_history(tmp_path, monkeypatch):
    original_files = Database.migration_files
    with monkeypatch.context() as scope:
        scope.setattr(Database, 'migration_files', lambda self: [path for path in original_files(self) if path.name < '0026'])
        case, reviews = generated_case(tmp_path, 'single')
    before = table_hashes(case.database)
    assert 'single_publication_bindings' not in before
    case.database.initialize()
    after = table_hashes(case.database)
    assert all(after[name] == digest for name, digest in before.items() if name != 'schema_migrations')
    assert 'single_publication_bindings' in after
    publication = DraftPublicationService(case.database, reviews, ImportService(case.database))
    case.authoring.verify_publication = publication.verify_recorded
    draft = case.authoring.draft(case.identity, case.candidate.draft_id)
    assert draft.state == 'draft' and draft.published_ref is None
    synthetic_numeric(case, 'new-synthetic-numeric')
    receipt = reviewed(case.database, case.identity, case.candidate, reviews)
    intent = publish_request(case.database, case.identity, case.candidate, reviews, receipt)
    assert publication.publish(case.identity, case.candidate.draft_id, intent, 'publish').revision == 1


def test_derived_expiry_alone_does_not_make_the_complete_numeric_endpoint_stale(tmp_path, monkeypatch):
    import services.api.app.application.review_numeric as numeric_reader
    case, _, publication, intent = ready_single(tmp_path)
    monkeypatch.setattr(numeric_reader, 'utc_now', lambda: '2099-01-01T00:00:00Z')
    assert publication.publish(case.identity, case.candidate.draft_id, intent, 'publish').revision == 1


def test_no_source_single_preserves_existing_not_applicable_source_admission(tmp_path):
    case, reviews = generated_case(tmp_path, 'single')
    publication = DraftPublicationService(case.database, reviews, ImportService(case.database))
    case.authoring.verify_publication = publication.verify_recorded
    synthetic_numeric(case, 'synthetic-numeric')
    receipt = reviewed(case.database, case.identity, case.candidate, reviews, sources='NOT_APPLICABLE')
    intent = publish_request(case.database, case.identity, case.candidate, reviews, receipt)
    result = publication.publish(case.identity, case.candidate.draft_id, intent, 'publish')
    assert case.authoring.draft(case.identity, case.candidate.draft_id).published_ref.id == result.id
    assert publication.publish(case.identity, case.candidate.draft_id, intent, 'publish') == result


def test_pending_preview_can_be_declined_after_publication_without_invalidating_old_ack(tmp_path):
    case, reviews = generated_case(tmp_path, 'single')
    publication = DraftPublicationService(case.database, reviews, ImportService(case.database))
    case.authoring.verify_publication = publication.verify_recorded
    pending = case.preview('old-pending')
    synthetic_numeric(case, 'latest-B')
    receipt = reviewed(case.database, case.identity, case.candidate, reviews)
    intent = publish_request(case.database, case.identity, case.candidate, reviews, receipt)
    result = publication.publish(case.identity, case.candidate.draft_id, intent, 'publish')
    declined = case.numeric.decide(case.identity, pending.id, decision(pending, 'decline'), 'decline-after-publication')
    assert declined.decision == 'decline' and declined.job is None
    assert publication.publish(case.identity, case.candidate.draft_id, intent, 'publish') == result
    assert case.authoring.draft(case.identity, case.candidate.draft_id).published_ref.id == result.id


@pytest.mark.parametrize('mode', ['independent', 'open_book'])
def test_current_assessment_blocks_published_payload_and_ack_but_keeps_safe_jobs(tmp_path, mode):
    case, _, publication, intent = ready_single(tmp_path)
    source_job = case.authoring.draft(case.identity, case.candidate.draft_id).source_job_id
    publication.publish(case.identity, case.candidate.draft_id, intent, 'publish')
    fixture = assessment_fixture('singlepolicy')
    import_fixture(case.database, case.identity, fixture, 'policy-content')
    AssessmentService(case.database).create_attempt(case.identity, fixture.assessment.id,
        AssessmentAttemptCreate(assessment_ref=reference(fixture.assessment), mode=mode), 'attempt')
    before = table_hashes(case.database)
    for read in (lambda: case.authoring.draft(case.identity, case.candidate.draft_id),
                 lambda: publication.publish(case.identity, case.candidate.draft_id, intent, 'publish')):
        with pytest.raises(ApiError):
            read()
    assert case.authoring.job(case.identity, source_job).status == 'completed'
    assert table_hashes(case.database) == before


class PausedSyntheticResult:
    """Records synthetic actual-start/output facts, never launches a process."""
    def __init__(self, ledger):
        self.ledger = ledger
        self.reached, self.release = Event(), Event()
        self.launch_requests = 0

    def check(self, profile):
        self.ledger.check(profile)

    def run_checked(self, value, cancelled, on_started):
        self.launch_requests += 1
        started = utc_now()
        on_started(started)
        self.reached.set()
        assert self.release.wait(timeout=30)
        assert not cancelled()  # Existing execution keeps its original Policy/lease checks after publication.
        assertions = [dict(id=item.id, actual=item.expected, passed=True, error_code=None) for item in value.plan.assertions]
        stdout = canonical_bytes({'synthetic_execution_only': True, 'assertions': assertions})
        result = dict(job_id=value.job_id, input_sha256=sha256_bytes(canonical_bytes(value)),
            operation_sha256=value.operation_sha256, outcome='passed', verdict='PASS', started_at=started,
            finished_at=utc_now(), exit_code=0, assertions=assertions, output_sha256=sha256_bytes(stdout))
        result['result_sha256'] = numeric_result_sha256(result)
        return NumericExecution(NumericCheckResult.model_validate(result), stdout, b'', True, (), self.ledger.manifest_document())


def test_execution_already_started_can_finish_after_publication_without_overwriting_ack(tmp_path):
    case, reviews = generated_case(tmp_path, 'single')
    publication = DraftPublicationService(case.database, reviews, ImportService(case.database))
    case.authoring.verify_publication = publication.verify_recorded
    first = case.preview('A')
    original_ack = case.numeric.decide(case.identity, first.id, decision(first), 'A-approve')
    worker = case.worker()
    runtime = PausedSyntheticResult(case.runtime)
    worker.runtime = runtime
    with ThreadPoolExecutor(max_workers=1) as pool:
        running = pool.submit(worker.run_once)
        try:
            assert runtime.reached.wait(timeout=30)
            synthetic_numeric(case, 'B')
            receipt = reviewed(case.database, case.identity, case.candidate, reviews)
            intent = publish_request(case.database, case.identity, case.candidate, reviews, receipt)
            result = publication.publish(case.identity, case.candidate.draft_id, intent, 'publish')
        finally:
            runtime.release.set()
        assert running.result(timeout=30)
    current = case.numeric.read(case.identity, first.id)
    assert runtime.launch_requests == 1 and current.result.started_at is not None
    assert current.result.outcome == 'passed' and current.result.output_sha256 is not None
    assert case.numeric.decide(case.identity, first.id, decision(first), 'A-approve') == original_ack
    assert publication.publish(case.identity, case.candidate.draft_id, intent, 'publish') == result
    assert case.authoring.draft(case.identity, case.candidate.draft_id).published_ref.id == result.id
    (tmp_path / 'synthetic-single-finish-after-publication.json').write_bytes(canonical_bytes({
        'evidence_kind': 'synthetic-start-and-completion-facts-only', 'physical_processes_started': 0,
        'runtime_run_checked_calls': runtime.launch_requests,
        'original_approval': original_ack.model_dump(mode='json'), 'current_numeric': current.model_dump(mode='json'),
        'publication': result.model_dump(mode='json')}))
