"""Explicit learning actions; no inferred grades, mastery, or read-on-open effects."""

from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
import sqlite3
from typing import Literal

from packages.contracts import domain_models as dm

from ..infrastructure.content_repository import ContentRepository, damaged, reference
from ..infrastructure.database import Database
from ..infrastructure.idempotency import execute_idempotent
from ..infrastructure.learning_repository import LearningRepository, ref_key
from ..infrastructure.security import SessionIdentity, guard_subject_access
from ..learning_dto import LearningActionRequest, LearningActionResponse, LearningProgress
from .errors import ApiError


def validated_ref(repository: ContentRepository, ref: dm.ContentRef) -> None:
    if reference(repository.load(ref.entity, ref.id, ref.revision).value) != ref:
        raise ApiError(422, "REFERENCE_HASH_MISMATCH", "引用哈希与指定修订不一致。")


def reading_states(connection: sqlite3.Connection, workspace_id: str, lesson_refs: Sequence[dm.ContentRef],
                   lesson_blocks: Mapping[str, Sequence[dm.ContentRef]]) -> dict[str, Literal["unread", "read", "stale"]]:
    guard_subject_access(connection, workspace_id)
    repository = ContentRepository(connection, workspace_id, allow_notes=True)
    repository.require_workspace()
    progress = LearningRepository(connection, workspace_id).progress()
    for item in progress.readings:
        validated_ref(repository, item.ref)
    exact = {ref_key(item.ref): item.read for item in progress.readings}
    prior = {(item.ref.entity, item.ref.id) for item in progress.readings if item.read}
    result: dict[str, Literal["unread", "read", "stale"]] = {}
    for ref in lesson_refs:
        validated_ref(repository, ref)
        key = f"{ref.entity}:{ref.id}:{ref.revision}:{ref.sha256}"
        blocks = lesson_blocks.get(key, ())
        for block in blocks:
            validated_ref(repository, block)
        if ref_key(ref) in exact:
            # An explicit unmark of this lesson takes precedence over block aggregation.
            state: Literal["unread", "read", "stale"] = "read" if exact[ref_key(ref)] else "unread"
        elif blocks and all(exact.get(ref_key(block)) is True for block in blocks):
            state = "read"
        elif (ref.entity, ref.id) in prior or any((block.entity, block.id) in prior and ref_key(block) not in exact for block in blocks):
            state = "stale"
        else:
            state = "unread"
        result[key] = state
    return result


class LearningService:
    def __init__(self, database: Database):
        self.database = database

    @contextmanager
    def _access(self, workspace_id: str) -> Iterator[tuple[ContentRepository, LearningRepository]]:
        try:
            with self.database.transaction() as connection:
                content = ContentRepository(connection, workspace_id, allow_notes=True)
                content.require_workspace()
                guard_subject_access(connection, workspace_id)
                yield content, LearningRepository(connection, workspace_id)
        except sqlite3.Error:
            raise ApiError(503, "LEARNING_STORAGE_UNAVAILABLE", "学习记录存储暂不可用。", True) from None

    def progress(self, workspace_id: str, course_id: str | None = None) -> LearningProgress:
        from .content_learning_access import target_in_course_scope
        from .route_progress import route_step_projection

        with self._access(workspace_id) as (content, learning):
            result = learning.progress()
            for ref in [*(item.ref for item in result.readings), *(item.ref for item in result.bookmarks)]:
                validated_ref(content, ref)
            routes = route_step_projection(content.connection, workspace_id)
            if course_id is None:
                return LearningProgress(revision=result.revision, readings=result.readings,
                    bookmarks=result.bookmarks, route_steps=routes)
            # The Content-owned port preserves exact members of every historical
            # course version, including precise Practice/Assessment membership.
            def includes(ref: dm.ContentRef) -> bool:
                return target_in_course_scope(content.connection, workspace_id, ref, course_id)
            course = content.current(course_id).value
            if not isinstance(course, dm.Course):
                raise ApiError(404, 'REFERENCE_MISSING', '指定课程不存在或不可访问。')
            scoped = []
            for state in routes:
                route = content.load('route', state.route_ref.id, state.route_ref.revision).value
                if not isinstance(route, dm.Route):
                    raise damaged()
                if any(step.id == state.step_id and includes(step.target) for step in route.steps):
                    scoped.append(state)
            return LearningProgress(revision=result.revision,
                readings=[item for item in result.readings if includes(item.ref)],
                bookmarks=[item for item in result.bookmarks if includes(item.ref)], route_steps=scoped)

    def action(self, identity: SessionIdentity, request: LearningActionRequest, key: str | None) -> LearningActionResponse:
        with self._access(identity.workspace_id) as (content, learning):
            def operation():
                validated_ref(content, request.ref)
                return learning.action(request).model_dump(mode="json")

            result = execute_idempotent(content.connection, actor=identity.workspace_id, route="POST /learning/actions",
                                        key=key, payload=request.model_dump(mode="json"), operation=operation)
            return LearningActionResponse.model_validate(result)


def record_note_created(connection: sqlite3.Connection, workspace_id: str, ref: dm.ContentRef) -> str:
    if not connection.in_transaction:
        raise ApiError(409, "TRANSACTION_REQUIRED", "笔记事件需要有效事务。")
    guard_subject_access(connection, workspace_id)
    content = ContentRepository(connection, workspace_id, allow_notes=True)
    content.require_workspace()
    validated_ref(content, ref)
    if ref.entity != "note":
        raise ApiError(422, "SCHEMA_INVALID", "笔记事件必须引用笔记修订。")
    return LearningRepository(connection, workspace_id).note_created(ref)


