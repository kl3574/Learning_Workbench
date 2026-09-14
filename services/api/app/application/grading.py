"""Deterministic assessment grading and explicit signed human review application."""

import sqlite3
from collections.abc import Callable
from typing import Literal

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256

from ..assessment_dto import AssessmentGradingJob, AssessmentGradingResult, RegradeRequest, ReleasedSolutionReview
from ..import_dto import JobCancelRequest, JobSnapshot
from ..infrastructure.assessment_repository import AssessmentRecord, AssessmentRepository, invalid_snapshot
from ..infrastructure.database import Database, utc_now
from ..infrastructure.grading_repository import GradeAudit, GradingLease, GradingRepository, uid
from ..infrastructure.idempotency import execute_idempotent
from ..infrastructure.security import SessionIdentity
from .assessment_content import AssessmentContent
from .errors import ApiError
from .grading_rules import GradingBindingError, RULES_VERSION, grade_item
from .learning import validate_test_submitted
from .policy import Policy


def checked_submission(connection: sqlite3.Connection, record: AssessmentRecord) -> None:
    if record.submission is None or record.submission_event_id is None:
        raise ApiError(409, "ATTEMPT_NOT_SUBMITTED", "作答尚未提交，没有可评分的固定快照。")
    AssessmentRepository(connection, record.workspace_id).validate_outbox(record)
    validate_test_submitted(connection, record.workspace_id, record.submission_event_id, record.assessment_ref, record.id)


