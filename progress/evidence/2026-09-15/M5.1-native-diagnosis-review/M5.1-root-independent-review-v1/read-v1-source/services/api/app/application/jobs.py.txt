"""Jobs-owned exclusion facts for atomic independent-assessment start."""

from dataclasses import dataclass
from datetime import datetime
import sqlite3


@dataclass(frozen=True)
class SubjectWork:
    id: str
    kind: str
    status: str


def active_subject_work(connection: sqlite3.Connection, workspace_id: str) -> tuple[SubjectWork, ...]:
    # Import parsing has its own independent guard at claim and completion. Every
    # other current or unknown active kind may disclose subject material; no
    # guessed allow-list for not-yet-implemented provider/export workers.
    rows = connection.execute(
        "SELECT id,kind,status FROM jobs WHERE workspace_id=? AND status IN ('queued','running','awaiting_approval') "
        "AND kind!='import' ORDER BY id", (workspace_id,),
    )
    return tuple(SubjectWork(row['id'], row['kind'], row['status']) for row in rows)


def outbound_source_kind(connection: sqlite3.Connection, workspace_id: str, job_id: str) -> str:
    """Jobs-owned identity lookup; the registered source must verify its content.

    This does not make an unknown job readable through JobService and does not
    supply a default Provider owner for import, grading or future job kinds.
    """
    from .errors import ApiError
    row = connection.execute(
        'SELECT kind FROM jobs WHERE id=? AND workspace_id=?', (job_id, workspace_id),
    ).fetchone()
    if row is None:
        raise ApiError(404, 'JOB_MISSING', '任务不存在或不可访问。')
    return str(row['kind'])


def outbound_lease_active(connection: sqlite3.Connection, workspace_id: str, job_id: str, now: str) -> bool:
    """A live owner lease excludes recovery, even after cancellation was requested.

    The caller holds the transaction while deciding recovery. Missing or corrupt
    job identity fails closed; an API restart cannot infer another worker died.
    """
    from pydantic import TypeAdapter
    from packages.contracts.domain_models import UTC
    from .errors import ApiError
    if not connection.in_transaction:
        raise ApiError(409, 'TRANSACTION_REQUIRED', '任务租约核验需要有效事务。')
    row = connection.execute('SELECT lease_owner,lease_until FROM jobs WHERE id=? AND workspace_id=?',
                             (job_id, workspace_id)).fetchone()
    if row is None:
        raise ApiError(404, 'JOB_MISSING', '任务不存在或不可访问。')
    if row['lease_owner'] is None and row['lease_until'] is None:
        return False
    try:
        if not isinstance(row['lease_owner'], str) or not row['lease_owner'].strip():
            raise ValueError('Lease owner unavailable')
        until = TypeAdapter(UTC).validate_python(row['lease_until'])
        checked_now = TypeAdapter(UTC).validate_python(now)
        return datetime.fromisoformat(until.replace('Z', '+00:00')) > datetime.fromisoformat(checked_now.replace('Z', '+00:00'))
    except (ValueError, TypeError):
        raise ApiError(503, 'JOB_LEASE_INVALID', '任务租约完整性无法确认。') from None


class JobService:
    """Dispatch only implemented job kinds to their owning application service."""
    def __init__(self, database):
        self.database = database

    def _owner(self, identity, identifier):
        from .errors import ApiError
        from .grading import GradingService
        from .imports import ImportService
        with self.database.connect() as connection:
            row = connection.execute("SELECT kind FROM jobs WHERE id=? AND workspace_id=?", (identifier, identity.workspace_id)).fetchone()
        if row is None:
            raise ApiError(404, "JOB_MISSING", "任务不存在或不可访问。")
        if row["kind"] == "assessment_grading":
            return GradingService(self.database)
        if row["kind"] == "import":
            return ImportService(self.database)
        raise ApiError(409, "JOB_KIND_UNAVAILABLE", "此任务类型尚未实现受控读取。")

    def job(self, identity, identifier):
        return self._owner(identity, identifier).job(identity, identifier)

    def cancel(self, identity, identifier, request, key):
        from .grading import GradingService
        owner = self._owner(identity, identifier)
        if isinstance(owner, GradingService):
            return owner.cancel(identity, identifier, request, key)
        return owner.cancel_job(identity, identifier, request, key)
