"""Practice can append trusted events atomically, without fabricating grades."""

import json

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes
from services.api.app.application.content import ContentService
from services.api.app.application.errors import ApiError
from services.api.app.application.learning import LearningService, record_practice_event, validate_practice_event
from services.api.app.infrastructure.config import Settings
from services.api.app.infrastructure.content_repository import reference
from services.api.app.infrastructure.database import Database, utc_now
from services.api.app.infrastructure.security import SessionIdentity
from services.api.app.learning_dto import LearningActionRequest
from tests.practice_fixtures import practice_fixture


@pytest.fixture
def practice_state(tmp_path):
    database = Database(Settings(data_dir=tmp_path / 'data'))
    workspace = database.initialize()
    fixture = practice_fixture('learningport', profile='learner')
    ContentService(database).publish(workspace, fixture.public_objects, fixture.bodies)
    return database, workspace, fixture


@pytest.mark.parametrize('kind', ['hint_revealed', 'solution_revealed', 'practice_submitted'])
def test_trusted_event_preserves_reading_projection_and_rolls_back_with_caller(practice_state, kind):
    database, workspace, fixture = practice_state
    service = LearningService(database)
    identity = SessionIdentity('session_learning_port', workspace, 'learner', 'unused', '2099-01-01T00:00:00Z')
    service.action(identity, LearningActionRequest(kind='bookmark_set', ref=reference(fixture.block), expected_revision=1, value=True), 'bookmark-before-practice')
    before = service.progress(workspace)
    ref = reference(fixture.practice if kind == 'practice_submitted' else fixture.questions[0])
    with database.transaction() as connection:
        event_id = record_practice_event(connection, workspace, kind, ref, 'practice_session_original')
    after = service.progress(workspace)
    assert after.revision == before.revision + 1
    assert after.readings == before.readings and after.bookmarks == before.bookmarks and after.route_steps == before.route_steps
    with database.connect() as connection:
        stored = dm.LearningEvent.model_validate_json(connection.execute('SELECT payload_json FROM learning_events WHERE event_id=?', (event_id,)).fetchone()[0])
        counts = [connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in ['learning_events', 'outbox']]
    assert stored.actor == 'server' and stored.origin == 'native' and stored.kind == kind
    assert stored.ref == ref and stored.attempt_id == 'practice_session_original'
    with database.connect() as connection:
        validate_practice_event(connection, workspace, event_id, kind, ref, 'practice_session_original')
    with pytest.raises(RuntimeError, match='caller failed'):
        with database.transaction() as connection:
            record_practice_event(connection, workspace, kind, ref, 'practice_session_failed')
            raise RuntimeError('caller failed after event append')
    assert service.progress(workspace) == after
    with database.connect() as connection:
        assert [connection.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] for table in ['learning_events', 'outbox']] == counts
        assert connection.execute('SELECT COUNT(*) FROM evidence').fetchone()[0] == 0


def test_port_requires_transaction_correct_kind_and_exact_ref_without_side_effects(practice_state):
    database, workspace, fixture = practice_state
    ref = reference(fixture.questions[0])
    with database.connect() as connection, pytest.raises(ApiError) as missing_transaction:
        record_practice_event(connection, workspace, 'hint_revealed', ref, 'practice_session')
    assert missing_transaction.value.status == 409
    for kind, candidate in [('grade_finalized', ref), ('hint_revealed', reference(fixture.practice)), ('hint_revealed', ref.model_copy(update={'sha256': '0' * 64}))]:
        with pytest.raises(ApiError) as rejected, database.transaction() as connection:
            record_practice_event(connection, workspace, kind, candidate, 'practice_session')
        assert rejected.value.status == 422
    with database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM learning_events').fetchone()[0] == 0
        assert connection.execute('SELECT COUNT(*) FROM learning_progress').fetchone()[0] == 0


@pytest.mark.parametrize('field,value', [
    ('workspace_id', 'workspace_other'), ('event_id', 'event_other'), ('actor', 'learner'),
    ('origin', 'user_supplied_import'), ('kind', 'solution_revealed'), ('attempt_id', 'practice_session_other'),
    ('occurred_at', '2020-01-01T00:00:00Z'),
])
def test_event_read_port_rejects_mismatched_payload_without_rewriting_history(practice_state, field, value):
    database, workspace, fixture = practice_state
    ref = reference(fixture.questions[0])
    event = dm.LearningEvent(event_id='event_corrupt_binding', workspace_id=workspace, actor='server', origin='native',
        kind='hint_revealed', ref=ref, occurred_at=utc_now(), attempt_id='practice_session_original')
    changed = {**event.model_dump(mode='json'), field: value}
    # Explicit storage corruption fixture: insert a mismatched immutable row,
    # without disabling guards or pretending a normal API produced this event.
    with database.transaction() as connection:
        connection.execute('INSERT INTO learning_events(event_id,workspace_id,kind,origin,payload_json,occurred_at) VALUES(?,?,?,?,?,?)',
            (event.event_id, workspace, event.kind, event.origin, canonical_bytes(changed).decode(), event.occurred_at))
    with database.connect() as connection, pytest.raises(ApiError) as rejected:
        validate_practice_event(connection, workspace, event.event_id, 'hint_revealed', ref, 'practice_session_original')
    assert rejected.value.status == 409 and rejected.value.code == 'PRACTICE_SNAPSHOT_INVALID'
    with database.connect() as connection:
        assert json.loads(connection.execute('SELECT payload_json FROM learning_events WHERE event_id=?', (event.event_id,)).fetchone()[0]) == changed
        assert connection.execute('SELECT COUNT(*) FROM learning_progress').fetchone()[0] == 0


def test_existing_independent_guard_blocks_practice_event_before_any_write(practice_state):
    database, workspace, fixture = practice_state
    assessment = dm.AssessmentBlueprint(id='assessment_learning_port', revision=1, title='Synthetic independent guard', question_refs=[reference(fixture.questions[0])], allowed_modes=['independent'])
    ContentService(database).publish(workspace, [assessment], {})
    policy = dm.PolicySnapshot(mode='independent', tutor_scope='operation_help_only', allow_web=False, allow_materials=False)
    with database.transaction() as connection:
        connection.execute('INSERT INTO attempts(id,workspace_id,assessment_id,assessment_revision,mode,policy_json,question_refs_json,solution_refs_private_json,status,revision,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)',
            ('attempt_learning_guard', workspace, assessment.id, 1, 'independent', canonical_bytes(policy).decode(), json.dumps([reference(fixture.questions[0]).model_dump(mode='json')]), '[]', 'active', 1, utc_now()))
    with pytest.raises(ApiError) as rejected, database.transaction() as connection:
        record_practice_event(connection, workspace, 'solution_revealed', reference(fixture.questions[0]), 'practice_session')
    assert rejected.value.status == 409
    with database.connect() as connection:
        assert connection.execute('SELECT COUNT(*) FROM learning_events').fetchone()[0] == 0
