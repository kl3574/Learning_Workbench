"""Practice assignment snapshots, CAS drafts, immutable submissions and exposures."""

from dataclasses import dataclass
import sqlite3
from typing import Literal
from uuid import uuid4

from pydantic import TypeAdapter

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes, strict_json

from ..application.errors import ApiError
from ..application.learning import validate_practice_event
from ..application.practice_content import FrozenSolution
from ..practice_dto import PracticeAssistance, PracticeAssistanceView
from .database import utc_now


def invalid_snapshot() -> ApiError:
    return ApiError(409, "PRACTICE_SNAPSHOT_INVALID", "练习会话完整性校验失败，未读取或替换其他答案版本。")


class StoredSubmission(dm.StrictModel):
    revision: dm.Revision
    submitted_at: dm.UTC
    responses: list[dm.ResponseDraft]
    results: list[dm.ItemGrade]
    exposure_event_ids: list[dm.Id]
    assisted: bool
    assistance: list[PracticeAssistance]


class StoredHelp(dm.StrictModel):
    markdown: dm.Text
    rule_version: str | None
    review_status: Literal["draft", "needs_review", "approved"] | None


@dataclass(frozen=True)
class PracticeRecord:
    id: str
    revision: int
    status: Literal["active", "submitted", "abandoned"]
    practice_ref: dm.ContentRef
    question_refs: list[dm.ContentRef]
    solution_refs: list[FrozenSolution]
    responses: list[dm.ResponseDraft]
    submission: StoredSubmission | None


def assignment_bytes(practice_ref: dm.ContentRef, questions: list[dm.ContentRef], solutions: list[FrozenSolution]) -> bytes:
    return canonical_bytes({"practice_ref": practice_ref.model_dump(mode="json"),
                            "questions": [ref.model_dump(mode="json") for ref in questions],
                            "solutions": [ref.model_dump(mode="json") for ref in solutions]})


