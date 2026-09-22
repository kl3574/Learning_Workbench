"""Tutor application boundary: current access, durable commands and read-only pages."""

import base64
import hashlib
import hmac
import secrets
import sqlite3
from typing import Protocol

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, strict_json

from ..infrastructure.database import Database
from ..infrastructure.security import SessionIdentity
from ..infrastructure.tutor_repository import TutorRepository
from ..import_dto import JobCancelRequest, JobSnapshot
from ..tutor_dto import (
    TutorContextBinding, TutorContextSummary, TutorMessagePage, TutorRunCancel, TutorRunControlView,
    TutorRunCreate, TutorRunView, TutorSSEEvent, TutorThreadCreate, TutorThreadPage, TutorThreadView,
)
from .errors import ApiError
from .tutor_models import PreparedTutorContext, TutorJobInput


class TutorContextPort(Protocol):
    def check_access(self, connection: sqlite3.Connection, identity: SessionIdentity) -> None: ...

    def check_scope(self, connection: sqlite3.Connection, identity: SessionIdentity,
                    scope: dm.ViewContext, binding: TutorContextBinding) -> None: ...

    def prepare(self, connection: sqlite3.Connection, identity: SessionIdentity,
                value: TutorJobInput) -> PreparedTutorContext: ...

    def verify(self, connection: sqlite3.Connection, identity: SessionIdentity, value: PreparedTutorContext) -> None: ...

    def read(self, connection: sqlite3.Connection, identity: SessionIdentity, snapshot_id: str) -> PreparedTutorContext: ...


