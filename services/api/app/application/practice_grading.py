"""Private deterministic practice audit, separate from public submission DTOs.

Legacy M3.1 submissions keep their original canonical bytes and ungraded label.
This module never promotes practice grades to independent learning evidence.
"""

from typing import Literal

from pydantic import model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes, strict_json

from ..infrastructure.practice_repository import PracticeRecord, PracticeRepository, StoredSubmission, invalid_snapshot
from .assessment_content import FrozenAnswer
from .grading_rules import GradingBindingError, PrivateGradeTrace, RULES_VERSION, grade_item
from .practice_content import FrozenSolution, PracticeContent


class PracticeGradeEntry(dm.StrictModel):
    question_ref: dm.ContentRef
    frozen_solution: FrozenSolution
    response_sha256: dm.Sha256
    result: dm.ItemGrade
    private_trace: PrivateGradeTrace | None
    missing_reason: Literal["frozen_solution_missing"] | None

    @model_validator(mode="after")
    def bound_entry(self):
        if self.question_ref != self.frozen_solution.question_ref or self.result.question_ref != self.question_ref:
            raise ValueError("practice grading entry does not bind its question")
        missing = self.frozen_solution.solution_revision is None
        if missing != (self.private_trace is None) or missing != (self.missing_reason is not None):
            raise ValueError("missing frozen solution must stay explicitly ungraded")
        if missing and (self.result.status != "needs_review" or self.result.score is not None):
            raise ValueError("missing frozen answer cannot produce a score")
        if self.result.solution_markdown is not None:
            raise ValueError("practice result cannot release a solution")
        if self.private_trace is not None:
            trace = self.private_trace
            if (trace.question_ref != self.question_ref or trace.private_pin.question_ref != self.question_ref
                    or trace.private_pin.solution_revision != self.frozen_solution.solution_revision
                    or trace.private_pin.sha256 != self.frozen_solution.sha256
                    or response_hash(trace.response) != self.response_sha256):
                raise ValueError("private trace must bind the frozen input")
        return self


class PracticeGradeAudit(dm.StrictModel):
    workspace_id: dm.Id
    session_id: dm.Id
    practice_ref: dm.ContentRef
    submission_sha256: dm.Sha256
    grading_rules_version: str
    entries: list[PracticeGradeEntry]


def response_hash(response: dm.ResponseDraft | None) -> str:
    return sha256_bytes(canonical_bytes(response))


def grade_practice(content: PracticeContent, record: PracticeRecord,
                   questions: list[dm.QuestionPublic]) -> list[PracticeGradeEntry]:
    responses = {response.question_id: response for response in record.responses}
    entries = []
    for ref, question, frozen in zip(record.question_refs, questions, record.solution_refs, strict=True):
        response = responses.get(ref.id)
        trace = None
        missing_reason: Literal["frozen_solution_missing"] | None = None
        if frozen.solution_revision is None:
            result = dm.ItemGrade(question_ref=ref, score=None, max_score=question.max_score, status="needs_review",
                feedback_markdown="开始本次练习时没有可用的固定答案；作答已保留，需要人工复核。无分数不等于零分。",
                solution_markdown=None)
            missing_reason = "frozen_solution_missing"
        else:
            # The older Practice pin has no separate review-status field. Its
            # immutable hash binds that field within the exact private object.
            solution = content.solution(frozen)
            if frozen.sha256 is None:
                raise invalid_snapshot()
            pin = FrozenAnswer(question_ref=ref, solution_revision=frozen.solution_revision,
                               sha256=frozen.sha256, review_status=solution.review_status)
            try:
                decision = grade_item(question_ref=ref, question=question, pin=pin, solution=solution, response=response)
            except GradingBindingError:
                raise invalid_snapshot() from None
            result, trace = decision.item_grade, decision.private_trace
        entries.append(PracticeGradeEntry(question_ref=ref, frozen_solution=frozen, response_sha256=response_hash(response),
            result=result, private_trace=trace, missing_reason=missing_reason))
    return entries


