"""Bounded scheduling over actual queued Tutor jobs, without altering bad history."""

import pytest

from packages.contracts import domain_models as dm
from services.api.app.application.errors import ApiError
from services.api.app.application.tutor_worker import TutorWorker
from services.api.app.infrastructure.tutor_repository import TutorRepository
from services.api.app.tutor_dto import TutorRunCreate
from tests.integration.test_tutor_runs import NoTransport, build_material, tutor as tutor_fixture


@pytest.fixture
def state(tmp_path):
    return tutor_fixture.__wrapped__(tmp_path)


def queue(state, key):
    _, identity, service, create = state
    thread = service.create_thread(identity, create, f'thread-{key}')
    return service.start(identity, TutorRunCreate(request=dm.TutorRequest(thread_id=thread.id,
        workspace_id=identity.workspace_id, message='独立线程中的原创问题。', intent='explain', context=create.scope),
        expected_thread_revision=thread.revision, binding=create.binding), f'run-{key}')


def remove_user(database, run_id):
    with database.transaction() as connection:
        original = connection.execute('SELECT * FROM messages WHERE run_id=?', (run_id,)).fetchone()
        owned = connection.execute('SELECT * FROM tutor_messages WHERE message_id=?', (original['id'],)).fetchone()
        connection.execute('DELETE FROM tutor_messages WHERE message_id=?', (original['id'],))
        connection.execute('DELETE FROM messages WHERE id=?', (original['id'],))
    return tuple(original), tuple(owned)


def job_rows(database, run_id):
    with database.connect() as connection:
        return {table: [tuple(row) for row in connection.execute(f'SELECT * FROM {table} WHERE {key}=?', (run_id,))]
            for table, key in [('jobs', 'id'), ('job_events', 'job_id'), ('runs', 'id'),
                              ('tutor_runs', 'run_id'), ('tutor_events', 'run_id')]}


def test_two_intact_threads_can_both_prepare_without_a_workspace_global_run_limit(state):
    database, identity, service, _ = state
    first, second = queue(state, 'first'), queue(state, 'second')
    provider = NoTransport()
    worker = TutorWorker(database, service.context, provider, build_material)
    assert worker.run_once() and worker.run_once()
    assert [service.read(identity, item.run.id).run.status for item in (first, second)] == ['awaiting_approval'] * 2
    assert provider.calls == 0


def test_candidate_scan_is_bounded_to_32_and_next_tick_reaches_the_next_actual_job(state, monkeypatch):
    database, identity, service, _ = state
    rejected = [queue(state, f'broken-{index:02}') for index in range(32)]
    good = queue(state, 'after-batch')
    for item in rejected:
        remove_user(database, item.run.id)
    before = {item.run.id: job_rows(database, item.run.id) for item in rejected}
    seen = []
    original = TutorRepository.source_state
    def observe(repo, run_id):
        seen.append(run_id)
        return original(repo, run_id)
    monkeypatch.setattr(TutorRepository, 'source_state', observe)
    worker = TutorWorker(database, service.context, NoTransport(), build_material)
    with pytest.raises(ApiError) as corrupt:
        worker.run_once()
    assert corrupt.value.code == 'TUTOR_INTEGRITY_ERROR'
    assert seen == [item.run.id for item in rejected]
    assert worker.run_once()
    assert service.read(identity, good.run.id).run.status == 'awaiting_approval'
    assert {item.run.id: job_rows(database, item.run.id) for item in rejected} == before


def test_unknown_admission_error_is_not_silently_reclassified_or_skipped(state, monkeypatch):
    database, _, service, _ = state
    first, second = queue(state, 'unknown'), queue(state, 'other')
    before = [job_rows(database, item.run.id) for item in (first, second)]
    error = ApiError(503, 'TEST_UNEXPECTED_OWNER_FAILURE', 'Synthetic owner failure.')
    seen = []
    def fail(repo, run_id):
        seen.append(run_id)
        raise error
    monkeypatch.setattr(TutorRepository, 'source_state', fail)
    worker = TutorWorker(database, service.context, NoTransport(), build_material)
    with pytest.raises(ApiError) as actual:
        worker.run_once()
    assert actual.value is error and seen == [first.run.id]
    assert [job_rows(database, item.run.id) for item in (first, second)] == before


def test_oldest_corrupt_job_cannot_starve_another_thread_and_repaired_original_can_reenter(state):
    database, identity, service, _ = state
    bad, good = queue(state, 'bad'), queue(state, 'good')
    with database.connect() as connection:
        assert [row[0] for row in connection.execute("SELECT id FROM jobs WHERE kind='tutor' ORDER BY created_at,id")] == [bad.run.id, good.run.id]
    original, owned = remove_user(database, bad.run.id)
    before = job_rows(database, bad.run.id)
    provider = NoTransport()
    worker = TutorWorker(database, service.context, provider, build_material)
    errors = []
    for _ in range(2):
        try:
            worker.run_once()
        except ApiError as error:
            errors.append(error.code)
    assert service.read(identity, good.run.id).run.status == 'awaiting_approval'
    assert errors and set(errors) == {'TUTOR_INTEGRITY_ERROR'}
    assert job_rows(database, bad.run.id) == before
    with pytest.raises(ApiError) as damaged:
        service.read(identity, bad.run.id)
    assert damaged.value.code == 'TUTOR_INTEGRITY_ERROR'
    # Explicit fixture repair restores the exact original bytes. The scheduler
    # itself does not rewrite, abandon, permanently quarantine or forgive them.
    with database.transaction() as connection:
        connection.execute('INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?)', original)
        connection.execute('INSERT INTO tutor_messages VALUES(?,?,?,?,?)', owned)
    assert worker.run_once()
    assert service.read(identity, bad.run.id).run.status == 'awaiting_approval'
    assert provider.calls == 0