class GradingService:
    def __init__(self, database: Database):
        self.database = database

    def result(self, identity: SessionIdentity, identifier: str) -> AssessmentGradingResult | AssessmentGradingJob:
        with self.database.transaction() as connection:
            Policy(connection, identity.workspace_id).check("attempt_read", attempt_id=identifier)
            repo = GradingRepository(connection, identity.workspace_id)
            record = repo.attempts.load(identifier)
            checked_submission(connection, record)
            job = repo.latest_job(identifier)
            if job is None:
                raise ApiError(503, "GRADING_RECOVERY_PENDING", "评分任务正在从持久提交恢复，请稍后重试。", True)
            grade = repo.load_grade(record)
            if job["status"] != "completed":
                previous = self._project(connection, repo, record, grade, release=False) if grade is not None else None
                return AssessmentGradingJob(id=job["id"], status=job["status"], last_completed_result=previous)
            if grade is None:
                raise invalid_snapshot()
            return self._project(connection, repo, record, grade, release=record.policy.mode != "independent" or grade[0].status == "graded")

    @staticmethod
    def _project(connection: sqlite3.Connection, repo: GradingRepository, record: AssessmentRecord,
                 grade: tuple[dm.GradingResult, GradeAudit], *, release: bool) -> AssessmentGradingResult:
        value, audit = grade
        content = AssessmentContent(connection, record.workspace_id)
        reviews = [repo.review(review_id, record)[1] for review_id in audit.review_ids]
        items = []
        solution_reviews = []
        for item, pin in zip(value.items, record.assignment.private_pins, strict=True):
            if release:
                Policy(connection, record.workspace_id).check("solution_read", question_ref=item.question_ref)
                solution = content.solution(pin)
                items.append(item.model_copy(update={"solution_markdown": solution.solution_markdown}))
                solution_reviews.append(ReleasedSolutionReview(question_id=item.question_ref.id, review_status=pin.review_status))
            else:
                items.append(item)
        return AssessmentGradingResult(**value.model_dump(exclude={"items"}), items=items, manual_reviews=reviews,
            solution_reviews=solution_reviews, eligibility_status="not_evaluated")

    def regrade(self, identity: SessionIdentity, identifier: str, request: RegradeRequest, key: str | None) -> dm.JobRef:
        with self.database.transaction() as connection:
            policy = Policy(connection, identity.workspace_id)
            policy.check("attempt_write", attempt_id=identifier)
            repo = GradingRepository(connection, identity.workspace_id)
            record = repo.attempts.load(identifier)
            checked_submission(connection, record)
            # Recheck actual session and role even before an idempotent receipt can be read.
            if identity.role != "author" or connection.execute("SELECT 1 FROM local_sessions WHERE id=? AND workspace_id=? AND role='author' AND revoked_at IS NULL AND expires_at>?", (identity.id, identity.workspace_id, utc_now())).fetchone() is None:
                raise ApiError(403, "HUMAN_AUTHOR_REQUIRED", "人工复核需要当前有效作者会话明确确认。")
            route = f"POST /attempts/{identifier}/regrade"
            replay = repo.attempts.replay_target(route, key)
            if replay is not None and replay != identifier:
                raise invalid_snapshot()
            questions = AssessmentContent(connection, identity.workspace_id).questions(AssessmentContent(connection, identity.workspace_id).blueprint(record.assessment_ref))
            scores = {question.id: question.max_score for question in questions}
            if any(item.question_id not in scores or item.score > scores[item.question_id] for item in request.item_reviews):
                raise ApiError(422, "REVIEW_ITEM_INVALID", "人工评分必须属于本次分配且不得超过题目分值。")
            def operation() -> dict[str, object]:
                if request.expected_grading_revision != repo.latest_revision(identifier):
                    raise ApiError(412, "GRADING_REVISION_CONFLICT", "评分版本已改变，请重新读取结果。")
                old = repo.load_grade(record)
                if old is None and request.expected_grading_revision != 0:
                    raise invalid_snapshot()
                review_id = repo.sign(identity, record, request)
                return repo.enqueue(record, base_revision=request.expected_grading_revision, review_id=review_id).model_dump(mode="json")
            value = execute_idempotent(connection, actor=identity.workspace_id, route=route, key=key, payload=request.model_dump(mode="json"), operation=operation)
            response = dm.JobRef.model_validate(value)
            job = repo.job(response.id)
            if repo.input(job).attempt_id != identifier:
                raise invalid_snapshot()
            if replay is None:
                repo.attempts.seal_receipt(route, key, record, value)
            return response

    def job(self, identity: SessionIdentity, identifier: str) -> JobSnapshot:
        with self.database.transaction() as connection:
            repo = GradingRepository(connection, identity.workspace_id)
            row = repo.job(identifier)
            Policy(connection, identity.workspace_id).check("attempt_read", attempt_id=repo.input(row).attempt_id)
            checked_submission(connection, repo.attempts.load(repo.input(row).attempt_id))
            if row["status"] == "completed":
                repo.load_grade(repo.attempts.load(repo.input(row).attempt_id), repo.input(row).grading_revision)
            return repo.snapshot(row)

    def cancel(self, identity: SessionIdentity, identifier: str, request: JobCancelRequest, key: str | None) -> JobSnapshot:
        with self.database.transaction() as connection:
            repo = GradingRepository(connection, identity.workspace_id)
            row = repo.job(identifier)
            record = repo.attempts.load(repo.input(row).attempt_id)
            Policy(connection, identity.workspace_id).check("attempt_write", attempt_id=record.id)
            route = f"POST /jobs/{identifier}/cancel"
            replay = repo.attempts.replay_target(route, key)
            if replay is not None and replay != record.id:
                raise invalid_snapshot()
            def operation() -> dict[str, object]:
                if row["revision"] != request.expected_revision:
                    raise ApiError(412, "REVISION_CONFLICT", "任务已改变，请重新读取状态。")
                repo.terminal(row, "cancelled")
                return repo.snapshot(repo.job(identifier)).model_dump(mode="json")
            value = execute_idempotent(connection, actor=identity.workspace_id, route=route, key=key, payload=request.model_dump(mode="json"), operation=operation)
            if replay is None:
                repo.attempts.seal_receipt(route, key, record, value)
            return JobSnapshot.model_validate(value)


class GradingStopped(Exception):
    """Shutdown relinquishes work for lease recovery without fabricating failure."""


