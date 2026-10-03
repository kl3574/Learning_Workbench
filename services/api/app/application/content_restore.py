"""Dedicated historical restore owner; neither create nor GET approves or publishes."""
from uuid import uuid4
from collections.abc import Callable
import sqlite3
from typing import TYPE_CHECKING
from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256
from ..content_restore_dto import ContentRestoreDraftCreateWrite, ContentRestoreDraftCreateAck, ContentRestoreDraftSnapshot
from ..infrastructure.database import utc_now
from ..infrastructure.content_restore_repository import RestoreRepository
from ..infrastructure.draft_candidate_repository import DraftCandidateRepository
from ..infrastructure.publication_repository import PublicationRepository
from ..infrastructure.security import current_session_identity, SessionIdentity
from .authoring_context import AuthoringContext
from .content_restore_models import RestorePayload, RestoreRecord, checked, integrity, restore_warnings
from .content_restore_source import ContentRestoreSource
from .draft_candidates import DraftCandidates
from .draft_candidate_models import ResolvedDraftCandidate, match_candidate
from .providers import validate_key
from .errors import ApiError

if TYPE_CHECKING:
    from .publication_models import PublicationHistory


class ContentRestoreService:
    def __init__(self, database):
        self.database, self.source = database, ContentRestoreSource(database)
        self.candidates = DraftCandidates({'authoring_restore': self})
        self.numeric_projection = None
        self.verify_publication: Callable[[sqlite3.Connection, SessionIdentity, 'PublicationHistory'], dm.ContentRef] | None = None

    @staticmethod
    def identity(conn, identity):
        current = current_session_identity(conn, identity)
        AuthoringContext.check_access(conn, current)
        return current

    def record(self, conn, identity, identifier, *, registered=True):
        current = self.identity(conn, identity)
        record = RestoreRepository(conn, current.workspace_id).load(identifier)
        try:
            if self.source.read(conn, current, record.payload.request.source_ref) != record.payload.source:
                raise integrity()
            # The historical base must remain intact even after current advances.
            self.source.content.verify_publication_in_transaction(conn, current.workspace_id, record.payload.request.expected_current_ref)
        except ApiError as error:
            if error.status == 404:
                raise integrity() from None
            raise
        if registered and DraftCandidateRepository(conn).lookup(current.workspace_id, identifier, 1) != ResolvedDraftCandidate(current.workspace_id, 'authoring', 'authoring_restore', record.candidate):
            raise integrity()
        return record

    @staticmethod
    def ack(record):
        return ContentRestoreDraftCreateAck(candidate=record.candidate, source_ref=record.payload.request.source_ref,
            base_ref=record.payload.request.expected_current_ref, state='draft')

    def create(self, identity, body: ContentRestoreDraftCreateWrite, command_key: str):
        body, command_key = checked(ContentRestoreDraftCreateWrite, body), validate_key(command_key)
        with self.database.transaction() as conn:
            current = self.identity(conn, identity)
            repo = RestoreRepository(conn, current.workspace_id)
            replay = repo.replay(current.id, command_key, body)
            if replay is not None:
                return self.ack(self.record(conn, current, replay.candidate.draft_id))
            self.source.require_current(conn, current, body.expected_current_ref)
            source = self.source.read(conn, current, body.source_ref)
            payload = RestorePayload(version='content-restore-v1', request=body, source=source,
                proposed_block=source.material.metadata.model_copy(update={'revision': body.expected_current_ref.revision + 1}), warnings=restore_warnings(source))
            candidate = dm.DraftCandidate(draft_id='restore_' + uuid4().hex, draft_revision=1, entity='block', candidate_sha256=metadata_sha256(payload))
            record = RestoreRecord(version='content-restore-record-v1', workspace_id=current.workspace_id, candidate=candidate,
                actor_id=current.id, command_key=command_key, payload=payload, created_at=utc_now())
            repo.append(record)
            self.candidates.admit(conn, current, 'authoring_restore', candidate)
            return self.ack(self.record(conn, current, candidate.draft_id))

    def resolve_candidate(self, conn, identity, candidate):
        record = self.record(conn, identity, candidate.draft_id, registered=False)
        match_candidate(candidate, record.candidate)
        return ResolvedDraftCandidate(record.workspace_id, 'authoring', 'authoring_restore', record.candidate)

    def require_current_candidate(self, conn, identity, candidate):
        record = self.record(conn, identity, candidate.draft_id)
        match_candidate(candidate, record.candidate)
        self.source.require_current(conn, identity, record.payload.request.expected_current_ref)

    def read_review_material(self, conn, identity, candidate):
        from .review_material_models import RestoreReviewMaterial, checked_material
        resolved = self.resolve_candidate(conn, identity, candidate)
        return checked_material(resolved, RestoreReviewMaterial(version='authoring-restore-review-material-v1', record=self.record(conn, identity, candidate.draft_id)))

    def read(self, identity, identifier):
        with self.database.connect() as conn:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute('PRAGMA query_only=ON')
            try:
                record = self.record(conn, identity, identifier)
                publication = PublicationRepository(conn, record.workspace_id).for_candidate(record.candidate)
                result = None
                if publication is not None:
                    if self.verify_publication is None:
                        raise ApiError(503, 'PUBLICATION_OWNER_UNAVAILABLE', '恢复发布记录核验服务暂不可用。')
                    result = self.verify_publication(conn, identity, publication)
                if self.numeric_projection is None:
                    raise ApiError(503, 'NUMERIC_OWNER_UNAVAILABLE', '恢复数值所属服务暂不可用。')
                numeric_material, numeric_check_ids = self.numeric_projection(conn, identity, record)
                p = record.payload
                return ContentRestoreDraftSnapshot(owner='authoring_restore', candidate=record.candidate,
                    source_ref=p.request.source_ref, base_ref=p.request.expected_current_ref, reason=p.request.reason,
                    proposed_block=p.proposed_block, body_markdown=p.source.body_markdown,
                    source_material_sha256=metadata_sha256(p.source.material), warnings=p.warnings,
                    state='published' if result else 'draft', published_ref=result,
                    numeric_material=numeric_material, numeric_check_ids=numeric_check_ids)
            finally:
                conn.rollback()
