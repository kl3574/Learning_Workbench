"""Jobs-owned review lifecycle; never creates a ReviewReceipt or approves content.

The isolated adapter shares checked events, leases and cancellation with the
existing Authoring consumers. Quality must authenticate its own candidate and
review history and current actor before using this internal persistence port.
"""
import sqlite3
from dataclasses import dataclass
from uuid import uuid4

from pydantic import ValidationError, TypeAdapter
from packages.contracts import domain_models as dm
from ..application.errors import ApiError
from ..application.review_models import ReviewJobInput
from .authoring_job_repository import AuthoringJobRepository, TERMINAL, checked, integrity


@dataclass(frozen=True)
class ReviewQueueCandidate:
    created_at: str
    job_id: str


@dataclass(frozen=True)
class ReviewQueueScan:
    candidates: tuple[ReviewQueueCandidate, ...]
    invalid_rows: int


class ReviewJobRepository(AuthoringJobRepository):
    kinds = frozenset({'draft_review'})
    transitions = {'queued': {'running', 'cancelled'}, 'running': {'running', *TERMINAL}}

    @staticmethod
    def initial_status(kind: str) -> str:
        return 'queued'

    def _transaction(self) -> None:
        if not self.conn.in_transaction:
            raise ApiError(409, 'TRANSACTION_REQUIRED', '审核任务需要当前事务。')

    def claimable_candidates(self, now: str) -> ReviewQueueScan:
        """Jobs-owned scheduling facts, never a lease or authority from input JSON.

        The consumer must load its full Quality history before Jobs.claim; a
        damaged consumer record can then be skipped without hiding valid work.
        """
        self._transaction()
        try:
            TypeAdapter(dm.UTC).validate_python(now)
            rows = self.conn.execute("SELECT created_at,id FROM jobs WHERE workspace_id=? AND kind='draft_review' "
                "AND (status='queued' OR (status='running' AND lease_until<=?)) ORDER BY created_at,id",
                (self.workspace_id, now)).fetchall()
        except (ValueError, TypeError):
            raise integrity() from None
        candidates, invalid_rows = [], 0
        for row in rows:
            try:
                candidates.append(ReviewQueueCandidate(TypeAdapter(dm.UTC).validate_python(row['created_at']),
                    TypeAdapter(dm.Id).validate_python(row['id'])))
            except (ValueError, TypeError):
                # A corrupt scheduling field grants no lease, and must not
                # prevent the consumer from inspecting other checked rows.
                invalid_rows += 1
        return ReviewQueueScan(tuple(candidates), invalid_rows)

    def _input(self, identifier: str, value: object) -> ReviewJobInput:
        try:
            raw = value.model_dump(mode='python', warnings='error') if isinstance(value, ReviewJobInput) else value
            result = ReviewJobInput.model_validate(raw)
        except (ValidationError, ValueError, TypeError):
            raise integrity() from None
        if result.review_id != identifier or result.workspace_id != self.workspace_id:
            raise integrity()
        return result

    def create(self, identifier: str, kind: str, value: object) -> None:
        self._transaction()
        value = self._input(identifier, value)
        super().create(identifier, kind, value)
        self.load(identifier)

    def load(self, identifier: str) -> sqlite3.Row:
        self._transaction()
        row = super().load(identifier)
        self._input(identifier, checked(row['input_json'], row['input_sha256']))
        return row

    def transition(self, row: sqlite3.Row, status: str, *, result: dict | None = None,
                   cancel: bool | None = None, owner: str | None = None, until: str | None = None) -> None:
        self._transaction()
        current = self.load(row['id'])
        if dict(current) != dict(row):
            raise ApiError(409, 'AUTHORING_LEASE_LOST', '任务的状态已改变。')
        if current['status'] in TERMINAL:
            raise ApiError(409, 'JOB_TERMINAL', '任务已经结束。')
        if status not in self.transitions[current['status']]:
            raise integrity()
        # Invalid lease/result shapes must not leave mutations if a caller
        # catches the error and commits its wider owner transaction. The name
        # comes only from a generated UUID, never a caller identifier.
        point = 'review_transition_' + uuid4().hex
        self.conn.execute(f'SAVEPOINT {point}')
        try:
            super().transition(current, status, result=result, cancel=cancel, owner=owner, until=until)
        except BaseException:
            self.conn.execute(f'ROLLBACK TO {point}')
            self.conn.execute(f'RELEASE {point}')
            raise
        self.conn.execute(f'RELEASE {point}')

    def input_version(self, identifier: str) -> str:
        self.load(identifier)
        return 'draft-review-job-v1'

    def input(self, identifier: str) -> ReviewJobInput:
        row = self.load(identifier)
        return self._input(identifier, checked(row['input_json'], row['input_sha256']))
