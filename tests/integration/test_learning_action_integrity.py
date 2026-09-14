"""Controlled SQLite faults: immutable user events retained; only outbox linkage changed."""
import pytest
from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, strict_json
from services.api.app.application.errors import ApiError
from services.api.app.application.learning import LearningService
from services.api.app.application.route_progress import record_route_completion, route_step_projection
from services.api.app.application.content import ContentService
from services.api.app.application.practice import PracticeService
from services.api.app.application.practice_activity_access import practice_participation
from services.api.app.infrastructure.content_repository import reference
from services.api.app.practice_dto import PracticeSessionCreate, PracticeSubmitRequest
from tests.integration.test_notes_learning import storage
from tests.integration.test_assessment_attempts import storage as assessment_storage

__all__ = ['storage', 'assessment_storage']


def test_original_manual_revision_binding_not_hidden_by_later_false(storage):
    database, workspace, _, objects, _ = storage
    route = dm.Route(id='route_review', revision=1, title='Source history review', goal='No grade', steps=[dm.RouteStep(id='step_review', title='Manual', target=reference(objects[0]), completion_rule='manual')])
    ContentService(database).publish(workspace, [route], {})
    with database.transaction() as connection:
        first = record_route_completion(connection, workspace, reference(route), 'step_review', True, 1)
        second = record_route_completion(connection, workspace, reference(route), 'step_review', False, 2)
        before = route_step_projection(connection, workspace)
        assert before[0].manual_override is False and before[0].source_event_ids == [second.event_id]
        row = connection.execute("SELECT id,payload_json FROM outbox WHERE json_extract(payload_json,'$.event_id')=?", (first.event_id,)).fetchone()
        payload = strict_json(row['payload_json'])
        assert payload['progress_revision'] == 2
        payload['progress_revision'] = 3
        connection.execute('UPDATE outbox SET payload_json=? WHERE id=?', (canonical_bytes(payload).decode(), row['id']))
    with database.transaction() as connection, pytest.raises(ApiError):
        route_step_projection(connection, workspace)


def test_practice_submission_without_own_learning_outbox_not_admitted(assessment_storage):
    database, identity, fixture, _ = assessment_storage
    service = PracticeService(database)
    session = service.create_session(identity, PracticeSessionCreate(practice_ref=reference(fixture.practice)), 'create')
    service.submit(identity, session.id, PracticeSubmitRequest(expected_revision=1), 'submit')
    with database.transaction() as connection:
        original = practice_participation(connection, identity.workspace_id)
        assert len(original.submissions) == 1
        event_id = original.submissions[0].event_id
        deleted = connection.execute("DELETE FROM outbox WHERE event_type='learning.action_recorded' AND json_extract(payload_json,'$.event_id')=?", (event_id,))
        assert deleted.rowcount == 1
    with database.transaction() as connection, pytest.raises(ApiError):
        practice_participation(connection, identity.workspace_id)


def test_manual_false_replay_does_not_change_older_original_time(storage):
    database, workspace, _, objects, _ = storage
    route = dm.Route(id='route_time_control', revision=1, title='Original times', goal='No grade', steps=[dm.RouteStep(id='step_review', title='Read', target=reference(objects[0]), completion_rule='read')])
    ContentService(database).publish(workspace, [route], {})
    with database.transaction() as connection:
        first = record_route_completion(connection, workspace, reference(route), 'step_review', True, 1)
        second = record_route_completion(connection, workspace, reference(route), 'step_review', False, 2)
        view = route_step_projection(connection, workspace)[0]
        assert view.completed is False and view.completed_at is None
        assert view.source_event_ids == [second.event_id] and first.event_id != second.event_id
    before = LearningService(database).progress(workspace)
    assert LearningService(database).progress(workspace) == before
