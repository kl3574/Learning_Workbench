"""Codex-owned append-only facts and independently checked heads/memberships.

Reads never rebuild a projection or repair an incomplete history. Original ACKs
come from their exact event, not from a later session or preparation projection.
"""
import sqlite3
from datetime import datetime, timedelta
from typing import TypeVar

from pydantic import ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json
from ..application.codex_bootstrap_models import (
    BootstrapCommand, BootstrapOperation, BootstrapSnapshot, PreparedEvent, DecidedEvent, ConsumedEvent, FinishedEvent,
)
from ..application.codex_bootstrap_ports import CodexBootstrapRuntime
from ..application.errors import ApiError
from ..codex_bootstrap_dto import CodexSessionView, CodexBootstrapFeatures
from ..serialization import canonical_json, content_sha256
from .security import historical_session_belongs_to
from .database import utc_now

M = TypeVar('M', bound=dm.StrictModel)
EVENT_TYPES = (PreparedEvent, DecidedEvent, ConsumedEvent, FinishedEvent)
NO_FEATURES = CodexBootstrapFeatures.model_validate({'approvals': False, 'interrupt': False, 'artifacts': False})


def damaged() -> ApiError:
    return ApiError(409, 'CODEX_CONTROL_INTEGRITY', '本地控制记录不完整或绑定无法核验；未重新启动操作。')


def decode(model: type[M], raw: str) -> M:
    value = model.model_validate(strict_json(raw))
    if canonical_json(value) != raw:
        raise damaged()
    return value


def command_route(command: BootstrapCommand) -> str:
    return command.route + ('/' + command.target_id if command.target_id is not None else '')


def event_digest(preparation_id: str, sequence: int, previous: str, raw: str) -> str:
    return sha256_bytes(canonical_bytes({'preparation_id': preparation_id, 'sequence': sequence,
                                      'previous_sha256': previous, 'record_json': raw}))


class CodexBootstrapRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str, runtime: CodexBootstrapRuntime):
        self.connection, self.workspace_id, self.runtime = connection, workspace_id, runtime
        if not connection.in_transaction:
            raise ApiError(409, 'TRANSACTION_REQUIRED', '控制事实需要当前事务核验。')

    def rows(self, table: str) -> list[sqlite3.Row]:
        return self.connection.execute(f'SELECT * FROM {table} WHERE workspace_id=?', (self.workspace_id,)).fetchall()

    def checked(self) -> dict[str, BootstrapSnapshot]:
        try:
            return self._checked()
        except (ValidationError, ValueError, TypeError, KeyError, IndexError, UnicodeError, RecursionError):
            raise damaged() from None

    def _checked(self) -> dict[str, BootstrapSnapshot]:
        preparations = {row['id']: row for row in self.rows('codex_bootstrap_preparations')}
        memberships = {row['preparation_id']: row for row in self.rows('codex_bootstrap_memberships')}
        heads = {row['preparation_id']: row for row in self.rows('codex_bootstrap_heads')}
        events = {(row['preparation_id'], row['sequence']): row for row in self.rows('codex_bootstrap_events')}
        event_members = {(row['preparation_id'], row['sequence']): row for row in self.rows('codex_bootstrap_event_memberships')}
        commands = {(row['preparation_id'], row['sequence']): row for row in self.rows('codex_bootstrap_commands')}
        sessions = {row['id']: row for row in self.rows('codex_sessions')}
        session_members = {row['session_id']: row for row in self.rows('codex_bootstrap_session_memberships')}
        if (set(preparations) != set(memberships) or set(preparations) != set(heads)
                or set(events) != set(event_members) or set(commands) != {key for key in events if key[1] <= 3}
                or {key[0] for key in events} != set(preparations) or set(sessions) != set(session_members)):
            raise damaged()
        result: dict[str, BootstrapSnapshot] = {}
        expected_sessions = set()
        now = datetime.fromisoformat(utc_now())
        for identifier, row in preparations.items():
            operation = decode(BootstrapOperation, row['operation_json'])
            digest = content_sha256(operation)
            if (digest != row['operation_sha256'] or operation.preparation_id != identifier
                    or operation.workspace_id != self.workspace_id or operation.actor_session_id != row['actor_session_id']
                    or dict(memberships[identifier]) != {'preparation_id': identifier, 'workspace_id': self.workspace_id,
                        'actor_session_id': operation.actor_session_id, 'operation_sha256': digest}
                    or not historical_session_belongs_to(self.connection, self.workspace_id, operation.actor_session_id)):
                raise damaged()
            self.runtime.validate_frozen(operation.runtime)
            created, expires = datetime.fromisoformat(operation.created_at), datetime.fromisoformat(operation.expires_at)
            if expires - created != timedelta(minutes=10) or created > now:
                raise damaged()
            head = heads[identifier]
            count, previous, parsed = head['event_count'], digest, []
            if not 1 <= count <= 4 or {seq for prep, seq in events if prep == identifier} != set(range(1, count + 1)):
                raise damaged()
            for sequence in range(1, count + 1):
                event = events[(identifier, sequence)]
                record = decode(EVENT_TYPES[sequence - 1], event['record_json'])
                checksum = event_digest(identifier, sequence, previous, event['record_json'])
                if (event['previous_sha256'] != previous or event['record_sha256'] != checksum
                        or event_members[(identifier, sequence)]['record_sha256'] != checksum):
                    raise damaged()
                if isinstance(record, (PreparedEvent, DecidedEvent, ConsumedEvent)):
                    command = record.command
                    expected = {'workspace_id': self.workspace_id, 'actor_session_id': operation.actor_session_id,
                                'route': command_route(command), 'command_key': command.key, 'preparation_id': identifier,
                                'sequence': sequence, 'command_sha256': content_sha256(command), 'record_sha256': checksum}
                    if (dict(commands[(identifier, sequence)]) != expected or command.workspace_id != self.workspace_id
                            or command.actor_session_id != operation.actor_session_id
                            or command.route != ('prepare', 'decision', 'session')[sequence - 1]
                            or command.target_id != (identifier if sequence == 2 else None)):
                        raise damaged()
                parsed.append(record)
                previous = checksum
            if head['head_sha256'] != previous:
                raise damaged()
            prepared = parsed[0]
            assert isinstance(prepared, PreparedEvent)
            ack = prepared.ack
            if (ack.id != identifier or ack.actor_session_id != operation.actor_session_id or ack.revision != 1
                    or ack.scope != operation.runtime.scope or ack.operation_sha256 != digest
                    or ack.created_at != operation.created_at or ack.expires_at != operation.expires_at
                    or ack.validity != ('current' if operation.runtime.available else 'unavailable')
                    or strict_json(prepared.command.body_json) != {'sandbox_root_id': ack.scope.sandbox_root_id, 'allowed_actions': []}):
                raise damaged()
            decided = parsed[1] if count >= 2 else None
            consumed = parsed[2] if count >= 3 else None
            finished = parsed[3] if count >= 4 else None
            assert decided is None or isinstance(decided, DecidedEvent)
            assert consumed is None or isinstance(consumed, ConsumedEvent)
            assert finished is None or isinstance(finished, FinishedEvent)
            if decided is not None:
                decision = decided.ack
                if (decision.preparation_id != identifier or decision.operation_sha256 != digest
                        or decision.actor_session_id != operation.actor_session_id
                        or not created <= datetime.fromisoformat(decision.decided_at) < expires
                        or datetime.fromisoformat(decision.decided_at) > now
                        or strict_json(decided.command.body_json) != {'expected_revision': 1,
                             'operation_sha256': digest, 'decision': decision.decision}):
                    raise damaged()
            session = None
            if consumed is not None:
                if (decided is None or decided.ack.decision != 'approve_once'
                        or consumed.consent_id != decided.ack.consent_id
                        or not datetime.fromisoformat(decided.ack.decided_at) <= datetime.fromisoformat(consumed.started_at) < expires
                        or datetime.fromisoformat(consumed.started_at) > now
                        or strict_json(consumed.command.body_json) != {'sandbox_root_id': ack.scope.sandbox_root_id,
                                                               'consent_id': consumed.consent_id, 'allowed_actions': []}):
                    raise damaged()
                session_id = consumed.session_id
                expected_sessions.add(session_id)
                member = {'session_id': session_id, 'workspace_id': self.workspace_id,
                          'actor_session_id': operation.actor_session_id, 'preparation_id': identifier,
                          'operation_sha256': digest, 'owner_id': consumed.owner_id}
                if session_id not in session_members or dict(session_members[session_id]) != member:
                    raise damaged()
                if finished is not None:
                    if (finished.session_id != session_id
                            or not datetime.fromisoformat(consumed.started_at) <= datetime.fromisoformat(finished.finished_at) <= now):
                        raise damaged()
                    self.runtime.validate_outcome(operation.runtime, consumed.owner_id, finished.outcome)
                    expected_ack = {'id': session_id, 'revision': 2, 'status': 'ready',
                                    'adapter_version': ack.scope.adapter_version, 'capabilities': NO_FEATURES.model_dump()}
                    if (finished.ack.model_dump() if finished.ack else None) != (expected_ack if finished.outcome.status == 'ready' else None):
                        raise damaged()
                session = CodexSessionView(id=session_id, revision=2 if finished else 1,
                    status=finished.outcome.status if finished else 'initializing', active_turn_id=None,
                    adapter_version=ack.scope.adapter_version, capabilities=NO_FEATURES)
                expected_row = {'id': session_id, 'workspace_id': self.workspace_id, 'revision': session.revision,
                    'sandbox_root_id': ack.scope.sandbox_root_id,
                    'external_thread_id': finished.outcome.thread_id if finished else None,
                    'adapter_version': ack.scope.adapter_version, 'status': session.status,
                    'metadata_json': canonical_json({'version': 'codex-bootstrap-session-v1', 'preparation_id': identifier,
                        'actor_session_id': operation.actor_session_id, 'operation_sha256': digest, 'owner_id': consumed.owner_id,
                        'receipt_sha256': sha256_bytes(finished.outcome.receipt_json.encode())
                            if finished and finished.outcome.receipt_json is not None else None})}
                if dict(sessions[session_id]) != expected_row:
                    raise damaged()
            result[identifier] = BootstrapSnapshot(operation=operation, operation_sha256=digest, prepared=prepared,
                decided=decided, consumed=consumed, finished=finished, session=session)
        if expected_sessions != set(sessions):
            raise damaged()
        return result

    def insert(self, operation: BootstrapOperation, prepared: PreparedEvent) -> None:
        digest, identifier = content_sha256(operation), operation.preparation_id
        self.connection.execute('INSERT INTO codex_bootstrap_preparations VALUES(?,?,?,?,?)',
            (identifier, self.workspace_id, operation.actor_session_id, canonical_json(operation), digest))
        self.connection.execute('INSERT INTO codex_bootstrap_memberships VALUES(?,?,?,?)',
            (identifier, self.workspace_id, operation.actor_session_id, digest))
        self.connection.execute('INSERT INTO codex_bootstrap_heads VALUES(?,?,0,?)', (identifier, self.workspace_id, digest))
        self.append(identifier, prepared)

    def append(self, identifier: str, event: PreparedEvent | DecidedEvent | ConsumedEvent | FinishedEvent) -> None:
        head = self.connection.execute('SELECT * FROM codex_bootstrap_heads WHERE preparation_id=? AND workspace_id=?',
                                       (identifier, self.workspace_id)).fetchone()
        if head is None:
            raise damaged()
        sequence, previous = head['event_count'] + 1, head['head_sha256']
        if sequence > 4 or type(event) is not EVENT_TYPES[sequence - 1]:
            raise damaged()
        raw = canonical_json(event)
        checksum = event_digest(identifier, sequence, previous, raw)
        self.connection.execute('INSERT INTO codex_bootstrap_events VALUES(?,?,?,?,?,?)',
            (identifier, self.workspace_id, sequence, previous, raw, checksum))
        self.connection.execute('INSERT INTO codex_bootstrap_event_memberships VALUES(?,?,?,?)',
            (identifier, self.workspace_id, sequence, checksum))
        if isinstance(event, (PreparedEvent, DecidedEvent, ConsumedEvent)):
            command = event.command
            self.connection.execute('INSERT INTO codex_bootstrap_commands VALUES(?,?,?,?,?,?,?,?)',
                (self.workspace_id, command.actor_session_id, command_route(command), command.key, identifier,
                 sequence, content_sha256(command), checksum))
        self.connection.execute('UPDATE codex_bootstrap_heads SET event_count=?,head_sha256=? WHERE preparation_id=? AND workspace_id=?',
                                (sequence, checksum, identifier, self.workspace_id))

    def project_session(self, snapshot: BootstrapSnapshot, consumed: ConsumedEvent, finished: FinishedEvent | None) -> None:
        operation = snapshot.operation
        receipt = finished.outcome.receipt_json if finished else None
        metadata = canonical_json({'version': 'codex-bootstrap-session-v1', 'preparation_id': operation.preparation_id,
            'actor_session_id': operation.actor_session_id, 'operation_sha256': snapshot.operation_sha256,
            'owner_id': consumed.owner_id, 'receipt_sha256': sha256_bytes(receipt.encode()) if receipt is not None else None})
        if finished is None:
            self.connection.execute('INSERT INTO codex_bootstrap_session_memberships VALUES(?,?,?,?,?,?)',
                (consumed.session_id, self.workspace_id, operation.actor_session_id, operation.preparation_id,
                 snapshot.operation_sha256, consumed.owner_id))
            self.connection.execute('INSERT INTO codex_sessions VALUES(?,?,?,?,?,?,?,?)',
                (consumed.session_id, self.workspace_id, 1, operation.runtime.scope.sandbox_root_id, None,
                 operation.runtime.scope.adapter_version, 'initializing', metadata))
        else:
            changed = self.connection.execute('UPDATE codex_sessions SET revision=2,status=?,external_thread_id=?,metadata_json=? '
                'WHERE id=? AND workspace_id=? AND revision=1 AND status=?',
                (finished.outcome.status, finished.outcome.thread_id, metadata, consumed.session_id, self.workspace_id, 'initializing'))
            if changed.rowcount != 1:
                raise damaged()
