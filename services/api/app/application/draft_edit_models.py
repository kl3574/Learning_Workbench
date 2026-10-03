"""Immutable local edit facts. Construction and stored hashes grant no access."""
from typing import Annotated, Literal, Self, TypeVar

from pydantic import BaseModel, Field, model_validator
from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256, sha256_bytes
from ..draft_dto import DraftCreateWrite, DraftPatchWrite, DraftCreated, DraftPatched, DraftModel
from ..infrastructure.provenance_repository import FrozenProvenance
from .errors import ApiError
from .content_dependency_models import ContentDependencyWitness

M = TypeVar('M', bound=BaseModel)
MAX_BODY_BYTES = 2_000_000
MAX_VERSIONS = 1000


def integrity() -> ApiError:
    return ApiError(503, 'DRAFT_EDIT_INTEGRITY', '草稿的原始材料或历史当前无法核验。')


def invalid() -> ApiError:
    return ApiError(422, 'DRAFT_EDIT_INVALID', '草稿字段或完整编辑请求无效。')


def unsupported() -> ApiError:
    return ApiError(409, 'DRAFT_EDIT_SCOPE_UNSUPPORTED', '当前只支持从精确公开文本块修订创建并编辑标题和正文。')


def checked(model: type[M], value: object, *, request: bool = False) -> M:
    try:
        return model.model_validate(value.model_dump(mode='python', warnings='error') if isinstance(value, BaseModel) else value)
    except (ValueError, TypeError, AttributeError, RecursionError):
        raise (invalid() if request else integrity()) from None


def body_hash(text: str) -> str:
    raw = text.encode('utf-8')
    if '\r' in text or len(raw) > MAX_BODY_BYTES:
        raise ValueError('draft body must be bounded UTF-8/LF')
    return sha256_bytes(raw)


class DraftBaseMaterial(DraftModel):
    version: Literal['draft-base-material-v1'] = 'draft-base-material-v1'
    ref: dm.ContentRef
    metadata: dm.ContentBlock
    body_markdown: str = Field(max_length=400000)
    provenance: FrozenProvenance | None
    warnings: list[dm.Warning]

    @model_validator(mode='after')
    def exact(self) -> Self:
        _verify_base(self)
        if self.metadata.depends_on or self.metadata.concepts:
            raise ValueError('legacy base has no frozen dependency witness')
        return self


class DependencyDraftBaseMaterial(DraftModel):
    version: Literal['draft-base-material-dependencies-v2']
    ref: dm.ContentRef
    metadata: dm.ContentBlock
    body_markdown: str = Field(max_length=400000)
    provenance: FrozenProvenance | None
    warnings: list[dm.Warning]
    dependency_witness: ContentDependencyWitness

    @model_validator(mode='after')
    def exact(self) -> Self:
        _verify_base(self)
        if not (self.metadata.depends_on or self.metadata.concepts) or self.dependency_witness.root_ref != self.ref:
            raise ValueError('dependency base must bind its original exact root and witness')
        return self


StoredDraftBase = Annotated[DraftBaseMaterial | DependencyDraftBaseMaterial, Field(discriminator='version')]


def _verify_base(base: DraftBaseMaterial | DependencyDraftBaseMaterial) -> None:
    value = base.metadata
    if (base.ref.entity != 'block' or base.ref.id != value.id or base.ref.revision != value.revision
            or base.ref.sha256 != metadata_sha256(value) or value.kind != 'text'
            or value.body_path.startswith('private/') or value.body_sha256 != body_hash(base.body_markdown)):
        raise ValueError('base must be the exact supported historical text block')
    if base.provenance is not None:
        if (base.provenance.block_ref != base.ref or {x.id for x in base.provenance.citations} != set(value.citations)
                or len(base.provenance.citations) != len(value.citations) or base.warnings != base.provenance.warnings):
            raise ValueError('base provenance must bind its exact metadata and original warnings')
    elif base.warnings != [unresolved_warning()]:
        raise ValueError('unresolved sources must retain their actual warning')


def unresolved_warning() -> dm.Warning:
    return dm.Warning(code='PROVENANCE_UNRESOLVED', severity='warning',
                      message='此精确修订尚无可核验的冻结来源记录；原始引用保留，未猜测来源。')


class DraftEditPayload(DraftModel):
    version: Literal['text-block-edit-v1']
    entity: Literal['block']
    kind: Literal['text']
    base_ref: dm.ContentRef
    body_path: str
    citations: list[dm.Id]
    title: dm.Text
    body_markdown: str = Field(max_length=400000)
    body_sha256: dm.Sha256
    base_material_sha256: dm.Sha256

    @model_validator(mode='after')
    def exact_body(self) -> Self:
        if self.body_sha256 != body_hash(self.body_markdown):
            raise ValueError('candidate must cover the actual full body bytes')
        return self


