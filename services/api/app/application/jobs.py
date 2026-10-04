"""Jobs-owned exclusion facts for atomic independent-assessment start."""

from dataclasses import dataclass
from datetime import datetime
import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .review_service import ReviewService


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


def artifact_job_kind(connection: sqlite3.Connection, workspace_id: str, job_id: str) -> str:
    """Jobs-owned kind fact for an artifact; never a content permission grant."""
    from .errors import ApiError
    if not connection.in_transaction:
        raise ApiError(409, 'TRANSACTION_REQUIRED', '附件任务核验需要有效事务。')
    return outbound_source_kind(connection, workspace_id, job_id)


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


@dataclass(frozen=True)
class ImportConfirmationState:
    status: str
    cancel_requested: bool


def import_confirmation_state(connection: sqlite3.Connection, workspace_id: str,
                              job_id: str, input_sha256: str) -> ImportConfirmationState:
    """Jobs-owned origin facts, including after a legitimate cancellation/commit."""
    from .errors import ApiError
    if not connection.in_transaction:
        raise ApiError(409, 'TRANSACTION_REQUIRED', '导入任务核验需要当前事务。')
    row = connection.execute('SELECT kind,status,cancel_requested,input_sha256 FROM jobs '
                             'WHERE id=? AND workspace_id=?', (job_id, workspace_id)).fetchone()
    if (row is None or row['kind'] != 'import' or row['input_sha256'] != input_sha256
            or row['status'] not in {'queued', 'running', 'awaiting_approval', 'completed', 'failed', 'cancelled'}
            or row['cancel_requested'] not in (0, 1)):
        raise ApiError(409, 'PUBLICATION_IMPORT_JOB_INVALID', '导入任务的原始身份和输入无法核验。')
    return ImportConfirmationState(row['status'], bool(row['cancel_requested']))


def require_pending_import_confirmation(connection: sqlite3.Connection, workspace_id: str,
                                        job_id: str, input_sha256: str) -> None:
    """Current eligibility for a new command; not the historical ACK read gate."""
    from .errors import ApiError
    state = import_confirmation_state(connection, workspace_id, job_id, input_sha256)
    if state.status != 'awaiting_approval' or state.cancel_requested:
        raise ApiError(409, 'PUBLICATION_IMPORT_NOT_PENDING', '导入任务当前不能新发布候选。')


class JobService:
    """Dispatch only implemented job kinds to their owning application service."""
    def __init__(self, database, review: 'ReviewService | None' = None, restore_numeric=None, codex_turn=None, codex_artifact_imports=None):
        self.database = database
        self.review = review
        self.restore_numeric = restore_numeric
        self.codex_turn = codex_turn
        self.codex_artifact_imports = codex_artifact_imports

    def _owner(self, identity, identifier):
        from .errors import ApiError
        from .grading import GradingService
        from .imports import ImportService
        with self.database.connect() as connection:
            row = connection.execute("SELECT kind FROM jobs WHERE id=? AND workspace_id=?", (identifier, identity.workspace_id)).fetchone()
        if row is None:
            raise ApiError(404, "JOB_MISSING", "任务不存在或不可访问。")
        if row['kind'] == 'codex_turn' and self.codex_turn is not None:
            return self.codex_turn
        if row['kind'] == 'codex_artifact_import' and self.codex_artifact_imports is not None:
            return self.codex_artifact_imports
        if row['kind'] == 'draft_review' and self.review is not None:
            return self.review
        if row["kind"] == "assessment_grading":
            return GradingService(self.database)
        if row["kind"] == "import":
            return ImportService(self.database)
        if row["kind"] == "retrieval_index":
            from .retrieval import RetrievalService
            return RetrievalService(self.database)
        if row['kind'] == 'tutor':
            from .tutor import TutorService
            from .tutor_context import ContextService
            return TutorService(self.database, ContextService(self.database))
        if row['kind'] == 'authoring':
            from ..infrastructure.authoring_job_repository import AuthoringJobRepository
            with self.database.transaction(immediate=False) as conn:
                version = AuthoringJobRepository(conn, identity.workspace_id).input_version(identifier)
            if version == 'authoring-group-job-v1':
                from .authoring_group import AuthoringGroupService
                return AuthoringGroupService(self.database)
            from .authoring import AuthoringService
            return AuthoringService(self.database)
        if row['kind'] == 'authoring_numeric_check':
            from ..infrastructure.authoring_job_repository import AuthoringJobRepository
            with self.database.transaction(immediate=False) as conn:
                version = AuthoringJobRepository(conn, identity.workspace_id).input_version(identifier)
            if version == 'restore-numeric-job-v1':
                if self.restore_numeric is None:
                    raise ApiError(503, 'NUMERIC_OWNER_UNAVAILABLE', '恢复数值安全控制服务当前不可用。')
                return self.restore_numeric
            if version == 'authoring-group-numeric-job-v1':
                from .authoring_group_context import AuthoringGroupContext
                from .authoring_group_numeric_service import GroupNumericService
                from ..infrastructure.authoring_numeric_runtime import NumericRuntime
                return GroupNumericService(self.database, AuthoringGroupContext(self.database), NumericRuntime())
            from .authoring_context import AuthoringContext
            from .authoring_numeric_service import NumericService
            from ..infrastructure.authoring_numeric_runtime import NumericRuntime
            return NumericService(self.database, AuthoringContext(self.database), NumericRuntime())
        raise ApiError(409, "JOB_KIND_UNAVAILABLE", "此任务类型尚未实现受控读取。")

    def job(self, identity, identifier):
        owner = self._owner(identity, identifier)
        if self.review is not None and owner is self.review:
            return self.review.read_job(identity, identifier)
        return owner.job(identity, identifier)

    def cancel(self, identity, identifier, request, key):
        from .grading import GradingService
        owner = self._owner(identity, identifier)
        if self.review is not None and owner is self.review:
            return self.review.cancel(identity, identifier, request, key)
        if isinstance(owner, GradingService):
            return owner.cancel(identity, identifier, request, key)
        return owner.cancel_job(identity, identifier, request, key)
