"""One complete history validation per Run in a synchronous snapshot read.

Real SQLite query counts make the repeated-work regression deterministic; elapsed
wall time belongs to the separate native/polling diagnostic, not this assertion.
"""
from collections import Counter

import pytest

from services.api.app.application.errors import ApiError
from services.api.app.infrastructure.tutor_repository import TutorRepository
from tests.integration.test_retrieval import all_rows
from tests.integration.test_tutor_runs import started, tutor as tutor_fixture


@pytest.mark.parametrize('operation', ['source_state', 'view', 'messages'])
def test_snapshot_read_scans_each_owned_event_history_once(tmp_path, operation):
    database, identity, _, _ = values = tutor_fixture.__wrapped__(tmp_path)
    thread, _, ack = started(values)
    before = all_rows(database)
    scans = Counter()
    with database.transaction(immediate=False) as connection:
        def record(statement):
            if statement.startswith('SELECT * FROM tutor_events WHERE run_id='):
                scans[statement] += 1
        connection.set_trace_callback(record)
        repo = TutorRepository(connection, identity.workspace_id)
        result = getattr(repo, operation)(thread.id if operation == 'messages' else ack.run.id)
        assert result is not None
    assert list(scans.values()) == [1]
    assert all_rows(database) == before


def test_same_repository_rechecks_write_rollback_and_next_transaction(tmp_path):
    database, identity, _, _ = values = tutor_fixture.__wrapped__(tmp_path)
    _, _, ack = started(values)
    with database.connect() as connection:
        repo = TutorRepository(connection, identity.workspace_id)
        connection.execute('BEGIN')
        assert repo.source_state(ack.run.id).status == 'queued'
        connection.execute('SAVEPOINT corrupt')
        connection.execute('DELETE FROM tutor_events WHERE run_id=?', (ack.run.id,))
        with pytest.raises(ApiError) as damaged:
            repo.source_state(ack.run.id)
        assert damaged.value.code == 'TUTOR_INTEGRITY_ERROR'
        connection.execute('ROLLBACK TO corrupt')
        assert repo.source_state(ack.run.id).status == 'queued'
        connection.commit()
        with database.transaction() as writer:
            writer.execute('DELETE FROM tutor_commands WHERE run_id=?', (ack.run.id,))
        connection.execute('BEGIN')
        with pytest.raises(ApiError) as missing:
            repo.source_state(ack.run.id)
        assert missing.value.code == 'TUTOR_INTEGRITY_ERROR'
        connection.rollback()


def test_untransactional_read_never_reuses_a_checked_run(tmp_path):
    database, identity, _, _ = values = tutor_fixture.__wrapped__(tmp_path)
    _, _, ack = started(values)
    with database.connect() as connection:
        repo = TutorRepository(connection, identity.workspace_id)
        assert repo.source_state(ack.run.id).status == 'queued'
        connection.execute('DELETE FROM tutor_events WHERE run_id=?', (ack.run.id,))
        with pytest.raises(ApiError) as missing:
            repo.source_state(ack.run.id)
        assert missing.value.code == 'TUTOR_INTEGRITY_ERROR'


def test_all_prior_runs_are_checked_once_and_damage_is_not_hidden(tmp_path):
    from services.api.app.tutor_dto import TutorRunCancel
    database, identity, service, _ = values = tutor_fixture.__wrapped__(tmp_path)
    thread, request, first = started(values)
    service.cancel(identity, first.run.id, TutorRunCancel(expected_revision=1), 'stop-first')
    second = service.start(identity, request.model_copy(update={'expected_thread_revision': 3}), 'second')
    scans = Counter()
    with database.transaction(immediate=False) as connection:
        def record(statement):
            if statement.startswith('SELECT * FROM tutor_events WHERE run_id='):
                scans[statement] += 1
        connection.set_trace_callback(record)
        assert TutorRepository(connection, identity.workspace_id).source_state(second.run.id).status == 'queued'
    assert sorted(scans.values()) == [1, 1]
    with database.transaction() as connection:
        connection.execute('DELETE FROM tutor_events WHERE run_id=?', (first.run.id,))
    with pytest.raises(ApiError) as damaged:
        service.read(identity, second.run.id)
    assert damaged.value.code == 'TUTOR_INTEGRITY_ERROR'


def test_local_write_inside_nested_read_invalidates_prior_checked_row(tmp_path, monkeypatch):
    database, identity, _, _ = values = tutor_fixture.__wrapped__(tmp_path)
    _, _, ack = started(values)
    original_thread = TutorRepository.thread
    def corrupt_before_nested_thread(self, *args, **kwargs):
        self.connection.execute('DELETE FROM tutor_events WHERE run_id=?', (ack.run.id,))
        return original_thread(self, *args, **kwargs)
    monkeypatch.setattr(TutorRepository, 'thread', corrupt_before_nested_thread)
    with database.transaction() as connection:
        repo = TutorRepository(connection, identity.workspace_id)
        with pytest.raises(ApiError) as damaged:
            repo.source_state(ack.run.id)
        assert damaged.value.code == 'TUTOR_INTEGRITY_ERROR'
        connection.rollback()