class PracticeRepository:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection = connection
        self.workspace_id = workspace_id

    def create(self, practice_ref: dm.ContentRef, questions: list[dm.ContentRef], solutions: list[FrozenSolution]) -> str:
        identifier = f"practice_session_{uuid4().hex}"
        self.connection.execute(
            "INSERT INTO practice_sessions(id,workspace_id,practice_id,practice_revision,question_refs_json,solution_refs_json,status,revision,created_at,practice_sha256,snapshot_sha256) "
            "VALUES(?,?,?,?,?,?,'active',1,?,?,?)",
            (identifier, self.workspace_id, practice_ref.id, practice_ref.revision,
             canonical_bytes([ref.model_dump(mode="json") for ref in questions]).decode(),
             canonical_bytes([ref.model_dump(mode="json") for ref in solutions]).decode(), utc_now(), practice_ref.sha256,
             sha256_bytes(assignment_bytes(practice_ref, questions, solutions))),
        )
        return identifier

    def load(self, identifier: str) -> PracticeRecord:
        row = self.connection.execute("SELECT * FROM practice_sessions WHERE id=? AND workspace_id=?", (identifier, self.workspace_id)).fetchone()
        if row is None:
            raise ApiError(404, "PRACTICE_SESSION_MISSING", "练习会话不存在或不可访问。")
        try:
            practice_ref = dm.ContentRef(entity="practice_set", id=row["practice_id"], revision=row["practice_revision"], sha256=row["practice_sha256"])
            questions = TypeAdapter(list[dm.ContentRef]).validate_python(strict_json(row["question_refs_json"]))
            solutions = TypeAdapter(list[FrozenSolution]).validate_python(strict_json(row["solution_refs_json"]))
            if (not questions or len({ref.id for ref in questions}) != len(questions)
                    or any(ref.entity != "question" for ref in questions)
                    or [ref.question_ref for ref in solutions] != questions
                    or sha256_bytes(assignment_bytes(practice_ref, questions, solutions)) != row["snapshot_sha256"]):
                raise invalid_snapshot()
            responses_by_id = {}
            for response in self.connection.execute("SELECT * FROM practice_responses WHERE session_id=?", (identifier,)):
                value = dm.ResponseDraft.model_validate(strict_json(response["answer_json"]))
                if value.question_id != response["question_id"] or value.question_id not in {ref.id for ref in questions}:
                    raise invalid_snapshot()
                responses_by_id[value.question_id] = value
            responses = [responses_by_id[ref.id] for ref in questions if ref.id in responses_by_id]
            submission = None
            if row["submission_json"] is not None:
                submission = StoredSubmission.model_validate(strict_json(row["submission_json"]))
                if (metadata_sha256(submission) != row["submission_sha256"] or row["status"] != "submitted"
                        or submission.responses != responses or submission.revision > row["revision"]
                        or [item.question_ref for item in submission.results] != questions):
                    raise invalid_snapshot()
            elif row["status"] == "submitted" or row["submission_sha256"] is not None:
                raise invalid_snapshot()
            return PracticeRecord(identifier, row["revision"], row["status"], practice_ref, questions, solutions, responses, submission)
        except (ValueError, TypeError, KeyError):
            raise invalid_snapshot() from None

    @staticmethod
    def expect(record: PracticeRecord, revision: int, *, active: bool = False) -> None:
        if record.revision != revision:
            raise ApiError(412, "REVISION_CONFLICT", "练习已更新，请读取最新会话并比较本机草稿。")
        if active and record.status != "active" or record.status == "abandoned":
            raise ApiError(409, "PRACTICE_NOT_ACTIVE", "练习已提交或结束，不能覆盖已保存的作答快照。")

    def bump(self, record: PracticeRecord) -> int:
        result = self.connection.execute("UPDATE practice_sessions SET revision=revision+1 WHERE id=? AND workspace_id=? AND revision=?", (record.id, self.workspace_id, record.revision))
        if result.rowcount != 1:
            raise ApiError(412, "REVISION_CONFLICT", "练习已更新，请读取最新会话后重试。")
        return record.revision + 1

    def save_responses(self, record: PracticeRecord, responses: list[dm.ResponseDraft]) -> tuple[int, str]:
        self.connection.execute("DELETE FROM practice_responses WHERE session_id=?", (record.id,))
        now = utc_now()
        for response in responses:
            self.connection.execute("INSERT INTO practice_responses(session_id,question_id,answer_json,updated_at) VALUES(?,?,?,?)", (record.id, response.question_id, canonical_bytes(response).decode(), now))
        return self.bump(record), now

    def exposure_facts(self, record: PracticeRecord, questions: list[dm.QuestionPublic]) -> tuple[list[str], list[PracticeAssistance]]:
        assigned = {question.id: question for question in questions}
        refs = {ref.id: ref for ref in record.question_refs}
        assistance = {ref.id: PracticeAssistance(question_id=ref.id, highest_hint_level=0, solution_revealed=False) for ref in record.question_refs}
        events = []
        rows = self.connection.execute(
            "SELECT p.question_id,p.kind,p.level,e.event_id,e.workspace_id,e.kind AS exposure_kind,e.question_ref_json,e.exposure_group "
            "FROM practice_exposures p JOIN exposures e ON e.id=p.exposure_id WHERE p.session_id=? ORDER BY e.occurred_at,e.id", (record.id,),
        )
        for row in rows:
            try:
                ref = dm.ContentRef.model_validate(strict_json(row["question_ref_json"]))
                if (row["workspace_id"] != self.workspace_id or refs.get(row["question_id"]) != ref
                        or row["kind"] != row["exposure_kind"] or row["exposure_group"] != assigned[ref.id].exposure_group):
                    raise invalid_snapshot()
                validate_practice_event(self.connection, self.workspace_id, row["event_id"],
                    "hint_revealed" if row["kind"] == "hint" else "solution_revealed", ref, record.id)
                previous = assistance[ref.id]
                if row["kind"] == "hint":
                    assistance[ref.id] = PracticeAssistance(question_id=ref.id, highest_hint_level=max(previous.highest_hint_level, row["level"]), solution_revealed=previous.solution_revealed)
                else:
                    assistance[ref.id] = PracticeAssistance(question_id=ref.id, highest_hint_level=previous.highest_hint_level, solution_revealed=True)
                events.append(row["event_id"])
            except (ValueError, TypeError, KeyError):
                raise invalid_snapshot() from None
        from .practice_model_help_repository import PracticeModelHelpRepository
        events.extend(item.event_id for item in PracticeModelHelpRepository(self.connection, self.workspace_id).facts(record, questions))
        return events, [assistance[ref.id] for ref in record.question_refs]

    def assistance_view(self, record: PracticeRecord, questions: list[dm.QuestionPublic],
                        assistance: list[PracticeAssistance], event_ids: list[str]) -> list[PracticeAssistanceView]:
        from .practice_model_help_repository import PracticeModelHelpRepository
        model_questions = {item.answer.practice.question_ref.id
            for item in PracticeModelHelpRepository(self.connection, self.workspace_id).facts(record, questions)
            if item.event_id in event_ids}
        return [PracticeAssistanceView(**item.model_dump(), model_help_received=item.question_id in model_questions)
                for item in assistance]

    def help(self, record: PracticeRecord, question_id: str, kind: Literal["hint", "solution"], level: int) -> tuple[str, StoredHelp] | None:
        row = self.connection.execute(
            "SELECT p.*,e.event_id,e.workspace_id FROM practice_exposures p JOIN exposures e ON e.id=p.exposure_id "
            "WHERE p.session_id=? AND p.question_id=? AND p.kind=? AND p.level=?", (record.id, question_id, kind, level),
        ).fetchone()
        if row is None:
            return None
        try:
            value = StoredHelp.model_validate(strict_json(row["help_json"]))
            if (row["workspace_id"] != self.workspace_id or metadata_sha256(value) != row["help_sha256"]
                    or kind == "hint" and (value.rule_version is None or value.review_status is not None)
                    or kind == "solution" and (value.rule_version is not None or value.review_status is None)):
                raise invalid_snapshot()
            return row["event_id"], value
        except (ValueError, TypeError, KeyError):
            raise invalid_snapshot() from None

    def expose(self, record: PracticeRecord, question: dm.QuestionPublic, question_ref: dm.ContentRef,
               kind: Literal["hint", "solution"], level: int, event_id: str, help: StoredHelp) -> int:
        exposure_id = f"exposure_{uuid4().hex}"
        self.connection.execute("INSERT INTO exposures(id,workspace_id,event_id,exposure_group,question_ref_json,kind,occurred_at) VALUES(?,?,?,?,?,?,?)",
            (exposure_id, self.workspace_id, event_id, question.exposure_group, canonical_bytes(question_ref).decode(), kind, utc_now()))
        self.connection.execute("INSERT INTO practice_exposures(session_id,question_id,kind,level,exposure_id,help_json,help_sha256) VALUES(?,?,?,?,?,?,?)",
            (record.id, question.id, kind, level, exposure_id, canonical_bytes(help).decode(), metadata_sha256(help)))
        return self.bump(record)

    def submit(self, record: PracticeRecord, snapshot: StoredSubmission, *,
               grading_rules_version: str = "not_graded_m3_1", grading_audit_sha256: str | None = None) -> str:
        result = self.connection.execute(
            "UPDATE practice_sessions SET status='submitted',revision=?,submission_json=?,submission_sha256=? WHERE id=? AND workspace_id=? AND revision=? AND status='active'",
            (snapshot.revision, canonical_bytes(snapshot).decode(), metadata_sha256(snapshot), record.id, self.workspace_id, record.revision),
        )
        if result.rowcount != 1:
            raise ApiError(412, "REVISION_CONFLICT", "练习已更新，请读取最新会话后重试。")
        payload = {"workspace_id": self.workspace_id, "practice_session_id": record.id,
                   "practice_ref": record.practice_ref.model_dump(mode="json"), "revision": snapshot.revision,
                   "status": "graded" if all(item.status == "graded" for item in snapshot.results) else "needs_review",
                   "grading_rules_version": grading_rules_version}
        if grading_audit_sha256 is not None:
            payload.update(grading_audit_sha256=grading_audit_sha256, submission_sha256=metadata_sha256(snapshot))
        outbox_id = f"outbox_{uuid4().hex}"
        self.connection.execute("INSERT INTO outbox(id,event_type,payload_json) VALUES(?,?,?)",
                               (outbox_id, "practice.submitted", canonical_bytes(payload).decode()))
        return outbox_id
