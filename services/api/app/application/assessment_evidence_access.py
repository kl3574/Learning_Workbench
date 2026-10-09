"""Assessment-owned verified witnesses for Learning, without grading/qualification recursion."""

from dataclasses import dataclass
import sqlite3
from typing import Literal

from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256

from ..assessment_dto import PriorSeen
from ..infrastructure.assessment_repository import AssessmentRepository, invalid_snapshot
from ..infrastructure.grading_repository import GradingRepository
from .assessment_content import FrozenAnswer
from .errors import ApiError
from .policy import Policy


class SubmissionWitness(dm.StrictModel):
    workspace_id: dm.Id
    attempt_id: dm.Id
    assessment_ref: dm.ContentRef
    assignment_sha256: dm.Sha256
    submission_sha256: dm.Sha256
    submission_event_id: dm.Id
    created_at: dm.UTC
    submitted_at: dm.UTC
    mode: Literal["independent", "open_book", "assisted"]
    question_refs: list[dm.ContentRef]
    private_pins: list[FrozenAnswer]
    prior_seen: PriorSeen


class CompletedGradeWitness(dm.StrictModel):
    workspace_id: dm.Id
    attempt_id: dm.Id
    assessment_ref: dm.ContentRef
    assignment_sha256: dm.Sha256
    submission_sha256: dm.Sha256
    result: dm.GradingResult
    result_sha256: dm.Sha256
    job_id: dm.Id


class GradeKey(dm.StrictModel):
    workspace_id: dm.Id
    attempt_id: dm.Id
    grading_revision: dm.Revision


def submission_witness(connection: sqlite3.Connection, workspace_id: str, attempt_id: str) -> SubmissionWitness:
    from .learning import validate_test_submitted
    Policy(connection, workspace_id).check("attempt_read", attempt_id=attempt_id)
    repository = AssessmentRepository(connection, workspace_id)
    record = repository.load(attempt_id)
    if record.submission is None or record.submission_event_id is None:
        raise ApiError(409, "ATTEMPT_NOT_SUBMITTED", "未提交的作答没有固定资格前提。")
    repository.validate_outbox(record)
    validate_test_submitted(connection, workspace_id, record.submission_event_id, record.assessment_ref, attempt_id)
    return SubmissionWitness(workspace_id=workspace_id, attempt_id=attempt_id, assessment_ref=record.assessment_ref,
        assignment_sha256=metadata_sha256(record.assignment), submission_sha256=metadata_sha256(record.submission),
        submission_event_id=record.submission_event_id, created_at=record.assignment.created_at,
        submitted_at=record.submission.submitted_at, mode=record.policy.mode, question_refs=record.question_refs,
        private_pins=record.assignment.private_pins, prior_seen=record.assignment.preflight.prior_seen)


def completed_grade_witness(connection: sqlite3.Connection, workspace_id: str, attempt_id: str,
                            grading_revision: int) -> CompletedGradeWitness:
    submission = submission_witness(connection, workspace_id, attempt_id)
    repository = GradingRepository(connection, workspace_id)
    grade = repository.load_grade(repository.attempts.load(attempt_id), grading_revision)
    if grade is None:
        raise invalid_snapshot()
    result, audit = grade
    return CompletedGradeWitness(workspace_id=workspace_id, attempt_id=attempt_id,
        assessment_ref=submission.assessment_ref, assignment_sha256=submission.assignment_sha256,
        submission_sha256=submission.submission_sha256, result=result,
        result_sha256=metadata_sha256(result), job_id=audit.job_id)


def completed_grade_keys(connection: sqlite3.Connection, workspace_id: str,
                         attempt_id: str | None = None) -> tuple[GradeKey, ...]:
    if attempt_id is None:
        Policy(connection, workspace_id).check("subject_read")
    else:
        Policy(connection, workspace_id).check("attempt_read", attempt_id=attempt_id)
    return tuple(GradeKey(workspace_id=workspace_id, attempt_id=row["attempt_id"], grading_revision=row["grading_revision"])
        for row in connection.execute("SELECT g.attempt_id,g.grading_revision FROM grades g JOIN attempts a ON a.id=g.attempt_id "
            "WHERE a.workspace_id=? AND (? IS NULL OR a.id=?) ORDER BY g.attempt_id,g.grading_revision",
            (workspace_id, attempt_id, attempt_id)))


def verify_applicability_pins(connection: sqlite3.Connection, workspace_id: str,
                              attempt_id: str) -> SubmissionWitness:
    """Verify every original private pin with Content; return metadata only."""
    from .assessment_content import AssessmentContent

    witness = submission_witness(connection, workspace_id, attempt_id)
    content = AssessmentContent(connection, workspace_id)
    for pin in witness.private_pins:
        content.solution(pin)
    return witness


# Bound the raw grade prefix before any workspace or recovery-progress filter.
# The grades owner retains immutable identities; this internal scan is not a DTO.
GRADE_RECOVERY_SCAN_ROWS = 32


@dataclass(frozen=True)
class GradeRecoveryScan:
    after_sequence: int
    ceiling: int
    through_sequence: int
    keys: tuple[tuple[int, GradeKey], ...]


def completed_grade_recovery_scan(connection: sqlite3.Connection, workspace_id: str,
                                  *, after_sequence: int, ceiling: int) -> GradeRecoveryScan:
    if type(after_sequence) is not int or type(ceiling) is not int or min(after_sequence, ceiling) < 0:
        raise ValueError('Invalid internal grade recovery sequence')
    Policy(connection, workspace_id).check('subject_read')
    if after_sequence >= ceiling:
        after_sequence = 0
        ceiling = connection.execute('SELECT COALESCE(MAX(rowid),0) FROM grades').fetchone()[0]
    # LIMIT is inside the rowid range subquery, before JOIN or owner selection.
    # Every row in this at-most32-row prefix advances the scan, including foreign
    # workspaces and already bound/failed grades. Rowid gaps cannot stall a tick.
    rows = connection.execute(
        'SELECT page.sequence,page.attempt_id,page.grading_revision,a.workspace_id '
        'FROM (SELECT rowid AS sequence,attempt_id,grading_revision FROM grades '
        'WHERE rowid>? AND rowid<=? ORDER BY rowid LIMIT ?) AS page '
        'LEFT JOIN attempts a ON a.id=page.attempt_id ORDER BY page.sequence',
        (after_sequence, ceiling, GRADE_RECOVERY_SCAN_ROWS),
    ).fetchall()
    keys = []
    for row in rows:
        if row['workspace_id'] is None:
            raise invalid_snapshot()
        if row['workspace_id'] == workspace_id:
            keys.append((row['sequence'], GradeKey(workspace_id=workspace_id,
                attempt_id=row['attempt_id'], grading_revision=row['grading_revision'])))
    return GradeRecoveryScan(after_sequence=after_sequence, ceiling=ceiling,
        through_sequence=rows[-1]['sequence'] if rows else ceiling, keys=tuple(keys))
