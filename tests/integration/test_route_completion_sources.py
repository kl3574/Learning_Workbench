"""Native route actions retain their provenance and do not grant ability evidence."""

import sqlite3

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, strict_json
from services.api.app.application.content import ContentService
from services.api.app.application.errors import ApiError
from services.api.app.application.learning import LearningService
from services.api.app.application.route_progress import checked_reading_activities, record_route_completion, route_step_projection
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database
from services.api.app.infrastructure.learning_repository import LearningRepository
from services.api.app.learning_dto import LearningActionRequest
from tests.integration.test_notes_learning import storage

__all__ = ['storage']


def publish_route(storage, revision=1):
    database, workspace, _, objects, _ = storage
    route = dm.Route(id='route_completion_sources', revision=revision, title='Original synthetic route', goal='Participation only', steps=[
        dm.RouteStep(id='step_manual', title='Explicit marker', target=reference(objects[0]), completion_rule='manual'),
        dm.RouteStep(id='step_read', title='Read precise lesson', target=reference(objects[1]), requires_steps=['step_manual'], completion_rule='read'),
    ])
    ContentService(database).publish(workspace, [route], {})
    return route


def mark(storage, ref, value=True, key='read'):
    database, workspace, identity, _, _ = storage
    with database.connect() as connection:
        revision = LearningRepository(connection, workspace).progress().revision
    return LearningService(database).action(identity, LearningActionRequest(kind='read_marked', ref=ref, value=value, expected_revision=revision), key)


def state(storage):
    database, workspace, *_ = storage
    with database.transaction() as connection:
        return route_step_projection(connection, workspace)


def counts(database):
    with database.connect() as connection:
        return {name: connection.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]
            for name in ['learning_events', 'learning_progress', 'outbox', 'evidence', 'grades', 'idempotency']}


def test_real_read_can_complete_without_prerequisite_and_manual_false_survives_restart(storage):
    database, workspace, _, objects, _ = storage
    route = publish_route(storage)
    read = mark(storage, reference(objects[1]))
    original = state(storage)
    auto = next(item for item in original if item.step_id == 'step_read')
    assert auto.completed and auto.completion_origin == 'read'
    assert auto.unmet_requires_steps == ['step_manual'] and auto.source_event_ids == [read.event_id]
    before = counts(database)
    with database.transaction() as connection:
        result = record_route_completion(connection, workspace, reference(route), 'step_read', False, read.progress_revision)
    changed = state(storage)
    manual = next(item for item in changed if item.step_id == 'step_read')
    assert not manual.completed and manual.manual_override is False
    assert manual.completion_origin == 'manual' and manual.completed_at is None and manual.updated_at
    assert manual.source_event_ids == [result.event_id]
    assert counts(database)['grades'] == before['grades'] == 0
    assert counts(database)['evidence'] == before['evidence'] == 0
    restarted = Database(database.settings)
    restarted.initialize()
    before_restart_read = counts(database)
    with restarted.transaction() as connection:
        assert route_step_projection(connection, workspace) == changed
    assert counts(database) == before_restart_read


def test_new_route_version_does_not_inherit_manual_but_preserves_original_activity_time(storage):
    database, workspace, _, objects, _ = storage
    first = publish_route(storage)
    read = mark(storage, reference(objects[1]))
    original_auto = next(item for item in state(storage) if item.step_id == 'step_read')
    with database.transaction() as connection:
        record_route_completion(connection, workspace, reference(first), 'step_read', False, read.progress_revision)
    second = publish_route(storage, revision=2)
    all_states = state(storage)
    old = next(item for item in all_states if item.route_ref == reference(first) and item.step_id == 'step_read')
    new = next(item for item in all_states if item.route_ref == reference(second) and item.step_id == 'step_read')
    assert not old.completed and old.manual_override is False
    assert new.completed and new.manual_override is None
    assert new.source_event_ids == original_auto.source_event_ids
    assert new.completed_at == original_auto.completed_at


def test_explicit_lesson_unread_overrides_all_blocks_and_preserves_unread_event(storage):
    _, _, _, objects, _ = storage
    publish_route(storage)
    block_read = mark(storage, reference(objects[0]))
    auto = next(item for item in state(storage) if item.step_id == 'step_read')
    assert auto.completed and auto.source_event_ids == [block_read.event_id]
    unread = mark(storage, reference(objects[1]), False, 'unread-lesson')
    auto = next(item for item in state(storage) if item.step_id == 'step_read')
    assert not auto.completed and auto.completion_origin == 'read' and auto.completed_at is None
    assert auto.source_event_ids == [unread.event_id]


def test_manual_write_failure_rolls_back_event_progress_and_outbox(storage):
    database, workspace, *_ = storage
    route = publish_route(storage)
    before = counts(database)
    with database.transaction() as connection:
        connection.execute("CREATE TRIGGER injected_route_outbox_failure BEFORE INSERT ON outbox WHEN NEW.event_type='learning.action_recorded' BEGIN SELECT RAISE(ABORT,'synthetic route failure'); END")
    with pytest.raises(sqlite3.IntegrityError), database.transaction() as connection:
        record_route_completion(connection, workspace, reference(route), 'step_manual', True, 1)
    assert counts(database) == before
    with database.transaction() as connection:
        connection.execute('DROP TRIGGER injected_route_outbox_failure')
        result = record_route_completion(connection, workspace, reference(route), 'step_manual', True, 1)
    assert result.progress_revision == 2
    assert next(item for item in state(storage) if item.step_id == 'step_manual').completed


@pytest.mark.parametrize('part', ['projection', 'event', 'outbox'])
def test_manual_projection_event_or_outbox_corruption_never_becomes_trusted_completion(storage, part):
    database, workspace, *_ = storage
    route = publish_route(storage)
    with database.transaction() as connection:
        result = record_route_completion(connection, workspace, reference(route), 'step_manual', False, 1)
        if part == 'projection':
            row = connection.execute('SELECT projection_json FROM learning_progress WHERE workspace_id=?', (workspace,)).fetchone()
            value = strict_json(row[0])
            value['route_steps'][0]['completed'] = True
            connection.execute('UPDATE learning_progress SET projection_json=? WHERE workspace_id=?', (canonical_bytes(value).decode(), workspace))
        elif part == 'event':
            connection.execute('DROP TRIGGER event_no_update')
            connection.execute("UPDATE learning_events SET origin='user_supplied_import' WHERE event_id=?", (result.event_id,))
        else:
            connection.execute("DELETE FROM outbox WHERE json_extract(payload_json,'$.event_id')=?", (result.event_id,))
    before = counts(database)
    with database.transaction() as connection, pytest.raises(ApiError) as rejected:
        route_step_projection(connection, workspace)
    assert rejected.value.code == 'LEARNING_ACTION_HISTORY_INVALID'
    assert counts(database) == before


def test_read_projection_without_native_action_is_not_a_route_completion_source(storage):
    database, workspace, _, objects, _ = storage
    mark(storage, reference(objects[1]))
    with database.transaction() as connection:
        connection.execute('UPDATE learning_progress SET last_event_id=NULL WHERE workspace_id=?', (workspace,))
        connection.execute("DELETE FROM learning_events WHERE kind='read_marked' AND workspace_id=?", (workspace,))
    with database.transaction() as connection, pytest.raises(ApiError) as rejected:
        checked_reading_activities(connection, workspace)
    assert rejected.value.code == 'LEARNING_ACTION_HISTORY_INVALID'
