"""Restore-owned immutable requests and records; never infer a producer from an ID."""
import sqlite3
from .security import historical_session_belongs_to
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json
from ..application.content_restore_models import RestoreRecord, checked, integrity
from ..application.errors import ApiError


class RestoreRepository:
    def __init__(self, conn: sqlite3.Connection, workspace: str):
        if not conn.in_transaction:
            raise integrity()
        self.conn, self.workspace = conn, workspace

    def load(self, identifier: str) -> RestoreRecord:
        row = self.conn.execute('SELECT * FROM content_restore_drafts WHERE id=? AND workspace_id=?', (identifier, self.workspace)).fetchone()
        if row is None:
            # The shared catalog is an independent immutable witness. A known
            # Restore candidate cannot become an ordinary unknown ID by losing
            # its owner record, including removal of the final or every row.
            if self.conn.execute("SELECT 1 FROM draft_candidate_identities WHERE draft_id=? AND workspace_id=? AND source_kind='authoring_restore'",
                    (identifier, self.workspace)).fetchone():
                raise integrity()
            raise ApiError(404, 'RESTORE_DRAFT_MISSING', '恢复稿不存在或不可访问。')
        try:
            value = checked(RestoreRecord, strict_json(row['record_json']))
            command = self.conn.execute('SELECT workspace_id,actor_id,command_key,draft_id,record_sha256 FROM content_restore_commands WHERE draft_id=?',
                (identifier,)).fetchone()
            actor_valid = historical_session_belongs_to(self.conn, self.workspace, value.actor_id)
            if (canonical_bytes(value).decode() != row['record_json'] or sha256_bytes(row['record_json'].encode()) != row['record_sha256']
                    or (value.candidate.draft_id, value.workspace_id, value.actor_id, value.command_key) != tuple(row[k] for k in ('id', 'workspace_id', 'actor_id', 'command_key'))
                    or not actor_valid or command is None or tuple(command) != (self.workspace, value.actor_id, value.command_key, identifier, row['record_sha256'])):
                raise integrity()
            return value
        except (ValueError, TypeError, KeyError):
            raise integrity() from None

    def replay(self, actor: str, key: str, request) -> RestoreRecord | None:
        row = self.conn.execute('SELECT draft_id FROM content_restore_commands WHERE workspace_id=? AND actor_id=? AND command_key=?', (self.workspace, actor, key)).fetchone()
        if row is None:
            if self.conn.execute('SELECT 1 FROM content_restore_drafts WHERE workspace_id=? AND actor_id=? AND command_key=?',
                    (self.workspace, actor, key)).fetchone():
                raise integrity()
            return None
        value = self.load(row[0])
        if canonical_bytes(value.payload.request) != canonical_bytes(request):
            raise ApiError(409, 'IDEMPOTENCY_CONFLICT', '原恢复命令键已用于不同完整命令。')
        return value

    def append(self, value: RestoreRecord) -> None:
        value = checked(RestoreRecord, value)
        if value.workspace_id != self.workspace:
            raise integrity()
        raw = canonical_bytes(value)
        self.conn.execute('INSERT INTO content_restore_drafts VALUES(?,?,?,?,?,?)',
            (value.candidate.draft_id, self.workspace, value.actor_id, value.command_key, raw.decode(), sha256_bytes(raw)))
        self.conn.execute('INSERT INTO content_restore_commands VALUES(?,?,?,?,?)',
            (self.workspace, value.actor_id, value.command_key, value.candidate.draft_id, sha256_bytes(raw)))
