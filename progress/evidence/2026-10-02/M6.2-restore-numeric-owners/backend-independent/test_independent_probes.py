"""Private independent review probes at ea3d92ae; synthetic execution only."""
import pytest
from packages.contracts import domain_models as dm
from services.api.app.application.errors import ApiError
from services.api.app.application.restore_numeric_worker import RestoreNumericWorker
from services.api.app.infrastructure.restore_numeric_repository import RestoreNumericRepository
from services.api.app.infrastructure.authoring_job_repository import AuthoringJobRepository
from services.api.app.infrastructure.database import utc_now
from tests.integration.test_restore_numeric_service import restored as restored, preview
from tests.integration.test_restore_numeric_execution import SyntheticExecution
from tests.integration.test_authoring_numeric_service import decision
from tests.integration.test_publication_admission import reviewed, publish_request, admit
from tests.integration.test_authoring_numeric_provider_history import table_hashes


@pytest.mark.parametrize('stage', ['unbound', 'pending', 'admitted'])
def test_frozen_review_survives_future_approval_start_and_terminal(restored, stage):
    case = restored
    runtime = SyntheticExecution()
    case.service.runtime = runtime
    worker = RestoreNumericWorker(case.database, case.service, runtime)
    candidate = dm.DraftCandidate.model_validate(case.snapshot['candidate'])
    view = preview(case) if stage != 'unbound' else None
    lease = value = actor = None
    if stage == 'admitted':
        case.service.decide(case.identity, view.id, decision(view), 'approve')
        lease, value, actor = worker.claim()
        with case.database.transaction() as conn:
            RestoreNumericRepository(conn, case.identity.workspace_id).begin(lease, utc_now())
    reviews = case.app.state.review_service
    receipt = reviewed(case.database, case.identity, candidate, reviews)
    request = publish_request(case.database, case.identity, candidate, reviews, receipt)
    if stage != 'admitted':
        view = view or preview(case)
        case.service.decide(case.identity, view.id, decision(view), 'approve')
        assert worker.run_once()
    else:
        execution = runtime.run_checked(value, lambda: False,
            on_started=lambda actual: worker._started(lease, actual))
        worker._finish(lease, execution)
    assert case.service.read(case.identity, view.id).result.verdict == 'PASS'
    before = table_hashes(case.database)
    assert reviews.read(case.identity, receipt.id) == receipt
    with pytest.raises(ApiError) as error:
        admit(case.database, case.identity, candidate, reviews, request)
    assert error.value.code == 'PUBLISH_NUMERIC_OBSERVATION_STALE'
    assert table_hashes(case.database) == before


def test_worker_rotates_beyond_full_page_of_invalid_owner_hints(restored):
    case = restored
    runtime = SyntheticExecution()
    case.service.runtime = runtime
    # Deliberately malformed ownership registrations. These are scheduling hints,
    # not genuine approved inputs. A healthy, later actual Restore must still run.
    with case.database.transaction() as conn:
        jobs = AuthoringJobRepository(conn, case.identity.workspace_id)
        for index in range(33):
            jobs.create(f'review_invalid_{index}', 'authoring_numeric_check',
                {'version': 'restore-numeric-job-v1', 'candidate': {'draft_id': 'review_missing'}})
    view = preview(case)
    ack = case.service.decide(case.identity, view.id, decision(view), 'approve')
    worker = RestoreNumericWorker(case.database, case.service, runtime)
    with pytest.raises(ApiError):
        worker.run_once()
    assert runtime.calls == 0
    assert worker.run_once()
    assert runtime.calls == 1
    assert case.service.read(case.identity, view.id).result.verdict == 'PASS'
    with case.database.transaction(immediate=False) as conn:
        assert AuthoringJobRepository(conn, case.identity.workspace_id).snapshot(ack.job.id).status == 'completed'
