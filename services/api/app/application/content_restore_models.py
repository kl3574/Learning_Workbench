"""Immutable restore facts; original history and permissions are checked by owners."""
from typing import Literal, Self, TypeVar
from pydantic import BaseModel, Field, model_validator
from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256, sha256_bytes
from ..authoring_dto import AuthoringModel
from ..content_restore_dto import ContentRestoreDraftCreateWrite, RestoreSourceMaterial
from ..infrastructure.provenance_repository import FrozenProvenance
from .errors import ApiError

M = TypeVar('M', bound=BaseModel)


def integrity() -> ApiError:
    return ApiError(409, 'RESTORE_INTEGRITY_ERROR', '恢复来源、候选或发布记录未通过完整性核验。')


def checked(model: type[M], value: object) -> M:
    try:
        return model.model_validate(value.model_dump(mode='python', warnings='error') if isinstance(value, BaseModel) else value)
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise integrity() from None


class RestoreDependency(AuthoringModel):
    owner_ref: dm.ContentRef
    target_ref: dm.ContentRef
    relation: Literal['reference', 'concept']


class RestoreSource(AuthoringModel):
    material: RestoreSourceMaterial
    body_markdown: str = Field(max_length=400000)
    provenance: FrozenProvenance | None
    dependencies: list[RestoreDependency]

    @model_validator(mode='after')
    def bytes_and_provenance(self) -> Self:
        m, block = self.material, self.material.metadata
        if (m.source_ref != dm.ContentRef(entity='block', id=block.id, revision=block.revision, sha256=metadata_sha256(block))
                or block.body_path.startswith('private/') or '\r' in self.body_markdown
                or sha256_bytes(self.body_markdown.encode()) != block.body_sha256 or m.body_sha256 != block.body_sha256
                or m.source_descriptor_sha256 != (metadata_sha256(self.provenance) if self.provenance else None)
                or self.provenance is not None and self.provenance.block_ref != m.source_ref):
            raise ValueError('restore source must retain original metadata, bytes and descriptor')
        return self


def restore_warnings(source: RestoreSource) -> list[dm.Warning]:
    return [*source.material.warnings, dm.Warning(code='RESTORE_REVIEW_REQUIRED', severity='warning',
        message='恢复完整历史块；原种类、概念、引用、依赖与当前版可能不同，须重新人工审校；父级引用不会自动更新。')]


class RestorePayload(AuthoringModel):
    version: Literal['content-restore-v1']
    request: ContentRestoreDraftCreateWrite
    source: RestoreSource
    proposed_block: dm.ContentBlock
    warnings: list[dm.Warning]

    @model_validator(mode='after')
    def complete_copy(self) -> Self:
        if (self.source.material.source_ref != self.request.source_ref
                or self.proposed_block != self.source.material.metadata.model_copy(update={'revision': self.request.expected_current_ref.revision + 1})
                or self.warnings != restore_warnings(self.source)):
            raise ValueError('restore copies the complete historical block into exactly current plus one')
        return self


class RestoreRecord(AuthoringModel):
    version: Literal['content-restore-record-v1']
    workspace_id: dm.Id
    candidate: dm.DraftCandidate
    actor_id: dm.Id
    command_key: str = Field(min_length=1)
    payload: RestorePayload
    created_at: dm.UTC

    @model_validator(mode='after')
    def candidate_binding(self) -> Self:
        if self.candidate.entity != 'block' or self.candidate.draft_revision != 1 or self.candidate.candidate_sha256 != metadata_sha256(self.payload):
            raise ValueError('restore candidate must bind all original immutable material')
        return self
