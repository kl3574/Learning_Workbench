"""Strict route application projections; completion remains Learning-owned."""

from typing import Annotated, Literal

from pydantic import Field, model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256


class RouteReaderOption(dm.StrictModel):
    kind: Literal['reader']
    course_ref: dm.ContentRef
    lesson_ref: dm.ContentRef
    block_ref: dm.ContentRef | None

    @model_validator(mode='after')
    def entities(self):
        if (self.course_ref.entity != 'course' or self.lesson_ref.entity != 'lesson'
                or self.block_ref is not None and self.block_ref.entity != 'block'):
            raise ValueError('invalid exact reader parent chain')
        return self


class RoutePracticeOption(dm.StrictModel):
    kind: Literal['practice']
    course_ref: dm.ContentRef
    lesson_ref: dm.ContentRef
    practice_ref: dm.ContentRef

    @model_validator(mode='after')
    def entities(self):
        if (self.course_ref.entity, self.lesson_ref.entity, self.practice_ref.entity) != ('course', 'lesson', 'practice_set'):
            raise ValueError('invalid exact practice parent chain')
        return self


class RouteAssessmentOption(dm.StrictModel):
    kind: Literal['assessment']
    assessment_ref: dm.ContentRef
    course_ref: dm.ContentRef | None

    @model_validator(mode='after')
    def entities(self):
        if self.assessment_ref.entity != 'assessment' or self.course_ref is not None and self.course_ref.entity != 'course':
            raise ValueError('invalid exact assessment association')
        return self


RouteNavigationOption = Annotated[RouteReaderOption | RoutePracticeOption | RouteAssessmentOption, Field(discriminator='kind')]


class RouteTargetBinding(dm.StrictModel):
    route_ref: dm.ContentRef
    step_id: dm.Id
    target_ref: dm.ContentRef
    navigation_options: list[RouteNavigationOption]
    unresolved_reason: Literal['NO_EXACT_COURSE_PARENT'] | None

    @model_validator(mode='after')
    def bindings(self):
        if self.route_ref.entity != 'route' or self.target_ref.entity not in {'lesson', 'block', 'practice_set', 'assessment'}:
            raise ValueError('invalid route binding')
        if bool(self.navigation_options) == (self.unresolved_reason is not None):
            raise ValueError('navigation must be resolved or explicitly unavailable')
        for option in self.navigation_options:
            target = (option.block_ref or option.lesson_ref) if isinstance(option, RouteReaderOption) else (
                option.practice_ref if isinstance(option, RoutePracticeOption) else option.assessment_ref)
            if target != self.target_ref:
                raise ValueError('navigation target does not bind the exact route step')
        if len({option.model_dump_json() for option in self.navigation_options}) != len(self.navigation_options):
            raise ValueError('duplicate navigation option')
        return self


class PageRoute(dm.StrictModel):
    items: list[dm.Route]
    item_refs: list[dm.ContentRef]
    targets: list[RouteTargetBinding]
    next_cursor: str | None

    @model_validator(mode='after')
    def exact_projection(self):
        expected = [dm.ContentRef(entity='route', id=value.id, revision=value.revision, sha256=metadata_sha256(value)) for value in self.items]
        if self.item_refs != expected:
            raise ValueError('route items and references must match in order')
        steps = [(ref, step.id, step.target) for ref, value in zip(expected, self.items, strict=True) for step in value.steps]
        if [(item.route_ref, item.step_id, item.target_ref) for item in self.targets] != steps:
            raise ValueError('every exact route step needs one matching binding')
        return self


class RouteCompletionRequest(dm.StrictModel):
    route_revision: dm.Revision
    expected_progress_revision: dm.Revision
    completed: bool
    origin: Literal['manual']
