"""Strict Reader projections derived from PRODUCT_DESIGN Appendix A and §20.1."""

from typing import Literal

from pydantic import Field, RootModel

from packages.contracts import domain_models as dm

ReadingState = Literal['unread', 'read', 'stale']


class OutlineBlock(dm.StrictModel):
    ref: dm.ContentRef
    kind: Literal['orientation', 'definition', 'theorem', 'proof', 'intuition', 'worked_example',
                  'boundary', 'summary', 'text', 'code', 'figure']
    title: dm.Text


class OutlineLesson(dm.StrictModel):
    ref: dm.ContentRef
    title: dm.Text
    blocks: list[OutlineBlock]
    reading_state: ReadingState


class OutlineSection(dm.StrictModel):
    id: dm.Id
    title: dm.Text
    lessons: list[OutlineLesson]


class OutlineResponse(dm.StrictModel):
    course_ref: dm.ContentRef
    sections: list[OutlineSection]


class DirectoryAncestor(dm.StrictModel):
    id: dm.Id
    title: dm.Text


class DirectoryHit(dm.StrictModel):
    ref: dm.ContentRef
    title: dm.Text
    ancestors: list[DirectoryAncestor]


class DirectorySearchResponse(dm.StrictModel):
    hits: list[DirectoryHit] = Field(max_length=50)


class ProvenanceSource(dm.StrictModel):
    id: dm.Id
    media_type: str
    size: int = Field(ge=0)
    sha256: dm.Sha256
    rights: str
    parser_version: str | None


class ResolvedCitation(dm.StrictModel):
    citation: dm.Citation
    source: ProvenanceSource
    original_access: Literal['allowed', 'author_required', 'unavailable']


class RetainedOriginal(dm.StrictModel):
    source: ProvenanceSource
    original_access: Literal['allowed', 'author_required', 'unavailable']


class BlockProvenanceResponse(dm.StrictModel):
    block: dm.ContentBlock
    block_ref: dm.ContentRef
    original_source: RetainedOriginal | None
    citations: list[ResolvedCitation]
    unresolved_citation_ids: list[dm.Id]
    warnings: list[dm.Warning]


class BlockReadResponse(RootModel[dm.ContentBlock | BlockProvenanceResponse]):
    """Default metadata and explicitly requested provenance retain distinct strict shapes."""
