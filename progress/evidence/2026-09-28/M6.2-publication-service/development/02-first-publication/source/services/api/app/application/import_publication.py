"""Import-owned prepare/finish/history ports; never completes the whole Import."""
import sqlite3

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes
from ..import_dto import BlockDraftPayload
from ..infrastructure.import_repository import ImportRepository, json_object
from ..infrastructure.provenance_repository import FrozenProvenance
from ..infrastructure.security import SessionIdentity, current_session_identity
from .authoring_context import AuthoringContext
from .errors import ApiError
from .imports import ImportService, visibility, preview_visibility
from .jobs import require_pending_import_confirmation
from .publication_models import PreparedImportBlock, PublicationRecord, integrity, validated
from .publication_provenance import PublicationProvenance
from .review_material_models import CheckedReviewMaterial, ImportReviewMaterial


def unsupported() -> ApiError:
    return ApiError(409, 'PUBLICATION_OWNER_SCOPE_UNSUPPORTED', '当前发布仅支持待确认导入中无依赖的公开纯文本块。')


class ImportBlockPublication:
    def __init__(self, imports: ImportService):
        self.imports = imports

    def _read(self, conn: sqlite3.Connection, identity: SessionIdentity,
              candidate: dm.DraftCandidate) -> tuple[PreparedImportBlock, sqlite3.Row, sqlite3.Row]:
        if not conn.in_transaction:
            raise ApiError(409, 'TRANSACTION_REQUIRED', '导入发布核验需要当前事务。')
        current = current_session_identity(conn, identity)
        AuthoringContext.check_access(conn, current)
        candidate = validated(dm.DraftCandidate, candidate)
        material = validated(CheckedReviewMaterial, self.imports.read_review_material(conn, current, candidate))
        if not isinstance(material.payload, ImportReviewMaterial) or not isinstance(material.payload.payload, BlockDraftPayload):
            raise unsupported()
        payload = material.payload
        block = validated(dm.ContentBlock, payload.payload.metadata)
        row = ImportRepository(conn, current.workspace_id).load(payload.import_id)
        draft = conn.execute('SELECT * FROM drafts WHERE id=? AND workspace_id=?',
                             (candidate.draft_id, current.workspace_id)).fetchone()
        if draft is None:
            raise integrity()
        options, metadata = json_object(row['input_json']), json_object(row['source_metadata'])
        preview = self.imports._preview_data(row)
        if (options.get('kind') not in {'markdown', 'text'} or options.get('archive_detected') is not False
                or options.get('target_ref') is not None or metadata.get('visibility_verified') is not True
                or visibility(row) != 'learner' or preview_visibility(row) != 'learner'
                or preview.get('solutions') != [] or metadata.get('symbols') != []
                or metadata.get('assets', {}) or metadata.get('untrusted_quality_receipt')
                or draft['base_ref_json'] is not None or candidate.draft_revision != 1
                or block.revision != 1 or block.kind != 'text' or block.concepts or block.depends_on):
            raise unsupported()
        return PreparedImportBlock(material, block, payload.payload.body_markdown.encode('utf-8'),
                                    self.imports.frozen_budgets(row)), row, draft

    def prepare(self, conn: sqlite3.Connection, identity: SessionIdentity,
                candidate: dm.DraftCandidate) -> PreparedImportBlock:
        prepared, row, draft = self._read(conn, identity, candidate)
        if (row['status'] != 'preview_ready' or row['job_status'] != 'awaiting_approval'
                or draft['status'] != 'draft'):
            raise ApiError(409, 'PUBLICATION_IMPORT_NOT_PENDING', '导入已终止或提交，不能新发布其候选。')
        require_pending_import_confirmation(conn, identity.workspace_id, row['job_id'], row['input_sha256'])
        return prepared

    def freeze(self, conn: sqlite3.Connection, identity: SessionIdentity,
               prepared: PreparedImportBlock, result: dm.ContentRef) -> FrozenProvenance:
        actual = self.prepare(conn, identity, prepared.material.candidate)
        if (canonical_bytes(actual.material) != canonical_bytes(prepared.material)
                or actual.body != prepared.body or actual.block != prepared.block):
            raise integrity()
        payload = actual.material.payload
        if not isinstance(payload, ImportReviewMaterial) or result.sha256 != payload.candidate.candidate_sha256:
            raise integrity()
        source = PublicationProvenance.freeze(conn, identity, payload.import_id, actual.block)
        self._source_matches(source, actual)
        if source.block_ref != result:
            raise integrity()
        return source

    @staticmethod
    def _source_matches(source: FrozenProvenance, prepared: PreparedImportBlock) -> None:
        payload = prepared.material.payload
        if (not isinstance(payload, ImportReviewMaterial) or not isinstance(payload.payload, BlockDraftPayload)
                or source.source.id != payload.source_id or source.source.sha256 != payload.original_input_sha256
                or source.citations != payload.payload.citations or source.warnings != payload.warnings):
            raise integrity()

    def verify(self, conn: sqlite3.Connection, identity: SessionIdentity,
               record: PublicationRecord) -> PreparedImportBlock:
        record = validated(PublicationRecord, record)
        prepared, row, _ = self._read(conn, identity, record.candidate)
        payload = prepared.material.payload
        if (row['status'] not in {'preview_ready', 'cancelled', 'committed'}
                or not isinstance(payload, ImportReviewMaterial) or payload.import_id != record.import_id
                or payload.original_input_sha256 != record.original_input_sha256
                or prepared.material.descriptor_sha256 != record.admission.material_descriptor_sha256
                or prepared.block != record.block):
            raise integrity()
        source = PublicationProvenance.read(conn, identity, record.import_id, prepared.block)
        self._source_matches(source, prepared)
        if source != record.source:
            raise integrity()
        return prepared
