"""Immutable candidate identity catalog; every admission still needs its real owner."""

import sqlite3

from ..application.draft_candidate_models import ResolvedDraftCandidate
from ..application.errors import ApiError


def conflict() -> ApiError:
    return ApiError(409, 'DRAFT_IDENTITY_CONFLICT', '草稿身份与原登记记录不一致。')


class DraftCandidateRepository:
    def __init__(self, connection: sqlite3.Connection):
        if not connection.in_transaction:
            raise ApiError(409, 'TRANSACTION_REQUIRED', '候选登记需要有效事务。')
        self.connection = connection

    def register(self, value: ResolvedDraftCandidate) -> None:
        """Called only after the source owner verified this candidate in this transaction.

        Existing catalog facts never authenticate source payloads or approve content.
        An exact retry performs no UPDATE/REPLACE and retains all older revisions.
        """
        candidate = value.candidate
        expected = (candidate.draft_id, value.workspace_id, value.owner,
                    value.source_kind, candidate.entity)
        row = self.connection.execute(
            'SELECT draft_id,workspace_id,owner,source_kind,entity '
            'FROM draft_candidate_identities WHERE draft_id=?', (candidate.draft_id,),
        ).fetchone()
        if row is not None and tuple(row) != expected:
            raise conflict()
        if row is None:
            self.connection.execute(
                'INSERT INTO draft_candidate_identities(draft_id,workspace_id,owner,source_kind,entity) '
                'VALUES(?,?,?,?,?)', expected,
            )
        expected_revision = (candidate.draft_id, value.workspace_id, value.owner, candidate.entity,
                             candidate.draft_revision, candidate.candidate_sha256)
        row = self.connection.execute(
            'SELECT draft_id,workspace_id,owner,entity,draft_revision,candidate_sha256 '
            'FROM draft_candidate_revisions WHERE draft_id=? AND draft_revision=?',
            (candidate.draft_id, candidate.draft_revision),
        ).fetchone()
        if row is not None and tuple(row) != expected_revision:
            raise conflict()
        if row is None:
            self.connection.execute(
                'INSERT INTO draft_candidate_revisions(draft_id,workspace_id,owner,entity,'
                'draft_revision,candidate_sha256) VALUES(?,?,?,?,?,?)', expected_revision,
            )