class EditDraftSnapshot(DraftModel):
    """Authoring-edit only projection of one verified immutable candidate."""
    owner: Literal['authoring_edit']
    candidate: dm.DraftCandidate
    base_ref: dm.ContentRef
    base_material_sha256: dm.Sha256
    payload: DraftEditPayload
    warnings: list[dm.Warning]
    state: Literal['draft', 'published']

    @model_validator(mode='after')
    def exact(self) -> Self:
        if (self.candidate.entity != 'block' or self.candidate.candidate_sha256 != metadata_sha256(self.payload)
                or self.base_ref != self.payload.base_ref
                or self.base_material_sha256 != self.payload.base_material_sha256):
            raise ValueError('edit draft snapshot must bind its exact candidate and base')
        return self


def initial_payload(base: StoredDraftBase, title: str) -> DraftEditPayload:
    return DraftEditPayload(version='text-block-edit-v1', entity='block', kind='text',
        base_ref=base.ref, body_path=base.metadata.body_path, citations=base.metadata.citations,
        title=title, body_markdown=base.body_markdown, body_sha256=base.metadata.body_sha256,
        base_material_sha256=metadata_sha256(base))


def apply_patch(payload: DraftEditPayload, request: DraftPatchWrite) -> DraftEditPayload:
    data = payload.model_dump(mode='python', warnings='error')
    for patch in request.patches:
        if patch.field not in {'title', 'body_markdown'} or type(patch.value) is not str:
            raise invalid()
        data[patch.field] = patch.value
    try:
        data['body_sha256'] = body_hash(data['body_markdown'])
        result = DraftEditPayload.model_validate(data)
    except (ValueError, TypeError, UnicodeError):
        raise invalid() from None
    if result == payload:
        raise invalid()
    return result


def edit_warnings(base: StoredDraftBase) -> list[dm.Warning]:
    return [*base.warnings, dm.Warning(code='DRAFT_EDIT_UNREVIEWED', severity='warning',
        message='此编辑候选尚未取得数学、来源或教学批准；继承来源不是对新正文的认证。')]


class DraftEditRecord(DraftModel):
    version: Literal['draft-edit-record-v1'] = 'draft-edit-record-v1'
    workspace_id: dm.Id
    candidate: dm.DraftCandidate
    base: StoredDraftBase
    payload: DraftEditPayload
    actor_id: dm.Id
    command_key: str | None
    request: DraftCreateWrite | DraftPatchWrite
    parent_sha256: dm.Sha256 | None
    created_at: dm.UTC
    warnings: list[dm.Warning]

    @model_validator(mode='after')
    def exact(self) -> Self:
        c, p, b = self.candidate, self.payload, self.base
        if (c.entity != 'block' or c.candidate_sha256 != metadata_sha256(p) or p.base_ref != b.ref
                or p.body_path != b.metadata.body_path or p.citations != b.metadata.citations
                or p.base_material_sha256 != metadata_sha256(b) or self.warnings != edit_warnings(b)):
            raise ValueError('edit record must bind the complete candidate and original base')
        if c.draft_revision == 1:
            if (not isinstance(self.request, DraftCreateWrite) or self.request.kind != 'block'
                    or self.request.base_ref != b.ref or self.parent_sha256 is not None or not self.command_key
                    or p != initial_payload(b, self.request.title)):
                raise ValueError('initial edit must preserve its actual create command')
        elif (not isinstance(self.request, DraftPatchWrite) or self.parent_sha256 is None
                or self.request.expected_revision != c.draft_revision - 1):
            raise ValueError('edit version must retain its exact predecessor request')
        return self


def ack(record: DraftEditRecord) -> DraftCreated | DraftPatched:
    c = record.candidate
    if c.draft_revision == 1:
        return DraftCreated(draft_id=c.draft_id, revision=1, base_ref=record.base.ref)
    return DraftPatched(draft_id=c.draft_id, revision=c.draft_revision, validation_warnings=record.warnings)


class DraftEditCommand(DraftModel):
    version: Literal['draft-edit-command-v1'] = 'draft-edit-command-v1'
    workspace_id: dm.Id
    actor_id: dm.Id
    route: str
    key: str
    record_sha256: dm.Sha256
    request: DraftCreateWrite | DraftPatchWrite
    ack: DraftCreated | DraftPatched
