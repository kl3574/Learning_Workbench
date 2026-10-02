"""Durable numeric launch orchestration; never waits for a process inside a write lock."""
import sqlite3
import threading

from ..authoring_dto import NumericCheckResult, numeric_result_sha256
from ..infrastructure.authoring_job_repository import AuthoringLease, integrity
from ..infrastructure.restore_numeric_repository import RestoreNumericRepository
from ..infrastructure.authoring_numeric_runtime import NumericExecution, NumericRuntime, NumericRuntimeError
from ..infrastructure.database import Database, utc_now
from ..infrastructure.security import author_execution_identity
from .restore_numeric_service import RestoreNumericService
from .restore_numeric_models import RestoreNumericJobInput
from .errors import ApiError


class RestoreNumericWorker:
    def __init__(self, database: Database, service: RestoreNumericService, runtime: NumericRuntime):
        self.database, self.service, self.runtime = database, service, runtime
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._cursor: tuple[str, str] | None = None
        self.last_error_code: str | None = None

    def start(self) -> None:
        if self.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name='learning-restore-numeric-worker', daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self.runtime.cancel()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                worked = self.run_once()
                self.last_error_code = None
            except (ApiError, sqlite3.Error, NumericRuntimeError) as error:
                self.last_error_code = error.code if isinstance(error, (ApiError, NumericRuntimeError)) else 'AUTHORING_INTEGRITY_ERROR'
                worked = False
            if not worked:
                self._stop.wait(0.25)

    def claim(self) -> tuple[AuthoringLease, RestoreNumericJobInput, str] | None:
        workspace = self.database.workspace_id()
        with self.database.transaction() as conn:
            rows = conn.execute("SELECT created_at,id FROM jobs WHERE workspace_id=? AND kind='authoring_numeric_check' AND json_extract(input_json,'$.version')='restore-numeric-job-v1' AND (status='queued' OR (status='running' AND lease_until<=?)) ORDER BY created_at,id",
                                (workspace, utc_now())).fetchall()
            if self._cursor is not None:
                rows = [row for row in rows if tuple(row) > self._cursor] + [row for row in rows if tuple(row) <= self._cursor]
            repo = RestoreNumericRepository(conn, workspace)
            first_error = None
            for row in rows[:32]:
                self._cursor = tuple(row)
                try:
                    return repo.claim(row['id'])
                except ApiError as error:
                    first_error = first_error or error
            if first_error is not None:
                raise first_error
            return None

    def _access(self, conn: sqlite3.Connection, lease: AuthoringLease, value: RestoreNumericJobInput,
                actor: str, *, current: bool = False) -> RestoreNumericRepository:
        identity = author_execution_identity(conn, lease.workspace_id, actor)
        record = self.service.subject(conn, identity, value.candidate.draft_id)
        repo = RestoreNumericRepository(conn, lease.workspace_id)
        if repo.job_input(lease.job_id) != value or record.candidate != value.candidate:
            raise integrity()
        if current:
            self.service.current_candidate(conn, identity, value.candidate)
        return repo

    def _watch(self, lease: AuthoringLease, value: RestoreNumericJobInput, actor: str) -> bool:
        if self._stop.is_set():
            return False
        try:
            with self.database.transaction() as conn:
                repo = self._access(conn, lease, value, actor)
                start, _ = repo.execution_state(lease.job_id)
                if start is None or start.actual_started_at is None:
                    self._access(conn, lease, value, actor, current=True)
                return repo.jobs.renew(lease)
        except (ApiError, sqlite3.Error):
            return False

    def _started(self, lease: AuthoringLease, actual: str) -> None:
        with self.database.transaction() as conn:
            RestoreNumericRepository(conn, lease.workspace_id).mark_started(lease, actual)

    def _blocked(self, lease: AuthoringLease, value: RestoreNumericJobInput, outcome: str) -> None:
        with self.database.transaction() as conn:
            repo = RestoreNumericRepository(conn, lease.workspace_id)
            row = repo.jobs.load(lease.job_id)
            if not repo.jobs.owned(row, lease, allow_cancel=True):
                return
            start, end = repo.execution_state(lease.job_id)
            if end is not None:
                return
            # An existing launch permission cannot prove the process never ran.
            # Preserve the actual started timestamp if it was durably observed.
            result = {'job_id': lease.job_id, 'input_sha256': row['input_sha256'],
                'operation_sha256': value.operation_sha256, 'outcome': outcome, 'verdict': 'BLOCKED',
                'started_at': start.actual_started_at if start is not None else None,
                'finished_at': utc_now(), 'exit_code': None, 'assertions': [], 'output_sha256': None}
            result['result_sha256'] = numeric_result_sha256(result)
            repo.finish(lease, NumericCheckResult.model_validate(result))

    def _finish(self, lease: AuthoringLease, execution: NumericExecution) -> None:
        with self.database.transaction() as conn:
            repo = RestoreNumericRepository(conn, lease.workspace_id)
            row = repo.jobs.load(lease.job_id)
            if not repo.jobs.owned(row, lease, allow_cancel=True):
                return
            result = execution.result
            if row['cancel_requested'] and result.outcome != 'outcome_unknown':
                value = result.model_dump(mode='json')
                value.update(outcome='cancelled', verdict='BLOCKED')
                value['result_sha256'] = numeric_result_sha256(value)
                result = NumericCheckResult.model_validate(value)
            repo.finish(lease, result, execution.stdout, execution.stderr,
                        execution.output_complete, manifest_json=execution.manifest_json)

    def process(self, lease: AuthoringLease, value: RestoreNumericJobInput, actor: str) -> None:
        with self.database.transaction(immediate=False) as conn:
            start, _ = RestoreNumericRepository(conn, lease.workspace_id).execution_state(lease.job_id)
        if start is not None:
            self._blocked(lease, value, 'outcome_unknown')
            return
        try:
            with self.database.transaction(immediate=False) as conn:
                self._access(conn, lease, value, actor, current=True)
            self.runtime.check(value.runtime)
            with self.database.transaction() as conn:
                repo = self._access(conn, lease, value, actor, current=True)
                admitted = repo.begin(lease, utc_now())
            if not admitted:
                self._blocked(lease, value, 'outcome_unknown')
                return
            execution = self.runtime.run_checked(value,
                lambda: not self._watch(lease, value, actor), on_started=lambda actual: self._started(lease, actual))
            self._finish(lease, execution)
        except NumericRuntimeError:
            self._blocked(lease, value, 'environment_unavailable')
        except ApiError as error:
            if error.status != 412 and error.code not in {'RESTORE_ALREADY_PUBLISHED', 'POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED', 'AUTHORING_LEASE_LOST'}:
                raise
            self._blocked(lease, value, 'cancelled')

    def run_once(self) -> bool:
        if self._stop.is_set() or not self._lock.acquire(blocking=False):
            return False
        try:
            work = self.claim()
            if work is None:
                return False
            self.process(*work)
            return True
        finally:
            self._lock.release()
