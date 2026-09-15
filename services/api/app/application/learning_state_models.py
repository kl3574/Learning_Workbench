"""Strict metadata ports for M4.1; no answers or private grading snapshots."""

from typing import Literal

from pydantic import Field, model_validator

from packages.contracts import domain_models as dm

from .eligibility_models import EligibilityReason, QualificationBasis, Skill


class EvidenceObservation(dm.StrictModel):
    evidence: dm.Evidence
    question_ref: dm.ContentRef
    concept_ref: dm.ContentRef
    assessment_ref: dm.ContentRef
    attempt_id: dm.Id
    grading_revision: dm.Revision
    submitted_at: dm.UTC
    exposure_group: dm.Id
    qualification_basis: QualificationBasis
    reason_codes: list[EligibilityReason]

    @model_validator(mode='after')
    def exact_types(self):
        if (self.question_ref.entity != 'question' or self.concept_ref.entity != 'concept'
                or self.assessment_ref.entity != 'assessment' or self.evidence.concept_id != self.concept_ref.id):
            raise ValueError('observation requires exact question/concept/assessment references')
        return self


class EvidenceApplicability(dm.StrictModel):
    status: Literal['usable', 'pending_review', 'confirmed_stale']
    reason_codes: list[str]
    checked_refs: list[dm.ContentRef]
    check_scope: Literal['exact_semantic_dependencies'] = 'exact_semantic_dependencies'


class ScopedConcept(dm.StrictModel):
    ref: dm.ContentRef
    title: str
    skill_dimensions: list[Skill]

    @model_validator(mode='after')
    def concept_type(self):
        if self.ref.entity != 'concept' or len(self.skill_dimensions) != len(set(self.skill_dimensions)):
            raise ValueError('invalid scoped concept')
        return self


class ContentLearningScope(dm.StrictModel):
    course_refs: list[dm.ContentRef]
    concepts: list[ScopedConcept]


class SubmissionActivity(dm.StrictModel):
    target_ref: dm.ContentRef
    source_id: dm.Id
    event_id: dm.Id
    submitted_at: dm.UTC
    question_refs: list[dm.ContentRef]

    @model_validator(mode='after')
    def submitted_target(self):
        if self.target_ref.entity not in {'practice_set', 'assessment'}:
            raise ValueError('submission activity must be a real practice or assessment')
        return self


class PracticeHelpActivity(dm.StrictModel):
    practice_session_id: dm.Id
    practice_set_ref: dm.ContentRef
    question_ref: dm.ContentRef
    event_id: dm.Id
    occurred_at: dm.UTC
    kind: Literal['hint_revealed', 'solution_revealed']


class PracticeParticipation(dm.StrictModel):
    submissions: list[SubmissionActivity] = Field(default_factory=list)
    help: list[PracticeHelpActivity] = Field(default_factory=list)
