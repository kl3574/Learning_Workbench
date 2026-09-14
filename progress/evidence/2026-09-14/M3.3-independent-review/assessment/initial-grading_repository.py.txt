"""Assessment-owned immutable grading, signed manual decisions and durable jobs."""

from dataclasses import dataclass
import hashlib
import hmac
import secrets
import sqlite3
from typing import Literal
from uuid import uuid4

from pydantic import Field

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, strict_json

from ..application.errors import ApiError
from ..application.grading_rules import PrivateGradeTrace
from ..assessment_dto import ManualReviewReceipt, RegradeRequest
from ..import_dto import JobProgress, JobSnapshot
from .assessment_repository import AssessmentRecord, AssessmentRepository, invalid_snapshot
from .database import utc_now
from .security import SessionIdentity, expires_after


def uid(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class GradeJobInput(dm.StrictModel):
    workspace_id: dm.Id
    attempt_id: dm.Id
    assignment_sha256: dm.Sha256
    submission_sha256: dm.Sha256
    grading_revision: dm.Revision
    base_grading_revision: int = Field(ge=0)
    review_id: dm.Id | None


class SignedReview(dm.StrictModel):
    id: dm.Id
    workspace_id: dm.Id
    attempt_id: dm.Id
    assignment_sha256: dm.Sha256
    submission_sha256: dm.Sha256
    actor_session_id: dm.Id
    actor_role: Literal["author"]
    signed_at: dm.UTC
    request: RegradeRequest


class GradeAudit(dm.StrictModel):
    job_id: dm.Id
    input: GradeJobInput
    rules_version: str
    traces: list[PrivateGradeTrace]
    review_ids: list[dm.Id]
    result_sha256: dm.Sha256


@dataclass(frozen=True)
class GradingLease:
    job_id: str
    workspace_id: str
    owner: str
    revision: int


class GradingRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection = connection
        self.workspace_id = workspace_id
        self.attempts = AssessmentRepository(connection, workspace_id)

    def event(self, job_id: str, status: str, revision: int) -> None:
        self.connection.execute("INSERT INTO job_events(job_id,seq,type,payload_json,occurred_at) VALUES(?,COALESCE((SELECT MAX(seq)+1 FROM job_events WHERE job_id=?),1),?,?,?)",
            (job_id, job_id, status, canonical_bytes({"status": status, "revision": revision}).decode(), utc_now()))

    def latest_job(self, attempt_id: str) -> sqlite3.Row | None:
        row = self.connection.execute("SELECT j.* FROM assessment_grade_jobs g JOIN jobs j ON j.id=g.job_id WHERE g.attempt_id=? AND j.workspace_id=? ORDER BY g.sequence DESC LIMIT 1", (attempt_id, self.workspace_id)).fetchone()
        if row is not None:
            self.input(row)
        return row

    def input(self, row: sqlite3.Row) -> GradeJobInput:
        try:
            value = GradeJobInput.model_validate(strict_json(row["input_json"]))
            allocation = self.connection.execute("SELECT * FROM assessment_grade_jobs WHERE job_id=?", (row["id"],)).fetchone()
            record = self.attempts.load(value.attempt_id)
            if (row["workspace_id"] != self.workspace_id or value.workspace_id != self.workspace_id or row["kind"] != "assessment_grading"
                    or metadata_sha256(value) != row["input_sha256"] or value.assignment_sha256 != metadata_sha256(record.assignment)
                    or record.submission is None or value.submission_sha256 != metadata_sha256(record.submission)
                    or allocation is None or allocation["attempt_id"] != record.id or allocation["grading_revision"] != value.grading_revision
                    or allocation["base_grading_revision"] != value.base_grading_revision
                    or value.grading_revision != value.base_grading_revision + 1):
                raise invalid_snapshot()
            self.attempts.validate_outbox(record)
            if value.review_id is not None:
                review, _ = self.review(value.review_id, record)
                if review.request.expected_grading_revision != value.base_grading_revision:
                    raise invalid_snapshot()
            return value
        except (ValueError, TypeError, KeyError):
            raise invalid_snapshot() from None

    def job(self, identifier: str) -> sqlite3.Row:
        row = self.connection.execute("SELECT * FROM jobs WHERE id=? AND workspace_id=? AND kind='assessment_grading'", (identifier, self.workspace_id)).fetchone()
        if row is None:
            raise ApiError(404, "JOB_MISSING", "任务不存在或不可访问。")
        self.input(row)
        return row

    def latest_revision(self, attempt_id: str) -> int:
        return int(self.connection.execute("SELECT COALESCE(MAX(grading_revision),0) FROM grades WHERE attempt_id=?", (attempt_id,)).fetchone()[0])

    def enqueue(self, record: AssessmentRecord, *, base_revision: int, review_id: str | None = None) -> dm.JobRef:
        if record.submission is None or self.latest_revision(record.id) != base_revision:
            raise ApiError(412, "GRADING_REVISION_CONFLICT", "评分版本已改变，请重新读取结果并比较。")
        previous = self.latest_job(record.id)
        if previous is not None and previous["status"] in {"queued", "running", "awaiting_approval"}:
            raise ApiError(409, "GRADING_IN_PROGRESS", "已有评分任务正在进行。")
        value = GradeJobInput(workspace_id=self.workspace_id, attempt_id=record.id, assignment_sha256=metadata_sha256(record.assignment),
            submission_sha256=metadata_sha256(record.submission), grading_revision=base_revision + 1, base_grading_revision=base_revision, review_id=review_id)
        identifier = uid("job")
        now = utc_now()
        self.connection.execute("INSERT INTO jobs(id,workspace_id,kind,status,revision,input_sha256,input_json,created_at,updated_at) VALUES(?,?,'assessment_grading','queued',1,?,?,?,?)",
            (identifier, self.workspace_id, metadata_sha256(value), canonical_bytes(value).decode(), now, now))
        self.connection.execute("INSERT INTO assessment_grade_jobs(job_id,attempt_id,sequence,grading_revision,base_grading_revision) VALUES(?,?,COALESCE((SELECT MAX(sequence)+1 FROM assessment_grade_jobs WHERE attempt_id=?),1),?,?)",
            (identifier, record.id, record.id, base_revision + 1, base_revision))
        self.event(identifier, "queued", 1)
        return dm.JobRef(id=identifier, status="queued")

    def sign(self, identity: SessionIdentity, record: AssessmentRecord, request: RegradeRequest) -> str:
        actor = self.connection.execute("SELECT * FROM local_sessions WHERE id=? AND workspace_id=? AND role='author' AND revoked_at IS NULL AND expires_at>?", (identity.id, self.workspace_id, utc_now())).fetchone()
        if identity.role != "author" or actor is None:
            raise ApiError(403, "HUMAN_AUTHOR_REQUIRED", "人工复核需要当前有效作者会话明确确认。")
        if record.submission is None:
            raise invalid_snapshot()
        payload = SignedReview(id=uid("review"), workspace_id=self.workspace_id, attempt_id=record.id,
            assignment_sha256=metadata_sha256(record.assignment), submission_sha256=metadata_sha256(record.submission),
            actor_session_id=identity.id, actor_role="author", signed_at=utc_now(), request=request)
        self.connection.execute("INSERT OR IGNORE INTO grading_signing_keys(workspace_id,secret) VALUES(?,?)", (self.workspace_id, secrets.token_bytes(32)))
        key = self.connection.execute("SELECT secret FROM grading_signing_keys WHERE workspace_id=?", (self.workspace_id,)).fetchone()[0]
        signature = hmac.new(key, canonical_bytes(payload), hashlib.sha256).hexdigest()
        self.connection.execute("INSERT INTO assessment_manual_reviews(id,workspace_id,attempt_id,payload_json,payload_sha256,signature) VALUES(?,?,?,?,?,?)",
            (payload.id, self.workspace_id, record.id, canonical_bytes(payload).decode(), metadata_sha256(payload), signature))
        return payload.id

    def review(self, identifier: str, record: AssessmentRecord) -> tuple[SignedReview, ManualReviewReceipt]:
        row = self.connection.execute("SELECT * FROM assessment_manual_reviews WHERE id=? AND workspace_id=? AND attempt_id=?", (identifier, self.workspace_id, record.id)).fetchone()
        secret = self.connection.execute("SELECT secret FROM grading_signing_keys WHERE workspace_id=?", (self.workspace_id,)).fetchone()
        try:
            if row is None or secret is None or record.submission is None:
                raise invalid_snapshot()
            payload = SignedReview.model_validate(strict_json(row["payload_json"]))
            expected = hmac.new(secret[0], canonical_bytes(payload), hashlib.sha256).hexdigest()
            if (payload.id != identifier or payload.workspace_id != self.workspace_id or payload.attempt_id != record.id
                    or metadata_sha256(payload) != row["payload_sha256"] or payload.assignment_sha256 != metadata_sha256(record.assignment)
                    or payload.submission_sha256 != metadata_sha256(record.submission) or not hmac.compare_digest(expected, row["signature"])):
                raise invalid_snapshot()
            return payload, ManualReviewReceipt(id=payload.id, actor_role="author", signed_at=payload.signed_at, reason=payload.request.reason,
                question_ids=[item.question_id for item in payload.request.item_reviews], signature=row["signature"], signature_algorithm="hmac-sha256-v1")
        except (ValueError, TypeError, KeyError):
            raise invalid_snapshot() from None

    def load_grade(self, record: AssessmentRecord, revision: int | None = None) -> tuple[dm.GradingResult, GradeAudit] | None:
        revision = self.latest_revision(record.id) if revision is None else revision
        if revision == 0:
            return None
        row = self.connection.execute("SELECT g.*,a.private_json,a.private_sha256,a.result_sha256,a.job_id FROM grades g JOIN assessment_grade_audits a USING(attempt_id,grading_revision) WHERE g.attempt_id=? AND g.grading_revision=?", (record.id, revision)).fetchone()
        try:
            if row is None:
                raise invalid_snapshot()
            result = dm.GradingResult.model_validate(strict_json(row["result_json"]))
            audit = GradeAudit.model_validate(strict_json(row["private_json"]))
            job = self.job(audit.job_id)
            value = self.input(job)
            if (result.attempt_id != record.id or result.grading_revision != revision or result.grading_rules_version != audit.rules_version
                    or [item.question_ref for item in result.items] != record.question_refs or any(item.solution_markdown is not None for item in result.items)
                    or metadata_sha256(result) != row["result_sha256"] or metadata_sha256(audit) != row["private_sha256"]
                    or audit.result_sha256 != row["result_sha256"] or audit.job_id != row["job_id"] or audit.input != value
                    or value.grading_revision != revision or job["status"] != "completed" or result.finalized_at != row["created_at"]
                    or (result.status == "needs_review") != any(item.status == "needs_review" for item in result.items)):
                raise invalid_snapshot()
            from ..application.assessment_content import AssessmentContent
            content = AssessmentContent(self.connection, self.workspace_id)
            questions = content.questions(content.blueprint(record.assessment_ref))
            responses = {item.question_id: item for item in record.responses}
            if (len(audit.traces) != len(record.question_refs)
                    or [trace.question_ref for trace in audit.traces] != record.question_refs
                    or [trace.private_pin for trace in audit.traces] != record.assignment.private_pins
                    or [trace.response for trace in audit.traces] != [responses.get(ref.id) for ref in record.question_refs]
                    or [item.max_score for item in result.items] != [question.max_score for question in questions]
                    or strict_json(job["result_json"]) != {"grading_revision": revision, "result_sha256": row["result_sha256"]}):
                raise invalid_snapshot()
            terminals = self.connection.execute("SELECT * FROM job_events WHERE job_id=? AND type IN ('completed','failed','cancelled')", (job["id"],)).fetchall()
            if (len(terminals) != 1 or terminals[0]["type"] != "completed"
                    or strict_json(terminals[0]["payload_json"]) != {"status": "completed", "revision": job["revision"]}):
                raise invalid_snapshot()
            for review_id in audit.review_ids:
                self.review(review_id, record)
            return result, audit
        except (ValueError, TypeError, KeyError):
            raise invalid_snapshot() from None

    def snapshot(self, row: sqlite3.Row) -> JobSnapshot:
        value = self.input(row)
        record = self.attempts.load(value.attempt_id)
        error = None
        if row["result_json"]:
            parsed = strict_json(row["result_json"])
            if isinstance(parsed, dict) and parsed.get("error"):
                error = dm.ErrorDetail.model_validate(parsed["error"])
        return JobSnapshot(id=row["id"], workspace_id=self.workspace_id, kind="assessment_grading", status=row["status"], revision=row["revision"],
            created_at=row["created_at"], updated_at=row["updated_at"], progress=JobProgress(completed=len(record.question_refs) if row["status"] == "completed" else 0,
            total=len(record.question_refs), label={"queued": "等待评分", "running": "正在评分", "completed": "评分已完成", "failed": "评分失败，原始提交已保留", "cancelled": "评分已取消，原始提交已保留", "awaiting_approval": "等待人工确认"}[row["status"]]), result_refs=[], warnings=[], error=error)

    def terminal(self, row: sqlite3.Row, status: Literal["completed", "cancelled", "failed"], result: dict[str, object] | None = None) -> None:
        if row["status"] in {"completed", "cancelled", "failed"}:
            raise ApiError(409, "JOB_TERMINAL", "任务已结束，不能再次改变终态。")
        self.connection.execute("UPDATE jobs SET status=?,revision=revision+1,result_json=?,lease_owner=NULL,lease_until=NULL,cancel_requested=?,updated_at=? WHERE id=? AND revision=?",
            (status, canonical_bytes(result).decode() if result else None, int(status == "cancelled"), utc_now(), row["id"], row["revision"]))
        self.event(row["id"], status, row["revision"] + 1)
        if status != "completed":
            value = self.input(row)
            self.connection.execute("UPDATE attempts SET status='needs_review',revision=revision+1 WHERE id=? AND workspace_id=? AND status='grading'", (value.attempt_id, self.workspace_id))

    def owned(self, row: sqlite3.Row, lease: GradingLease) -> bool:
        return row["status"] == "running" and row["revision"] == lease.revision and row["lease_owner"] == lease.owner and row["lease_until"] > utc_now()

    def claim(self, row: sqlite3.Row, lease_seconds: int) -> GradingLease:
        value = self.input(row)
        owner = uid("lease")
        self.connection.execute("UPDATE jobs SET status='running',revision=revision+1,lease_owner=?,lease_until=?,retry_count=retry_count+?,updated_at=? WHERE id=? AND revision=?",
            (owner, expires_after(lease_seconds), int(row["status"] == "running"), utc_now(), row["id"], row["revision"]))
        self.connection.execute("UPDATE attempts SET status='grading',revision=revision+1 WHERE id=? AND workspace_id=? AND status<>'grading'", (value.attempt_id, self.workspace_id))
        self.event(row["id"], "running", row["revision"] + 1)
        return GradingLease(row["id"], self.workspace_id, owner, row["revision"] + 1)
