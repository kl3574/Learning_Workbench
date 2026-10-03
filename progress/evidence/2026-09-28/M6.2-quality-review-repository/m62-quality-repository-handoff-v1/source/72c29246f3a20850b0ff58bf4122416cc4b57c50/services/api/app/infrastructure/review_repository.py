"""Quality-owned persistence in the caller transaction; no authority from JSON.

Jobs mutations remain with Jobs. Each write's savepoint protects this method's
Quality changes; the caller must cover earlier Jobs writes in its outer operation.
"""
from contextlib import contextmanager
import sqlite3
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel, TypeAdapter
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json
from ..application.errors import ApiError
from ..application.review_history_models import (
    ReviewBinding, ReviewCommand, ReviewCreateCommand, ReviewCancelCommand, ReviewCancelAck, instant,
)
from ..application.review_models import ReviewJobInput
from ..import_dto import JobSnapshot
from .draft_candidate_repository import DraftCandidateRepository
from .review_job_repository import ReviewJobRepository

M = TypeVar('M', bound=BaseModel)
COMMAND = TypeAdapter(ReviewCommand)


def integrity() -> ApiError:
    return ApiError(409, 'REVIEW_INTEGRITY_ERROR', '审核持久历史未通过完整性校验。')


def checked(raw: str, digest: str) -> dict:
    try:
        value = strict_json(raw)
        if not isinstance(value, dict) or canonical_bytes(value).decode() != raw or sha256_bytes(raw.encode()) != digest:
            raise integrity()
        return value
    except (ValueError, TypeError, UnicodeError):
        raise integrity() from None


def validated(model: type[M], value: object) -> M:
    try:
        return model.model_validate(value.model_dump(mode='python') if isinstance(value, BaseModel) else value)
    except (ValueError, TypeError, AttributeError):
        raise integrity() from None


class ReviewRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.conn, self.workspace_id = connection, workspace_id
        self.jobs = ReviewJobRepository(connection, workspace_id)

    def _transaction(self) -> None:
        if not self.conn.in_transaction:
            raise ApiError(409, 'TRANSACTION_REQUIRED', '审核持久操作需要当前事务。')

    @contextmanager
    def _write(self):
        self._transaction()
        point = 'quality_write_' + uuid4().hex
        self.conn.execute(f'SAVEPOINT {point}')
        try:
            yield
        except BaseException as error:
            self.conn.execute(f'ROLLBACK TO {point}')
            self.conn.execute(f'RELEASE {point}')
            if isinstance(error, sqlite3.Error):
                raise integrity() from None
            raise
        self.conn.execute(f'RELEASE {point}')

    def _binding(self, identifier: str) -> ReviewBinding:
        self._transaction()
        row = self.conn.execute('SELECT * FROM review_jobs WHERE review_id=? AND workspace_id=?',
                                (identifier, self.workspace_id)).fetchone()
        if row is None:
            if self.conn.execute('SELECT 1 FROM reviews WHERE id=? AND workspace_id=?',
                                 (identifier, self.workspace_id)).fetchone():
                raise ApiError(409, 'REVIEW_LEGACY_HISTORY_UNVERIFIABLE', '原审核记录保留，但缺少可认证的审核历史。')
            raise ApiError(404, 'REVIEW_MISSING', '审核不存在或不可访问。')
        value = validated(ReviewJobInput, checked(row['input_json'], row['input_sha256']))
        job = self.jobs.load(identifier)
        resolved = DraftCandidateRepository(self.conn).lookup(self.workspace_id, value.candidate.draft_id,
                                                              value.candidate.draft_revision)
        if (value.review_id != identifier or value.workspace_id != self.workspace_id
                or row['job_kind'] != 'draft_review' or row['owner'] != resolved.owner
                or row['source_kind'] != resolved.source_kind or value.source_kind != resolved.source_kind
                or value.candidate != resolved.candidate or row['creator_actor_id'] != value.creator_session_id
                or row['created_at'] != value.created_at or canonical_bytes(value).decode() != row['input_json']
                or row['input_json'] != job['input_json'] or row['input_sha256'] != job['input_sha256']
                or any(row[key] != getattr(value.candidate, key) for key in
                       ('draft_id', 'draft_revision', 'entity', 'candidate_sha256'))
                or instant(value.created_at) > instant(job['created_at'])):
            raise integrity()
        return ReviewBinding(input=value, owner=resolved.owner,
                             job=validated(ReviewCancelAck, self.jobs.snapshot(identifier)))

    def binding(self, identifier: str) -> ReviewBinding:
        """Internal binding read, including queued/cancelled jobs with no receipt."""
        value = self._binding(identifier)
        self._commands(value)
        return value

    def _command(self, row: sqlite3.Row) -> ReviewCommand:
        try:
            value = COMMAND.validate_python({key: row[key] for key in
                ('workspace_id', 'actor_id', 'route', 'command_key', 'review_id', 'command_kind',
                 'basis_revision', 'resulting_revision', 'recorded_at')} | {
                'request': checked(row['request_json'], row['request_sha256']),
                'ack': checked(row['ack_json'], row['ack_sha256'])})
            if (canonical_bytes(value.request).decode() != row['request_json']
                    or canonical_bytes(value.ack).decode() != row['ack_json']):
                raise integrity()
            return value
        except (ValueError, TypeError, KeyError):
            raise integrity() from None

    def _verify_command(self, command: ReviewCommand, binding: ReviewBinding) -> None:
        value = binding.input
        if (command.workspace_id != self.workspace_id or command.review_id != value.review_id
                or instant(command.recorded_at) < instant(value.created_at)):
            raise integrity()
        if isinstance(command, ReviewCreateCommand):
            original = self.jobs.snapshot(value.review_id, 1)
            if (command.actor_id != value.creator_session_id or command.request != value.request
                    or command.route != f'POST /drafts/{value.candidate.draft_id}/review'
                    or original.status != command.ack.status
                    or instant(command.recorded_at) < instant(original.updated_at)
                    or any(instant(event.occurred_at) < instant(command.recorded_at)
                           for event in self.jobs.event_prefix(value.review_id, binding.job.revision)[1:])):
                raise integrity()
        elif isinstance(command, ReviewCancelCommand):
            self.jobs.verify_cancel_ack(value.review_id, command.request.expected_revision,
                validated(JobSnapshot, command.ack), command.basis_revision, command.recorded_at)
        else:
            raise integrity()

    def _commands(self, binding: ReviewBinding) -> list[ReviewCommand]:
        rows = self.conn.execute('SELECT * FROM review_commands WHERE review_id=? ORDER BY rowid',
                                 (binding.input.review_id,)).fetchall()
        commands = [self._command(row) for row in rows]
        for command in commands:
            self._verify_command(command, binding)
        if sum(isinstance(command, ReviewCreateCommand) for command in commands) != 1:
            raise integrity()
        return commands

    def _insert_command(self, command: ReviewCommand) -> None:
        request, ack = canonical_bytes(command.request).decode(), canonical_bytes(command.ack).decode()
        self.conn.execute('INSERT INTO review_commands(workspace_id,actor_id,route,command_key,command_kind,'
            'review_id,request_json,request_sha256,ack_json,ack_sha256,basis_revision,resulting_revision,recorded_at) '
            'VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)', (self.workspace_id, command.actor_id, command.route,
            command.command_key, command.command_kind, command.review_id, request, sha256_bytes(request.encode()),
            ack, sha256_bytes(ack.encode()), command.basis_revision, command.resulting_revision, command.recorded_at))

    def bind(self, value: ReviewJobInput, command: ReviewCreateCommand) -> None:
        with self._write():
            value, command = validated(ReviewJobInput, value), validated(ReviewCreateCommand, command)
            row = self.jobs.load(value.review_id)
            if (value.workspace_id != self.workspace_id or row['revision'] != 1 or row['status'] != 'queued'
                    or canonical_bytes(value).decode() != row['input_json']
                    or self.conn.execute('SELECT 1 FROM reviews WHERE id=?', (value.review_id,)).fetchone()):
                raise integrity()
            candidate = value.candidate
            owner = 'import' if value.source_kind == 'import' else 'authoring'
            raw = canonical_bytes(value).decode()
            self.conn.execute('INSERT INTO review_jobs(review_id,workspace_id,owner,source_kind,draft_id,'
                'draft_revision,entity,candidate_sha256,creator_actor_id,input_json,input_sha256,created_at) '
                'VALUES(?,?,?,?,?,?,?,?,?,?,?,?)', (value.review_id, self.workspace_id, owner, value.source_kind,
                candidate.draft_id, candidate.draft_revision, candidate.entity, candidate.candidate_sha256,
                value.creator_session_id, raw, sha256_bytes(raw.encode()), value.created_at))
            binding = self._binding(value.review_id)
            self._verify_command(command, binding)
            self._insert_command(command)
            self.binding(value.review_id)

    def record_cancel(self, command: ReviewCancelCommand) -> None:
        with self._write():
            command = validated(ReviewCancelCommand, command)
            binding = self.binding(command.review_id)
            self._verify_command(command, binding)
            self._insert_command(command)
            self.binding(command.review_id)

    def replay(self, actor_id: str, route: str, key: str, body: BaseModel) -> ReviewCommand | None:
        self._transaction()
        row = self.conn.execute('SELECT * FROM review_commands WHERE workspace_id=? AND actor_id=? '
                                'AND route=? AND command_key=?', (self.workspace_id, actor_id, route, key)).fetchone()
        if row is None:
            return None
        self.binding(row['review_id'])
        command = self._command(row)
        try:
            body = type(command.request).model_validate(body.model_dump(mode='python'))
        except (ValueError, TypeError, AttributeError):
            raise integrity() from None
        if canonical_bytes(body) != canonical_bytes(command.request):
            raise ApiError(409, 'IDEMPOTENCY_CONFLICT', '原命令键已用于不同的完整命令。')
        return command