def build_audit(workspace_id: str, record: PracticeRecord, snapshot: StoredSubmission,
                entries: list[PracticeGradeEntry]) -> PracticeGradeAudit:
    return PracticeGradeAudit(workspace_id=workspace_id, session_id=record.id, practice_ref=record.practice_ref,
        submission_sha256=metadata_sha256(snapshot), grading_rules_version=RULES_VERSION, entries=entries)


def persist_audit(repository: PracticeRepository, audit: PracticeGradeAudit, outbox_id: str,
                  submitted_at: str) -> None:
    repository.connection.execute(
        "INSERT INTO practice_grading_audits(session_id,workspace_id,outbox_id,audit_json,audit_sha256,created_at) "
        "VALUES(?,?,?,?,?,?)", (audit.session_id, audit.workspace_id, outbox_id, canonical_bytes(audit).decode(),
                                metadata_sha256(audit), submitted_at))


def validate_audit(repository: PracticeRepository, record: PracticeRecord,
                   questions: list[dm.QuestionPublic]) -> None:
    row = repository.connection.execute("SELECT * FROM practice_grading_audits WHERE session_id=?", (record.id,)).fetchone()
    outboxes = repository.connection.execute(
        "SELECT * FROM outbox WHERE event_type='practice.submitted' "
        "AND json_extract(payload_json,'$.practice_session_id')=?", (record.id,)).fetchall()
    if record.submission is None:
        if row is not None or outboxes:
            raise invalid_snapshot()
        return
    try:
        if len(outboxes) != 1:
            raise invalid_snapshot()
        outbox = outboxes[0]
        payload = strict_json(outbox["payload_json"])
        if row is None:
            # An old result stays explicitly ungraded; no new rules are applied
            # to it during reads or a replay of its original submit request.
            expected = {"workspace_id": repository.workspace_id, "practice_session_id": record.id,
                "practice_ref": record.practice_ref.model_dump(mode="json"), "revision": record.submission.revision,
                "status": "needs_review", "grading_rules_version": "not_graded_m3_1"}
            if payload != expected or any(item.status != "needs_review" or item.score is not None for item in record.submission.results):
                raise invalid_snapshot()
            return
        audit = PracticeGradeAudit.model_validate(strict_json(row["audit_json"]))
        digest = metadata_sha256(audit)
        if (row["workspace_id"] != repository.workspace_id or audit.workspace_id != repository.workspace_id
                or audit.session_id != record.id or audit.practice_ref != record.practice_ref
                or row["audit_sha256"] != digest or row["outbox_id"] != outbox["id"]
                or audit.submission_sha256 != metadata_sha256(record.submission)
                or row["created_at"] != record.submission.submitted_at
                or [entry.question_ref for entry in audit.entries] != record.question_refs
                or [entry.frozen_solution for entry in audit.entries] != record.solution_refs
                or [entry.result for entry in audit.entries] != record.submission.results):
            raise invalid_snapshot()
        expected = {"workspace_id": repository.workspace_id, "practice_session_id": record.id,
            "practice_ref": record.practice_ref.model_dump(mode="json"), "revision": record.submission.revision,
            "status": "graded" if all(item.status == "graded" for item in record.submission.results) else "needs_review",
            "grading_rules_version": audit.grading_rules_version, "grading_audit_sha256": digest,
            "submission_sha256": audit.submission_sha256}
        if payload != expected:
            raise invalid_snapshot()
        responses = {response.question_id: response for response in record.submission.responses}
        for entry, question in zip(audit.entries, questions, strict=True):
            if (entry.response_sha256 != response_hash(responses.get(question.id)) or entry.result.max_score != question.max_score
                    or entry.private_trace is not None and entry.private_trace.rules_version != audit.grading_rules_version):
                raise invalid_snapshot()
    except (ValueError, TypeError, KeyError):
        raise invalid_snapshot() from None
