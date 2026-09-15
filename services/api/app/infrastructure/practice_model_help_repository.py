"""Immutable Practice receipts bind Learning exposure and Tutor's original answer event."""
import sqlite3
from typing import Literal

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, strict_json
from ..application.learning import read_learning_event, validate_practice_event
from ..application.tutor_answer_access import TutorAnswerFact, read_answer_fact
from .practice_repository import PracticeRecord, invalid_snapshot


class ModelHelpReceipt(dm.StrictModel):
    version: Literal['practice-model-help-v1']
    source: Literal['model']
    answer: TutorAnswerFact
    event_id: dm.Id
    exposure_id: dm.Id
    exposure_group: dm.Id
    occurred_at: dm.UTC


class PracticeModelHelpRepository:
    def __init__(self, conn: sqlite3.Connection, workspace_id: str):
        self.conn, self.workspace_id = conn, workspace_id

    def read(self, run_id: str) -> ModelHelpReceipt | None:
        row = self.conn.execute('SELECT * FROM practice_model_help WHERE run_id=? AND workspace_id=?',
            (run_id, self.workspace_id)).fetchone()
        if row is None:
            return None
        try:
            receipt = ModelHelpReceipt.model_validate(strict_json(row['receipt_json']))
            fact = receipt.answer
            if (receipt.version != 'practice-model-help-v1' or receipt.source != 'model'
                    or canonical_bytes(receipt).decode() != row['receipt_json']
                    or metadata_sha256(receipt) != row['receipt_sha256']
                    or fact.workspace_id != self.workspace_id or fact.run_id != row['run_id']
                    or fact.practice.session_id != row['session_id'] or receipt.exposure_id != row['exposure_id']
                    or read_answer_fact(self.conn, self.workspace_id, run_id) != fact):
                raise invalid_snapshot()
            exposure = self.conn.execute('SELECT * FROM exposures WHERE id=?', (receipt.exposure_id,)).fetchone()
            if (exposure is None or exposure['workspace_id'] != self.workspace_id
                    or exposure['event_id'] != receipt.event_id or exposure['kind'] != 'hint'
                    or exposure['exposure_group'] != receipt.exposure_group
                    or exposure['question_ref_json'] != canonical_bytes(fact.practice.question_ref).decode()
                    or exposure['occurred_at'] != receipt.occurred_at):
                raise invalid_snapshot()
            validate_practice_event(self.conn, self.workspace_id, receipt.event_id, 'hint_revealed',
                fact.practice.question_ref, fact.practice.session_id)
            return receipt
        except (ValueError, TypeError, KeyError):
            raise invalid_snapshot() from None

    def facts(self, record: PracticeRecord, questions: list[dm.QuestionPublic]) -> list[ModelHelpReceipt]:
        assigned = {q.id: q for q in questions}
        receipts = []
        for row in self.conn.execute('SELECT run_id FROM practice_model_help WHERE workspace_id=? AND session_id=? ORDER BY run_id',
                                     (self.workspace_id, record.id)):
            value = self.read(row['run_id'])
            if (value is None or value.answer.practice.question_ref not in record.question_refs
                    or value.exposure_group != assigned[value.answer.practice.question_ref.id].exposure_group):
                raise invalid_snapshot()
            receipts.append(value)
        # A missing model receipt must not turn its surviving trusted exposure
        # into an unassisted session. Rules receipts retain their original owner.
        known = {item.exposure_id for item in receipts}
        known.update(row['exposure_id'] for row in self.conn.execute(
            'SELECT exposure_id FROM practice_exposures WHERE session_id=?', (record.id,)))
        for exposure in self.conn.execute("SELECT id,event_id FROM exposures WHERE workspace_id=? AND kind IN ('hint','solution')",
                                          (self.workspace_id,)):
            if exposure['id'] not in known:
                event = read_learning_event(self.conn, self.workspace_id, exposure['event_id'])
                if event.attempt_id == record.id:
                    raise invalid_snapshot()
        return receipts

    def by_exposure(self, exposure_id: str) -> ModelHelpReceipt | None:
        row = self.conn.execute('SELECT run_id FROM practice_model_help WHERE exposure_id=? AND workspace_id=?',
            (exposure_id, self.workspace_id)).fetchone()
        return self.read(row['run_id']) if row is not None else None

    def insert(self, receipt: ModelHelpReceipt) -> None:
        fact = receipt.answer
        self.conn.execute('INSERT INTO exposures(id,workspace_id,event_id,exposure_group,question_ref_json,kind,occurred_at) VALUES(?,?,?,?,?,?,?)',
            (receipt.exposure_id, self.workspace_id, receipt.event_id, receipt.exposure_group,
             canonical_bytes(fact.practice.question_ref).decode(), 'hint', receipt.occurred_at))
        self.conn.execute('INSERT INTO practice_model_help VALUES(?,?,?,?,?,?)',
            (fact.run_id, self.workspace_id, fact.practice.session_id, receipt.exposure_id,
             canonical_bytes(receipt).decode(), metadata_sha256(receipt)))
