"""Strict M2.4 HTTP projections; actions never assert assessment evidence."""

from typing import Literal

from pydantic import Field

from packages.contracts.domain_models import ContentRef, Evidence, Id, Note, Revision, StrictModel, UTC


class PageEvidence(StrictModel):
    items: list[Evidence]
    next_cursor: str | None


class PageNote(StrictModel):
    items: list[Note]
    next_cursor: str | None


class NoteDeleted(StrictModel):
    id: Id
    deleted: Literal[True] = True


class ReadingState(StrictModel):
    ref: ContentRef
    read: bool
    read_at: UTC | None


class RouteStepState(StrictModel):
    route_ref: ContentRef
    step_id: Id
    completed: bool
    completion_origin: Literal['none', 'manual', 'read', 'practice_submitted', 'assessment_submitted'] = 'none'
    manual_override: bool | None = None
    completed_at: UTC | None = None
    updated_at: UTC | None = None
    source_event_ids: list[Id] = Field(default_factory=list)
    unmet_requires_steps: list[Id] = Field(default_factory=list)


class BookmarkState(StrictModel):
    ref: ContentRef
    value: bool
    updated_at: UTC


class LearningProgress(StrictModel):
    revision: Revision
    readings: list[ReadingState]
    route_steps: list[RouteStepState]
    bookmarks: list[BookmarkState]


class LearningActionRequest(StrictModel):
    kind: Literal["read_marked", "bookmark_set"]
    ref: ContentRef
    expected_revision: Revision
    value: bool


class LearningActionResponse(StrictModel):
    event_id: Id
    progress_revision: Revision
