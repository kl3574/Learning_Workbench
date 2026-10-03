"""Closed M6.2 historical public block restoration DTOs, PRODUCT_DESIGN §20.11."""
from typing import Annotated, Literal, Self
from pydantic import AfterValidator, Field, model_validator
from packages.contracts import domain_models as dm
from .authoring_dto import AuthoringModel, _nonblank
from .restore_numeric_dto import RestoreNumericMaterialView

RestoreReason = Annotated[str, Field(min_length=1, max_length=2000), AfterValidator(_nonblank)]


class ContentRestoreDraftCreateWrite(AuthoringModel):
    source_ref: dm.ContentRef
    expected_current_ref: dm.ContentRef
    reason: RestoreReason

    @model_validator(mode='after')
    def same_history(self) -> Self:
        a, b = self.source_ref, self.expected_current_ref
        if a.entity != 'block' or b.entity != 'block' or a.id != b.id or a.revision >= b.revision:
            raise ValueError('restore requires an earlier revision of the same public block')
        return self


class RestoreSourceMaterial(AuthoringModel):
    version: Literal['restore-source-v1']
    source_ref: dm.ContentRef
    metadata: dm.ContentBlock
    body_sha256: dm.Sha256
    source_descriptor_sha256: dm.Sha256 | None
    warnings: list[dm.Warning]


class ContentRestoreDraftCreateAck(AuthoringModel):
    candidate: dm.DraftCandidate
    source_ref: dm.ContentRef
    base_ref: dm.ContentRef
    state: Literal['draft']


class ContentRestoreDraftSnapshot(AuthoringModel):
    owner: Literal['authoring_restore']
    candidate: dm.DraftCandidate
    source_ref: dm.ContentRef
    base_ref: dm.ContentRef
    reason: RestoreReason
    proposed_block: dm.ContentBlock
    body_markdown: str = Field(max_length=400000)
    source_material_sha256: dm.Sha256
    warnings: list[dm.Warning]
    state: Literal['draft', 'published']
    published_ref: dm.ContentRef | None
    numeric_material: RestoreNumericMaterialView | None
    numeric_check_ids: Annotated[list[dm.Id], Field(max_length=100)]

    @model_validator(mode='after')
    def state_binding(self) -> Self:
        if (self.state == 'published') != (self.published_ref is not None):
            raise ValueError('published state requires its actual immutable result')
        if len(set(self.numeric_check_ids)) != len(self.numeric_check_ids):
            raise ValueError('numeric check identities must be unique')
        material = self.numeric_material
        if (material is not None) != bool(self.numeric_check_ids):
            raise ValueError('a material binding and its first numeric preview are atomic')
        if material is not None and (
            self.proposed_block.kind != 'worked_example'
            or material.candidate.model_dump() != self.candidate.model_dump()
            or material.source_ref.model_dump() != self.source_ref.model_dump()
            or material.source_material_sha256 != self.source_material_sha256
            or material.body_sha256 != self.proposed_block.body_sha256
        ):
            raise ValueError('numeric material must belong to this exact Restore snapshot')
        return self
