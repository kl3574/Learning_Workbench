"""Actual SQLite lifecycle adapter, not an implemented review HTTP/worker flow."""
import json

import pytest
from packages.contracts.canonical import canonical_bytes, sha256_bytes
from services.api.app.application.errors import ApiError
from services.api.app.application.jobs import JobService, active_subject_work
from services.api.app.application.review_models import ReviewJobInput
from services.api.app.infrastructure.authoring_job_repository import AuthoringJobRepository
from services.api.app.infrastructure.database import utc_now
from services.api.app.infrastructure.review_job_repository import ReviewJobRepository
from services.api.app.review_dto import DraftReviewWrite
from tests.integration.test_draft_candidate_owners import imported_candidate as import_fixture
from tests.integration.test_authoring_numeric_provider_history import table_hashes


@pytest.fixture
def prepared(tmp_path):
    for database, identity, _, _, _, candidate in import_fixture.__wrapped__(tmp_path):
        value = ReviewJobInput(version='draft-review-job-v1', workspace_id=identity.workspace_id,
            review_id='review_synthetic', source_kind='import', candidate=candidate,
            request=DraftReviewWrite(expected_revision=candidate.draft_revision,
                checks=['structure', 'sources'], reviewer_note='Synthetic review intent; no approval'),
            creator_session_id=identity.id, rules_version='draft-review-rules-v1', created_at=utc_now())
        yield database, identity, value


def create(prepared):
    database, identity, value = prepared
    with database.transaction() as conn:
        ReviewJobRepository(conn, identity.workspace_id).create(value.review_id, 'draft_review', value)
    return database, identity, value


def test_review_job_is_queued_excluded_from_authoring_and_not_registered_as_fake_handler(prepared):
    database, identity, value = create(prepared)
    with database.transaction(immediate=False) as conn:
        conn.execute('PRAGMA query_only=ON')
        repo = ReviewJobRepository(conn, identity.workspace_id)
        job = repo.snapshot(value.review_id)
        assert (job.kind, job.status, job.revision, job.result_refs) == ('draft_review', 'queued', 1, [])
        assert repo.input(value.review_id) == value
        assert repo.input_version(value.review_id) == 'draft-review-job-v1'
        assert value.review_id in repo.member_ids()
        assert value.review_id not in AuthoringJobRepository(conn, identity.workspace_id).member_ids()
        assert any(work.id == value.review_id for work in active_subject_work(conn, identity.workspace_id))
        with pytest.raises(ApiError) as caught:
            AuthoringJobRepository(conn, identity.workspace_id).load(value.review_id)
        assert caught.value.code == 'JOB_MISSING'
        assert conn.execute('SELECT count(*) FROM reviews').fetchone()[0] == 0
    # This adapter alone cannot pretend that the future review application exists.
    with pytest.raises(ApiError) as caught:
        JobService(database).job(identity, value.review_id)
    assert caught.value.code == 'JOB_KIND_UNAVAILABLE'


def test_claim_cancel_ack_history_and_single_terminal_share_real_transaction(prepared):
    database, identity, value = create(prepared)
    with database.transaction() as conn:
        repo = ReviewJobRepository(conn, identity.workspace_id)
        queued = repo.snapshot(value.review_id)
        lease = repo.claim(value.review_id)
        assert repo.owned(repo.load(value.review_id), lease)
        assert repo.renew(lease)
        with pytest.raises(ApiError):
            repo.claim(value.review_id)
        running = repo.snapshot(value.review_id)
        ack = repo.cancel(value.review_id, running.revision)
        recorded_at = utc_now()
        assert (ack.status, ack.revision) == ('running', running.revision + 1)
        assert not repo.owned(repo.load(value.review_id), lease)
        assert repo.owned(repo.load(value.review_id), lease, allow_cancel=True)
        repo.transition(repo.load(value.review_id), 'cancelled', result={'cancelled_before_report': True})
        assert repo.snapshot(value.review_id).status == 'cancelled'
        assert repo.snapshot(value.review_id, queued.revision) == queued
        repo.verify_cancel_ack(value.review_id, running.revision, ack, running.revision, recorded_at)
        assert [event.seq for event in repo.event_prefix(value.review_id, ack.revision)] == [1, 2, 3]
        with pytest.raises(ApiError) as caught:
            repo.transition(repo.load(value.review_id), 'completed', result={'not_a_report': True})
        assert caught.value.code == 'JOB_TERMINAL'
        assert conn.execute('SELECT count(*) FROM reviews').fetchone()[0] == 0
    before = table_hashes(database)
    with database.transaction(immediate=False) as conn:
        conn.execute('PRAGMA query_only=ON')
        repo = ReviewJobRepository(conn, identity.workspace_id)
        assert repo.input(value.review_id) == value
        repo.verify_cancel_ack(value.review_id, running.revision, ack, running.revision, recorded_at)
    assert table_hashes(database) == before


