"""Strict publication facts; neither construction nor stored JSON grants access."""
from dataclasses import dataclass
from typing import Annotated, Literal, Self, TypeVar

from pydantic import BaseModel, Field, model_validator
from packages.contracts import domain_models as dm
from packages.contracts.budgets import ImportBudgets
from packages.contracts.canonical import metadata_sha256
from ..authoring_dto import AuthoringModel
from ..infrastructure.provenance_repository import FrozenProvenance
from .errors import ApiError
from .draft_edit_models import DraftBaseMaterial, DraftEditPayload
from .content_restore_models import RestorePayload
from .publication_admission_models import DraftPublishWrite, PublicationAdmission
from .review_material_models import CheckedReviewMaterial

M = TypeVar('M', bound=BaseModel)


def integrity() -> ApiError:
    return ApiError(409, 'PUBLICATION_INTEGRITY_ERROR', '发布的原始持久事实未通过完整性核验。')


def validated(model: type[M], value: object) -> M:
    try:
        return model.model_validate(value.model_dump(mode='python', warnings='error')
                                    if isinstance(value, BaseModel) else value)
    except (ValueError, TypeError, AttributeError):
        raise integrity() from None


@dataclass(frozen=True, repr=False)
class PreparedImportBlock:
    material: CheckedReviewMaterial
    block: dm.ContentBlock
    body: bytes
    budgets: ImportBudgets


class PublicationRecord(AuthoringModel):
    version: Literal['draft-publication-v1']
    id: dm.Id
    workspace_id: dm.Id
    owner: Literal['import']
    candidate: dm.DraftCandidate
    actor_id: dm.Id
    route: str
    command_key: str
    request: DraftPublishWrite
    admission: PublicationAdmission
    human_record_sha256: dm.Sha256
    import_id: dm.Id
    original_input_sha256: dm.Sha256
    block: dm.ContentBlock
    source: FrozenProvenance
    result: dm.ContentRef
    adopted_at: dm.UTC
    published_at: dm.UTC

    @model_validator(mode='after')
    def exact_bindings(self) -> Self:
        c, a, r = self.candidate, self.admission, self.request
        if (self.route != f'POST /drafts/{c.draft_id}/publish' or not self.command_key
                or c.entity != 'block' or c.draft_revision != r.expected_revision
                or c.candidate_sha256 != r.expected_content_sha256
                or a.workspace_id != self.workspace_id or a.candidate != c
                or a.review_receipt_id != r.review_receipt_id
                or a.acknowledged_warning_codes != r.acknowledged_warning_codes
                or a.numeric_coverage != 'not_required_by_material' or a.numeric_check_ids
                or self.block.revision != 1 or self.block.kind != 'text'
                or self.block.concepts or self.block.depends_on
                or metadata_sha256(self.block) != c.candidate_sha256
                or self.result != dm.ContentRef(entity='block', id=self.block.id, revision=1,
                                                sha256=c.candidate_sha256)
                or self.source.block_ref != self.result
                or self.source.source.sha256 != self.original_input_sha256):
            raise ValueError('Publication requires one original block and an exact committed decision')
        return self


class EditPublicationRecord(AuthoringModel):
    version: Literal['edit-publication-v1']
    id: dm.Id
    workspace_id: dm.Id
    owner: Literal['authoring']
    candidate: dm.DraftCandidate
    actor_id: dm.Id
    route: str
    command_key: str
    request: DraftPublishWrite
    admission: PublicationAdmission
    human_record_sha256: dm.Sha256
    edit_record_sha256: dm.Sha256
    base: DraftBaseMaterial
    payload: DraftEditPayload
    block: dm.ContentBlock
    result: dm.ContentRef
    adopted_at: dm.UTC
    published_at: dm.UTC

    @model_validator(mode='after')
    def exact_bindings(self) -> Self:
        c, a, r, p, b = self.candidate, self.admission, self.request, self.payload, self.base
        expected = b.metadata.model_copy(update={'revision': b.ref.revision + 1,
            'title': p.title, 'body_sha256': p.body_sha256})
        if (self.route != f'POST /drafts/{c.draft_id}/publish' or not self.command_key
                or c.entity != 'block' or c.draft_revision != r.expected_revision
                or c.candidate_sha256 != r.expected_content_sha256 or c.candidate_sha256 != metadata_sha256(p)
                or a.workspace_id != self.workspace_id or a.candidate != c
                or a.review_receipt_id != r.review_receipt_id
                or a.acknowledged_warning_codes != r.acknowledged_warning_codes
                or a.numeric_coverage != 'not_required_by_material' or a.numeric_check_ids
                or p.base_ref != b.ref or p.base_material_sha256 != metadata_sha256(b)
                or p.body_path != b.metadata.body_path or p.citations != b.metadata.citations
                or self.block != expected
                or self.result != dm.ContentRef(entity='block', id=expected.id, revision=expected.revision,
                                                sha256=metadata_sha256(expected))):
            raise ValueError('Edit publication must bind the exact edit and next base Content revision')
        return self


