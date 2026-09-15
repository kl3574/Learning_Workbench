"""Learning owns manual route actions and derives completion from checked sources."""

import sqlite3
from uuid import uuid4

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, strict_json

from ..infrastructure.content_repository import ContentRepository, reference
from ..infrastructure.database import utc_now
from ..infrastructure.learning_repository import LearningRepository, StoredRouteCompletionAction, StoredUserAction, ref_key
from ..infrastructure.security import guard_subject_access
from ..learning_dto import LearningActionResponse, LearningProgress, RouteStepState
from .errors import ApiError
from .learning import validated_ref
from .practice_help_access import instant


def invalid_action() -> ApiError:
    return ApiError(409, 'LEARNING_ACTION_HISTORY_INVALID', '原生学习动作及进度无法通过来源校验。')


def _access(connection: sqlite3.Connection, workspace_id: str) -> tuple[ContentRepository, LearningRepository]:
    if not connection.in_transaction:
        raise ApiError(409, 'TRANSACTION_REQUIRED', '路线完成需要同一事务的内容与学习记录。')
    guard_subject_access(connection, workspace_id)
    content = ContentRepository(connection, workspace_id, allow_notes=True)
    content.require_workspace()
    return content, LearningRepository(connection, workspace_id)


def _binding(connection: sqlite3.Connection, workspace_id: str, row: sqlite3.Row,
             event: StoredUserAction | StoredRouteCompletionAction, revisions: dict[str, int]) -> None:
    if (event.workspace_id != workspace_id or event.event_id != row['event_id'] or event.kind != row['kind']
            or event.origin != row['origin'] or event.occurred_at != row['occurred_at']
            or canonical_bytes(event).decode() != row['payload_json']):
        raise invalid_action()
    rows = connection.execute("SELECT payload_json FROM outbox WHERE event_type='learning.action_recorded' AND json_extract(payload_json,'$.event_id')=?", (event.event_id,)).fetchall()
    if len(rows) != 1:
        raise invalid_action()
    payload = strict_json(rows[0]['payload_json'])
    if (not isinstance(payload, dict) or set(payload) != {'workspace_id', 'event_id', 'progress_revision'}
            or payload['workspace_id'] != workspace_id or payload['event_id'] != event.event_id
            or type(payload['progress_revision']) is not int or payload['progress_revision'] != revisions.get(event.event_id)
            or canonical_bytes(payload).decode() != rows[0]['payload_json']):
        raise invalid_action()


def checked_reading_activities(connection: sqlite3.Connection, workspace_id: str) -> list[StoredUserAction]:
    """Latest native read/unread per full ref, matching the stored read projection."""
    content, learning = _access(connection, workspace_id)
    progress = learning.progress()
    revisions = learning.action_revisions()
    latest: dict[tuple[str, str, int, str], StoredUserAction] = {}
    try:
        for row in connection.execute("SELECT * FROM learning_events WHERE workspace_id=? AND kind='read_marked' ORDER BY rowid", (workspace_id,)):
            event = StoredUserAction.model_validate(strict_json(row['payload_json']))
            _binding(connection, workspace_id, row, event, revisions)
            validated_ref(content, event.ref)
            latest[ref_key(event.ref)] = event
        actual = {ref_key(item.ref): item for item in progress.readings}
        if set(actual) != set(latest):
            raise invalid_action()
        for key, event in latest.items():
            if actual[key].read != event.value or actual[key].read_at != (event.occurred_at if event.value else None):
                raise invalid_action()
        return [latest[key] for key in sorted(latest)]
    except (ValueError, TypeError, KeyError):
        raise invalid_action() from None


def _manual_state(event: StoredRouteCompletionAction) -> RouteStepState:
    return RouteStepState(route_ref=event.route_ref, step_id=event.step_id, completed=event.completed,
        completion_origin='manual', manual_override=event.completed,
        completed_at=event.occurred_at if event.completed else None, updated_at=event.occurred_at,
        source_event_ids=[event.event_id])


def _checked_manual(connection: sqlite3.Connection, workspace_id: str) -> dict[tuple[tuple[str, str, int, str], str], StoredRouteCompletionAction]:
    content, learning = _access(connection, workspace_id)
    progress = learning.progress()
    revisions = learning.action_revisions()
    latest: dict[tuple[tuple[str, str, int, str], str], StoredRouteCompletionAction] = {}
    try:
        for row in connection.execute("SELECT * FROM learning_events WHERE workspace_id=? AND kind='route_step_completion_set' ORDER BY rowid", (workspace_id,)):
            event = StoredRouteCompletionAction.model_validate(strict_json(row['payload_json']))
            _binding(connection, workspace_id, row, event, revisions)
            validated_ref(content, event.route_ref)
            route = content.load('route', event.route_ref.id, event.route_ref.revision).value
            if event.route_ref.entity != 'route' or not isinstance(route, dm.Route) or sum(step.id == event.step_id for step in route.steps) != 1:
                raise invalid_action()
            latest[(ref_key(event.route_ref), event.step_id)] = event
        projected = {(ref_key(item.route_ref), item.step_id): item for item in progress.route_steps}
        if set(projected) != set(latest) or any(projected[key] != _manual_state(event) for key, event in latest.items()):
            raise invalid_action()
        return latest
    except (ValueError, TypeError, KeyError):
        raise invalid_action() from None


