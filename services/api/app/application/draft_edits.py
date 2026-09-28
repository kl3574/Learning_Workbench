"""Local text-block draft create/edit, with immutable history and exact owner reads."""
from contextlib import contextmanager
import sqlite3
from uuid import uuid4

from pydantic import TypeAdapter
from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256
from ..draft_dto import DraftCreateWrite, DraftPatchWrite, DraftCreated, DraftPatched
from ..infrastructure.database import Database, utc_now
from ..infrastructure.draft_candidate_repository import DraftCandidateRepository
from ..infrastructure.draft_edit_repository import DraftEditRepository
from ..infrastructure.security import SessionIdentity, current_session_identity
from .authoring_context import AuthoringContext
from .content_draft_source import ContentDraftSource
from .draft_candidate_models import ResolvedDraftCandidate, match_candidate
from .draft_candidates import DraftCandidates
from .draft_edit_models import (
    DraftEditRecord, MAX_VERSIONS, ack, apply_patch, checked, initial_payload, invalid, edit_warnings, unsupported, integrity,
)
from .errors import ApiError
from .providers import validate_key


class DraftEditService:
    def __init__(self, database: Database, source: ContentDraftSource | None = None):
        self.database = database
        self.source = source or ContentDraftSource(database)
        self.candidates = DraftCandidates({'authoring_edit': self})

    @staticmethod
    def _identity(conn: sqlite3.Connection, identity: SessionIdentity) -> SessionIdentity:
        current = current_session_identity(conn, identity)
        AuthoringContext.check_access(conn, current)
        return current

    @staticmethod
    def _id(value: str) -> str:
        try:
            return TypeAdapter(dm.Id).validate_python(value, strict=True)
        except (ValueError, TypeError):
            raise invalid() from None

    @contextmanager
    def _transaction(self):
        try:
            with self.database.transaction() as conn:
                yield conn
        except sqlite3.Error:
            raise ApiError(503, 'DRAFT_EDIT_STORAGE_UNAVAILABLE', '草稿存储暂不可用，未确认新的修改。', True) from None

    def _history(self, conn: sqlite3.Connection, identity: SessionIdentity, identifier: str) -> list[DraftEditRecord]:
        current = self._identity(conn, identity)
        records = DraftEditRepository(conn, current.workspace_id).history(self._id(identifier))
        self.source.verify_exact(conn, current, records[0].base)
        return records

    def _registered_history(self, conn: sqlite3.Connection, identity: SessionIdentity,
                            identifier: str) -> list[DraftEditRecord]:
        records = self._history(conn, identity, identifier)
        catalog = DraftCandidateRepository(conn)
        for record in records:
            expected = ResolvedDraftCandidate(record.workspace_id, 'authoring', 'authoring_edit', record.candidate)
            if catalog.lookup(record.workspace_id, identifier, record.candidate.draft_revision) != expected:
                raise integrity()
        return records

    def read(self, identity: SessionIdentity, draft_id: str, revision: int) -> DraftEditRecord:
        """Internal exact read; not a new HTTP endpoint or an Import snapshot."""
        try:
            revision = TypeAdapter(dm.Revision).validate_python(revision, strict=True)
        except (ValueError, TypeError):
            raise invalid() from None
        with self._transaction() as conn:
            records = self._registered_history(conn, identity, draft_id)
            if revision > len(records):
                raise ApiError(412, 'DRAFT_REVISION_MISMATCH', '草稿修订不存在，请重新读取。')
            record = records[revision - 1]
            match_candidate(record.candidate, DraftCandidateRepository(conn).lookup(
                record.workspace_id, draft_id, revision).candidate)
            return record

    def create(self, identity: SessionIdentity, body: DraftCreateWrite, key: str) -> DraftCreated:
        body, key = checked(DraftCreateWrite, body, request=True), validate_key(key)
        with self._transaction() as conn:
            current = self._identity(conn, identity)
            repo = DraftEditRepository(conn, current.workspace_id)
            replay = repo.replay(current.id, 'POST /drafts', key, body)
            if replay:
                self._registered_history(conn, current, replay.candidate.draft_id)
                return checked(DraftCreated, ack(replay))
            if body.kind != 'block' or body.base_ref is None:
                raise unsupported()
            base = self.source.read_exact(conn, current, body.base_ref)
            payload = initial_payload(base, body.title)
            candidate = dm.DraftCandidate(draft_id='draft_' + uuid4().hex, draft_revision=1,
                                           entity='block', candidate_sha256=metadata_sha256(payload))
            record = DraftEditRecord(workspace_id=current.workspace_id, candidate=candidate, base=base, payload=payload,
                actor_id=current.id, command_key=key, request=body, parent_sha256=None, created_at=utc_now(),
                warnings=edit_warnings(base))
            repo.append(record)
            self.candidates.admit(conn, current, 'authoring_edit', candidate)
            self._registered_history(conn, current, candidate.draft_id)
            return checked(DraftCreated, ack(record))

    def patch(self, identity: SessionIdentity, draft_id: str, body: DraftPatchWrite, key: str | None = None) -> DraftPatched:
        draft_id = self._id(draft_id)
        body = checked(DraftPatchWrite, body, request=True)
        key = validate_key(key) if key is not None else None
        with self._transaction() as conn:
            current = self._identity(conn, identity)
            repo = DraftEditRepository(conn, current.workspace_id)
            if key is not None:
                replay = repo.replay(current.id, f'PATCH /drafts/{draft_id}', key, body)
                if replay:
                    self._registered_history(conn, current, draft_id)
                    return checked(DraftPatched, ack(replay))
            history = self._registered_history(conn, current, draft_id)
            prior = history[-1]
            if body.expected_revision != prior.candidate.draft_revision:
                raise ApiError(412, 'DRAFT_REVISION_MISMATCH', '草稿已变化，请重新读取当前修订。')
            if len(history) >= MAX_VERSIONS:
                raise ApiError(413, 'DRAFT_HISTORY_BUDGET', '草稿历史达到当前本地核验上限。')
            payload = apply_patch(prior.payload, body)
            candidate = dm.DraftCandidate(draft_id=draft_id, draft_revision=body.expected_revision + 1,
                                           entity='block', candidate_sha256=metadata_sha256(payload))
            record = DraftEditRecord(workspace_id=current.workspace_id, candidate=candidate, base=prior.base,
                payload=payload, actor_id=current.id, command_key=key, request=body,
                parent_sha256=metadata_sha256(prior), created_at=utc_now(), warnings=edit_warnings(prior.base))
            repo.append(record)
            self.candidates.admit(conn, current, 'authoring_edit', candidate)
            self._registered_history(conn, current, draft_id)
            return checked(DraftPatched, ack(record))

    def resolve_candidate(self, connection: sqlite3.Connection, identity: SessionIdentity,
                          candidate: dm.DraftCandidate) -> ResolvedDraftCandidate:
        candidate = checked(dm.DraftCandidate, candidate)
        records = self._history(connection, identity, candidate.draft_id)
        if candidate.draft_revision > len(records):
            raise ApiError(412, 'DRAFT_REVISION_MISMATCH', '草稿修订不存在。')
        match_candidate(candidate, records[candidate.draft_revision - 1].candidate)
        return ResolvedDraftCandidate(identity.workspace_id, 'authoring', 'authoring_edit', candidate)

    def require_current_candidate(self, connection: sqlite3.Connection, identity: SessionIdentity,
                                  candidate: dm.DraftCandidate) -> None:
        candidate = checked(dm.DraftCandidate, candidate)
        records = self._history(connection, identity, candidate.draft_id)
        match_candidate(candidate, records[-1].candidate)

    def publication_record(self, connection: sqlite3.Connection, identity: SessionIdentity,
                           candidate: dm.DraftCandidate, *, require_current: bool = False) -> DraftEditRecord:
        """Exact owner history in the publication transaction; replay does not select the latest head."""
        candidate = checked(dm.DraftCandidate, candidate)
        records = self._registered_history(connection, identity, candidate.draft_id)
        if candidate.draft_revision > len(records):
            raise ApiError(412, 'DRAFT_REVISION_MISMATCH', '草稿修订不存在。')
        record = records[candidate.draft_revision - 1]
        match_candidate(candidate, record.candidate)
        if require_current:
            match_candidate(candidate, records[-1].candidate)
        return record

    def read_review_material(self, connection: sqlite3.Connection, identity: SessionIdentity, candidate: dm.DraftCandidate):
        from .review_material_models import EditReviewMaterial, checked_material
        resolved = self.resolve_candidate(connection, identity, candidate)
        records = self._history(connection, identity, candidate.draft_id)
        return checked_material(resolved, EditReviewMaterial(record=records[candidate.draft_revision - 1]))
