"""Jobs-owned lifecycle operations for Tutor; no conversation or Provider SQL."""

from dataclasses import dataclass
import sqlite3
from typing import Literal
from uuid import uuid4

from pydantic import TypeAdapter

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json

from ..application.errors import ApiError
from ..application.provider_models import DispatchLease
from ..import_dto import JobProgress, JobSnapshot
from .database import utc_now
from .security import expires_after

TERMINAL = {'completed', 'failed', 'cancelled'}
JobStatus = Literal['queued', 'running', 'awaiting_approval', 'completed', 'failed', 'cancelled']


def integrity() -> ApiError:
    return ApiError(409, 'TUTOR_INTEGRITY_ERROR', '助教任务的持久记录未通过完整性校验。')


@dataclass(frozen=True)
class TutorLease:
    job_id: str
    workspace_id: str
    owner: str
    revision: int
    expires_at: str

    def dispatch(self) -> DispatchLease:
        return DispatchLease(owner_id=self.owner, job_revision=self.revision, expires_at=self.expires_at)


class TutorJobRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection, self.workspace_id = connection, workspace_id

    def load(self, identifier: str) -> sqlite3.Row:
        row = self.connection.execute("SELECT * FROM jobs WHERE id=? AND workspace_id=? AND kind='tutor'",
                                      (identifier, self.workspace_id)).fetchone()
        if row is None:
            raise ApiError(404, 'JOB_MISSING', '任务不存在或不可访问。')
        try:
            if canonical_bytes(strict_json(row['input_json'])).decode() != row['input_json'] or sha256_bytes(row['input_json'].encode()) != row['input_sha256']:
                raise integrity()
            TypeAdapter(dm.Id).validate_python(row['id'])
            TypeAdapter(dm.Revision).validate_python(row['revision'])
            for field in ('created_at', 'updated_at'):
                TypeAdapter(dm.UTC).validate_python(row[field])
            events = self.connection.execute('SELECT * FROM job_events WHERE job_id=? ORDER BY seq', (identifier,)).fetchall()
            if len(events) != row['revision'] or not events:
                raise integrity()
            previous = None
            for seq, event in enumerate(events, 1):
                payload = strict_json(event['payload_json'])
                if (event['seq'] != seq or set(payload) != {'revision', 'status', 'cancel_requested'}
                        or type(payload['cancel_requested']) is not bool or payload['revision'] != seq
                        or payload['status'] != event['type'] or canonical_bytes(payload).decode() != event['payload_json']
                        or previous in TERMINAL or seq == 1 and event['type'] != 'queued'):
                    raise integrity()
                allowed = {'queued': {'running', 'cancelled'}, 'running': {'running', 'awaiting_approval', *TERMINAL},
                           'awaiting_approval': {'queued', 'cancelled'}}
                if previous is not None and event['type'] not in allowed[previous]:
                    raise integrity()
                TypeAdapter(dm.UTC).validate_python(event['occurred_at'])
                previous = event['type']
            if (previous != row['status'] or payload['cancel_requested'] != bool(row['cancel_requested'])
                    or events[0]['occurred_at'] != row['created_at'] or events[-1]['occurred_at'] != row['updated_at']):
                raise integrity()
            running = row['status'] == 'running'
            if running != (row['lease_owner'] is not None) or running != (row['lease_until'] is not None):
                raise integrity()
            if running:
                TypeAdapter(dm.Id).validate_python(row['lease_owner'])
                TypeAdapter(dm.UTC).validate_python(row['lease_until'])
            if row['status'] not in TERMINAL and row['result_json'] is not None:
                raise integrity()
            if row['status'] in TERMINAL and row['result_json'] is None:
                raise integrity()
            if row['status'] in {'queued', 'awaiting_approval'} and row['cancel_requested']:
                raise integrity()
            return row
        except (ValueError, TypeError, KeyError):
            raise integrity() from None

    def _event(self, identifier: str, status: str, revision: int, cancel: bool, now: str) -> None:
        value = {'revision': revision, 'status': status, 'cancel_requested': cancel}
        self.connection.execute('INSERT INTO job_events VALUES(?,?,?,?,?)',
                                (identifier, revision, status, canonical_bytes(value).decode(), now))

    def snapshot(self, identifier: str, revision: int | None = None) -> JobSnapshot:
        """Safe control projection from the checked Jobs row and exact event."""
        row = self.load(identifier)
        revision = row['revision'] if revision is None else revision
        event = self.connection.execute('SELECT * FROM job_events WHERE job_id=? AND seq=?',
                                        (identifier, revision)).fetchone()
        if event is None:
            raise integrity()
        labels = {'queued': '排队中', 'running': '运行中', 'awaiting_approval': '等待批准',
                  'completed': '已完成', 'failed': '已失败', 'cancelled': '已取消'}
        return JobSnapshot(id=identifier, workspace_id=self.workspace_id, kind='tutor',
            status=event['type'], revision=revision, created_at=row['created_at'], updated_at=event['occurred_at'],
            progress=JobProgress(completed=0, total=None, label=labels[event['type']]),
            result_refs=[], warnings=[], error=None)

    def verify_cancel_ack(self, identifier: str, expected: int, ack: JobSnapshot, recorded_at: str) -> None:
        """Bind an original cancellation ACK to its real transition or no-op."""
        try:
            TypeAdapter(dm.UTC).validate_python(recorded_at)
        except (ValueError, TypeError):
            raise integrity() from None
        if ack != self.snapshot(identifier, ack.revision) or ack.updated_at > recorded_at:
            raise integrity()
        # The command and its transition were committed in one writer transaction.
        # A later event cannot be substituted merely because its bytes are valid.
        later = self.connection.execute('SELECT 1 FROM job_events WHERE job_id=? AND seq>? AND occurred_at<?',
                                        (identifier, ack.revision, recorded_at)).fetchone()
        if later is not None:
            raise integrity()
        event = self.connection.execute('SELECT payload_json FROM job_events WHERE job_id=? AND seq=?',
                                        (identifier, ack.revision)).fetchone()
        state = strict_json(event['payload_json'])
        if ack.status in TERMINAL:
            # A terminal task is an explicit no-op, even for a stale expected revision.
            return
        elif ack.status != 'running' or not state['cancel_requested']:
            raise integrity()
        if ack.revision == expected and state['cancel_requested']:
            return  # A second explicit cancellation of an already requested stop.
        if ack.revision != expected + 1 or not state['cancel_requested']:
            raise integrity()
        previous = self.connection.execute('SELECT payload_json FROM job_events WHERE job_id=? AND seq=?',
                                           (identifier, expected)).fetchone()
        if previous is None:
            raise integrity()
        before = strict_json(previous['payload_json'])
        if before['cancel_requested'] or before['status'] not in {'queued', 'running', 'awaiting_approval'}:
            raise integrity()
        if ack.status != ('running' if before['status'] == 'running' else 'cancelled'):
            raise integrity()

    def enqueue(self, identifier: str, raw: str) -> None:
        now = utc_now()
        self.connection.execute("INSERT INTO jobs(id,workspace_id,kind,status,revision,input_sha256,input_json,created_at,updated_at) VALUES(?,?,'tutor','queued',1,?,?,?,?)",
                                (identifier, self.workspace_id, sha256_bytes(raw.encode()), raw, now, now))
        self._event(identifier, 'queued', 1, False, now)

    def available(self) -> str | None:
        values = self.candidates(limit=1)
        return values[0][1] if values else None

    def candidates(self, after: tuple[str, str] | None = None, *, limit: int = 32) -> list[tuple[str, str]]:
        """One bounded cyclic pass; reading candidates does not repair history."""
        if type(limit) is not int or not 1 <= limit <= 32:
            raise ValueError('Tutor candidate batch must contain at most 32 jobs')
        query = "SELECT created_at,id FROM jobs WHERE workspace_id=? AND kind='tutor' AND (status='queued' OR (status='running' AND lease_until<=?))"
        args = (self.workspace_id, utc_now())
        if after is None:
            rows = self.connection.execute(query + ' ORDER BY created_at,id LIMIT ?', (*args, limit)).fetchall()
        else:
            rows = self.connection.execute(query + ' AND (created_at,id)>(?,?) ORDER BY created_at,id LIMIT ?',
                (*args, *after, limit)).fetchall()
            if len(rows) < limit:
                rows += self.connection.execute(query + ' AND (created_at,id)<=(?,?) ORDER BY created_at,id LIMIT ?',
                    (*args, *after, limit - len(rows))).fetchall()
        return [(str(row['created_at']), str(row['id'])) for row in rows]

    def claim(self, row: sqlite3.Row, seconds: int) -> TutorLease:
        now, owner, until = utc_now(), f'lease_{uuid4().hex}', expires_after(seconds)
        if row['status'] != 'queued' and not (row['status'] == 'running' and row['lease_until'] <= now):
            raise ApiError(409, 'TUTOR_LEASE_LOST', '任务已有有效持有者。')
        changed = self.connection.execute("UPDATE jobs SET status='running',revision=revision+1,lease_owner=?,lease_until=?,updated_at=?,retry_count=retry_count+? WHERE id=? AND workspace_id=? AND revision=?",
            (owner, until, now, int(row['status'] == 'running'), row['id'], self.workspace_id, row['revision']))
        if changed.rowcount != 1:
            raise ApiError(409, 'TUTOR_LEASE_LOST', '任务已由另一工作进程领取。')
        self._event(row['id'], 'running', row['revision'] + 1, bool(row['cancel_requested']), now)
        return TutorLease(row['id'], self.workspace_id, owner, row['revision'] + 1, until)

    @staticmethod
    def owned(row: sqlite3.Row, lease: TutorLease, *, allow_cancel: bool = False) -> bool:
        return (row['id'] == lease.job_id and row['workspace_id'] == lease.workspace_id and row['status'] == 'running'
                and row['lease_owner'] == lease.owner and row['lease_until'] > utc_now()
                and (row['revision'] == lease.revision or allow_cancel and row['cancel_requested'])
                and (allow_cancel or not row['cancel_requested']))

    def transition(self, row: sqlite3.Row, status: JobStatus, *, result: dict | None = None,
                   cancel: bool | None = None, retain_lease: bool = False) -> None:
        if row['status'] in TERMINAL:
            raise ApiError(409, 'JOB_TERMINAL', '任务已经结束。')
        now = utc_now()
        cancel = bool(row['cancel_requested']) if cancel is None else cancel
        changed = self.connection.execute('UPDATE jobs SET status=?,revision=revision+1,result_json=?,cancel_requested=?,lease_owner=?,lease_until=?,updated_at=? WHERE id=? AND workspace_id=? AND revision=?',
            (status, canonical_bytes(result).decode() if result is not None else None, int(cancel),
             row['lease_owner'] if retain_lease else None, row['lease_until'] if retain_lease else None,
             now, row['id'], self.workspace_id, row['revision']))
        if changed.rowcount != 1:
            raise ApiError(409, 'TUTOR_LEASE_LOST', '任务的状态已改变。')
        self._event(row['id'], status, row['revision'] + 1, cancel, now)

    def renew(self, lease: TutorLease, seconds: int) -> bool:
        row = self.load(lease.job_id)
        if not self.owned(row, lease, allow_cancel=True):
            return False
        self.connection.execute('UPDATE jobs SET lease_until=? WHERE id=? AND workspace_id=? AND lease_owner=?',
                                (expires_after(seconds), lease.job_id, lease.workspace_id, lease.owner))
        return True
