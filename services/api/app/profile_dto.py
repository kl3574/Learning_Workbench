"""Complete self-report writes; origin and timestamps are exclusively server data."""

from typing import Literal

from pydantic import Field, model_validator

from packages.contracts import domain_models as dm


class SelfAssessmentWrite(dm.StrictModel):
    concept_id: dm.Id
    level: Literal['not_learned', 'encountered', 'independent_use']


class ProfileWrite(dm.StrictModel):
    expected_revision: dm.Revision
    goals: list[str]
    goal_concept_ids: list[dm.Id]
    weekly_minutes: int = Field(ge=1, le=10080)
    language: str
    preferred_difficulty: Literal['beginner', 'intermediate', 'advanced']
    self_assessments: list[SelfAssessmentWrite]

    @model_validator(mode='after')
    def unique_concepts(self):
        assessments = [item.concept_id for item in self.self_assessments]
        if len(set(assessments)) != len(assessments) or len(set(self.goal_concept_ids)) != len(self.goal_concept_ids):
            raise ValueError('profile concept identities must be unique within each list')
        return self
