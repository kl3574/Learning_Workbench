"""Strict review requests from Appendix A; no client-authored machine verdicts."""
from typing import Annotated, Literal, Self

from pydantic import Field, model_validator
from packages.contracts import domain_models as dm
from .authoring_dto import AuthoringModel, NonBlank

ReviewCheck = Literal['structure', 'sources', 'mathematics', 'numerical_examples']
HumanVerdict = Literal['APPROVED', 'REJECTED', 'NOT_APPLICABLE']


class DraftReviewWrite(AuthoringModel):
    expected_revision: dm.Revision
    checks: Annotated[list[ReviewCheck], Field(min_length=1, max_length=4)]
    reviewer_note: str

    @model_validator(mode='after')
    def distinct_checks(self) -> Self:
        if len(set(self.checks)) != len(self.checks):
            raise ValueError('Each requested check must be distinct')
        return self


class ReviewDecisionWrite(AuthoringModel):
    expected_revision: dm.Revision
    candidate_sha256: dm.Sha256
    mathematical: HumanVerdict
    sources: HumanVerdict
    reason: NonBlank
    evidence_artifact_ids: list[dm.Id]

    @model_validator(mode='after')
    def distinct_artifacts(self) -> Self:
        if len(set(self.evidence_artifact_ids)) != len(self.evidence_artifact_ids):
            raise ValueError('Each evidence artifact must be distinct')
        return self
