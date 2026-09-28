"""Local Quality worker: real Jobs leases, read-only numeric history, no execution."""
import sqlite3
import threading

from packages.contracts.canonical import metadata_sha256
from ..infrastructure.authoring_job_repository import AuthoringLease, TERMINAL, integrity as job_integrity
from ..infrastructure.database import utc_now
from ..infrastructure.review_repository import ReviewRepository, integrity
from ..infrastructure.security import author_execution_identity
from .errors import ApiError
from .review_artifacts import report_bytes
from .review_checks import review_structure
from .review_history_models import ReviewMachineRecord, StoredReviewReceipt, MACHINE_REASON, machine_job_result
from .review_service import ReviewService


class ReviewWorker:
    def __init__(self, service: ReviewService):
        self.service, self.database = service, service.database
        self._stop, self._lock = threading.Event(), threading.Lock()
        self._thread: threading.Thread | None = None
        self._cursor: tuple[str, str] | None = None
        self.last_error_code: str | None = None
        self.last_queue_error_code: str | None = None

    def start(self) -> None:
        if self.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name='learning-review-worker', daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                worked = self.run_once()
                self.last_error_code = None
            except (ApiError, sqlite3.Error) as error:
                self.last_error_code = error.code if isinstance(error, ApiError) else 'REVIEW_STORAGE_UNAVAILABLE'
                worked = False
            if not worked:
                self._stop.wait(0.25)

    def claim(self) -> AuthoringLease | None:
        workspace = self.database.workspace_id()
        with self.database.transaction() as conn:
            repo = ReviewRepository(conn, workspace)
            scan = repo.jobs.claimable_candidates(utc_now())
            rows = list(scan.candidates)
            first_error = job_integrity() if scan.invalid_rows else None
            self.last_queue_error_code = first_error.code if first_error else None
            if self._cursor is not None:
                rows = [r for r in rows if (r.created_at, r.job_id) > self._cursor] + [r for r in rows if (r.created_at, r.job_id) <= self._cursor]
            for row in rows[:32]:
                self._cursor = (row.created_at, row.job_id)
                try:
                    repo.load(row.job_id)
                except ApiError as error:
                    first_error = first_error or error
                    continue
                lease = repo.jobs.claim(row.job_id)
                repo.load(row.job_id)
                return lease
            if first_error is not None:
                raise first_error
            return None

    def finish(self, lease: AuthoringLease) -> None:
        # No process or remote operation occurs under this transaction. Physical
        # report write may leave an unreferenced immutable blob after rollback;
        # no report, receipt or successful Job pointer can survive separately.
        with self.database.transaction() as conn:
            repo = ReviewRepository(conn, lease.workspace_id)
            history, row = repo.load(lease.job_id), repo.jobs.load(lease.job_id)
            if row['status'] in TERMINAL or not repo.jobs.owned(row, lease, allow_cancel=True):
                return
            if row['cancel_requested']:
                repo.jobs.transition(row, 'cancelled', result={'cancelled_before_report':True})
                repo.load(lease.job_id)
                return
            value = history.binding.input
            try:
                identity = author_execution_identity(conn, lease.workspace_id, value.creator_session_id)
                _, material = self.service._history(conn, identity, lease.job_id)
                numeric = self.service.numeric.read_review_numeric(conn, identity,
                    value.candidate.draft_id, value.candidate.draft_revision)
            except ApiError as error:
                if error.code not in {'SESSION_REQUIRED', 'POLICY_DENIED', 'ASSESSMENT_ACTIVE', 'ASSESSMENT_ANSWER_PROTECTED'}:
                    raise
                repo.jobs.transition(row, 'failed', result={'error_code':error.code})
                repo.load(lease.job_id)
                return
            if not repo.jobs.owned(repo.jobs.load(lease.job_id), lease):
                return
            structure = review_structure(material, requested='structure' in value.request.checks)
            report = self.service.artifacts.write(conn, value, report_bytes(value, material, numeric, structure))
            receipt = StoredReviewReceipt(id=lease.job_id, revision=1, candidate=value.candidate,
                structural=structure.structural, mathematical='NOT_RUN', sources='NOT_RUN',
                independent_pedagogy='NOT_RUN', reviewer='system:draft-review-rules-v1', created_at=value.created_at,
                evidence_paths=[report.artifact.download_path], decision_reason=MACHINE_REASON)
            machine = ReviewMachineRecord(version='review-machine-record-v1', workspace_id=lease.workspace_id,
                review_id=lease.job_id, job_revision=row['revision'] + 1, input_sha256=metadata_sha256(value),
                material=material, numeric=numeric, structural_report=structure, report=report,
                receipt=receipt, checked_at=utc_now())
            # Disk work cannot extend a lease. Recheck immediately before the
            # unique terminal and roll back every staged DB row if it expired.
            if not repo.jobs.owned(repo.jobs.load(lease.job_id), lease):
                raise ApiError(409, 'REVIEW_LEASE_LOST', '审核任务租约已失效。')
            repo.jobs.transition(row, 'completed', result=machine_job_result(machine))
            repo.append_machine(machine)
            checked, _ = self.service._history(conn, identity, lease.job_id)
            if checked.receipt != receipt:
                raise integrity()

    def run_once(self) -> bool:
        if not self._lock.acquire(blocking=False):
            return False
        try:
            lease = self.claim()
            if lease is None:
                return False
            self.finish(lease)
            return True
        finally:
            self._lock.release()