class TutorService:
    def __init__(self, database: Database, context: TutorContextPort):
        self.database, self.context = database, context
        # Server-private signing material, created in memory; no credential read
        # or IO at construction. A restart invalidates a cursor explicitly.
        self._cursor_key = secrets.token_bytes(32)

    def _check_run(self, connection: sqlite3.Connection, identity: SessionIdentity,
                   repo: TutorRepository, identifier: str) -> None:
        source = repo.source_state(identifier)
        self.context.check_scope(connection, identity, source.input.request.request.context, source.input.request.binding)
        if source.context_id is not None:
            prepared = self.context.read(connection, identity, source.context_id)
            actual = TutorContextSummary(snapshot=prepared.snapshot, included=prepared.included,
                history_message_ids=prepared.history_message_ids, omissions=prepared.omissions, warnings=prepared.warnings)
            if actual != repo.view(identifier).context or prepared.run_id != identifier:
                raise ApiError(409, 'TUTOR_INTEGRITY_ERROR', '助教上下文与真实持久快照不一致。')

    def authorize(self, identity: SessionIdentity, thread_id: str | None = None, run_id: str | None = None) -> None:
        with self.database.transaction(immediate=False) as connection:
            self.context.check_access(connection, identity)
            repo = TutorRepository(connection, identity.workspace_id)
            if run_id is not None:
                self._check_run(connection, identity, repo, run_id)
                source = repo.source_state(run_id)
                repo.messages(source.input.request.request.thread_id)
            elif thread_id is not None:
                thread = repo.thread(thread_id)
                self.context.check_scope(connection, identity, thread.scope, thread.binding)
                repo.messages(thread_id)

    def create_thread(self, identity: SessionIdentity, body: TutorThreadCreate, key: str) -> TutorThreadView:
        with self.database.transaction() as connection:
            self.context.check_access(connection, identity)
            self.context.check_scope(connection, identity, body.scope, body.binding)
            repo = TutorRepository(connection, identity.workspace_id)
            previous = repo.replay('POST /threads', key, body, TutorThreadView)
            if previous is not None:
                return previous
            result = repo.create_thread(body)
            repo.record_command('POST /threads', key, body, result, result.id)
            return result

    @staticmethod
    def _root(scope: dm.ViewContext, binding: TutorContextBinding) -> tuple:
        return (scope.view_kind, scope.active_ref, scope.attempt_id,
                binding.practice.session_id if binding.practice is not None else None)

    def start(self, identity: SessionIdentity, body: TutorRunCreate, key: str) -> TutorRunView:
        if body.request.workspace_id != identity.workspace_id:
            raise ApiError(403, 'POLICY_DENIED', '请求不属于当前工作区。')
        with self.database.transaction() as connection:
            self.context.check_access(connection, identity)
            repo = TutorRepository(connection, identity.workspace_id)
            thread = repo.thread(body.request.thread_id)
            self.context.check_scope(connection, identity, body.request.context, body.binding)
            previous = repo.replay('POST /tutor/runs', key, body, TutorRunView)
            if previous is not None:
                return previous
            if body.request.web_search or body.request.consent_id is not None:
                raise ApiError(409, 'CAPABILITY_UNSUPPORTED', '首次任务只准备本地上下文，不接收旧许可或联网请求。')
            if self._root(thread.scope, thread.binding) != self._root(body.request.context, body.binding):
                raise ApiError(409, 'TUTOR_THREAD_SCOPE_MISMATCH', '本次精确上下文不属于此对话根。')
            result = repo.start(body, repo.history(thread.id))
            repo.record_command('POST /tutor/runs', key, body, result, thread.id, result.run.id)
            return result

    def read(self, identity: SessionIdentity, identifier: str) -> TutorRunView:
        with self.database.transaction(immediate=False) as connection:
            self.context.check_access(connection, identity)
            repo = TutorRepository(connection, identity.workspace_id)
            self._check_run(connection, identity, repo, identifier)
            source = repo.source_state(identifier)
            repo.messages(source.input.request.request.thread_id)
            return repo.view(identifier)

    def events(self, identity: SessionIdentity, identifier: str, after_seq: int) -> list[TutorSSEEvent]:
        with self.database.transaction(immediate=False) as connection:
            self.context.check_access(connection, identity)
            repo = TutorRepository(connection, identity.workspace_id)
            self._check_run(connection, identity, repo, identifier)
            source = repo.source_state(identifier)
            repo.messages(source.input.request.request.thread_id)
            view = repo.view(identifier)
            if type(after_seq) is not int or after_seq < 0:
                raise ApiError(400, 'CURSOR_INVALID', '事件游标必须是非负整数。')
            if after_seq > view.run.last_seq:
                raise ApiError(409, 'CURSOR_AHEAD', '事件游标超过已持久记录。')
            return repo.events_raw(identifier)[after_seq:after_seq + 200]

    def cancel(self, identity: SessionIdentity, identifier: str, body: TutorRunCancel, key: str) -> TutorRunControlView:
        # Pure control is allowed by workspace ownership even when subject output
        # is restricted. It never returns questions, scopes or output text.
        with self.database.transaction() as connection:
            repo = TutorRepository(connection, identity.workspace_id)
            source = repo.source_state(identifier)
            route = f'POST /runs/{identifier}/cancel'
            previous = repo.replay(route, key, body, TutorRunControlView)
            if previous is not None:
                return previous
            result = repo.cancel(identifier, body.expected_revision)
            repo.record_command(route, key, body, result, source.input.request.request.thread_id, identifier)
            return result

    def control(self, identity: SessionIdentity, identifier: str) -> TutorRunControlView:
        with self.database.transaction(immediate=False) as connection:
            return TutorRepository(connection, identity.workspace_id).control(identifier)

    def job(self, identity: SessionIdentity, identifier: str) -> JobSnapshot:
        with self.database.transaction(immediate=False) as connection:
            repo = TutorRepository(connection, identity.workspace_id)
            repo.source_state(identifier)
            return repo.jobs.snapshot(identifier)

    def cancel_job(self, identity: SessionIdentity, identifier: str, request: JobCancelRequest, key: str) -> JobSnapshot:
        with self.database.transaction() as connection:
            repo = TutorRepository(connection, identity.workspace_id)
            source = repo.source_state(identifier)
            route = f'POST /jobs/{identifier}/cancel'
            previous = repo.replay(route, key, request, JobSnapshot)
            if previous is not None:
                return previous
            repo.cancel(identifier, request.expected_revision)
            result = repo.jobs.snapshot(identifier)
            repo.record_command(route, key, request, result, source.input.request.request.thread_id, identifier)
            return result

    def _page(self, identity: SessionIdentity, kind: str, limit: int, cursor: str | None,
              current: list[str]) -> tuple[list[str], int, int]:
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ApiError(400, 'CURSOR_INVALID', '分页数量须为1至100的整数。')
        if cursor is None:
            return current, 0, len(current)
        try:
            if not isinstance(cursor, str) or not 1 <= len(cursor) <= 4096:
                raise ValueError('cursor')
            raw = base64.b64decode(cursor + '=' * (-len(cursor) % 4), altchars=b'-_', validate=True)
            if not hmac.compare_digest(raw[:32], hmac.new(self._cursor_key, raw[32:], hashlib.sha256).digest()):
                raise ValueError('signature')
            value = strict_json(raw[32:])
            if (set(value) != {'workspace', 'session', 'kind', 'limit', 'offset', 'high', 'high_id'}
                    or value['workspace'] != identity.workspace_id or value['session'] != identity.id
                    or value['kind'] != kind or value['limit'] != limit
                    or type(value['offset']) is not int or type(value['high']) is not int
                    or not 0 <= value['offset'] <= value['high'] <= len(current)
                    or value['high'] == 0 or current[value['high'] - 1] != value['high_id']):
                raise ValueError('context')
            return current, value['offset'], value['high']
        except (ValueError, TypeError, KeyError):
            raise ApiError(400, 'CURSOR_INVALID', '分页游标无效，请重新读取第一页。') from None

    def _next(self, identity: SessionIdentity, kind: str, limit: int, current: list[str], offset: int, high: int) -> str | None:
        if offset >= high:
            return None
        raw = canonical_bytes({'workspace': identity.workspace_id, 'session': identity.id, 'kind': kind,
            'limit': limit, 'offset': offset, 'high': high, 'high_id': current[high - 1]})
        return base64.urlsafe_b64encode(hmac.new(self._cursor_key, raw, hashlib.sha256).digest() + raw).decode().rstrip('=')

    def threads(self, identity: SessionIdentity, cursor: str | None = None, limit: int = 20) -> TutorThreadPage:
        with self.database.transaction(immediate=False) as connection:
            self.context.check_access(connection, identity)
            repo = TutorRepository(connection, identity.workspace_id)
            current, offset, high = self._page(identity, 'threads', limit, cursor, repo.thread_ids())
            items = [repo.thread(identifier) for identifier in current[offset:min(high, offset + limit)]]
            for item in items:
                self.context.check_scope(connection, identity, item.scope, item.binding)
            return TutorThreadPage(items=items, next_cursor=self._next(identity, 'threads', limit, current, offset + len(items), high))

    def messages(self, identity: SessionIdentity, identifier: str, cursor: str | None = None, limit: int = 20) -> TutorMessagePage:
        with self.database.transaction(immediate=False) as connection:
            self.context.check_access(connection, identity)
            repo = TutorRepository(connection, identity.workspace_id)
            thread = repo.thread(identifier)
            self.context.check_scope(connection, identity, thread.scope, thread.binding)
            messages = repo.messages(identifier)
            for run_id in dict.fromkeys(item.run_id for item in messages):
                self._check_run(connection, identity, repo, run_id)
            kind = f'messages:{identifier}'
            current, offset, high = self._page(identity, kind, limit, cursor, [item.id for item in messages])
            items = messages[offset:min(high, offset + limit)]
            return TutorMessagePage(thread=thread, items=items,
                next_cursor=self._next(identity, kind, limit, current, offset + len(items), high))
