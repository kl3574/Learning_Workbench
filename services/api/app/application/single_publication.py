"""Single generation publication through the registered Authoring owner only."""
from dataclasses import dataclass
from uuid import uuid4

from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256
from .draft_candidates import DraftCandidates
from .publication_models import SinglePublicationRecord, integrity, single_block, validated
from .review_material_models import CheckedReviewMaterial, SingleReviewMaterial


@dataclass(frozen=True, repr=False)
class PreparedSingleBlock:
    material: CheckedReviewMaterial
    block: dm.ContentBlock
    body: bytes


class SingleBlockPublication:
    def __init__(self, candidates: DraftCandidates):
        self.candidates = candidates

    def prepare(self, conn, identity, candidate, identifier: str | None = None) -> PreparedSingleBlock:
        material = self.candidates.read_review_material(conn, identity, candidate.draft_id, candidate.draft_revision)
        if (material.source_kind != 'authoring_single' or material.candidate != candidate
                or not isinstance(material.payload, SingleReviewMaterial)):
            raise integrity()
        payload = material.payload.record.payload
        block = single_block(payload, identifier or 'generated_' + uuid4().hex)
        return PreparedSingleBlock(material, block, payload.body_markdown.encode())

    def verify(self, conn, identity, record: SinglePublicationRecord) -> PreparedSingleBlock:
        record = validated(SinglePublicationRecord, record)
        actual = self.prepare(conn, identity, record.candidate, record.block.id)
        assert isinstance(actual.material.payload, SingleReviewMaterial)
        original = actual.material.payload.record
        if (record.payload != original.payload or record.block != actual.block
                or record.generation_record_sha256 != metadata_sha256(original)
                or record.source_job_id != original.source_job_id
                or record.admission.material_descriptor_sha256 != actual.material.descriptor_sha256):
            raise integrity()
        return actual
