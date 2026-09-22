"""Review Job inputs bind intent to a candidate; construction grants no authority."""
from typing import Literal, Self

from pydantic import model_validator
from packages.contracts import domain_models as dm
from ..authoring_dto import AuthoringModel
from ..review_dto import DraftReviewWrite
from .draft_candidate_models import DraftSourceKind


class ReviewJobInput(AuthoringModel):
    version: Literal['draft-review-job-v1']
    workspace_id: dm.Id
    review_id: dm.Id
    source_kind: DraftSourceKind
    candidate: dm.DraftCandidate
    request: DraftReviewWrite
    creator_session_id: dm.Id
    rules_version: Literal['draft-review-rules-v1']
    created_at: dm.UTC

    @model_validator(mode='after')
    def same_revision(self) -> Self:
        if self.request.expected_revision != self.candidate.draft_revision:
            raise ValueError('Review intent must retain its original candidate revision')
        return self
