"""Narrow Assessment-owned read port for Policy; never exports private pins."""

from dataclasses import dataclass
import sqlite3
from typing import Literal

from packages.contracts import domain_models as dm

from ..infrastructure.assessment_repository import AssessmentRepository


@dataclass(frozen=True)
class AttemptAccess:
    id: str
    workspace_id: str
    assessment_ref: dm.ContentRef
    status: Literal['active', 'submitted', 'grading', 'graded', 'needs_review', 'abandoned']
    policy: dm.PolicySnapshot
    question_refs: tuple[dm.ContentRef, ...]


class AssessmentAccess:
    def __init__(self, connection: sqlite3.Connection, workspace_id: str):
        self.connection = connection
        self.workspace_id = workspace_id

    def active_independent(self) -> str | None:
        # Even an incomplete legacy allocation continues to lock academic data.
        row = self.connection.execute(
            "SELECT id FROM attempts WHERE workspace_id=? AND mode='independent' AND status='active' ORDER BY id LIMIT 1",
            (self.workspace_id,),
        ).fetchone()
        return str(row['id']) if row else None

    def load(self, identifier: str) -> AttemptAccess:
        # Assignment/submission hashes are checked by their owner. Submission
        # event/outbox links intentionally are NOT checked during Policy: these
        # are appended immediately after the state transition in the same TX.
        value = AssessmentRepository(self.connection, self.workspace_id).load(identifier)
        return AttemptAccess(value.id, value.workspace_id, value.assessment_ref, value.status,
                             value.policy, tuple(value.question_refs))

    def active_open_book(self) -> str | None:
        row = self.connection.execute(
            "SELECT id FROM attempts WHERE workspace_id=? AND mode='open_book' AND status='active' ORDER BY id LIMIT 1",
            (self.workspace_id,),
        ).fetchone()
        return str(row['id']) if row else None

    def protected(self) -> tuple[AttemptAccess, ...]:
        rows = self.connection.execute(
            "SELECT id FROM attempts WHERE workspace_id=? AND (status='active' OR "
            "(mode='independent' AND status IN ('submitted','grading','needs_review'))) ORDER BY id", (self.workspace_id,),
        ).fetchall()
        return tuple(self.load(row['id']) for row in rows)
