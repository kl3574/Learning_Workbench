"""Closed recommendation projections from PRODUCT_DESIGN.md v3.0.1 appendix A.

These application DTOs are deliberately distinct from the frozen core
Recommendation. Cross-object ownership, hashes, history and grading provenance
are checked by their owning application ports before constructing this view.
"""

from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import Field, StringConstraints, model_validator

from packages.contracts import domain_models as dm


RecommendationReason = Literal[
    'prerequisite_gap', 'assessment_error', 'review_due', 'next_route_step',
    'user_goal', 'read_without_practice', 'practice_without_independent',
]
RecommendationAction = Literal['read', 'practice', 'test', 'review', 'inspect_source']
NonEmpty = Annotated[str, StringConstraints(min_length=1)]


def _unique(values: Sequence[str], label: str) -> None:
    if len(values) != len(set(values)):
        raise ValueError(f'duplicate {label}')


class RecommendationDecisionWrite(dm.StrictModel):
    decision: Literal['accepted', 'dismissed']
    reason: str | None


class RecommendationEvidenceRef(dm.StrictModel):
    evidence: dm.Evidence
    question_ref: dm.ContentRef
    concept_ref: dm.ContentRef
    assessment_ref: dm.ContentRef
    attempt_id: dm.Id
    grading_revision: dm.Revision
    submitted_at: dm.UTC
    applicability: Literal['usable', 'pending_review', 'confirmed_stale']
    grading_origin: Literal['deterministic', 'human_review', 'unknown']

    @model_validator(mode='after')
    def exact_identity(self):
        if ((self.question_ref.entity, self.concept_ref.entity, self.assessment_ref.entity)
                != ('question', 'concept', 'assessment')
                or self.concept_ref.id != self.evidence.concept_id):
            raise ValueError('evidence must bind exact question, concept and assessment identities')
        return self


class RecommendationActivityRef(dm.StrictModel):
    kind: Literal['read_marked', 'practice_submitted', 'test_submitted']
    event_id: dm.Id
    target_ref: dm.ContentRef
    source_id: dm.Id | None
    occurred_at: dm.UTC

    @model_validator(mode='after')
    def source_kind(self):
        if self.kind == 'read_marked':
            if self.source_id is not None or self.target_ref.entity not in {'lesson', 'block'}:
                raise ValueError('reading source must identify a lesson or block and no attempt')
        else:
            entity = 'practice_set' if self.kind == 'practice_submitted' else 'assessment'
            if self.source_id is None or self.target_ref.entity != entity:
                raise ValueError('submission source must identify its real session and target')
        return self


class RecommendationProfileBasis(dm.StrictModel):
    revision: dm.Revision
    goal_concept_ids: list[dm.Id]
    goals: list[str]
    self_assessments: list[dm.SelfAssessment]

    @model_validator(mode='after')
    def unique_concepts(self):
        _unique(self.goal_concept_ids, 'goal concept')
        _unique([item.concept_id for item in self.self_assessments], 'self-assessment concept')
        return self


class RecommendationRouteBasis(dm.StrictModel):
    route_ref: dm.ContentRef
    step_id: dm.Id
    source_event_ids: list[dm.Id]

    @model_validator(mode='after')
    def route_identity(self):
        if self.route_ref.entity != 'route':
            raise ValueError('route basis requires an exact route')
        _unique(self.source_event_ids, 'route event')
        return self


class RecommendationReaderOption(dm.StrictModel):
    kind: Literal['reader']
    course_ref: dm.ContentRef
    lesson_ref: dm.ContentRef
    block_ref: dm.ContentRef | None

    @model_validator(mode='after')
    def entities(self):
        if ((self.course_ref.entity, self.lesson_ref.entity) != ('course', 'lesson')
                or self.block_ref is not None and self.block_ref.entity != 'block'):
            raise ValueError('reader navigation requires an exact course and lesson parent chain')
        return self


class RecommendationPracticeOption(dm.StrictModel):
    kind: Literal['practice']
    course_ref: dm.ContentRef
    lesson_ref: dm.ContentRef
    practice_ref: dm.ContentRef

    @model_validator(mode='after')
    def entities(self):
        if ((self.course_ref.entity, self.lesson_ref.entity, self.practice_ref.entity)
                != ('course', 'lesson', 'practice_set')):
            raise ValueError('practice navigation requires an exact course, lesson and practice set')
        return self


class RecommendationAssessmentOption(dm.StrictModel):
    kind: Literal['assessment']
    assessment_ref: dm.ContentRef
    course_ref: dm.ContentRef | None

    @model_validator(mode='after')
    def entities(self):
        if (self.assessment_ref.entity != 'assessment'
                or self.course_ref is not None and self.course_ref.entity != 'course'):
            raise ValueError('assessment navigation requires an exact assessment and optional real course')
        return self


