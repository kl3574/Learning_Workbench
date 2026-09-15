"""Assessment-owned submission participation, independent of grading outcomes."""

import sqlite3

from ..infrastructure.assessment_repository import AssessmentRepository
from ..infrastructure.content_repository import damaged, reference
from .assessment_content import AssessmentContent
from .assessment_evidence_access import submission_witness
from .learning_state_models import SubmissionActivity
from .policy import Policy


def assessment_submissions(connection: sqlite3.Connection, workspace_id: str) -> list[SubmissionActivity]:
    content = AssessmentContent(connection, workspace_id)
    content.public.require_workspace()
    Policy(connection, workspace_id).check('subject_read')
    output = []
    repository = AssessmentRepository(connection, workspace_id)
    for identifier in repository.history_ids():
        record = repository.load(identifier)
        # Validate every allocation before filtering; a damaged submitted snapshot
        # must not become indistinguishable from a real unsubmitted attempt.
        if record.submission is None:
            continue
        witness = submission_witness(connection, workspace_id, identifier)
        blueprint = content.blueprint(witness.assessment_ref)
        questions = content.questions(blueprint)
        if [reference(value) for value in questions] != witness.question_refs:
            raise damaged()
        output.append(SubmissionActivity(target_ref=witness.assessment_ref, source_id=witness.attempt_id,
            event_id=witness.submission_event_id, submitted_at=witness.submitted_at, question_refs=witness.question_refs))
    return output
