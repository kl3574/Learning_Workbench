"""Assessment-owned immutable assignments, CAS response snapshots and submission outbox."""

from dataclasses import dataclass
import sqlite3
from typing import Literal
from uuid import uuid4

from pydantic import TypeAdapter, model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes, strict_json

from ..application.errors import ApiError
from ..application.assessment_content import FrozenAnswer
from ..assessment_dto import AssessmentPreflight, RecentAttempt
from .database import utc_now


def invalid_snapshot() -> ApiError:
    return ApiError(409, "ASSESSMENT_SNAPSHOT_INVALID", "测验快照完整性校验失败，未替换题目或答案版本。")


class StoredAssignment(dm.StrictModel):
    id: dm.Id
    workspace_id: dm.Id
    assessment_ref: dm.ContentRef
    policy: dm.PolicySnapshot
    question_refs: list[dm.ContentRef]
    private_pins: list[FrozenAnswer]
    preflight: AssessmentPreflight
    created_at: dm.UTC
    deadline_at: dm.UTC | None

    @model_validator(mode="after")
    def exact_allocation(self):
        if (self.assessment_ref.entity != "assessment" or not self.question_refs
                or any(ref.entity != "question" for ref in self.question_refs)
                or len({ref.id for ref in self.question_refs}) != len(self.question_refs)
                or [pin.question_ref for pin in self.private_pins] != self.question_refs
                or [item.question_ref for item in self.preflight.prior_seen.questions] != self.question_refs
                or not self.preflight.startable or self.deadline_at is not None):
            raise ValueError("invalid frozen assessment allocation")
        return self


class StoredSubmission(dm.StrictModel):
    revision: dm.Revision
    submitted_at: dm.UTC
    responses: list[dm.ResponseDraft]
    assignment_sha256: dm.Sha256


@dataclass(frozen=True)
class AssessmentRecord:
    assignment: StoredAssignment
    revision: int
    status: Literal["active", "submitted", "grading", "graded", "needs_review", "abandoned"]
    responses: list[dm.ResponseDraft]
    saved_at: str | None
    submitted_at: str | None
    submission: StoredSubmission | None
    submission_event_id: str | None
    grading_outbox_id: str | None

    @property
    def id(self) -> str:
        return self.assignment.id

    @property
    def workspace_id(self) -> str:
        return self.assignment.workspace_id

    @property
    def assessment_ref(self) -> dm.ContentRef:
        return self.assignment.assessment_ref

    @property
    def question_refs(self) -> list[dm.ContentRef]:
        return self.assignment.question_refs

    @property
    def policy(self) -> dm.PolicySnapshot:
        return self.assignment.policy


class AssessmentRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection = connection
        self.workspace_id = workspace_id

    def create(self, assessment_ref: dm.ContentRef, policy: dm.PolicySnapshot, question_refs: list[dm.ContentRef],
               private_pins: list[FrozenAnswer], preflight: AssessmentPreflight) -> AssessmentRecord:
        assignment = StoredAssignment(id=f"attempt_{uuid4().hex}", workspace_id=self.workspace_id,
            assessment_ref=assessment_ref, policy=policy, question_refs=question_refs, private_pins=private_pins,
            preflight=preflight, created_at=utc_now(), deadline_at=None)
        self.connection.execute(
            "INSERT INTO attempts(id,workspace_id,assessment_id,assessment_revision,mode,policy_json,question_refs_json,"
            "solution_refs_private_json,status,revision,created_at,deadline_at,assessment_sha256,snapshot_sha256,preflight_json,preflight_sha256) "
            "VALUES(?,?,?,?,?,?,?,?,'active',1,?,NULL,?,?,?,?)",
            (assignment.id, self.workspace_id, assessment_ref.id, assessment_ref.revision, policy.mode,
             canonical_bytes(policy).decode(), canonical_bytes([ref.model_dump(mode="json") for ref in question_refs]).decode(),
             canonical_bytes([pin.model_dump(mode="json") for pin in private_pins]).decode(), assignment.created_at,
             assessment_ref.sha256, metadata_sha256(assignment), canonical_bytes(preflight).decode(), metadata_sha256(preflight)),
        )
        return self.load(assignment.id)

    def load(self, identifier: str) -> AssessmentRecord:
        """Read only; Policy may use this before the submission event is linked in the same transaction."""
        row = self.connection.execute("SELECT * FROM attempts WHERE id=? AND workspace_id=?", (identifier, self.workspace_id)).fetchone()
        if row is None:
            raise ApiError(404, "ATTEMPT_MISSING", "测验作答不存在或不可访问。")
        try:
            preflight = AssessmentPreflight.model_validate(strict_json(row["preflight_json"]))
            assignment = StoredAssignment(id=row["id"], workspace_id=row["workspace_id"],
                assessment_ref=dm.ContentRef(entity="assessment", id=row["assessment_id"], revision=row["assessment_revision"], sha256=row["assessment_sha256"]),
                policy=dm.PolicySnapshot.model_validate(strict_json(row["policy_json"])),
                question_refs=TypeAdapter(list[dm.ContentRef]).validate_python(strict_json(row["question_refs_json"])),
                private_pins=TypeAdapter(list[FrozenAnswer]).validate_python(strict_json(row["solution_refs_private_json"])),
                preflight=preflight, created_at=row["created_at"], deadline_at=row["deadline_at"])
            if (metadata_sha256(assignment) != row["snapshot_sha256"] or metadata_sha256(preflight) != row["preflight_sha256"]
                    or assignment.policy.mode != row["mode"]):
                raise invalid_snapshot()
            assigned = {ref.id for ref in assignment.question_refs}
            responses_by_id = {}
            for response in self.connection.execute("SELECT * FROM responses WHERE attempt_id=?", (identifier,)):
                value = dm.ResponseDraft.model_validate(strict_json(response["answer_json"]))
                if (value.question_id != response["question_id"] or value.question_id not in assigned
                        or response["draft_revision"] > row["revision"] or response["updated_at"] != row["responses_saved_at"]):
                    raise invalid_snapshot()
                responses_by_id[value.question_id] = value
            responses = [responses_by_id[ref.id] for ref in assignment.question_refs if ref.id in responses_by_id]
            saved_at: str | None = TypeAdapter(dm.UTC | None).validate_python(row["responses_saved_at"])
            if responses and saved_at is None:
                raise invalid_snapshot()
            submission = None
            if row["status"] not in {"active", "submitted", "grading", "graded", "needs_review", "abandoned"}:
                raise invalid_snapshot()
            if row["submission_json"] is not None:
                submission = StoredSubmission.model_validate(strict_json(row["submission_json"]))
                persisted = TypeAdapter(list[dm.ResponseDraft]).validate_python(strict_json(row["submitted_responses_json"]))
                if (metadata_sha256(submission) != row["submission_sha256"] or submission.assignment_sha256 != row["snapshot_sha256"]
                        or submission.responses != responses or persisted != responses or submission.submitted_at != row["submitted_at"]
                        or submission.revision > row["revision"] or row["status"] in {"active", "abandoned"} or row["submit_reason"] != "user"):
                    raise invalid_snapshot()
            elif (row["status"] not in {"active", "abandoned"} or any(row[name] is not None for name in
                    ("submission_sha256", "submitted_responses_json", "submitted_at", "submit_reason", "submission_event_id", "grading_outbox_id"))):
                raise invalid_snapshot()
            return AssessmentRecord(assignment, row["revision"], row["status"], responses, saved_at, row["submitted_at"],
                                    submission, row["submission_event_id"], row["grading_outbox_id"])
        except (ValueError, TypeError, KeyError):
            raise invalid_snapshot() from None

    @staticmethod
    def expect_active(record: AssessmentRecord, expected_revision: int) -> None:
        if record.status != "active":
            raise ApiError(409, "ATTEMPT_NOT_ACTIVE", "测验已提交或放弃，不能覆盖最后作答。")
        if record.revision != expected_revision:
            raise ApiError(412, "REVISION_CONFLICT", "测验作答已改变，请读取并比较本机与服务端内容。")

    def save(self, record: AssessmentRecord, responses: list[dm.ResponseDraft]) -> AssessmentRecord:
        self.connection.execute("DELETE FROM responses WHERE attempt_id=?", (record.id,))
        now = utc_now()
        for response in responses:
            self.connection.execute("INSERT INTO responses(attempt_id,question_id,draft_revision,answer_json,updated_at) VALUES(?,?,?,?,?)",
                (record.id, response.question_id, record.revision + 1, canonical_bytes(response).decode(), now))
        changed = self.connection.execute("UPDATE attempts SET revision=revision+1,responses_saved_at=? WHERE id=? AND workspace_id=? AND revision=? AND status='active'",
            (now, record.id, self.workspace_id, record.revision))
        if changed.rowcount != 1:
            raise invalid_snapshot()
        return self.load(record.id)

    def submit(self, record: AssessmentRecord) -> AssessmentRecord:
        snapshot = StoredSubmission(revision=record.revision + 1, submitted_at=utc_now(), responses=record.responses,
                                    assignment_sha256=metadata_sha256(record.assignment))
        changed = self.connection.execute(
            "UPDATE attempts SET revision=?,status='submitted',submitted_at=?,submit_reason='user',submitted_responses_json=?,submission_json=?,submission_sha256=? "
            "WHERE id=? AND workspace_id=? AND revision=? AND status='active'",
            (snapshot.revision, snapshot.submitted_at, canonical_bytes([item.model_dump(mode="json") for item in record.responses]).decode(),
             canonical_bytes(snapshot).decode(), metadata_sha256(snapshot), record.id, self.workspace_id, record.revision))
        if changed.rowcount != 1:
            raise invalid_snapshot()
        return self.load(record.id)

    def link_submission(self, record: AssessmentRecord, event_id: str) -> AssessmentRecord:
        if record.submission is None or record.submission_event_id is not None or record.grading_outbox_id is not None:
            raise invalid_snapshot()
        outbox_id = f"outbox_{uuid4().hex}"
        payload = self.grading_request(record, event_id)
        self.connection.execute("INSERT INTO outbox(id,event_type,payload_json) VALUES(?,'assessment.grading.requested',?)",
                                (outbox_id, canonical_bytes(payload).decode()))
        self.connection.execute("UPDATE attempts SET submission_event_id=?,grading_outbox_id=? WHERE id=? AND workspace_id=?",
                                (event_id, outbox_id, record.id, self.workspace_id))
        return self.load(record.id)

    @staticmethod
    def grading_request(record: AssessmentRecord, event_id: str) -> dict[str, object]:
        if record.submission is None:
            raise invalid_snapshot()
        return {"workspace_id": record.workspace_id, "attempt_id": record.id, "submission_sha256": metadata_sha256(record.submission),
                "assignment_sha256": metadata_sha256(record.assignment), "event_id": event_id}

    def validate_outbox(self, record: AssessmentRecord) -> None:
        if record.submission is None:
            return
        row = self.connection.execute("SELECT * FROM outbox WHERE id=?", (record.grading_outbox_id,)).fetchone()
        if (row is None or record.submission_event_id is None or row["event_type"] != "assessment.grading.requested"
                or strict_json(row["payload_json"]) != self.grading_request(record, record.submission_event_id)):
            raise invalid_snapshot()

    def abandon(self, record: AssessmentRecord) -> AssessmentRecord:
        result = self.connection.execute("UPDATE attempts SET status='abandoned',revision=revision+1 WHERE id=? AND workspace_id=? AND revision=? AND status='active'",
                                         (record.id, self.workspace_id, record.revision))
        if result.rowcount != 1:
            raise invalid_snapshot()
        return self.load(record.id)

    def recent(self, ref: dm.ContentRef) -> tuple[list[RecentAttempt], bool]:
        rows = self.connection.execute("SELECT id FROM attempts WHERE workspace_id=? AND assessment_id=? AND assessment_revision=? ORDER BY created_at DESC,id DESC LIMIT 11",
                                       (self.workspace_id, ref.id, ref.revision)).fetchall()
        result = []
        for row in rows[:10]:
            value = self.load(row["id"])
            if value.assessment_ref != ref:
                raise invalid_snapshot()
            result.append(RecentAttempt(id=value.id, revision=value.revision, status=value.status, mode=value.policy.mode,
                                        created_at=value.assignment.created_at, submitted_at=value.submitted_at))
        return result, len(rows) > 10

    def history_ids(self) -> list[str]:
        return [row["id"] for row in self.connection.execute("SELECT id FROM attempts WHERE workspace_id=? ORDER BY created_at,id", (self.workspace_id,))]

    def replay_target(self, route: str, key: str | None) -> str | None:
        """Resolve a receipt's sealed allocation, never trust cached response.id."""
        row = self.connection.execute(
            "SELECT * FROM idempotency WHERE actor=? AND route=? AND key=? AND (expires_at IS NULL OR expires_at>?)",
            (self.workspace_id, route, key, utc_now()),
        ).fetchone()
        if row is None:
            return None
        binding = self.connection.execute(
            "SELECT * FROM assessment_receipts WHERE workspace_id=? AND route=? AND key=?",
            (self.workspace_id, route, key),
        ).fetchone()
        try:
            result = strict_json(row["result_json"])
            if (binding is None or not isinstance(result, dict)
                    or binding["request_sha256"] != row["request_sha256"]
                    or binding["receipt_created_at"] != row["created_at"]
                    or binding["result_sha256"] != sha256_bytes(canonical_bytes(result))):
                raise invalid_snapshot()
            target = TypeAdapter(dm.Id).validate_python(binding["attempt_id"])
            record = self.load(target)
            if binding["assignment_sha256"] != metadata_sha256(record.assignment):
                raise invalid_snapshot()
            return target
        except (TypeError, ValueError, KeyError):
            raise invalid_snapshot() from None

    def seal_receipt(self, route: str, key: str | None, record: AssessmentRecord, result: dict[str, object]) -> None:
        """Seal this actual idempotency instance in the same operation transaction.

        Its FK follows expiration deletion; reusing an expired key makes a new
        instance and does not retain the former allocation as a permanent lock.
        """
        row = self.connection.execute("SELECT * FROM idempotency WHERE actor=? AND route=? AND key=?",
                                      (self.workspace_id, route, key)).fetchone()
        if row is None or strict_json(row["result_json"]) != result:
            raise invalid_snapshot()
        self.connection.execute(
            "INSERT INTO assessment_receipts(workspace_id,route,key,receipt_created_at,request_sha256,attempt_id,assignment_sha256,result_sha256) "
            "VALUES(?,?,?,?,?,?,?,?)", (self.workspace_id, route, key, row["created_at"], row["request_sha256"], record.id,
                                        metadata_sha256(record.assignment), sha256_bytes(canonical_bytes(result))))
