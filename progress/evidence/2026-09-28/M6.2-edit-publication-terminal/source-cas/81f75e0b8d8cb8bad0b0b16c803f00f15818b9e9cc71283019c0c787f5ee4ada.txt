"""Edit-owned publication material: exact immutable history and current-head admission."""
from dataclasses import dataclass
import sqlite3

from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256
from ..infrastructure.security import SessionIdentity
from .draft_candidate_models import ResolvedDraftCandidate
from .draft_edit_models import DraftEditRecord
from .draft_edits import DraftEditService
from .publication_models import EditPublicationRecord, integrity, validated
from .review_material_models import CheckedReviewMaterial, EditReviewMaterial, checked_material


@dataclass(frozen=True, repr=False)
class PreparedEditBlock:
    material: CheckedReviewMaterial
    record: DraftEditRecord
    block: dm.ContentBlock
    body: bytes


class EditBlockPublication:
    def __init__(self, edits: DraftEditService):
        self.edits = edits

    def _read(self, conn: sqlite3.Connection, identity: SessionIdentity, candidate: dm.DraftCandidate,
              *, require_current: bool) -> PreparedEditBlock:
        record = self.edits.publication_record(conn, identity, candidate, require_current=require_current)
        material = checked_material(ResolvedDraftCandidate(record.workspace_id, 'authoring', 'authoring_edit', candidate),
                                    EditReviewMaterial(record=record))
        block = validated(dm.ContentBlock, record.base.metadata.model_copy(update={
            'revision': record.base.ref.revision + 1, 'title': record.payload.title,
            'body_sha256': record.payload.body_sha256}))
        return PreparedEditBlock(material, record, block, record.payload.body_markdown.encode('utf-8'))

    def prepare(self, conn: sqlite3.Connection, identity: SessionIdentity,
                candidate: dm.DraftCandidate) -> PreparedEditBlock:
        return self._read(conn, identity, candidate, require_current=True)

    def verify(self, conn: sqlite3.Connection, identity: SessionIdentity,
               record: EditPublicationRecord) -> PreparedEditBlock:
        record = validated(EditPublicationRecord, record)
        prepared = self._read(conn, identity, record.candidate, require_current=False)
        if (prepared.record.base != record.base or prepared.record.payload != record.payload
                or metadata_sha256(prepared.record) != record.edit_record_sha256
                or prepared.material.descriptor_sha256 != record.admission.material_descriptor_sha256
                or prepared.block != record.block):
            raise integrity()
        return prepared