def record_route_completion(connection: sqlite3.Connection, workspace_id: str, route_ref: dm.ContentRef,
                            step_id: str, completed: bool, expected_revision: int) -> LearningActionResponse:
    content, learning = _access(connection, workspace_id)
    validated_ref(content, route_ref)
    route = content.load('route', route_ref.id, route_ref.revision).value
    if route_ref.entity != 'route' or not isinstance(route, dm.Route) or sum(step.id == step_id for step in route.steps) != 1:
        raise ApiError(422, 'ROUTE_STEP_INVALID', '步骤不属于该精确路线修订。')
    _checked_manual(connection, workspace_id)
    previous = learning.progress()
    if type(completed) is not bool or type(expected_revision) is not int:
        raise ApiError(422, 'SCHEMA_INVALID', '完成标记与进度基准类型无效。')
    if previous.revision != expected_revision:
        raise ApiError(412, 'REVISION_CONFLICT', '学习记录已更新，请保留本机候选并读取最新进度。')
    event = StoredRouteCompletionAction(event_id=f'event_{uuid4().hex}', workspace_id=workspace_id,
        route_ref=route_ref, step_id=step_id, completed=completed, occurred_at=utc_now())
    steps = {(ref_key(item.route_ref), item.step_id): item for item in previous.route_steps}
    steps[(ref_key(route_ref), step_id)] = _manual_state(event)
    updated = LearningProgress(revision=previous.revision + 1, readings=previous.readings, bookmarks=previous.bookmarks,
        route_steps=[steps[key] for key in sorted(steps)])
    learning.append(event)
    learning.save(previous, updated, event.event_id)
    _checked_manual(connection, workspace_id)
    from .recommendations import inputs_changed
    inputs_changed(connection, workspace_id, 'route.completion_recorded')
    return LearningActionResponse(event_id=event.event_id, progress_revision=updated.revision)


def validate_route_completion_receipt(connection: sqlite3.Connection, workspace_id: str, route_ref: dm.ContentRef,
                                      step_id: str, completed: bool, expected_revision: int,
                                      result: LearningActionResponse) -> LearningActionResponse:
    """A replay must still bind the original action, even after a later manual choice."""
    _, learning = _access(connection, workspace_id)
    _checked_manual(connection, workspace_id)
    row = connection.execute('SELECT * FROM learning_events WHERE workspace_id=? AND event_id=?',
        (workspace_id, result.event_id)).fetchone()
    try:
        if row is None:
            raise invalid_action()
        event = StoredRouteCompletionAction.model_validate(strict_json(row['payload_json']))
        _binding(connection, workspace_id, row, event, learning.action_revisions())
        if (event.route_ref != route_ref or event.step_id != step_id or event.completed != completed
                or result.progress_revision != expected_revision + 1):
            raise invalid_action()
        outbox = connection.execute("SELECT payload_json FROM outbox WHERE event_type='learning.action_recorded' "
            "AND json_extract(payload_json,'$.event_id')=?", (event.event_id,)).fetchone()
        if strict_json(outbox['payload_json'])['progress_revision'] != result.progress_revision:
            raise invalid_action()
        return result
    except (ValueError, TypeError, KeyError):
        raise invalid_action() from None


def route_step_projection(connection: sqlite3.Connection, workspace_id: str) -> list[RouteStepState]:
    from .assessment_activity_access import assessment_submissions
    from .content_learning_access import route_values
    from .practice_activity_access import practice_participation

    content, _ = _access(connection, workspace_id)
    manual = _checked_manual(connection, workspace_id)
    routes = route_values(connection, workspace_id)
    if not routes:
        return []
    readings = {ref_key(item.ref): item for item in checked_reading_activities(connection, workspace_id)}
    participation = practice_participation(connection, workspace_id)
    submissions = [*participation.submissions, *assessment_submissions(connection, workspace_id)]
    result = []
    for route in routes:
        route_ref = reference(route)
        states: dict[str, RouteStepState] = {}
        for step in route.steps:
            prior = manual.get((ref_key(route_ref), step.id))
            if prior is not None:
                states[step.id] = _manual_state(prior)
                continue
            state = RouteStepState(route_ref=route_ref, step_id=step.id, completed=False)
            if step.completion_rule == 'read':
                exact = readings.get(ref_key(step.target))
                sources = [exact] if exact is not None else []
                if exact is None and step.target.entity == 'lesson':
                    lesson = content.load('lesson', step.target.id, step.target.revision).value
                    if not isinstance(lesson, dm.Lesson):
                        raise invalid_action()
                    blocks = [readings.get(ref_key(ref)) for ref in lesson.block_refs]
                    if blocks and all(item is not None and item.value for item in blocks):
                        sources = [item for item in blocks if item is not None]
                if sources:
                    complete = all(item.value for item in sources)
                    time = max((item.occurred_at for item in sources), key=instant)
                    state = RouteStepState(route_ref=route_ref, step_id=step.id, completed=complete,
                        completion_origin='read', completed_at=time if complete else None, updated_at=time,
                        source_event_ids=[item.event_id for item in sources])
            elif step.completion_rule in {'practice_submitted', 'assessment_submitted'}:
                matches = [item for item in submissions if item.target_ref == step.target]
                if matches:
                    latest = max(matches, key=lambda item: (instant(item.submitted_at), item.event_id))
                    state = RouteStepState(route_ref=route_ref, step_id=step.id, completed=True,
                        completion_origin=step.completion_rule, completed_at=latest.submitted_at,
                        updated_at=latest.submitted_at, source_event_ids=[latest.event_id])
            states[step.id] = state
        for step in route.steps:
            state = states[step.id]
            result.append(RouteStepState(**{**state.model_dump(),
                'unmet_requires_steps': [key for key in step.requires_steps if not states[key].completed]}))
    return result