class GradingWorker:
    """Driven by the existing single worker thread, never another task queue."""
    def __init__(self, database: Database, stopping: Callable[[], bool] = lambda: False):
        self.database = database
        self.stopping = stopping
        self.lease_seconds = 90

    def recover(self) -> None:
        with self.database.transaction() as connection:
            rows = connection.execute("SELECT id,workspace_id FROM attempts a WHERE status='submitted' AND submission_json IS NOT NULL AND NOT EXISTS(SELECT 1 FROM assessment_grade_jobs g WHERE g.attempt_id=a.id) AND NOT EXISTS(SELECT 1 FROM grading_recovery_failures f WHERE f.attempt_id=a.id) AND NOT EXISTS(SELECT 1 FROM attempts other WHERE other.workspace_id=a.workspace_id AND other.mode='independent' AND other.status='active')").fetchall()
            for row in rows:
                if self.stopping():
                    raise GradingStopped()
                connection.execute("SAVEPOINT recover_grading_item")
                try:
                    repo = GradingRepository(connection, row["workspace_id"])
                    record = repo.attempts.load(row["id"])
                    checked_submission(connection, record)
                    repo.enqueue(record, base_revision=0)
                except (ApiError, ValueError, TypeError):
                    connection.execute("ROLLBACK TO recover_grading_item")
                    connection.execute("INSERT INTO grading_recovery_failures(attempt_id,workspace_id,code,detected_at) VALUES(?,?,'GRADING_RECOVERY_INVALID',?)", (row["id"], row["workspace_id"], utc_now()))
                finally:
                    connection.execute("RELEASE recover_grading_item")

    def claim(self) -> GradingLease | None:
        with self.database.transaction() as connection:
            now = utc_now()
            rows = connection.execute("SELECT j.* FROM jobs j WHERE kind='assessment_grading' AND cancel_requested=0 AND (status='queued' OR (status='running' AND lease_until<=?)) AND (next_retry_at IS NULL OR next_retry_at<=?) AND NOT EXISTS(SELECT 1 FROM attempts a WHERE a.workspace_id=j.workspace_id AND a.mode='independent' AND a.status='active') ORDER BY j.created_at,j.id", (now, now)).fetchall()
            for row in rows:
                if self.stopping():
                    raise GradingStopped()
                repo = GradingRepository(connection, row["workspace_id"])
                try:
                    record = repo.attempts.load(repo.input(row).attempt_id)
                    checked_submission(connection, record)
                except (ApiError, ValueError, TypeError):
                    # Only the trustworthy jobs row/namespace is used to fail this
                    # task; corrupt input never identifies a domain mutation target.
                    error = dm.ErrorDetail(code="GRADING_INPUT_INVALID", message="评分输入完整性校验失败，任务已隔离；未生成成绩。", request_id=uid("request"), retryable=False)
                    connection.execute("UPDATE jobs SET status='failed',revision=revision+1,result_json=?,lease_owner=NULL,lease_until=NULL,updated_at=? WHERE id=? AND revision=?", (canonical_bytes({"error": error.model_dump(mode="json")}).decode(), utc_now(), row["id"], row["revision"]))
                    repo.event(row["id"], "failed", row["revision"] + 1)
                    continue
                lease = repo.claim(row, self.lease_seconds)
                connection.execute("UPDATE outbox SET delivered_at=? WHERE id=? AND delivered_at IS NULL", (utc_now(), record.grading_outbox_id))
                return lease
            return None

    def compute(self, lease: GradingLease) -> tuple[dm.GradingResult, GradeAudit]:
        if self.stopping():
            raise GradingStopped()
        with self.database.connect() as connection:
            repo = GradingRepository(connection, lease.workspace_id)
            row = repo.job(lease.job_id)
            if not repo.owned(row, lease):
                raise ApiError(409, "GRADING_LEASE_LOST", "评分任务已取消或由另一工作进程恢复。")
            value = repo.input(row)
            record = repo.attempts.load(value.attempt_id)
            checked_submission(connection, record)
            content = AssessmentContent(connection, lease.workspace_id)
            questions = content.questions(content.blueprint(record.assessment_ref))
            responses = {item.question_id: item for item in record.responses}
            solutions = [content.solution(pin) for pin in record.assignment.private_pins]
            base = repo.load_grade(record, value.base_grading_revision)
            if base is None:
                decisions = []
                for ref, question, pin, solution in zip(record.question_refs, questions, record.assignment.private_pins, solutions, strict=True):
                    if self.stopping():
                        raise GradingStopped()
                    decisions.append(grade_item(question_ref=ref, question=question, pin=pin, solution=solution, response=responses.get(ref.id)))
                items = [decision.item_grade for decision in decisions]
                traces = [decision.private_trace for decision in decisions]
                review_ids: list[str] = []
            else:
                items = base[0].items
                traces = base[1].traces
                review_ids = list(base[1].review_ids)
            if value.review_id is not None:
                review, _ = repo.review(value.review_id, record)
                mapping = {item.question_id: item for item in review.request.item_reviews}
                items = [dm.ItemGrade(question_ref=item.question_ref, score=mapping[item.question_ref.id].score, max_score=item.max_score,
                    status="graded", feedback_markdown=mapping[item.question_ref.id].feedback_markdown, solution_markdown=None)
                    if item.question_ref.id in mapping else item for item in items]
                review_ids.append(value.review_id)
            status: Literal["graded", "needs_review"] = "needs_review" if any(item.status == "needs_review" for item in items) else "graded"
            version = RULES_VERSION + ("+human-v1" if review_ids else "")
            result = dm.GradingResult(attempt_id=record.id, grading_revision=value.grading_revision, grading_rules_version=version,
                status=status, items=items, finalized_at=utc_now())
            return result, GradeAudit(job_id=lease.job_id, input=value, rules_version=version, traces=traces, review_ids=review_ids, result_sha256=metadata_sha256(result))

    def finish(self, lease: GradingLease, result: dm.GradingResult, audit: GradeAudit) -> bool:
        if self.stopping():
            return False
        with self.database.transaction() as connection:
            repo = GradingRepository(connection, lease.workspace_id)
            row = repo.job(lease.job_id)
            if not repo.owned(row, lease):
                return False
            value = repo.input(row)
            record = repo.attempts.load(value.attempt_id)
            checked_submission(connection, record)
            if (audit.input != value or audit.job_id != lease.job_id or audit.result_sha256 != metadata_sha256(result)
                    or result.attempt_id != record.id or result.grading_revision != value.grading_revision
                    or [item.question_ref for item in result.items] != record.question_refs or repo.latest_revision(record.id) != value.base_grading_revision):
                raise invalid_snapshot()
            connection.execute("INSERT INTO grades(attempt_id,grading_revision,result_json,created_at) VALUES(?,?,?,?)", (record.id, result.grading_revision, canonical_bytes(result).decode(), result.finalized_at))
            connection.execute("INSERT INTO assessment_grade_audits(attempt_id,grading_revision,result_sha256,private_json,private_sha256,job_id) VALUES(?,?,?,?,?,?)",
                (record.id, result.grading_revision, metadata_sha256(result), canonical_bytes(audit).decode(), metadata_sha256(audit), lease.job_id))
            connection.execute("UPDATE attempts SET status=?,revision=revision+1 WHERE id=? AND workspace_id=? AND status='grading'", (result.status, record.id, lease.workspace_id))
            repo.terminal(row, "completed", {"grading_revision": result.grading_revision, "result_sha256": metadata_sha256(result)})
            return True

    def fail(self, lease: GradingLease) -> None:
        with self.database.transaction() as connection:
            repo = GradingRepository(connection, lease.workspace_id)
            # Invalid private content may fail compute; input itself still must be intact.
            row = repo.job(lease.job_id)
            if repo.owned(row, lease):
                error = dm.ErrorDetail(code="GRADING_FAILED", message="评分未完成；原始提交与既有成绩已保留，请检查冻结材料或明确人工复核。", request_id=uid("request"), retryable=False)
                repo.terminal(row, "failed", {"error": error.model_dump(mode="json")})

    def run_once(self) -> bool:
        lease = None
        try:
            self.recover()
            lease = self.claim()
            if lease is None:
                return False
            result, audit = self.compute(lease)
            self.finish(lease, result, audit)
        except GradingStopped:
            return False
        except (ApiError, GradingBindingError, ValueError, TypeError):
            if lease is not None:
                self.fail(lease)
            else:
                raise
        return True
