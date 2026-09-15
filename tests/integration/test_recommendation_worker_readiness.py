"""Real WAL snapshots and owner operations at the maintenance admission boundary."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
import sqlite3
from threading import Event, current_thread

import pytest

from services.api.app.application import recommendations
from services.api.app.application.content import ContentService
from services.api.app.application.errors import ApiError
from services.api.app.application.reader import ReaderService
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.recommendation_repository import RecommendationRepository
from services.api.app.infrastructure.security import SessionIdentity
from tests.integration.test_content_repository import ref, tree
from tests.integration.test_assessment_attempts import start, storage
from tests.integration.test_recommendations import stored_rows

__all__ = ['storage']


@pytest.fixture
def current_projection(tmp_path):
    database = Database(Settings(data_dir=tmp_path / 'data'))
    workspace = database.initialize()
    content = ContentService(database)
    values, bodies = tree(concept=False)
    content.publish(workspace, values, bodies)
    assert recommendations.RecommendationWorker(database).run_once()
    return database, workspace, content, values


def held_current_basis(monkeypatch, database):
    """Hold after the real checked basis returns true, still inside its transaction."""
    held, release, contender_begin = Event(), Event(), Event()
    original_basis = recommendations.basis_current
    original_connect = database.connect

    def basis(*args):
        result = original_basis(*args)
        if result and not held.is_set():
            held.set()
            assert release.wait(10), 'test cleanup did not release the real read snapshot'
        return result

    @contextmanager
    def connect(*args, **kwargs):
        with original_connect(*args, **kwargs) as connection:
            if current_thread().name.startswith('contender'):
                connection.set_trace_callback(lambda sql: contender_begin.set()
                                              if sql == 'BEGIN IMMEDIATE' else None)
            yield connection

    monkeypatch.setattr(recommendations, 'basis_current', basis)
    monkeypatch.setattr(database, 'connect', connect)
    return held, release, contender_begin


@pytest.mark.parametrize('read', ['lesson', 'outline'])
def test_no_work_snapshot_does_not_reserve_writer_while_actual_content_read_completes(
        current_projection, monkeypatch, read):
    database, workspace, content, values = current_projection
    identity = SessionIdentity('session_readiness_test', workspace, 'learner', 'unused', '2099-01-01T00:00:00Z')
    before = stored_rows(database)
    held, release, contender_begin = held_current_basis(monkeypatch, database)
    completed = Event()

    def read_content():
        try:
            if read == 'lesson':
                return content.read(workspace, 'lesson', values[1].id, 1)
            return ReaderService(database).outline(identity, values[2].id, 1)
        finally:
            completed.set()

    with ThreadPoolExecutor(1, thread_name_prefix='maintenance') as maintenance, \
            ThreadPoolExecutor(1, thread_name_prefix='contender') as reader:
        worker = maintenance.submit(recommendations.RecommendationWorker(database).run_once)
        try:
            assert held.wait(5)
            result = reader.submit(read_content)
            assert contender_begin.wait(5), 'actual Content transaction was not attempted'
            # This measures lock independence at a held snapshot, not a CI latency SLA.
            assert completed.wait(1), 'actual Content BEGIN remains blocked by a no-work maintenance snapshot'
            actual = result.result()
            assert (actual if read == 'lesson' else actual.course_ref) == (values[1] if read == 'lesson' else ref(values[2]))
        finally:
            release.set()
        assert worker.result(timeout=5) is False
    assert stored_rows(database) == before


def test_source_can_commit_during_no_work_snapshot_and_dirty_survives_until_next_tick(
        current_projection, monkeypatch):
    database, workspace, content, old_values = current_projection
    held, release, contender_begin = held_current_basis(monkeypatch, database)
    values, bodies = tree(2, concept=False)
    completed = Event()

    def publish():
        try:
            return content.publish(workspace, values, bodies)
        finally:
            completed.set()

    with ThreadPoolExecutor(1, thread_name_prefix='maintenance') as maintenance, \
            ThreadPoolExecutor(1, thread_name_prefix='contender') as writer:
        worker = maintenance.submit(recommendations.RecommendationWorker(database).run_once)
        try:
            assert held.wait(5)
            publication = writer.submit(publish)
            assert contender_begin.wait(5)
            assert completed.wait(1), 'source publication remains blocked by a no-work maintenance snapshot'
            assert publication.result() == [ref(value) for value in values]
        finally:
            release.set()
        assert worker.result(timeout=5) is False
    with database.transaction(immediate=False) as connection:
        state, snapshots, _ = RecommendationRepository(connection, workspace).checked()
        assert state['generation'] > state['completed_generation']
        assert state['failure_json'] is None
        old_snapshot = snapshots[-1].id
    assert recommendations.RecommendationWorker(database).run_once() is True
    with database.transaction(immediate=False) as connection:
        state, snapshots, _ = RecommendationRepository(connection, workspace).checked()
        assert state['generation'] == state['completed_generation']
        assert snapshots[-1].id != old_snapshot
        assert recommendations.basis_current(snapshots[-1], recommendations.load_inputs(connection, workspace),
                                             recommendations.parameters(database), recommendations.utc_now())
        assert recommendations.load_inputs(connection, workspace).catalog.course_refs == [ref(old_values[2]), ref(values[2])]


def after_read_snapshot(monkeypatch, database, action):
    """Perform a real owner action after the first read txn has fully exited."""
    original = database.transaction
    observed = []

    @contextmanager
    def transaction(*args, **kwargs):
        with original(*args, **kwargs) as connection:
            yield connection
        if kwargs.get('immediate') is False and not observed:
            observed.append('read snapshot exited')
            action()

    monkeypatch.setattr(database, 'transaction', transaction)
    return observed


def test_needed_work_uses_new_source_in_separate_writer_transaction(current_projection, monkeypatch):
    database, workspace, content, first = current_projection
    second, bodies = tree(2, concept=False)
    content.publish(workspace, second, bodies)
    third, bodies = tree(3, concept=False)
    observed = after_read_snapshot(monkeypatch, database, lambda: content.publish(workspace, third, bodies))
    published = []
    original_publish = RecommendationRepository.publish

    def publish(repository, **kwargs):
        # The production publication must still own the native SQLite writer
        # lock. A separate connection cannot begin a competing write here.
        with database.connect(busy_timeout_ms=0) as contender:
            with pytest.raises(sqlite3.OperationalError, match='locked'):
                contender.execute('BEGIN IMMEDIATE')
        published.append(kwargs['basis'])
        return original_publish(repository, **kwargs)

    monkeypatch.setattr(RecommendationRepository, 'publish', publish)
    assert recommendations.RecommendationWorker(database).run_once() is True
    assert observed and len(published) == 1
    with database.transaction(immediate=False) as connection:
        state, snapshots, _ = RecommendationRepository(connection, workspace).checked()
        current = recommendations.load_inputs(connection, workspace)
        assert current.catalog.course_refs == [ref(first[2]), ref(second[2]), ref(third[2])]
        assert published == [current.model_dump(mode='json')]
        assert snapshots[-1].basis == published[0]
        assert state['generation'] == state['completed_generation']


def test_peer_worker_can_finish_between_admission_phases_without_duplicate_publish(current_projection, monkeypatch):
    database, workspace, content, _ = current_projection
    second, bodies = tree(2, concept=False)
    content.publish(workspace, second, bodies)
    peer_rows = []

    def peer():
        assert recommendations.RecommendationWorker(database).run_once() is True
        peer_rows.append(stored_rows(database))

    observed = after_read_snapshot(monkeypatch, database, peer)
    assert recommendations.RecommendationWorker(database).run_once() is False
    assert observed and stored_rows(database) == peer_rows[0]
    assert recommendations.RecommendationService(database).page(workspace).projection_state == 'ready'


@pytest.mark.parametrize('phase', ['before_read', 'before_write'])
def test_actual_independent_policy_blocks_without_refresh_failure_or_snapshot(storage, monkeypatch, phase):
    database, _, _, _ = storage
    before = []

    def activate():
        assert start(storage).status == 'active'
        before.append(stored_rows(database))

    if phase == 'before_read':
        activate()
    else:
        # Import's committed source is dirty, so classification requires work.
        observed = after_read_snapshot(monkeypatch, database, activate)
    assert recommendations.RecommendationWorker(database).run_once() is False
    if phase == 'before_write':
        assert observed
    assert stored_rows(database) == before[0]


def test_read_failure_retains_snapshot_and_retry_is_checked_readonly_until_due(current_projection, monkeypatch):
    database, workspace, _, _ = current_projection
    original_load = recommendations.load_inputs
    calls = []

    def failure(connection, owner):
        calls.append(owner)
        raise ValueError('controlled read failure')

    monkeypatch.setattr(recommendations, 'load_inputs', failure)
    assert recommendations.RecommendationWorker(database).run_once() is False
    assert calls == [workspace]
    with database.transaction(immediate=False) as connection:
        state, snapshots, _ = RecommendationRepository(connection, workspace).checked()
        assert state['failure_json'] is not None and state['retry_at'] is not None
        original_snapshot = snapshots[-1]
        future = (datetime.fromisoformat(state['retry_at'].replace('Z', '+00:00')) + timedelta(seconds=1)).isoformat().replace('+00:00', 'Z')
    before = stored_rows(database)
    checked = []
    original_checked = RecommendationRepository.checked

    def check(repository):
        checked.append(repository.workspace_id)
        return original_checked(repository)

    monkeypatch.setattr(RecommendationRepository, 'checked', check)
    assert recommendations.RecommendationWorker(database).run_once() is False
    assert checked == [workspace] and calls == [workspace]
    assert stored_rows(database) == before
    monkeypatch.setattr(recommendations, 'load_inputs', original_load)
    monkeypatch.setattr(recommendations, 'utc_now', lambda: future)
    assert recommendations.RecommendationWorker(database).run_once() is True
    with database.transaction(immediate=False) as connection:
        state, snapshots, _ = RecommendationRepository(connection, workspace).checked()
        assert state['failure_json'] is None and state['retry_at'] is None
        assert snapshots[-1] == original_snapshot


def test_retry_cannot_bypass_corrupt_history(current_projection, monkeypatch):
    database, workspace, _, _ = current_projection
    # Explicit integrity fault fixture; not a product mutation or repair.
    with database.transaction() as connection:
        connection.execute('DROP TRIGGER recommendation_snapshots_no_update')
        connection.execute('UPDATE recommendation_snapshots SET sequence=sequence+1 WHERE workspace_id=?', (workspace,))
        connection.execute('UPDATE recommendation_projection_state SET retry_at=? WHERE workspace_id=?',
                           ((datetime.now(UTC) + timedelta(minutes=1)).isoformat().replace('+00:00', 'Z'), workspace))
    before = stored_rows(database)
    errors = []
    original = RecommendationRepository.checked

    def check(repository):
        try:
            return original(repository)
        except ApiError as error:
            errors.append(error.code)
            raise

    monkeypatch.setattr(RecommendationRepository, 'checked', check)
    assert recommendations.RecommendationWorker(database).run_once() is False
    # Initial read and original guarded recovery both fail closed; no error
    # projection is allowed to overwrite an unverified ledger.
    assert errors == ['RECOMMENDATION_INTEGRITY_INVALID'] * 2
    assert stored_rows(database) == before


def test_unknown_read_error_retains_original_propagation_and_never_writes(current_projection, monkeypatch):
    database, _, _, _ = current_projection
    before = stored_rows(database)

    def unexpected(*_args):
        raise RuntimeError('controlled unexpected owner failure')

    monkeypatch.setattr(recommendations, 'load_inputs', unexpected)
    with pytest.raises(RuntimeError, match='controlled unexpected owner failure'):
        recommendations.RecommendationWorker(database).run_once()
    assert stored_rows(database) == before
