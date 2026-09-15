"""Content-owned safe recommendation facts; neither answers nor review approval."""

from typing import Literal

from pydantic import model_validator

from packages.contracts import domain_models as dm

from ..route_dto import RouteNavigationOption
from .eligibility_models import Skill


class CandidateCourse(dm.StrictModel):
    ref: dm.ContentRef
    title: str
    language: str
    difficulty: Literal['beginner', 'intermediate', 'advanced']
    lifecycle: Literal['active', 'archived']


class CandidateConcept(dm.StrictModel):
    ref: dm.ContentRef
    title: str
    skill_dimensions: list[Skill]
    prerequisite_refs: list[dm.ContentRef]
    mapping_state: Literal['complete', 'unresolved']
    available: bool


class CandidateConceptSkill(dm.StrictModel):
    concept_ref: dm.ContentRef
    skill: Skill

    @model_validator(mode='after')
    def concept_type(self):
        if self.concept_ref.entity != 'concept':
            raise ValueError('a declared skill needs its exact concept')
        return self


class RecommendationCandidate(dm.StrictModel):
    target_ref: dm.ContentRef
    title: str
    navigation_options: list[RouteNavigationOption]
    concept_refs: list[dm.ContentRef]
    concept_skills: list[CandidateConceptSkill]
    prerequisite_refs: list[dm.ContentRef]
    course_refs: list[dm.ContentRef]
    lesson_refs: list[dm.ContentRef]
    block_refs: list[dm.ContentRef]
    mapping_state: Literal['complete', 'unresolved']
    material_review: Literal['unreviewed']
    available: bool
    unavailable_reason_codes: list[str]
    test_ready: bool
    test_warning_codes: list[str]
    estimated_minutes: None

    @model_validator(mode='after')
    def exact_facts(self):
        if self.target_ref.entity not in {'lesson', 'block', 'practice_set', 'assessment'}:
            raise ValueError('unsupported recommendation target')
        for values, entity in [(self.concept_refs, 'concept'), (self.prerequisite_refs, 'concept'),
                               (self.course_refs, 'course'), (self.lesson_refs, 'lesson'), (self.block_refs, 'block')]:
            if any(ref.entity != entity for ref in values) or len({ref.model_dump_json() for ref in values}) != len(values):
                raise ValueError('wrong or duplicate exact references')
        if self.available and (not self.navigation_options or self.unavailable_reason_codes):
            raise ValueError('available target needs a real navigation chain and no blocker')
        if self.test_ready and (self.target_ref.entity != 'assessment' or not self.available
                                or self.mapping_state != 'complete' or self.test_warning_codes):
            raise ValueError('independent candidate readiness must match all checked facts')
        if any(item.concept_ref not in self.concept_refs for item in self.concept_skills):
            raise ValueError('question skill needs a declared exact candidate concept')
        return self


class RecommendationCatalog(dm.StrictModel):
    course_refs: list[dm.ContentRef]
    courses: list[CandidateCourse]
    concepts: list[CandidateConcept]
    candidates: list[RecommendationCandidate]
    routes: list[dm.Route]
    content_basis_sha256: dm.Sha256

    @model_validator(mode='after')
    def catalog_identity(self):
        if self.course_refs != [course.ref for course in self.courses]:
            raise ValueError('catalog course facts must bind every listed exact course')
        if any(course.ref.entity != 'course' for course in self.courses) or any(concept.ref.entity != 'concept' for concept in self.concepts):
            raise ValueError('invalid catalog entities')
        for values in ([course.ref for course in self.courses], [concept.ref for concept in self.concepts],
                       [item.target_ref for item in self.candidates]):
            if len({ref.model_dump_json() for ref in values}) != len(values):
                raise ValueError('duplicate catalog identity')
        return self
