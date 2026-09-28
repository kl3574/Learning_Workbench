"""Explicit single-block publication, with real owners in one writer transaction."""
import sqlite3
from uuid import uuid4

from pydantic import TypeAdapter
from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256
from ..infrastructure.database import Database, utc_now
from ..infrastructure.publication_repository import PublicationRepository
from ..infrastructure.security import SessionIdentity, current_session_identity
from .authoring_context import AuthoringContext
from .content import ContentService
from .errors import ApiError
from .import_publication import ImportBlockPublication, unsupported
from .imports import ImportService
from .providers import validate_key
from .publication_admission import PublicationAdmissionService
from .publication_admission_models import DraftPublishWrite
from .publication_models import PublicationHistory, PublicationRecord, integrity, validated
from .review_history_models import ReviewDecisionRecord, ReviewMachineRecord
from .review_material_models import ImportReviewMaterial
from .review_service import ReviewService


class DraftPublicationService:
    def __init__(self, database: Database, reviews: ReviewService, imports: ImportService):
        self.database, self.reviews = database, reviews
        self.owner, self.content = ImportBlockPublication(imports), ContentService(database)
        self.admission = PublicationAdmissionService(reviews)

    @staticmethod
    def _access(conn: sqlite3.Connection, identity: SessionIdentity) -> SessionIdentity:
        current = current_session_identity(conn, identity)
        AuthoringContext.check_access(conn, current)
        return current

    def _verify(self, conn: sqlite3.Connection, identity: SessionIdentity,
                publication: PublicationHistory) -> dm.ContentRef:
        record = publication.record
        self.admission.verify_recorded(conn, identity, record.candidate.draft_id, record.request, record.admission)
        history, material = self.reviews.read_publication_basis(conn, identity, record.request.review_receipt_id)
        if (record.workspace_id != identity.workspace_id or material.candidate != record.candidate
                or material.descriptor_sha256 != record.admission.material_descriptor_sha256
                or not history.records or not isinstance(history.records[0], ReviewMachineRecord)):
            raise integrity()
        machine = history.records[0]
        humans = [item for item in history.records if isinstance(item, ReviewDecisionRecord)
                  and item.receipt.revision == record.admission.review_revision]
        if (len(humans) != 1 or metadata_sha256(humans[0]) != record.human_record_sha256
                or metadata_sha256(humans[0].receipt) != record.admission.receipt_sha256
                or humans[0].receipt.mathematical != 'NOT_APPLICABLE' or humans[0].receipt.sources != 'APPROVED'
                or machine.structural_report.structural != 'PASS'
                or machine.numeric.descriptor_sha256 != record.admission.numeric_observation_sha256):
            raise integrity()
        prepared = self.owner.verify(conn, identity, record)
        block, raw = self.content.verify_publication_in_transaction(conn, identity.workspace_id, record.result)
        if block != prepared.block or raw != prepared.body:
            raise integrity()
        return record.result

    def publish(self, identity: SessionIdentity, draft_id: str, body: DraftPublishWrite, key: str) -> dm.ContentRef:
        key, body = validate_key(key), validated(DraftPublishWrite, body)
        try:
            draft_id = TypeAdapter(dm.Id).validate_python(draft_id, strict=True)
        except (ValueError, TypeError):
            raise ApiError(422, 'SCHEMA_INVALID', '发布草稿标识无效。') from None
        route = f'POST /drafts/{draft_id}/publish'
        try:
            with self.database.transaction() as conn:
                current = self._access(conn, identity)
                repo = PublicationRepository(conn, current.workspace_id)
                replay = repo.replay(current.id, route, key, body)
                if replay is not None:
                    return self._verify(conn, current, replay)
                history, material = self.reviews.read_publication_basis(conn, current, body.review_receipt_id)
                if (material.candidate.draft_id != draft_id or material.candidate.draft_revision != body.expected_revision
                        or material.candidate.candidate_sha256 != body.expected_content_sha256):
                    raise ApiError(412, 'PUBLISH_CANDIDATE_MISMATCH', '发布请求与精确审核候选不符。')
                if not isinstance(material.payload, ImportReviewMaterial):
                    raise unsupported()
                prepared = self.owner.prepare(conn, current, material.candidate)
                if prepared.material != material:
                    raise integrity()
                identifier, adopted = 'publication_' + uuid4().hex, utc_now()
                repo.adopt(identifier, material.candidate, adopted)
                repo.advance(identifier, 1, 'draft', 'in_review', utc_now())
                admission = self.admission.check(conn, current, draft_id, body)
                human = history.records[-1]
                if (not isinstance(human, ReviewDecisionRecord) or human.receipt.mathematical != 'NOT_APPLICABLE'
                        or human.receipt.sources != 'APPROVED'):
                    raise unsupported()
                repo.advance(identifier, 2, 'in_review', 'approved', utc_now())
                result = self.content.publish_new_block_in_transaction(conn, current.workspace_id,
                    prepared.block, prepared.body, prepared.budgets)
                source = self.owner.freeze(conn, current, prepared, result)
                record = PublicationRecord(version='draft-publication-v1', id=identifier,
                    workspace_id=current.workspace_id, owner='import', candidate=material.candidate,
                    actor_id=current.id, route=route, command_key=key, request=body, admission=admission,
                    human_record_sha256=metadata_sha256(human), import_id=material.payload.import_id,
                    original_input_sha256=material.payload.original_input_sha256, block=prepared.block,
                    source=source, result=result, adopted_at=adopted, published_at=utc_now())
                published = repo.finish(record)
                return self._verify(conn, current, published)
        except sqlite3.Error:
            raise ApiError(503, 'PUBLICATION_STORAGE_UNAVAILABLE', '发布存储暂不可用，未确认新的发布。', True) from None
