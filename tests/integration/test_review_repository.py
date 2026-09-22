"""Internal Quality persistence with explicit synthetic intent; no review application."""
import pytest

from services.api.app.application.review_history_models import ReviewCreateCommand
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
