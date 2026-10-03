"""Quality's immutable report bytes; authorization remains with ReviewService.

The report precedes its artifact binding and receipt. It never hashes itself or
the later machine record, so the content graph has no circular hash dependency.
"""
import sqlite3
from typing import Literal
from uuid import uuid4

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256, sha256_bytes
from ..authoring_dto import AuthoringModel
from ..import_dto import DownloadArtifact
from ..infrastructure.blobs import BlobStore
from ..infrastructure.content_repository import ContentRepository
from ..infrastructure.database import utc_now
from ..infrastructure.review_repository import integrity
from .review_checks import StructuralReviewReport
from .review_history_models import ReviewArtifactBinding, ReviewMachineRecord
from .review_material_models import CheckedReviewMaterial
from .review_models import ReviewJobInput
from .review_numeric_models import ReviewNumericObservation

PROFILE = 'quality_review_report'
FILENAME = 'review-report.json'


class ReviewReport(AuthoringModel):
    version: Literal['quality-review-report-v1']
    review_id: dm.Id
    candidate: dm.DraftCandidate
    input_sha256: dm.Sha256
    material_descriptor_sha256: dm.Sha256
    structure: StructuralReviewReport
    numerical_examples_requested: bool
    numeric_observation: ReviewNumericObservation
    mathematical: Literal['NOT_RUN']
    sources: Literal['NOT_RUN']
    independent_pedagogy: Literal['NOT_RUN']
    scope: Literal['Only declared structure and existing numeric history; no new execution or mathematical/source/pedagogical verification.']


def report_bytes(value: ReviewJobInput, material: CheckedReviewMaterial,
                 numeric: ReviewNumericObservation, structural: StructuralReviewReport) -> bytes:
    return canonical_bytes(ReviewReport(version='quality-review-report-v1', review_id=value.review_id,
        candidate=value.candidate, input_sha256=metadata_sha256(value),
        material_descriptor_sha256=material.descriptor_sha256, structure=structural,
        numerical_examples_requested='numerical_examples' in value.request.checks, numeric_observation=numeric,
        mathematical='NOT_RUN', sources='NOT_RUN', independent_pedagogy='NOT_RUN',
        scope='Only declared structure and existing numeric history; no new execution or mathematical/source/pedagogical verification.'))


class ReviewArtifacts:
    def __init__(self, store: BlobStore):
        self.store = store

    def write(self, conn: sqlite3.Connection, value: ReviewJobInput, raw: bytes) -> ReviewArtifactBinding:
        if not conn.in_transaction:
            raise integrity()
        info = self.store.write(raw)
        previous = conn.execute('SELECT * FROM content_blobs WHERE sha256=?', (info.sha256,)).fetchone()
        if previous is not None and ContentRepository.decode_blob(previous) != info:
            raise integrity()
        now, identifier = utc_now(), 'artifact_' + uuid4().hex
        conn.execute('INSERT OR IGNORE INTO content_blobs VALUES(?,?,?,?)',
                     (info.sha256, info.relative_path, info.size, now))
        manifest = canonical_bytes(dict(version=1, filename=FILENAME, media_type='application/json',
                                        size=info.size, sha256=info.sha256)).decode()
        conn.execute('INSERT INTO artifacts VALUES(?,?,?,?,?,?,?,?)', (identifier, value.workspace_id,
            value.review_id, info.sha256, PROFILE, manifest, 'author_private', now))
        artifact = DownloadArtifact(artifact_id=identifier, filename=FILENAME, media_type='application/json',
            size=info.size, sha256=info.sha256, download_path=f'/api/v1/artifacts/{identifier}/download')
        return ReviewArtifactBinding(version='review-artifact-binding-v1', workspace_id=value.workspace_id,
            candidate=value.candidate, artifact=artifact, artifact_owner='quality', source_job_id=value.review_id,
            profile=PROFILE, manifest_sha256=sha256_bytes(manifest.encode()), purpose='machine_report', bound_at=now)

    def read(self, conn: sqlite3.Connection, value: ReviewJobInput,
             machine: ReviewMachineRecord) -> tuple[bytes, DownloadArtifact]:
        binding = machine.report
        identifier = binding.artifact.artifact_id
        row = conn.execute('SELECT * FROM artifacts WHERE id=? AND workspace_id=?',
                            (identifier, value.workspace_id)).fetchone()
        blob = conn.execute('SELECT * FROM content_blobs WHERE sha256=?', (binding.artifact.sha256,)).fetchone()
        expected = report_bytes(value, machine.material, machine.numeric, machine.structural_report)
        artifact = DownloadArtifact(artifact_id=identifier, filename=FILENAME, media_type='application/json',
            size=len(expected), sha256=sha256_bytes(expected), download_path=f'/api/v1/artifacts/{identifier}/download')
        manifest = canonical_bytes(dict(version=1, filename=FILENAME, media_type='application/json',
            size=artifact.size, sha256=artifact.sha256)).decode()
        if (not conn.in_transaction or row is None or blob is None or binding.artifact != artifact
                or row['job_id'] != value.review_id or row['profile'] != PROFILE
                or binding.profile != PROFILE or row['visibility'] != 'author_private'
                or row['blob_sha256'] != artifact.sha256 or row['manifest_json'] != manifest
                or sha256_bytes(manifest.encode()) != binding.manifest_sha256):
            raise integrity()
        info = ContentRepository.decode_blob(blob)
        if info.sha256 != artifact.sha256 or info.size != artifact.size:
            raise integrity()
        raw = self.store.read(artifact.sha256, expected_size=artifact.size)
        if raw != expected:
            raise integrity()
        return raw, artifact
