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
from .draft_edits import DraftEditService
from .edit_publication import EditBlockPublication
from .content_restore import ContentRestoreService
from .restore_publication import RestoreBlockPublication
from .errors import ApiError
from .import_publication import ImportBlockPublication, unsupported
from .imports import ImportService
from .providers import validate_key
from .publication_admission import PublicationAdmissionService
from .publication_admission_models import PublicationAdmission
from .publication_admission_models import DraftPublishWrite
from .publication_models import PublicationHistory, PublicationRecord, EditPublicationRecord, RestorePublicationRecord, integrity, validated
from .review_history_models import ReviewDecisionRecord, ReviewMachineRecord
from .review_material_models import ImportReviewMaterial, EditReviewMaterial, RestoreReviewMaterial, CheckedReviewMaterial
from .review_service import ReviewService


class DraftPublicationService:
    def __init__(self, database: Database, reviews: ReviewService, imports: ImportService):
        self.database, self.reviews = database, reviews
        self.owner, self.content = ImportBlockPublication(imports), ContentService(database)
        self.admission = PublicationAdmissionService(reviews)
        self.edit_owner = EditBlockPublication(DraftEditService(database))
        self.restore_owner = RestoreBlockPublication(ContentRestoreService(database))

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
                or (isinstance(record, PublicationRecord) and humans[0].receipt.mathematical != 'NOT_APPLICABLE')
                or humans[0].receipt.sources != 'APPROVED'
                or machine.structural_report.structural != 'PASS'
                or machine.numeric.descriptor_sha256 != record.admission.numeric_observation_sha256):
            raise integrity()
        if isinstance(record, RestorePublicationRecord):
            restored = self.restore_owner.verify(conn, identity, record)
            expected_block, expected_body = restored.payload.proposed_block, restored.payload.source.body_markdown.encode()
        elif isinstance(record, EditPublicationRecord):
            edited = self.edit_owner.verify(conn, identity, record)
            expected_block, expected_body = edited.block, edited.body
        else:
            imported = self.owner.verify(conn, identity, record)
            expected_block, expected_body = imported.block, imported.body
        block, raw = self.content.verify_publication_in_transaction(conn, identity.workspace_id, record.result)
        if block != expected_block or raw != expected_body:
            raise integrity()
        return record.result

    def verify_recorded(self, conn: sqlite3.Connection, identity: SessionIdentity,
                        publication: PublicationHistory) -> dm.ContentRef:
        """Read-only owner port: authenticate the complete publication and human-review chain."""
        return self._verify(conn, self._access(conn, identity), publication)

    def _publish_edit(self, conn: sqlite3.Connection, current: SessionIdentity, repo: PublicationRepository,
                      material: CheckedReviewMaterial, body: DraftPublishWrite, key: str) -> dm.ContentRef:
        if repo.for_candidate(material.candidate) is not None:
            raise ApiError(409, 'DRAFT_ALREADY_PUBLISHED', '此精确候选已经发布。')
        prepared = self.edit_owner.prepare(conn, current, material.candidate)
        if prepared.material != material:
            raise integrity()
        identifier, adopted = 'publication_' + uuid4().hex, utc_now()
        repo.adopt(identifier, material.candidate, adopted, owner='authoring')
        repo.advance(identifier, 1, 'draft', 'in_review', utc_now())
        admission = self.admission.check(conn, current, material.candidate.draft_id, body)
        history, checked_material = self.reviews.read_publication_basis(conn, current, body.review_receipt_id)
        human = history.records[-1]
        if checked_material != material or not isinstance(human, ReviewDecisionRecord):
            raise integrity()
        repo.advance(identifier, 2, 'in_review', 'approved', utc_now())
        result = self.content.publish_edited_block_in_transaction(conn, current.workspace_id,
            prepared.record.base.ref, prepared.block, prepared.body)
        assert isinstance(admission, PublicationAdmission)
        record = EditPublicationRecord(version='edit-publication-v1', id=identifier,
            workspace_id=current.workspace_id, owner='authoring', candidate=material.candidate,
            actor_id=current.id, route=f'POST /drafts/{material.candidate.draft_id}/publish', command_key=key,
            request=body, admission=admission, human_record_sha256=metadata_sha256(human),
            edit_record_sha256=metadata_sha256(prepared.record), base=prepared.record.base,
            payload=prepared.record.payload, block=prepared.block, result=result,
            adopted_at=adopted, published_at=utc_now())
        return self._verify(conn, current, repo.finish(record))

    def _publish_restore(self, conn, current, repo, material, body, key):
        repo.require_unpublished_draft(material.candidate.draft_id)
        prepared = self.restore_owner.prepare(conn, current, material.candidate)
        if prepared != material.payload.record:
            raise integrity()
        identifier, adopted = 'publication_' + uuid4().hex, utc_now()
        repo.adopt(identifier, material.candidate, adopted, owner='authoring')
        repo.advance(identifier, 1, 'draft', 'in_review', utc_now())
        admission = self.admission.check(conn, current, material.candidate.draft_id, body)
        history, checked_material = self.reviews.read_publication_basis(conn, current, body.review_receipt_id)
        human = history.records[-1]
        if checked_material != material or not isinstance(human, ReviewDecisionRecord):
            raise integrity()
        repo.advance(identifier, 2, 'in_review', 'approved', utc_now())
        p = prepared.payload
        result = self.content.publish_restored_block_in_transaction(conn, current.workspace_id,
            p.request.expected_current_ref, p.request.source_ref, p.proposed_block, p.source.body_markdown.encode())
        source = self.restore_owner.freeze(conn, current, prepared)
        record = RestorePublicationRecord(version='restore-numeric-publication-v1' if p.proposed_block.kind == 'worked_example' else 'restore-publication-v1', id=identifier,
            workspace_id=current.workspace_id, owner='authoring', candidate=material.candidate, actor_id=current.id,
            route=f'POST /drafts/{material.candidate.draft_id}/publish', command_key=key, request=body,
            admission=admission, human_record_sha256=metadata_sha256(human), restore_record_sha256=metadata_sha256(prepared),
            payload=p, block=p.proposed_block, source=source, result=result, adopted_at=adopted, published_at=utc_now())
        return self._verify(conn, current, repo.finish(record))

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
                if isinstance(material.payload, RestoreReviewMaterial):
                    return self._publish_restore(conn, current, repo, material, body, key)
                if isinstance(material.payload, EditReviewMaterial):
                    return self._publish_edit(conn, current, repo, material, body, key)
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
                assert isinstance(admission, PublicationAdmission)
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
