"""Practice-owned prior-view facts from validated persisted session allocations."""

from collections.abc import Sequence
from dataclasses import dataclass
import sqlite3
from typing import Literal

from pydantic import TypeAdapter

from packages.contracts import domain_models as dm

from packages.contracts.canonical import strict_json

from ..infrastructure.content_repository import reference
from ..infrastructure.practice_repository import PracticeRepository
from .assessment_content import AssessmentContent
from .errors import ApiError
from .learning import read_learning_event


@dataclass(frozen=True)
class SeenQuestion:
    question_ref: dm.ContentRef
    state: Literal['unseen', 'seen', 'unknown']
    reason_codes: tuple[str, ...]


class PracticeHistory:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection = connection
        self.workspace_id = workspace_id

    def seen(self, questions: Sequence[dm.QuestionPublic]) -> tuple[SeenQuestion, ...]:
        repository = PracticeRepository(self.connection, self.workspace_id)
        content = AssessmentContent(self.connection, self.workspace_id)
        groups: set[str] = set()
        exact: set[tuple[str, int, str]] = set()
        incomplete = False
        rows = self.connection.execute('SELECT id FROM practice_sessions WHERE workspace_id=? ORDER BY id', (self.workspace_id,))
        for row in rows:
            try:
                session = repository.load(row['id'])
                practice = content.exact(session.practice_ref)
                if not isinstance(practice, dm.PracticeSet) or practice.question_refs != session.question_refs:
                    raise ValueError('assignment changed')
                historical = []
                for ref in session.question_refs:
                    question = content.exact(ref)
                    if not isinstance(question, dm.QuestionPublic):
                        raise ValueError('question missing')
                    historical.append(question)
                repository.exposure_facts(session, historical)
                for question in historical:
                    ref = reference(question)
                    exact.add((ref.id, ref.revision, ref.sha256))
                    groups.add(question.exposure_group)
            except (ApiError, ValueError, TypeError, KeyError):
                incomplete = True
        unknown_groups: set[str] = set()
        for row in self.connection.execute('SELECT * FROM exposures WHERE workspace_id=? ORDER BY id', (self.workspace_id,)):
            try:
                ref = dm.ContentRef.model_validate(strict_json(row['question_ref_json']))
                value = content.exact(ref)
                if not isinstance(value, dm.QuestionPublic) or row['exposure_group'] != value.exposure_group:
                    raise ValueError('exposure reference mismatch')
                event = read_learning_event(self.connection, self.workspace_id, row['event_id'])
                # Exposure insertion and its Learning event have distinct server
                # timestamps within the same transaction; no equality is promised.
                TypeAdapter(dm.UTC).validate_python(row['occurred_at'])
                if event.origin == 'user_supplied_import' or row['kind'] == 'imported_claim':
                    unknown_groups.add(value.exposure_group)
                    continue
                if event.actor != 'server' or event.origin != 'native':
                    raise ValueError('exposure actor mismatch')
                if row['kind'] in {'hint', 'solution'}:
                    expected = 'hint_revealed' if row['kind'] == 'hint' else 'solution_revealed'
                    if event.kind != expected or event.ref != ref or event.attempt_id is None:
                        raise ValueError('exposure event mismatch')
                    record = repository.load(event.attempt_id)
                    if ref not in record.question_refs:
                        raise ValueError('exposure assignment mismatch')
                    linked = self.connection.execute(
                        'SELECT 1 FROM practice_exposures WHERE session_id=? AND exposure_id=? AND question_id=? AND kind=?',
                        (record.id, row['id'], ref.id, row['kind']),
                    ).fetchone()
                    if linked is None:
                        raise ValueError('exposure receipt missing')
                elif row['kind'] == 'prior_attempt':
                    from .assessment_access import AssessmentAccess
                    if event.kind != 'test_submitted' or event.attempt_id is None:
                        raise ValueError('assessment exposure event mismatch')
                    attempt = AssessmentAccess(self.connection, self.workspace_id).load(event.attempt_id)
                    if event.ref != attempt.assessment_ref or ref not in attempt.question_refs or attempt.status not in {'submitted', 'grading', 'graded', 'needs_review'}:
                        raise ValueError('assessment exposure allocation mismatch')
                else:
                    raise ValueError('unrecognized exposure kind')
                exact.add((ref.id, ref.revision, ref.sha256))
                groups.add(value.exposure_group)
            except (ApiError, ValueError, TypeError, KeyError):
                incomplete = True
        result = []
        for question in questions:
            ref = reference(question)
            if (ref.id, ref.revision, ref.sha256) in exact:
                result.append(SeenQuestion(ref, 'seen', ('practice_question_seen',)))
            elif question.exposure_group in groups:
                result.append(SeenQuestion(ref, 'seen', ('practice_template_seen',)))
            elif question.exposure_group in unknown_groups:
                result.append(SeenQuestion(ref, 'unknown', ('imported_exposure_unverified',)))
            elif incomplete:
                result.append(SeenQuestion(ref, 'unknown', ('practice_history_incomplete',)))
            else:
                result.append(SeenQuestion(ref, 'unseen', ()))
        return tuple(result)
