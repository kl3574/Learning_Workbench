"""Publication adapter for the actual Restore owner and retained source provenance."""
from packages.contracts.canonical import metadata_sha256
from ..infrastructure.provenance_repository import ProvenanceRepository
from .publication_models import RestorePublicationRecord, validated, integrity


class RestoreBlockPublication:
    def __init__(self, restores):
        self.restores = restores

    def prepare(self, conn, identity, candidate):
        self.restores.require_current_candidate(conn, identity, candidate)
        return self.restores.record(conn, identity, candidate.draft_id)

    def freeze(self, conn, identity, record):
        return ProvenanceRepository(conn, identity.workspace_id).freeze_restored(record.payload.source.material.metadata,
            record.payload.proposed_block, self.restores.source.content.blobs.read)

    def verify(self, conn, identity, record):
        record = validated(RestorePublicationRecord, record)
        actual = self.restores.record(conn, identity, record.candidate.draft_id)
        material = self.restores.read_review_material(conn, identity, record.candidate)
        if (actual.candidate != record.candidate or actual.payload != record.payload or metadata_sha256(actual) != record.restore_record_sha256
                or record.admission.material_descriptor_sha256 != material.descriptor_sha256):
            raise integrity()
        block, raw = self.restores.source.content.verify_publication_in_transaction(conn, identity.workspace_id, record.result)
        provenance = ProvenanceRepository(conn, identity.workspace_id).verified_original(block, self.restores.source.content.blobs.read)
        if block != record.block or raw != actual.payload.source.body_markdown.encode() or provenance != record.source:
            raise integrity()
        return actual
