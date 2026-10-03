"""Real worker/write transactions with a deliberately nonexecuting runtime boundary."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.content import ContentService
from services.api.app.application.draft_publication import DraftPublicationService
from services.api.app.application.errors import ApiError
from services.api.app.application.imports import ImportService
from services.api.app.infrastructure.authoring_numeric_repository import NumericRepository
from services.api.app.infrastructure.authoring_numeric_runtime import NumericRuntimeError
from tests.integration.test_authoring_numeric_provider_history import table_hashes
from tests.integration.test_authoring_numeric_service import decision
from tests.integration.test_publication_admission import generated_case, publish_request, reviewed, synthetic_numeric
from tests.integration.test_single_publication import ready_single


class PausedNonexecutingRuntime:
    """Synchronization at the external runtime seam; never claims a process started."""
    def __init__(self, after_permit):
        self.after_permit = after_permit
        self.reached, self.release = Event(), Event()
        self.launch_requests = 0

    def pause(self):
        self.reached.set()
        assert self.release.wait(timeout=30)

    def check(self, profile):
        if not self.after_permit:
            self.pause()

    def run_checked(self, value, cancelled, on_started):
        self.launch_requests += 1
        assert self.after_permit, 'Published candidate received a new runtime request'
        self.pause()
        raise NumericRuntimeError('BLOCKED_ENVIRONMENT')


@pytest.mark.parametrize('permit_first', [False, True])
def test_publication_and_actual_worker_start_permission_serialize_on_one_writer_transaction(tmp_path, permit_first):
    case, reviews = generated_case(tmp_path, 'single')
    publication = DraftPublicationService(case.database, reviews, ImportService(case.database))
    case.authoring.verify_publication = publication.verify_recorded
    first = case.preview('A')
    case.numeric.decide(case.identity, first.id, decision(first), 'A-approval')
    worker = case.worker()
    work = worker.claim()
    synthetic_numeric(case, 'B')
    receipt = reviewed(case.database, case.identity, case.candidate, reviews)
    intent = publish_request(case.database, case.identity, case.candidate, reviews, receipt)
    runtime = PausedNonexecutingRuntime(permit_first)
    worker.runtime = runtime
    with ThreadPoolExecutor(max_workers=1) as pool:
        running = pool.submit(worker.process, *work)
        try:
            assert runtime.reached.wait(timeout=30)
            if permit_first:
                before = table_hashes(case.database)
                with pytest.raises(ApiError) as caught:
                    publication.publish(case.identity, case.candidate.draft_id, intent, 'publish')
                assert caught.value.code == 'PUBLISH_NUMERIC_OBSERVATION_STALE'
                assert table_hashes(case.database) == before
            else:
                result = publication.publish(case.identity, case.candidate.draft_id, intent, 'publish')
        finally:
            runtime.release.set()
        running.result(timeout=30)
    with case.database.transaction(immediate=False) as conn:
        start, end = NumericRepository(conn, case.identity.workspace_id).execution_state(work[0].job_id)
        assert (start.admitted_at is not None) == permit_first
        assert start.actual_started_at is None and end.result.started_at is None
    assert runtime.launch_requests == int(permit_first)
    if not permit_first:
        assert end.result.outcome == 'cancelled'
        assert publication.publish(case.identity, case.candidate.draft_id, intent, 'publish') == result
    (tmp_path / 'synthetic-single-start-publication-race.json').write_bytes(canonical_bytes({
        'evidence_kind': 'controlled-runtime-boundary-with-synthetic-B-ledger', 'physical_processes_started': 0,
        'order': 'start-permit-before-publication' if permit_first else 'publication-before-start-permit',
        'runtime_run_checked_calls': runtime.launch_requests, 'start': start.model_dump(mode='json'),
        'end': end.model_dump(mode='json'), 'job': case.numeric.job(case.identity, work[0].job_id).model_dump(mode='json'),
        'publication': {'error': 'PUBLISH_NUMERIC_OBSERVATION_STALE'} if permit_first else result.model_dump(mode='json')}))


def test_allocated_id_collision_is_absent_current_cas_not_revision_two(tmp_path, monkeypatch):
    from uuid import UUID
    from packages.contracts import domain_models as dm
    import services.api.app.application.single_publication as owner
    case, _, publication, intent = ready_single(tmp_path)
    fixed = UUID('01234567-89ab-cdef-0123-456789abcdef')
    identifier = 'generated_' + fixed.hex
    raw = b'Already occupied, synthetic content.\n'
    block = dm.ContentBlock(id=identifier, revision=1, kind='text', title='Occupied',
        body_path='content/occupied.md', body_sha256=sha256_bytes(raw))
    content = ContentService(case.database)
    old = content.publish(case.identity.workspace_id, [block], {block.body_path: raw})[0]
    monkeypatch.setattr(owner, 'uuid4', lambda: fixed)
    before = table_hashes(case.database)
    with pytest.raises(ApiError) as caught:
        publication.publish(case.identity, case.candidate.draft_id, intent, 'publish')
    assert caught.value.code == 'PUBLICATION_ID_UNAVAILABLE'
    assert table_hashes(case.database) == before
    assert content.current(case.identity.workspace_id, identifier) == old
