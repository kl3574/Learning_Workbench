"""Quality's immutable report bytes; authorization remains with ReviewService.

The report precedes its artifact binding and receipt. It never hashes itself or
the later machine record, so the content graph has no circular hash dependency.
"""
from typing import Literal

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, metadata_sha256
from ..authoring_dto import AuthoringModel
from .review_checks import StructuralReviewReport
from .review_material_models import CheckedReviewMaterial
from .review_models import ReviewJobInput
from .review_numeric_models import ReviewNumericObservation
from .restore_review_numeric import RestoreReviewNumericObservation

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
    numeric_observation: ReviewNumericObservation | RestoreReviewNumericObservation
    mathematical: Literal['NOT_RUN']
    sources: Literal['NOT_RUN']
    independent_pedagogy: Literal['NOT_RUN']
    scope: Literal['Only declared structure and existing numeric history; no new execution or mathematical/source/pedagogical verification.']


def report_bytes(value: ReviewJobInput, material: CheckedReviewMaterial,
                 numeric: ReviewNumericObservation | RestoreReviewNumericObservation, structural: StructuralReviewReport) -> bytes:
    return canonical_bytes(ReviewReport(version='quality-review-report-v1', review_id=value.review_id,
        candidate=value.candidate, input_sha256=metadata_sha256(value),
        material_descriptor_sha256=material.descriptor_sha256, structure=structural,
        numerical_examples_requested='numerical_examples' in value.request.checks, numeric_observation=numeric,
        mathematical='NOT_RUN', sources='NOT_RUN', independent_pedagogy='NOT_RUN',
        scope='Only declared structure and existing numeric history; no new execution or mathematical/source/pedagogical verification.'))


