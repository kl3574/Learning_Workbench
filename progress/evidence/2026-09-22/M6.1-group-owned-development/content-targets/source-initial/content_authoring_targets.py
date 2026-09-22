"""Content-owned exact target metadata reads in the caller's SQLite transaction."""

from collections.abc import Iterator
from contextlib import contextmanager
import sqlite3

from pydantic import ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes

from ..authoring_group_dto import AuthoringTargetMaterial
from ..infrastructure.content_repository import ContentRepository, damaged, reference
from ..infrastructure.database import Database
from ..infrastructure.security import SessionIdentity
from .errors import ApiError
from .policy import Policy


def invalid() -> ApiError:
    return ApiError(422, 'AUTHORING_TARGET_INVALID', '请选择不重复的小节或概念完整修订。')


def _refs(refs: list[dm.ContentRef]) -> list[dm.ContentRef]:
    if not isinstance(refs, list) or len(refs) > 33:
        raise invalid()
    checked: list[dm.ContentRef] = []
    seen: set[tuple[str, str, int]] = set()
    for supplied in refs:
        try:
            ref = dm.ContentRef.model_validate(supplied.model_dump(mode='python'))
        except (AttributeError, TypeError, ValueError):
            raise invalid() from None
        key = (ref.entity, ref.id, ref.revision)
        if ref.entity not in {'lesson', 'concept'} or key in seen:
            raise invalid()
        seen.add(key)
        checked.append(ref)
    return checked


class ContentAuthoringTargetSource:
    def __init__(self, database: Database):
        # Construction matches the other Content ports. All reads below use
        # the caller connection, including its uncommitted changes and Policy.
        self.database = database

    @staticmethod
    @contextmanager
    def _access(conn: sqlite3.Connection, identity: SessionIdentity) -> Iterator[ContentRepository]:
        if not isinstance(conn, sqlite3.Connection) or not conn.in_transaction:
            raise ApiError(409, 'TRANSACTION_REQUIRED', '目标元数据读取需要有效事务。')
        try:
            Policy(conn, identity.workspace_id).check('subject_read')
            repository = ContentRepository(conn, identity.workspace_id)
            repository.require_workspace()
            yield repository
        except sqlite3.Error:
            raise ApiError(503, 'CONTENT_STORAGE_UNAVAILABLE', '内容存储暂不可用。', retryable=True) from None
        except (ValidationError, UnicodeError):
            raise damaged() from None

    @staticmethod
    def _resolve(repository: ContentRepository, refs: list[dm.ContentRef]) -> list[AuthoringTargetMaterial]:
        result: list[AuthoringTargetMaterial] = []
        for ref in refs:
            value = repository.load(ref.entity, ref.id, ref.revision).value
            if not isinstance(value, (dm.Lesson, dm.Concept)) or reference(value) != ref:
                raise damaged()
            result.append(AuthoringTargetMaterial(ref=ref, metadata=value))
        return result

    def resolve_targets(self, conn: sqlite3.Connection, identity: SessionIdentity,
                        refs: list[dm.ContentRef]) -> list[AuthoringTargetMaterial]:
        with self._access(conn, identity) as repository:
            return self._resolve(repository, _refs(refs))

    def revalidate_targets(self, conn: sqlite3.Connection, identity: SessionIdentity,
                           expected: list[AuthoringTargetMaterial]) -> None:
        with self._access(conn, identity) as repository:
            if not isinstance(expected, list) or len(expected) > 33:
                raise invalid()
            try:
                # model_copy/construct and mutable nested metadata cannot bypass
                # the frozen ref/type/hash binding when a stored context is read.
                checked = [AuthoringTargetMaterial.model_validate(item.model_dump(mode='python')) for item in expected]
            except (AttributeError, TypeError, ValueError):
                raise damaged() from None
            refs = _refs([dm.ContentRef.model_validate(item.ref.model_dump(mode='python')) for item in checked])
            current = self._resolve(repository, refs)
            if canonical_bytes(current) != canonical_bytes(checked):
                raise damaged()
