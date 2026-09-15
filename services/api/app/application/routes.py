"""Immutable route commands and exact navigation, separate from user progress."""

from contextlib import contextmanager
from collections.abc import Iterator
import sqlite3

from pydantic import TypeAdapter

from packages.contracts import domain_models as dm
from packages.contracts.validation import validate_route

from ..infrastructure.content_repository import damaged, reference
from ..infrastructure.database import Database
from ..infrastructure.idempotency import execute_idempotent
from ..infrastructure.security import SessionIdentity
from ..learning_dto import LearningActionResponse
from ..route_dto import (PageRoute, RouteAssessmentOption, RouteCompletionRequest,
    RouteNavigationOption, RoutePracticeOption, RouteReaderOption, RouteTargetBinding)
from .assessment_content import AssessmentContent
from .content import ContentService, invalid
from .content_learning_access import learning_scope, route_values
from .errors import ApiError
from .policy import Policy


class RouteService:
    def __init__(self, database: Database):
        self.database = database
        self.content = ContentService(database)

    @contextmanager
    def _access(self, workspace_id: str) -> Iterator[AssessmentContent]:
        try:
            with self.database.transaction() as connection:
                content = AssessmentContent(connection, workspace_id)
                content.public.require_workspace()
                Policy(connection, workspace_id).check('subject_read')
                yield content
        except sqlite3.Error:
            raise ApiError(503, 'ROUTE_STORAGE_UNAVAILABLE', '路线存储暂不可用。', True) from None

    @staticmethod
    def _validate(value: dm.Route) -> dm.Route:
        try:
            checked = dm.Route.model_validate(value.model_dump(mode='python'))
            validate_route(checked)
            return checked
        except (ValueError, TypeError):
            raise invalid() from None

    def _navigation(self, content: AssessmentContent, route_ref: dm.ContentRef, step: dm.RouteStep,
                    course_refs: list[dm.ContentRef]) -> RouteTargetBinding:
        target = content.exact(step.target)
        options: list[RouteNavigationOption] = []
        if isinstance(target, dm.AssessmentBlueprint):
            concepts = content.concepts(content.questions(target))
            parents = list(content.course_witnesses(concepts))
            options = [RouteAssessmentOption(kind='assessment', assessment_ref=step.target, course_ref=parent) for parent in parents]
            if not options:
                options.append(RouteAssessmentOption(kind='assessment', assessment_ref=step.target, course_ref=None))
        else:
            for course_ref in course_refs:
                course = content.exact(course_ref)
                if not isinstance(course, dm.Course):
                    raise damaged()
                for lesson_ref in course.lesson_refs:
                    lesson = content.exact(lesson_ref)
                    if not isinstance(lesson, dm.Lesson):
                        raise damaged()
                    if isinstance(target, dm.PracticeSet) and target.lesson_ref == lesson_ref:
                        options.append(RoutePracticeOption(kind='practice', course_ref=course_ref,
                            lesson_ref=lesson_ref, practice_ref=step.target))
                    elif isinstance(target, dm.Lesson) and step.target == lesson_ref:
                        options.append(RouteReaderOption(kind='reader', course_ref=course_ref,
                            lesson_ref=lesson_ref, block_ref=None))
                    elif isinstance(target, dm.ContentBlock) and step.target in lesson.block_refs:
                        options.append(RouteReaderOption(kind='reader', course_ref=course_ref,
                            lesson_ref=lesson_ref, block_ref=step.target))
        return RouteTargetBinding(route_ref=route_ref, step_id=step.id, target_ref=step.target,
            navigation_options=options, unresolved_reason=None if options else 'NO_EXACT_COURSE_PARENT')

    def list(self, workspace_id: str, limit: int = 20, cursor: str | None = None) -> PageRoute:
        context = self.content._context(workspace_id, 'routes', '', limit)
        position = self.content._position(cursor, context, str)
        if position is not None and not isinstance(position, str):
            raise invalid()
        position_key = ('', 0)
        if position is not None:
            try:
                identifier, revision = position.rsplit(':', 1)
                position_key = (TypeAdapter(dm.Id).validate_python(identifier), TypeAdapter(dm.Revision).validate_python(int(revision)))
            except (ValueError, TypeError):
                raise invalid() from None
        with self._access(workspace_id) as content:
            values = route_values(content.connection, workspace_id)
            # Match SQL ORDER BY id,revision even when one valid ID prefixes another.
            candidates = [value for value in values if (value.id, value.revision) > position_key]
            items = candidates[:limit]
            refs = [reference(value) for value in items]
            courses = learning_scope(content.connection, workspace_id).course_refs if items else []
            targets = [self._navigation(content, ref, step, courses)
                for value, ref in zip(items, refs, strict=True) for step in value.steps]
            cursor = self.content._cursor(context, f'{items[-1].id}:{items[-1].revision:020}') if len(candidates) > limit else None
            return PageRoute(items=items, item_refs=refs, targets=targets, next_cursor=cursor)

    def _receipt(self, content: AssessmentContent, candidate: dm.Route, result: dict) -> dm.ContentRef:
        try:
            ref = dm.ContentRef.model_validate(result)
            if ref != reference(candidate) or content.exact(ref) != candidate:
                raise damaged()
            return ref
        except (ValueError, TypeError):
            raise damaged() from None

    def create(self, identity: SessionIdentity, route: dm.Route, key: str | None) -> dm.ContentRef:
        candidate = self._validate(route)
        with self._access(identity.workspace_id) as content:
            def operation():
                if candidate.revision != 1:
                    raise ApiError(422, 'SCHEMA_INVALID', '新路线必须从修订 1 开始。')
                return self.content.publish_in_transaction(content.connection, identity.workspace_id, [candidate], {})[0].model_dump(mode='json')
            result = execute_idempotent(content.connection, actor=identity.workspace_id, route='POST /routes', key=key,
                payload=candidate.model_dump(mode='json'), operation=operation)
            return self._receipt(content, candidate, result)

    def update(self, identity: SessionIdentity, id: str, route: dm.Route,
               expected_sha256: str, key: str | None) -> dm.ContentRef:
        candidate = self._validate(route)
        if id != candidate.id:
            raise invalid()
        with self._access(identity.workspace_id) as content:
            def operation():
                current = content.public.current(id).value
                if not isinstance(current, dm.Route):
                    raise invalid()
                if reference(current).sha256 != expected_sha256:
                    raise ApiError(412, 'REVISION_CONFLICT', '路线已有新修订，请读取并比较后保存。')
                if candidate.revision != current.revision + 1:
                    raise ApiError(422, 'SCHEMA_INVALID', '路线候选修订必须正好递增 1。')
                return self.content.publish_in_transaction(content.connection, identity.workspace_id, [candidate], {})[0].model_dump(mode='json')
            result = execute_idempotent(content.connection, actor=identity.workspace_id, route=f'PUT /routes/{id}', key=key,
                payload={'route': candidate.model_dump(mode='json'), 'if_match': expected_sha256}, operation=operation)
            return self._receipt(content, candidate, result)

    def complete(self, identity: SessionIdentity, id: str, step_id: str,
                 request: RouteCompletionRequest, key: str | None) -> LearningActionResponse:
        from .route_progress import record_route_completion, validate_route_completion_receipt
        with self._access(identity.workspace_id) as content:
            value = content.public.load('route', id, request.route_revision).value
            if not isinstance(value, dm.Route) or sum(step.id == step_id for step in value.steps) != 1:
                raise ApiError(422, 'ROUTE_STEP_INVALID', '步骤不属于该精确路线修订。')
            self._validate(value)
            for step in value.steps:
                content.exact(step.target)
            def operation():
                return record_route_completion(content.connection, identity.workspace_id, reference(value), step_id,
                    request.completed, request.expected_progress_revision).model_dump(mode='json')
            result = execute_idempotent(content.connection, actor=identity.workspace_id,
                route=f'POST /routes/{id}/steps/{step_id}/complete', key=key, payload=request.model_dump(mode='json'), operation=operation)
            return validate_route_completion_receipt(content.connection, identity.workspace_id, reference(value), step_id,
                request.completed, request.expected_progress_revision, LearningActionResponse.model_validate(result))