def record_practice_event(connection: sqlite3.Connection, workspace_id: str,
                          kind: Literal["hint_revealed", "solution_revealed", "practice_submitted"],
                          ref: dm.ContentRef, practice_session_id: str) -> str:
    """Trusted Practice application port; no public event or grade-writing API."""
    if not connection.in_transaction:
        raise ApiError(409, "TRANSACTION_REQUIRED", "练习事件需要有效事务。")
    expected_entity = {"hint_revealed": "question", "solution_revealed": "question", "practice_submitted": "practice_set"}
    if kind not in expected_entity or ref.entity != expected_entity[kind]:
        raise ApiError(422, "SCHEMA_INVALID", "练习事件类型与引用不匹配。")
    content = ContentRepository(connection, workspace_id)
    content.require_workspace()
    guard_subject_access(connection, workspace_id)
    validated_ref(content, ref)
    return LearningRepository(connection, workspace_id).practice_event(kind, ref, practice_session_id)


def validate_practice_event(connection: sqlite3.Connection, workspace_id: str, event_id: str,
                            kind: Literal["hint_revealed", "solution_revealed", "practice_submitted"],
                            ref: dm.ContentRef, practice_session_id: str) -> None:
    """Read-only verification port for an immutable Practice-to-Learning binding."""
    expected_entity = {"hint_revealed": "question", "solution_revealed": "question", "practice_submitted": "practice_set"}
    if kind not in expected_entity or ref.entity != expected_entity[kind]:
        raise ApiError(409, "PRACTICE_SNAPSHOT_INVALID", "练习事件类型与引用不匹配。")
    content = ContentRepository(connection, workspace_id)
    content.require_workspace()
    guard_subject_access(connection, workspace_id)
    validated_ref(content, ref)
    LearningRepository(connection, workspace_id).validate_practice_event(event_id, kind, ref, practice_session_id)


def record_test_submitted(connection: sqlite3.Connection, workspace_id: str,
                          assessment_ref: dm.ContentRef, attempt_id: str) -> str:
    """Trusted Assessment port; only the caller's just-submitted transaction may append."""
    from .assessment_content import validate_assessment_reference
    from .policy import guard_attempt_access

    if not connection.in_transaction:
        raise ApiError(409, "TRANSACTION_REQUIRED", "测验提交事件需要有效事务。")
    if assessment_ref.entity != "assessment":
        raise ApiError(422, "SCHEMA_INVALID", "测验提交事件必须引用准确测验修订。")
    access = guard_attempt_access(connection, workspace_id, attempt_id, assessment_ref=assessment_ref)
    if access.status != "submitted":
        raise ApiError(409, "ASSESSMENT_STATE_INVALID", "只有已持久化交卷的测验可记录提交事件。")
    validate_assessment_reference(connection, workspace_id, assessment_ref)
    return LearningRepository(connection, workspace_id).test_submitted(assessment_ref, attempt_id)


def validate_test_submitted(connection: sqlite3.Connection, workspace_id: str, event_id: str,
                            assessment_ref: dm.ContentRef, attempt_id: str) -> None:
    """Read-only validation of the real Assessment-to-Learning event association."""
    from .assessment_content import validate_assessment_reference
    from .policy import guard_attempt_access

    if assessment_ref.entity != "assessment":
        raise ApiError(409, "ASSESSMENT_SNAPSHOT_INVALID", "测验事件引用类型无效。")
    access = guard_attempt_access(connection, workspace_id, attempt_id, assessment_ref=assessment_ref)
    if access.status not in {"submitted", "grading", "graded", "needs_review"}:
        raise ApiError(409, "ASSESSMENT_SNAPSHOT_INVALID", "未交卷测验不能关联提交事件。")
    validate_assessment_reference(connection, workspace_id, assessment_ref)
    LearningRepository(connection, workspace_id).validate_test_submitted(event_id, assessment_ref, attempt_id)


def read_learning_event(connection: sqlite3.Connection, workspace_id: str, event_id: str) -> dm.LearningEvent:
    """Typed read port for module-owned exposure references, without claiming eligibility."""
    guard_subject_access(connection, workspace_id)
    return LearningRepository(connection, workspace_id).read_learning_event(event_id)


def checked_action_revisions(connection: sqlite3.Connection, workspace_id: str) -> dict[str, int]:
    """Learning-owned original progress bindings, for transaction-scoped projections."""
    if not connection.in_transaction:
        raise ApiError(409, 'TRANSACTION_REQUIRED', '学习动作来源需要同一事务的进度记录。')
    guard_subject_access(connection, workspace_id)
    ContentRepository(connection, workspace_id).require_workspace()
    return LearningRepository(connection, workspace_id).action_revisions()


def practice_submission_event(connection: sqlite3.Connection, workspace_id: str,
                              practice_ref: dm.ContentRef, session_id: str) -> dm.LearningEvent:
    """Learning-owned lookup for the original single Practice submission event."""
    if not connection.in_transaction:
        raise ApiError(409, 'TRANSACTION_REQUIRED', '练习提交来源需要同一事务的学习记录。')
    guard_subject_access(connection, workspace_id)
    rows = connection.execute("SELECT event_id FROM learning_events WHERE workspace_id=? AND kind='practice_submitted' "
        "AND json_extract(payload_json,'$.attempt_id')=?", (workspace_id, session_id)).fetchall()
    if len(rows) != 1:
        raise ApiError(409, 'PRACTICE_SNAPSHOT_INVALID', '练习提交缺少唯一原生学习事件。')
    event_id = rows[0]['event_id']
    validate_practice_event(connection, workspace_id, event_id, 'practice_submitted', practice_ref, session_id)
    if event_id not in checked_action_revisions(connection, workspace_id):
        raise ApiError(409, 'LEARNING_ACTION_HISTORY_INVALID', '练习提交缺少原始学习进度回执。')
    return read_learning_event(connection, workspace_id, event_id)