RecommendationNavigation = Annotated[
    RecommendationReaderOption | RecommendationPracticeOption | RecommendationAssessmentOption,
    Field(discriminator='kind'),
]


class RecommendationView(dm.StrictModel):
    id: dm.Id
    target_ref: dm.ContentRef
    target_title: NonEmpty
    action: RecommendationAction
    reason_codes: list[RecommendationReason] = Field(min_length=1)
    explanation: NonEmpty
    evidence_refs: list[RecommendationEvidenceRef]
    activity_refs: list[RecommendationActivityRef]
    profile_basis: RecommendationProfileBasis | None
    route_basis: RecommendationRouteBasis | None
    prerequisite_gaps: list[dm.ContentRef]
    navigation_options: list[RecommendationNavigation] = Field(min_length=1)
    estimated_minutes: int | None = Field(gt=0)
    rule_version: NonEmpty
    generated_at: dm.UTC
    staleness: Literal['current', 'stale']
    decision: Literal['pending', 'accepted', 'dismissed']
    decision_revision: dm.Revision
    decision_sha256: dm.Sha256
    decision_reason: str | None

    @model_validator(mode='after')
    def coherent_projection(self):
        allowed = {
            'read': {'lesson', 'block'}, 'inspect_source': {'lesson', 'block'},
            'practice': {'practice_set'}, 'test': {'assessment'},
            'review': {'lesson', 'block', 'practice_set', 'assessment'},
        }
        if self.target_ref.entity not in allowed[self.action]:
            raise ValueError('recommendation action and target entity disagree')
        _unique(self.reason_codes, 'reason')
        _unique([item.evidence.id for item in self.evidence_refs], 'evidence')
        _unique([item.event_id for item in self.activity_refs], 'activity event')
        _unique([ref.model_dump_json() for ref in self.prerequisite_gaps], 'prerequisite')
        if any(ref.entity != 'concept' for ref in self.prerequisite_gaps):
            raise ValueError('prerequisite gaps require exact concept references')
        _unique([item.model_dump_json() for item in self.navigation_options], 'navigation')
        for option in self.navigation_options:
            if isinstance(option, RecommendationReaderOption):
                target = option.block_ref or option.lesson_ref
            elif isinstance(option, RecommendationPracticeOption):
                target = option.practice_ref
            else:
                target = option.assessment_ref
            if target != self.target_ref:
                raise ValueError('navigation must bind the complete recommendation target reference')
        if self.decision == 'pending':
            if self.decision_revision != 1 or self.decision_reason is not None:
                raise ValueError('pending recommendation must preserve its initial decision')
        elif self.decision_revision < 2:
            raise ValueError('an actual user decision must follow the initial pending revision')
        return self


class RecommendationRuleParameters(dm.StrictModel):
    review_after_days: int = Field(gt=0)
    calibration: Literal['uncalibrated']


class RecommendationPage(dm.StrictModel):
    items: list[RecommendationView]
    next_cursor: str | None
    # Optional, never serialized as null. A supplied total is a nonnegative count.
    total_hint: int = Field(default=0, ge=0, exclude_if=lambda value: value == 0)
    projection_state: Literal['missing', 'pending_refresh', 'ready', 'stale', 'failed']
    warnings: list[dm.Warning]
    snapshot_id: dm.Id | None
    generated_at: dm.UTC | None
    rule_version: NonEmpty
    rule_parameters: RecommendationRuleParameters

    @model_validator(mode='after')
    def coherent_batch(self):
        if (self.snapshot_id is None) != (self.generated_at is None):
            raise ValueError('snapshot identity and original generation time must appear together')
        if self.snapshot_id is None:
            if self.items or self.next_cursor is not None or self.projection_state in {'ready', 'stale'}:
                raise ValueError('missing snapshot cannot invent items, cursor or a readable batch')
        elif self.projection_state == 'missing':
            raise ValueError('a persisted snapshot cannot be labelled missing')
        _unique([item.id for item in self.items], 'recommendation id')
        for item in self.items:
            if item.generated_at != self.generated_at or item.rule_version != self.rule_version:
                raise ValueError('recommendation must retain its actual batch time and rule version')
            if self.projection_state != 'ready' and item.staleness != 'stale':
                raise ValueError('an outdated batch cannot present current recommendations')
        if 'total_hint' in self.model_fields_set and self.total_hint < len(self.items):
            raise ValueError('total hint cannot be smaller than the returned page')
        return self
