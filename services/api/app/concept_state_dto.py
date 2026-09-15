"""Explainable exact-concept state, with distinct evidence and participation units."""

from typing import Literal

from pydantic import Field, model_validator

from packages.contracts import domain_models as dm

from .application.eligibility_models import Skill
from .application.learning_state_models import (
    EvidenceApplicability, EvidenceObservation, PracticeHelpActivity, ScopedConcept, SubmissionActivity,
)


class ConceptStateSource(EvidenceObservation):
    applicability: EvidenceApplicability


class ConceptState(dm.StrictModel):
    concept_id: dm.Id
    concept_ref: dm.ContentRef
    title: str
    skill: Skill
    evidence_state: Literal['none', 'preliminary', 'needs_support', 'consistent']
    independent_count: int = Field(ge=0)
    assisted_count: int = Field(ge=0)
    stale_count: int = Field(ge=0)
    repeated_count: int = Field(ge=0)
    unknown_count: int = Field(ge=0)
    null_count: int = Field(ge=0)
    pending_review_count: int = Field(ge=0)
    self_report: dm.SelfAssessment | None
    evidence_ids: list[dm.Id]
    state_input_evidence_ids: list[dm.Id] = Field(max_length=3)
    sources: list[ConceptStateSource]
    practice_submission_count: int = Field(ge=0)
    hint_count: int = Field(ge=0)
    solution_count: int = Field(ge=0)
    practice_submission_sources: list[SubmissionActivity]
    hint_sources: list[PracticeHelpActivity]
    solution_sources: list[PracticeHelpActivity]
    rule_version: Literal['learning-state-v1'] = 'learning-state-v1'

    @model_validator(mode='after')
    def exact_sources(self):
        if self.concept_ref.entity != 'concept' or self.concept_ref.id != self.concept_id:
            raise ValueError('concept state requires one exact concept identity')
        if self.self_report is not None and self.self_report.concept_id != self.concept_id:
            raise ValueError('self-report belongs to a different concept identity')
        ids = [item.evidence.id for item in self.sources]
        if (self.evidence_ids != ids or len(ids) != len(set(ids))
                or len(self.state_input_evidence_ids) != len(set(self.state_input_evidence_ids))
                or not set(self.state_input_evidence_ids) <= set(ids)
                or any(item.concept_ref != self.concept_ref or item.evidence.skill != self.skill for item in self.sources)):
            raise ValueError('state sources require unique evidence with matching exact concept and skill')
        if (self.practice_submission_count != len(self.practice_submission_sources)
                or self.hint_count != len(self.hint_sources) or self.solution_count != len(self.solution_sources)
                or any(item.kind != 'hint_revealed' for item in self.hint_sources)
                or any(item.kind != 'solution_revealed' for item in self.solution_sources)):
            raise ValueError('participation counts and explicit event kinds must match their sources')
        return self


class ConceptStateResponse(dm.StrictModel):
    items: list[ConceptState]
    course_refs: list[dm.ContentRef]
    concepts: list[ScopedConcept]
    rule_version: Literal['learning-state-v1'] = 'learning-state-v1'
    calibration: Literal['uncalibrated'] = 'uncalibrated'
    evidence_count_unit: Literal['question_attempts'] = 'question_attempts'
    practice_submission_count_unit: Literal['sessions'] = 'sessions'
    help_count_unit: Literal['events'] = 'events'

    @model_validator(mode='after')
    def unique_rows(self):
        keys = [(item.concept_ref.id, item.concept_ref.revision, item.concept_ref.sha256, item.skill) for item in self.items]
        if len(set(keys)) != len(keys) or any(ref.entity != 'course' for ref in self.course_refs):
            raise ValueError('concept states require unique exact concept/skill rows and real course scope')
        refs = [value.ref.model_dump_json() for value in self.concepts]
        if len(refs) != len(set(refs)) or any(item.concept_ref.model_dump_json() not in refs for item in self.items):
            raise ValueError('concept rows require a unique complete concept catalog')
        return self
