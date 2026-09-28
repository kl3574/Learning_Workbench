"""Appendix A publish intent and a non-durable read-only admission observation.

Constructing either model grants no publication permission. A publisher must
invoke the real service again inside its own current write transaction.
"""
from typing import Literal, Self

from pydantic import model_validator
from packages.contracts import domain_models as dm
from ..authoring_dto import AuthoringModel


class DraftPublishWrite(AuthoringModel):
    expected_revision: dm.Revision
    expected_content_sha256: dm.Sha256
    review_receipt_id: dm.Id
    acknowledged_warning_codes: list[str]

    @model_validator(mode='after')
    def distinct_warnings(self) -> Self:
        if (len(set(self.acknowledged_warning_codes)) != len(self.acknowledged_warning_codes)
                or any(not value.strip() for value in self.acknowledged_warning_codes)):
            raise ValueError('Warning acknowledgments require distinct nonblank codes')
        return self


class PublicationAdmission(AuthoringModel):
    version: Literal['publication-admission-observation-v1']
    workspace_id: dm.Id
    candidate: dm.DraftCandidate
    review_receipt_id: dm.Id
    review_revision: dm.Revision
    receipt_sha256: dm.Sha256
    material_descriptor_sha256: dm.Sha256
    numeric_observation_sha256: dm.Sha256
    numeric_check_ids: list[dm.Id]
    numeric_coverage: Literal['complete', 'not_required_by_material']
    acknowledged_warning_codes: list[str]
    publication: Literal['NOT_RUN']
