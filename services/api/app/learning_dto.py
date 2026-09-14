"""Strict M2.4 HTTP projections; actions never assert assessment evidence."""

from typing import Literal

from packages.contracts.domain_models import ContentRef, Id, Note, Revision, StrictModel, UTC


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
