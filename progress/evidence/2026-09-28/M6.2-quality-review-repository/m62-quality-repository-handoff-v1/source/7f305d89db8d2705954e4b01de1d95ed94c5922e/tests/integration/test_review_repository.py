"""Internal Quality persistence with explicit synthetic intent; no review application."""
import pytest

from services.api.app.application.errors import ApiError
from services.api.app.application.review_history_models import ReviewCreateCommand, ReviewCancelCommand
from services.api.app.infrastructure.authoring_job_repository import AuthoringJobRepository
from services.api.app.infrastructure.database import utc_now
from services.api.app.infrastructure.review_job_repository import ReviewJobRepository
from services.api.app.infrastructure.review_repository import ReviewRepository
from tests.integration.test_review_job_lifecycle import prepared as job_fixture


@pytest.fixture
def prepared(tmp_path):
    yield from job_fixture.__wrapped__(tmp_path)


def create_job(connection, workspace, value):
    jobs = ReviewJobRepository(connection, workspace)
    jobs.create(value.review_id, 'draft_review', value)
    return ReviewCreateCommand(workspace_id=workspace, actor_id=value.creator_session_id,
        route=f'POST /drafts/{value.candidate.draft_id}/review', command_key='synthetic_create',
        review_id=value.review_id, basis_revision=value.candidate.draft_revision, resulting_revision=1,
        recorded_at=utc_now(), command_kind='create', request=value.request,
        ack={'id': value.review_id, 'status': 'queued'})


def test_binding_and_original_create_replay_preserve_real_job_without_a_receipt(prepared):
    database, identity, value = prepared
    with database.transaction() as connection:
        command = create_job(connection, identity.workspace_id, value)
        repo = ReviewRepository(connection, identity.workspace_id)
        repo.bind(value, command)
        bound = repo.binding(value.review_id)
        assert bound.input == value and bound.owner == 'import'
        assert bound.job.status == 'queued' and bound.job.revision == 1
        assert repo.replay(command.actor_id, command.route, command.command_key, command.request) == command
        assert connection.execute('SELECT count(*) FROM reviews').fetchone()[0] == 0
        assert connection.execute('SELECT count(*) FROM review_revisions').fetchone()[0] == 0


def test_cancel_ack_and_original_create_replay_do_not_use_latest_snapshot(prepared):
    database, identity, value = prepared
    with database.transaction() as connection:
        create = create_job(connection, identity.workspace_id, value)
        repo = ReviewRepository(connection, identity.workspace_id)
        repo.bind(value, create)
        jobs = ReviewJobRepository(connection, identity.workspace_id)
        ack = jobs.cancel(value.review_id, 1)
        cancel = ReviewCancelCommand(workspace_id=identity.workspace_id, actor_id=identity.id,
            route=f'POST /jobs/{value.review_id}/cancel', command_key='synthetic_cancel',
            review_id=value.review_id, basis_revision=1, resulting_revision=ack.revision,
            recorded_at=utc_now(), command_kind='cancel', request={'expected_revision': 1}, ack=ack.model_dump())
        repo.record_cancel(cancel)
        assert repo.replay(create.actor_id, create.route, create.command_key, create.request) == create
        assert repo.replay(cancel.actor_id, cancel.route, cancel.command_key, cancel.request) == cancel
        assert repo.binding(value.review_id).job.status == 'cancelled'
        assert connection.execute('SELECT count(*) FROM reviews').fetchone()[0] == 0


def test_failed_binding_is_rolled_back_when_caller_catches_and_commits_other_work(prepared):
    database, identity, value = prepared
    with database.transaction() as connection:
        command = create_job(connection, identity.workspace_id, value)
        connection.execute("UPDATE workspace SET title='unrelated outer change' WHERE id=?", (identity.workspace_id,))
        connection.execute("CREATE TEMP TRIGGER reject_quality_command BEFORE INSERT ON review_commands "
                           "BEGIN SELECT RAISE(ABORT,'synthetic injected failure'); END")
        with pytest.raises(ApiError) as caught:
            ReviewRepository(connection, identity.workspace_id).bind(value, command)
        assert caught.value.code == 'REVIEW_INTEGRITY_ERROR'
        assert connection.in_transaction
    with database.connect() as connection:
        assert connection.execute('SELECT count(*) FROM review_jobs').fetchone()[0] == 0
        assert connection.execute('SELECT count(*) FROM review_commands').fetchone()[0] == 0
        assert connection.execute('SELECT title FROM workspace WHERE id=?', (identity.workspace_id,)).fetchone()[0] == 'unrelated outer change'
        # This method's savepoint does not undo the caller's earlier Jobs write.
        assert connection.execute('SELECT count(*) FROM jobs WHERE id=?', (value.review_id,)).fetchone()[0] == 1


@pytest.mark.parametrize('method', ['bind', 'binding', 'replay', 'record_cancel'])
def test_each_operation_rechecks_current_transaction_even_after_construction(prepared, method):
    database, identity, value = prepared
    with database.connect() as connection:
        connection.execute('BEGIN')
        repo = ReviewRepository(connection, identity.workspace_id)
        connection.commit()
        with pytest.raises(ApiError) as caught:
            if method == 'bind':
                repo.bind(value, None)
            elif method == 'record_cancel':
                repo.record_cancel(None)
            elif method == 'binding':
                repo.binding(value.review_id)
            else:
                repo.replay(identity.id, 'POST /synthetic', 'synthetic', value.request)
        assert caught.value.code == 'TRANSACTION_REQUIRED'


def test_original_key_conflict_and_cross_workspace_do_not_mutate(prepared):
    database, identity, value = prepared
    with database.transaction() as connection:
        command = create_job(connection, identity.workspace_id, value)
        repo = ReviewRepository(connection, identity.workspace_id)
        repo.bind(value, command)
        with pytest.raises(ApiError) as caught:
            repo.replay(command.actor_id, command.route, command.command_key,
                        command.request.model_copy(update={'reviewer_note': 'different synthetic request'}))
        assert caught.value.code == 'IDEMPOTENCY_CONFLICT'
        assert repo.replay('another_actor', command.route, command.command_key, command.request) is None
        with pytest.raises(ApiError) as caught:
            ReviewRepository(connection, 'another_workspace').binding(value.review_id)
        assert caught.value.status == 404
        assert connection.execute('SELECT count(*) FROM review_commands').fetchone()[0] == 1


def test_other_job_consumer_cannot_be_bound_as_a_review(prepared):
    database, identity, value = prepared
    with database.transaction() as connection:
        AuthoringJobRepository(connection, identity.workspace_id).create(value.review_id, 'authoring', {})
        with pytest.raises(ApiError) as caught:
            ReviewRepository(connection, identity.workspace_id).bind(value, {})
        assert caught.value.code == 'REVIEW_INTEGRITY_ERROR'
        assert connection.execute('SELECT count(*) FROM review_jobs').fetchone()[0] == 0
