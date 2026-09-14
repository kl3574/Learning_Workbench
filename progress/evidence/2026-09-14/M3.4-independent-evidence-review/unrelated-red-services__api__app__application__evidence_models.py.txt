"""Private immutable Learning bindings; never serialized as HTTP answer content."""

from typing import Literal

from pydantic import Field, model_validator

from packages.contracts import domain_models as dm

from .assessment_evidence_access import SubmissionWitness
from .eligibility_models import EligibilityDecision, ItemPrerequisites, QualificationBasis
from .practice_help_access import HelpFacts


class FrozenItem(dm.StrictModel):
    prerequisites: ItemPrerequisites
    help: HelpFacts


class FrozenPrerequisites(dm.StrictModel):
    version: Literal['eligibility-v1'] = 'eligibility-v1'
    submission: SubmissionWitness
    recorded_at: dm.UTC
    items: list[FrozenItem]

    @model_validator(mode='after')
    def exact_items(self):
        if [item.prerequisites.question_ref for item in self.items] != self.submission.question_refs:
            raise ValueError('frozen prerequisites must retain assignment order')
        return self


class SubmissionBasis(dm.StrictModel):
    workspace_id: dm.Id
    attempt_id: dm.Id
    basis: QualificationBasis
    recorded_at: dm.UTC
    prerequisites: FrozenPrerequisites | None
    prerequisites_sha256: dm.Sha256 | None

    @model_validator(mode='after')
    def actual_basis(self):
        if self.basis == 'submission_frozen':
            if self.prerequisites is None or self.prerequisites_sha256 is None:
                raise ValueError('new submission must have frozen prerequisites')
            if (self.prerequisites.submission.workspace_id != self.workspace_id
                    or self.prerequisites.submission.attempt_id != self.attempt_id
                    or self.prerequisites.recorded_at != self.recorded_at):
                raise ValueError('submission prerequisite binding mismatch')
        elif self.prerequisites is not None or self.prerequisites_sha256 is not None:
            raise ValueError('history must never invent a frozen prerequisite snapshot')
        return self


class BoundItem(dm.StrictModel):
    prerequisites: ItemPrerequisites
    decision: EligibilityDecision
    evidence: list[dm.Evidence]


class GradeBinding(dm.StrictModel):
    version: Literal['eligibility-v1'] = 'eligibility-v1'
    workspace_id: dm.Id
    attempt_id: dm.Id
    grading_revision: dm.Revision
    result_sha256: dm.Sha256
    qualification_basis: QualificationBasis
    prerequisites_sha256: dm.Sha256 | None
    finalized_at: dm.UTC
    recorded_at: dm.UTC
    event: dm.LearningEvent
    event_sha256: dm.Sha256
    progress_revision: dm.Revision
    outbox_id: dm.Id
    items: list[BoundItem] = Field(min_length=1)

    @model_validator(mode='after')
    def binding_identity(self):
        if (self.event.workspace_id != self.workspace_id or self.event.attempt_id != self.attempt_id
                or self.event.kind != 'grade_finalized' or self.event.actor != 'server'
                or self.event.origin != 'native' or self.event.occurred_at != self.recorded_at):
            raise ValueError('grade finalized event must match its binding')
        if (self.qualification_basis == 'submission_frozen') != (self.prerequisites_sha256 is not None):
            raise ValueError('grade must preserve the original submission basis')
        refs = [item.prerequisites.question_ref.id for item in self.items]
        ids = [value.id for item in self.items for value in item.evidence]
        if len(refs) != len(set(refs)) or len(ids) != len(set(ids)):
            raise ValueError('duplicate grade evidence identity')
        return self
