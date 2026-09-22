"""Durable numeric launch orchestration; never waits for a process inside a write lock."""
import sqlite3
import threading

from ..authoring_dto import NumericCheckResult, numeric_result_sha256
from ..infrastructure.authoring_job_repository import AuthoringLease, integrity
from ..infrastructure.authoring_numeric_repository import NumericRepository
from ..infrastructure.authoring_numeric_runtime import NumericExecution, NumericRuntime, NumericRuntimeError
from ..infrastructure.database import Database, utc_now
from ..infrastructure.security import author_execution_identity
from .authoring_context import AuthoringContext
from .authoring_models import NumericJobInput
from .errors import ApiError


class NumericWorker:
    def __init__(self, database: Database, context: AuthoringContext, runtime: NumericRuntime):
        self.database, self.context, self.runtime = database, context, runtime
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._cursor: tuple[str, str] | None = None
        self.last_error_code: str | None = None

    def start(self) -> None:
        if self.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name='learning-numeric-worker', daemon=True)
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

    def claim(self) -> tuple[AuthoringLease, NumericJobInput, str] | None:
        workspace = self.database.workspace_id()
        with self.database.transaction() as conn:
            rows = conn.execute("SELECT created_at,id FROM jobs WHERE workspace_id=? AND kind='authoring_numeric_check' AND (status='queued' OR (status='running' AND lease_until<=?)) ORDER BY created_at,id",
                                (workspace, utc_now())).fetchall()
            if self._cursor is not None:
                rows = [row for row in rows if tuple(row) > self._cursor] + [row for row in rows if tuple(row) <= self._cursor]
            repo = NumericRepository(conn, workspace)
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

    def _access(self, conn: sqlite3.Connection, lease: AuthoringLease, value: NumericJobInput, actor: str) -> NumericRepository:
        identity = author_execution_identity(conn, lease.workspace_id, actor)
        self.context.check_access(conn, identity)
        repo = NumericRepository(conn, lease.workspace_id)
        if repo.job_input(lease.job_id) != value:
            raise integrity()
        candidate = repo.candidate(value.candidate.draft_id)
        generation = repo.authoring.load(candidate.source_job_id)
        self.context.verify_history(conn, identity, generation.input, generation.view.preparation)
        return repo

    def _watch(self, lease: AuthoringLease, value: NumericJobInput, actor: str) -> bool:
        if self._stop.is_set():
            return False
        try:
            with self.database.transaction() as conn:
                repo = self._access(conn, lease, value, actor)
                return repo.jobs.renew(lease)
        except (ApiError, sqlite3.Error):
            return False

    def _started(self, lease: AuthoringLease, actual: str) -> None:
        with self.database.transaction() as conn:
            NumericRepository(conn, lease.workspace_id).mark_started(lease, actual)

    def _blocked(self, lease: AuthoringLease, value: NumericJobInput, outcome: str) -> None:
        with self.database.transaction() as conn:
            repo = NumericRepository(conn, lease.workspace_id)
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
            repo = NumericRepository(conn, lease.workspace_id)
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

    def process(self, lease: AuthoringLease, value: NumericJobInput, actor: str) -> None:
        with self.database.transaction(immediate=False) as conn:
            start, _ = NumericRepository(conn, lease.workspace_id).execution_state(lease.job_id)
        if start is not None:
            self._blocked(lease, value, 'outcome_unknown')
            return
        try:
            with self.database.transaction(immediate=False) as conn:
                self._access(conn, lease, value, actor)
            self.runtime.check(value.runtime)
            with self.database.transaction() as conn:
                repo = self._access(conn, lease, value, actor)
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
            if error.code not in {'POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED', 'AUTHORING_LEASE_LOST'}:
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
