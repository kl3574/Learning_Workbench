"""Jobs-owned review lifecycle; never creates a ReviewReceipt or approves content.

The isolated adapter shares checked events, leases and cancellation with the
existing Authoring consumers. Quality must authenticate its own candidate and
review history and current actor before using this internal persistence port.
"""
import sqlite3

from pydantic import ValidationError
from ..application.errors import ApiError
from ..application.review_models import ReviewJobInput
from .authoring_job_repository import AuthoringJobRepository, TERMINAL, checked, integrity


class ReviewJobRepository(AuthoringJobRepository):
    kinds = frozenset({'draft_review'})
    transitions = {'queued': {'running', 'cancelled'}, 'running': {'running', *TERMINAL}}

    @staticmethod
    def initial_status(kind: str) -> str:
        return 'queued'

    def _input(self, identifier: str, value: object) -> ReviewJobInput:
        try:
            raw = value.model_dump(mode='python') if isinstance(value, ReviewJobInput) else value
            result = ReviewJobInput.model_validate(raw)
        except (ValidationError, ValueError, TypeError):
            raise integrity() from None
        if result.review_id != identifier or result.workspace_id != self.workspace_id:
            raise integrity()
        return result

    def create(self, identifier: str, kind: str, value: object) -> None:
        if not self.conn.in_transaction:
            raise ApiError(409, 'TRANSACTION_REQUIRED', '审核任务需要当前事务。')
        value = self._input(identifier, value)
        super().create(identifier, kind, value)
        self.load(identifier)

    def load(self, identifier: str) -> sqlite3.Row:
        row = super().load(identifier)
        self._input(identifier, checked(row['input_json'], row['input_sha256']))
        return row

    def input_version(self, identifier: str) -> str:
        self.load(identifier)
        return 'draft-review-job-v1'

    def input(self, identifier: str) -> ReviewJobInput:
        row = self.load(identifier)
        return self._input(identifier, checked(row['input_json'], row['input_sha256']))
