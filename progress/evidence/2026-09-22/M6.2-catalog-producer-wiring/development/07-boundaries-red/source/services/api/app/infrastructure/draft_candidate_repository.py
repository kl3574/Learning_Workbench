"""Immutable candidate identity catalog; every admission still needs its real owner."""

import sqlite3

from pydantic import TypeAdapter, ValidationError

from packages.contracts import domain_models as dm
from ..application.draft_candidate_models import DraftOwner, DraftSourceKind, ResolvedDraftCandidate
from ..application.errors import ApiError


def conflict() -> ApiError:
    return ApiError(409, 'DRAFT_IDENTITY_CONFLICT', '草稿身份与原登记记录不一致。')


class DraftCandidateRepository:
    def __init__(self, connection: sqlite3.Connection):
        if not connection.in_transaction:
            raise ApiError(409, 'TRANSACTION_REQUIRED', '候选登记需要有效事务。')
        self.connection = connection

    def lookup(self, workspace_id: str, draft_id: str, revision: int) -> ResolvedDraftCandidate:
        """Locate an exact registered revision; this does not authenticate its owner."""
        try:
            draft_id = TypeAdapter(dm.Id).validate_python(draft_id, strict=True)
            revision = TypeAdapter(dm.Revision).validate_python(revision, strict=True)
        except ValidationError:
            raise ApiError(422, 'SCHEMA_INVALID', '草稿候选身份无效。') from None
        identity = self.connection.execute(
            'SELECT * FROM draft_candidate_identities WHERE draft_id=? AND workspace_id=?',
            (draft_id, workspace_id),
        ).fetchone()
        if identity is None:
            raise ApiError(404, 'DRAFT_CANDIDATE_UNREGISTERED', '草稿候选未登记或不可访问。')
        row = self.connection.execute(
            'SELECT * FROM draft_candidate_revisions WHERE draft_id=? AND draft_revision=?',
            (draft_id, revision),
        ).fetchone()
        if row is None:
            raise ApiError(412, 'DRAFT_REVISION_MISMATCH', '草稿候选修订未登记，请重新读取。')
        try:
            owner = TypeAdapter(DraftOwner).validate_python(identity['owner'], strict=True)
            kind = TypeAdapter(DraftSourceKind).validate_python(identity['source_kind'], strict=True)
            candidate = dm.DraftCandidate.model_validate(dict(
                draft_id=row['draft_id'], draft_revision=row['draft_revision'],
                entity=row['entity'], candidate_sha256=row['candidate_sha256']))
            if (tuple(row[key] for key in ('draft_id', 'workspace_id', 'owner', 'entity'))
                    != tuple(identity[key] for key in ('draft_id', 'workspace_id', 'owner', 'entity'))
                    or owner != ('import' if kind == 'import' else 'authoring')
                    or kind == 'authoring_single' and candidate.entity != 'block'
                    or kind == 'authoring_group' and candidate.entity not in {'lesson', 'practice_set', 'assessment'}):
                raise ValueError('Candidate registry linkage is inconsistent')
        except (ValidationError, ValueError, TypeError, KeyError):
            raise ApiError(503, 'DRAFT_OWNER_INTEGRITY', '草稿所属记录当前无法核验。') from None
        return ResolvedDraftCandidate(workspace_id, owner, kind, candidate)

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
