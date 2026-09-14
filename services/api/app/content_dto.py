"""Strict M2.1 read projections; publication does not imply a review approval."""

from typing import Literal

from pydantic import Field

from packages.contracts.domain_models import ContentRef, StrictModel, UTC


class CourseSummary(StrictModel):
    ref: ContentRef
    title: str
    language: str
    lesson_count: int = Field(ge=0)
    review_state: Literal["unreviewed"] = "unreviewed"


class RevisionSummary(StrictModel):
    ref: ContentRef
    created_at: UTC
    review_state: Literal["unreviewed"] = "unreviewed"
    lifecycle: Literal["active", "archived"]


class PageCourse(StrictModel):
    items: list[CourseSummary]
    next_cursor: str | None


class PageRevision(StrictModel):
    items: list[RevisionSummary]
    next_cursor: str | None
