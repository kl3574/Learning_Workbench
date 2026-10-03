"""Jobs-owned lifecycle for two Authoring consumers, with safe projections."""
from dataclasses import dataclass
import sqlite3
from uuid import uuid4

from pydantic import TypeAdapter
from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json
from ..application.errors import ApiError
from ..application.provider_models import DispatchLease
from ..import_dto import JobProgress, JobSnapshot
from .database import utc_now
from .security import expires_after

KINDS = {'authoring', 'authoring_numeric_check'}
TERMINAL = {'completed', 'failed', 'cancelled'}


def integrity() -> ApiError:
    return ApiError(409, 'AUTHORING_INTEGRITY_ERROR', '创作持久记录未通过完整性校验。')


def checked(raw: str, digest: str) -> dict:
    try:
        value = strict_json(raw)
        if not isinstance(value, dict) or canonical_bytes(value).decode() != raw or sha256_bytes(raw.encode()) != digest:
            raise integrity()
        return value
    except (ValueError, TypeError):
        raise integrity() from None


@dataclass(frozen=True)
class AuthoringLease:
    job_id: str
    workspace_id: str
    owner: str
    revision: int
    expires_at: str

    def dispatch(self) -> DispatchLease:
        return DispatchLease(owner_id=self.owner, job_revision=self.revision, expires_at=self.expires_at)


@dataclass(frozen=True, repr=False)
class AuthoringJobEvent:
    seq: int
    type: str
    payload_json: str
    occurred_at: str


class AuthoringJobRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.conn, self.workspace_id = connection, workspace_id

    def member_ids(self) -> set[str]:
        return {row[0] for row in self.conn.execute("SELECT id FROM jobs WHERE workspace_id=? AND kind IN ('authoring','authoring_numeric_check')",
                                                   (self.workspace_id,))}

    def input_version(self, identifier: str) -> str:
        """Route only an existing, hash/event-checked Job owned by this workspace."""
        row = self.load(identifier)
        value = checked(row['input_json'], row['input_sha256'])
        version = value.get('version')
        allowed = ({'authoring-job-v1', 'authoring-group-job-v1'} if row['kind'] == 'authoring'
                   else {'authoring-numeric-job-v1', 'authoring-group-numeric-job-v1'})
        if not isinstance(version, str) or version not in allowed:
            raise integrity()
        return version

    def load(self, identifier: str) -> sqlite3.Row:
        row = self.conn.execute('SELECT * FROM jobs WHERE id=? AND workspace_id=?',
                                (identifier, self.workspace_id)).fetchone()
        if row is None or row['kind'] not in KINDS:
            raise ApiError(404, 'JOB_MISSING', '任务不存在或不可访问。')
        try:
            checked(row['input_json'], row['input_sha256'])
            TypeAdapter(dm.Id).validate_python(row['id'])
            events = self.conn.execute('SELECT * FROM job_events WHERE job_id=? ORDER BY seq', (identifier,)).fetchall()
            if not events or len(events) != row['revision']:
                raise integrity()
            previous = None
            previous_time = ''
            cancel = False
            allowed = {'awaiting_approval': {'queued', 'cancelled'}, 'queued': {'running', 'cancelled'},
                       'running': {'running', 'awaiting_approval', *TERMINAL}}
            for seq, event in enumerate(events, 1):
                payload = strict_json(event['payload_json'])
                if (set(payload) != {'revision', 'status', 'cancel_requested', 'kind', 'input_sha256', 'result_sha256'}
                        or canonical_bytes(payload).decode() != event['payload_json']
                        or payload['revision'] != seq or type(payload['revision']) is not int or event['seq'] != seq
                        or payload['kind'] != row['kind'] or payload['input_sha256'] != row['input_sha256']
                        or type(payload['cancel_requested']) is not bool or cancel and not payload['cancel_requested']
                        or payload['status'] != event['type'] or previous in TERMINAL
                        or previous is not None and event['type'] not in allowed[previous]):
                    raise integrity()
                if seq == 1 and event['type'] != ('awaiting_approval' if row['kind'] == 'authoring' else 'queued'):
                    raise integrity()
                TypeAdapter(dm.UTC).validate_python(event['occurred_at'])
                if event['occurred_at'] < previous_time:
                    raise integrity()
                previous, previous_time, cancel = event['type'], event['occurred_at'], payload['cancel_requested']
                if (event['type'] in TERMINAL) != (payload['result_sha256'] is not None):
                    raise integrity()
            if (previous != row['status'] or cancel != bool(row['cancel_requested'])
                    or events[0]['occurred_at'] != row['created_at'] or previous_time != row['updated_at']):
                raise integrity()
            running = row['status'] == 'running'
            if running != (row['lease_owner'] is not None) or running != (row['lease_until'] is not None):
                raise integrity()
            if running:
                TypeAdapter(dm.Id).validate_python(row['lease_owner'])
                TypeAdapter(dm.UTC).validate_python(row['lease_until'])
            if row['status'] in TERMINAL:
                checked(row['result_json'], payload['result_sha256'])
            elif row['result_json'] is not None:
                raise integrity()
            if row['status'] in {'queued', 'awaiting_approval'} and cancel:
                raise integrity()
            return row
        except (ValueError, TypeError, KeyError):
            raise integrity() from None

    def _event(self, row: sqlite3.Row) -> None:
        payload = {'revision': row['revision'], 'status': row['status'], 'cancel_requested': bool(row['cancel_requested']),
            'kind': row['kind'], 'input_sha256': row['input_sha256'],
            'result_sha256': sha256_bytes(row['result_json'].encode()) if row['result_json'] is not None else None}
        self.conn.execute('INSERT INTO job_events VALUES(?,?,?,?,?)',
                          (row['id'], row['revision'], row['status'], canonical_bytes(payload).decode(), row['updated_at']))

    def create(self, identifier: str, kind: str, value: object) -> None:
        if kind not in KINDS:
            raise integrity()
        raw, now = canonical_bytes(value).decode(), utc_now()
        status = 'awaiting_approval' if kind == 'authoring' else 'queued'
        self.conn.execute('INSERT INTO jobs(id,workspace_id,kind,status,revision,input_sha256,input_json,created_at,updated_at) VALUES(?,?,?,?,1,?,?,?,?)',
                          (identifier, self.workspace_id, kind, status, sha256_bytes(raw.encode()), raw, now, now))
        self._event(self.conn.execute('SELECT * FROM jobs WHERE id=?', (identifier,)).fetchone())

    def snapshot(self, identifier: str, revision: int | None = None) -> JobSnapshot:
        row = self.load(identifier)
        revision = row['revision'] if revision is None else revision
        event = self.conn.execute('SELECT * FROM job_events WHERE job_id=? AND seq=?', (identifier, revision)).fetchone()
        if event is None:
            raise integrity()
        return JobSnapshot(id=identifier, workspace_id=self.workspace_id, kind=row['kind'], status=event['type'],
            revision=revision, created_at=row['created_at'], updated_at=event['occurred_at'],
            progress=JobProgress(completed=0, total=None, label=event['type']), result_refs=[], warnings=[], error=None)

    def event_prefix(self, identifier: str, revision: int) -> tuple[AuthoringJobEvent, ...]:
        """Return exact owned events after checking complete history in this transaction."""
        if not self.conn.in_transaction:
            raise ApiError(409, 'TRANSACTION_REQUIRED', '任务历史需要当前事务核验。')
        self.snapshot(identifier, revision)
        rows = self.conn.execute('SELECT * FROM job_events WHERE job_id=? AND seq<=? ORDER BY seq',
                                 (identifier, revision)).fetchall()
        return tuple(AuthoringJobEvent(row['seq'], row['type'], row['payload_json'], row['occurred_at']) for row in rows)

    def transition(self, row: sqlite3.Row, status: str, *, result: dict | None = None,
                   cancel: bool | None = None, owner: str | None = None, until: str | None = None) -> None:
        if row['status'] in TERMINAL:
            raise ApiError(409, 'JOB_TERMINAL', '任务已经结束。')
        raw = canonical_bytes(result).decode() if result is not None else None
        cancel = bool(row['cancel_requested']) if cancel is None else cancel
        changed = self.conn.execute('UPDATE jobs SET status=?,revision=revision+1,result_json=?,cancel_requested=?,lease_owner=?,lease_until=?,updated_at=? WHERE id=? AND workspace_id=? AND revision=?',
            (status, raw, int(cancel), owner, until, utc_now(), row['id'], self.workspace_id, row['revision']))
        if changed.rowcount != 1:
            raise ApiError(409, 'AUTHORING_LEASE_LOST', '任务的状态已改变。')
        self._event(self.conn.execute('SELECT * FROM jobs WHERE id=?', (row['id'],)).fetchone())
        self.load(row['id'])

    def claim(self, identifier: str, seconds: int = 30) -> AuthoringLease:
        row = self.load(identifier)
        if row['status'] != 'queued' and not (row['status'] == 'running' and row['lease_until'] <= utc_now()):
            raise ApiError(409, 'AUTHORING_LEASE_LOST', '任务已有有效持有者。')
        owner, until = 'lease_' + uuid4().hex, expires_after(seconds)
        self.transition(row, 'running', owner=owner, until=until)
        return AuthoringLease(identifier, self.workspace_id, owner, row['revision'] + 1, until)

    @staticmethod
    def owned(row: sqlite3.Row, lease: AuthoringLease, *, allow_cancel: bool = False) -> bool:
        return (row['id'] == lease.job_id and row['workspace_id'] == lease.workspace_id and row['status'] == 'running'
            and row['lease_owner'] == lease.owner and row['lease_until'] > utc_now()
            and (row['revision'] == lease.revision or allow_cancel and row['cancel_requested'])
            and (allow_cancel or not row['cancel_requested']))

    def renew(self, lease: AuthoringLease, seconds: int = 30) -> bool:
        row = self.load(lease.job_id)
        if not self.owned(row, lease):
            return False
        self.conn.execute('UPDATE jobs SET lease_until=? WHERE id=? AND workspace_id=? AND lease_owner=?',
                          (expires_after(seconds), lease.job_id, self.workspace_id, lease.owner))
        return True

    def cancel(self, identifier: str, expected: int) -> JobSnapshot:
        row = self.load(identifier)
        if row['status'] in TERMINAL:
            return self.snapshot(identifier)
        if row['revision'] != expected:
            raise ApiError(412, 'REVISION_MISMATCH', '任务已更新，请读取当前状态后取消。')
        if row['cancel_requested']:
            return self.snapshot(identifier)
        running = row['status'] == 'running'
        self.transition(row, 'running' if running else 'cancelled', cancel=True,
            result=None if running else {'cancelled_before_execution': True},
            owner=row['lease_owner'] if running else None, until=row['lease_until'] if running else None)
        return self.snapshot(identifier)

    def verify_cancel_ack(self, identifier: str, expected: int, ack: JobSnapshot,
                          basis_revision: int, recorded_at: str) -> None:
        if type(basis_revision) is not int or basis_revision < 1:
            raise integrity()
        basis = self.snapshot(identifier, basis_revision)
        if ack != self.snapshot(identifier, ack.revision) or ack.updated_at > recorded_at:
            raise integrity()
        if basis.status in TERMINAL:
            if ack != basis:
                raise integrity()
        else:
            if expected != basis_revision:
                raise integrity()
            event = self.conn.execute('SELECT payload_json FROM job_events WHERE job_id=? AND seq=?',
                                      (identifier, basis_revision)).fetchone()
            before = strict_json(event['payload_json'])
            if before['cancel_requested']:
                if ack != basis:
                    raise integrity()
            else:
                after = self.conn.execute('SELECT payload_json FROM job_events WHERE job_id=? AND seq=?',
                                          (identifier, basis_revision + 1)).fetchone()
                if (ack.revision != basis_revision + 1 or after is None
                        or not strict_json(after['payload_json'])['cancel_requested']
                        or ack.status != ('running' if basis.status == 'running' else 'cancelled')):
                    raise integrity()
        if self.conn.execute('SELECT 1 FROM job_events WHERE job_id=? AND seq>? AND occurred_at<?',
                              (identifier, ack.revision, recorded_at)).fetchone():
            raise integrity()