class RestorePublicationRecord(AuthoringModel):
    version: Literal['restore-publication-v1']
    id: dm.Id
    workspace_id: dm.Id
    owner: Literal['authoring']
    candidate: dm.DraftCandidate
    actor_id: dm.Id
    route: str
    command_key: str
    request: DraftPublishWrite
    admission: PublicationAdmission
    human_record_sha256: dm.Sha256
    restore_record_sha256: dm.Sha256
    payload: RestorePayload
    block: dm.ContentBlock
    source: FrozenProvenance | None
    result: dm.ContentRef
    adopted_at: dm.UTC
    published_at: dm.UTC

    @model_validator(mode='after')
    def exact_bindings(self) -> Self:
        c, a, r = self.candidate, self.admission, self.request
        original = self.payload.source.provenance
        expected_source = original.model_copy(update={'block_ref': self.result}) if original else None
        if (self.route != f'POST /drafts/{c.draft_id}/publish' or not self.command_key
                or c.entity != 'block' or c.draft_revision != 1 or r.expected_revision != 1
                or c.candidate_sha256 != metadata_sha256(self.payload) or r.expected_content_sha256 != c.candidate_sha256
                or a.workspace_id != self.workspace_id or a.candidate != c or a.review_receipt_id != r.review_receipt_id
                or a.acknowledged_warning_codes != r.acknowledged_warning_codes
                or a.numeric_coverage != 'not_required_by_material' or a.numeric_check_ids
                or self.block != self.payload.proposed_block or self.source != expected_source
                or self.result != dm.ContentRef(entity='block', id=self.block.id, revision=self.block.revision, sha256=metadata_sha256(self.block))):
            raise ValueError('Restore publication must bind the old source, original candidate, new review and actual new block')
        return self


def publication_record(value: object) -> PublicationRecord | EditPublicationRecord | RestorePublicationRecord:
    if isinstance(value, PublicationRecord):
        return validated(PublicationRecord, value)
    if isinstance(value, EditPublicationRecord):
        return validated(EditPublicationRecord, value)
    if isinstance(value, RestorePublicationRecord):
        return validated(RestorePublicationRecord, value)
    if isinstance(value, dict):
        if value.get('version') == 'draft-publication-v1':
            return validated(PublicationRecord, value)
        if value.get('version') == 'restore-publication-v1':
            return validated(RestorePublicationRecord, value)
        if value.get('version') == 'edit-publication-v1':
            return validated(EditPublicationRecord, value)
    raise integrity()


PublicationState = Literal['draft', 'in_review', 'approved', 'published']


class PublicationEvent(AuthoringModel):
    version: Literal['draft-publication-event-v1']
    publication_id: dm.Id
    revision: dm.Revision
    state: PublicationState
    recorded_at: dm.UTC


class PublicationHistory(AuthoringModel):
    record: Annotated[PublicationRecord | EditPublicationRecord | RestorePublicationRecord, Field(discriminator='version')]
    events: list[PublicationEvent]

    @model_validator(mode='after')
    def complete_transition_chain(self) -> Self:
        if (len(self.events) != 4
                or [(e.revision, e.state) for e in self.events]
                != [(1, 'draft'), (2, 'in_review'), (3, 'approved'), (4, 'published')]
                or any(e.publication_id != self.record.id for e in self.events)
                or self.events[0].recorded_at != self.record.adopted_at
                or self.events[-1].recorded_at != self.record.published_at):
            raise ValueError('Publication requires its entire actual transaction transition chain')
        return self
