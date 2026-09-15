"""Self-reported learner goals, wholly separate from verified learning evidence."""

from collections.abc import Iterator
from contextlib import contextmanager
import sqlite3

from pydantic import ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes

from ..infrastructure.content_repository import ContentRepository
from ..infrastructure.database import Database, utc_now
from ..infrastructure.idempotency import execute_idempotent
from ..infrastructure.profile_repository import PROFILE_ROUTE, ProfileRepository, invalid_profile
from ..infrastructure.security import SessionIdentity, guard_subject_access
from ..profile_dto import ProfileWrite
from .errors import ApiError


class ProfileService:
    def __init__(self, database: Database):
        self.database = database

    @contextmanager
    def _access(self, workspace_id: str) -> Iterator[ProfileRepository]:
        try:
            with self.database.transaction() as connection:
                guard_subject_access(connection, workspace_id)
                ContentRepository(connection, workspace_id).require_workspace()
                yield ProfileRepository(connection, workspace_id)
        except sqlite3.Error:
            raise ApiError(503, 'PROFILE_STORAGE_UNAVAILABLE', '学习目标与基础暂时无法保存或读取。', True) from None

    def read(self, workspace_id: str) -> dm.LearnerProfile:
        with self._access(workspace_id) as repository:
            return repository.read()

    def save(self, identity: SessionIdentity, request: ProfileWrite, key: str | None) -> dm.LearnerProfile:
        try:
            request = ProfileWrite.model_validate(request.model_dump(mode='json'))
        except (ValidationError, ValueError, TypeError):
            raise ApiError(422, 'SCHEMA_INVALID', '学习目标与基础请求不符合规范。') from None
        with self._access(identity.workspace_id) as repository:
            previous = repository.read()  # Validate actual current storage before any cached return.
            applied = False
            request_hash = sha256_bytes(canonical_bytes(request))

            def operation():
                nonlocal applied
                from .content_learning_access import learning_scope
                if request.expected_revision != previous.revision:
                    raise ApiError(412, 'REVISION_CONFLICT', '学习目标与基础已更新，请读取最新版本后比较。')
                scope = learning_scope(repository.connection, identity.workspace_id)
                available = {item.ref.id for item in scope.concepts}
                requested = set(request.goal_concept_ids) | {item.concept_id for item in request.self_assessments}
                if not requested <= available:
                    raise ApiError(422, 'PROFILE_CONCEPT_UNAVAILABLE', '自报或目标概念不在本工作区可访问的概念中。')
                now = utc_now()
                old = {item.concept_id: item for item in previous.self_assessments}
                assessments = [old[item.concept_id] if item.concept_id in old and old[item.concept_id].level == item.level
                    else dm.SelfAssessment(concept_id=item.concept_id, level=item.level, updated_at=now)
                    for item in request.self_assessments]
                updated = dm.LearnerProfile(workspace_id=identity.workspace_id, revision=previous.revision + 1,
                    goals=request.goals, goal_concept_ids=request.goal_concept_ids, weekly_minutes=request.weekly_minutes,
                    language=request.language, preferred_difficulty=request.preferred_difficulty, self_assessments=assessments)
                repository.save(request, updated, now, request_hash)
                applied = True
                return updated.model_dump(mode='json')

            try:
                result = execute_idempotent(repository.connection, actor=identity.workspace_id, route=PROFILE_ROUTE,
                    key=key, payload=request.model_dump(mode='json'), operation=operation)
            except (ValueError, TypeError):
                raise invalid_profile() from None
            assert key is not None  # execute_idempotent has rejected missing or malformed keys.
            return repository.checked_receipt(key=key, request_hash=request_hash, expected_revision=request.expected_revision,
                                               result=result, applied=applied)