def test_expired_lease_recovery_rejects_previous_owner_and_preserves_input(prepared):
    database, identity, value = create(prepared)
    with database.transaction() as conn:
        repo = ReviewJobRepository(conn, identity.workspace_id)
        old = repo.claim(value.review_id)
        conn.execute("UPDATE jobs SET lease_until='2000-01-01T00:00:00Z' WHERE id=?", (value.review_id,))
    with database.transaction() as conn:
        repo = ReviewJobRepository(conn, identity.workspace_id)
        fresh = repo.claim(value.review_id)
        assert fresh.owner != old.owner and fresh.revision == old.revision + 1
        assert not repo.owned(repo.load(value.review_id), old)
        assert not repo.renew(old)
        assert repo.owned(repo.load(value.review_id), fresh)
        assert repo.input(value.review_id) == value
        repo.transition(repo.load(value.review_id), 'failed', result={'error_code': 'SYNTHETIC_REVIEW_NOT_EXECUTED'})
    with database.transaction(immediate=False) as conn:
        repo = ReviewJobRepository(conn, identity.workspace_id)
        assert repo.snapshot(value.review_id).status == 'failed'
        assert len(repo.event_prefix(value.review_id, 4)) == 4
        assert conn.execute('SELECT count(*) FROM reviews').fetchone()[0] == 0


def test_local_review_job_cannot_acquire_an_authoring_approval_state(prepared):
    database, identity, value = create(prepared)
    with database.transaction() as conn:
        ReviewJobRepository(conn, identity.workspace_id).claim(value.review_id)
    before = table_hashes(database)
    with pytest.raises(ApiError), database.transaction() as conn:
        repo = ReviewJobRepository(conn, identity.workspace_id)
        repo.transition(repo.load(value.review_id), 'awaiting_approval')
    assert table_hashes(database) == before


@pytest.mark.parametrize('damage', ['workspace', 'id', 'version', 'request_revision', 'unknown', 'kind'])
def test_invalid_review_input_is_rejected_before_any_job_or_event(prepared, damage):
    database, identity, value = prepared
    raw = value.model_dump(mode='json')
    kind = 'draft_review'
    if damage == 'workspace':
        raw['workspace_id'] = 'workspace_other'
    elif damage == 'id':
        raw['review_id'] = 'review_other'
    elif damage == 'version':
        raw['version'] = 'authoring-job-v1'
    elif damage == 'request_revision':
        raw['request']['expected_revision'] += 1
    elif damage == 'unknown':
        raw['approved'] = True
    else:
        kind = 'authoring'
    before = table_hashes(database)
    with database.transaction() as conn, pytest.raises(ApiError):
        ReviewJobRepository(conn, identity.workspace_id).create(value.review_id, kind, raw)
    assert table_hashes(database) == before


def test_caller_transaction_rollback_keeps_job_and_event_atomic(prepared):
    database, identity, value = prepared
    before = table_hashes(database)
    with pytest.raises(RuntimeError), database.transaction() as conn:
        ReviewJobRepository(conn, identity.workspace_id).create(value.review_id, 'draft_review', value)
        raise RuntimeError('synthetic owner transaction failed')
    assert table_hashes(database) == before
    with database.connect() as conn, pytest.raises(ApiError) as caught:
        ReviewJobRepository(conn, identity.workspace_id).create(value.review_id, 'draft_review', value)
    assert caught.value.code == 'TRANSACTION_REQUIRED'
    assert table_hashes(database) == before


@pytest.mark.parametrize('damage', ['event', 'input_bytes', 'self_consistent_wrong_version', 'workspace_read'])
def test_restart_read_checks_complete_history_and_consumer_identity(prepared, damage):
    database, identity, value = create(prepared)
    workspace = identity.workspace_id
    with database.transaction() as conn:
        if damage == 'event':
            conn.execute('DELETE FROM job_events WHERE job_id=?', (value.review_id,))
        elif damage == 'input_bytes':
            conn.execute("UPDATE jobs SET input_json='{}' WHERE id=?", (value.review_id,))
        elif damage == 'self_consistent_wrong_version':
            raw = value.model_dump(mode='json')
            raw['version'] = 'authoring-job-v1'
            encoded = canonical_bytes(raw)
            digest = sha256_bytes(encoded)
            conn.execute('UPDATE jobs SET input_json=?,input_sha256=? WHERE id=?',
                         (encoded.decode(), digest, value.review_id))
            event = conn.execute('SELECT payload_json FROM job_events WHERE job_id=?', (value.review_id,)).fetchone()
            payload = json.loads(event[0])
            payload['input_sha256'] = digest
            conn.execute('UPDATE job_events SET payload_json=? WHERE job_id=?',
                         (canonical_bytes(payload).decode(), value.review_id))
        else:
            workspace = 'workspace_other'
    before = table_hashes(database)
    with database.transaction(immediate=False) as conn, pytest.raises(ApiError):
        conn.execute('PRAGMA query_only=ON')
        ReviewJobRepository(conn, workspace).input(value.review_id)
    assert table_hashes(database) == before


@pytest.mark.parametrize('kind', ['authoring', 'authoring_numeric_check'])
def test_authoring_initial_statuses_and_consumer_isolation_remain_unchanged(prepared, kind):
    database, identity, _ = prepared
    with database.transaction() as conn:
        authoring = AuthoringJobRepository(conn, identity.workspace_id)
        authoring.create('job_synthetic_legacy', kind, {'version': 'synthetic_lifecycle_only'})
        assert authoring.snapshot('job_synthetic_legacy').status == ('awaiting_approval' if kind == 'authoring' else 'queued')
        review = ReviewJobRepository(conn, identity.workspace_id)
        assert 'job_synthetic_legacy' not in review.member_ids()
        with pytest.raises(ApiError) as caught:
            review.load('job_synthetic_legacy')
        assert caught.value.code == 'JOB_MISSING'
