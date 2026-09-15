"""Bounded internal retrieval models, PRODUCT_DESIGN.md 3.0.3 appendix D.

These models bind local facts and hashes; callers still need the actual owner
ports for Policy, graph integrity, physical public bodies and job ownership.
"""

from typing import Annotated, Literal, Self

from pydantic import Field, model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes

from ..provider_dto import NonNegativeInt
from ..retrieval_dto import (
    RetrievalModel, RetrievalProvenance, RetrievalScopePath, RetrievalScopeRefs,
    normalize_scope_refs, path_sort_key, ref_sort_key,
)

SCOPE_BYTE_BUDGET = 16 * 1024 * 1024
MAX_BLOCKS = 512
MAX_PATHS = 8192


class RetrievalAlgorithmVersions(RetrievalModel):
    resource: Literal['retrieval-resource-v1']
    normalization: Literal['nfc-v1']
    tokenizer: Literal['lexical-han-gram-v1']
    unicode: Literal['15.0.0']
    ranking: Literal['scope-coverage-v1']
    locator: Literal['whole-block-v1']


def algorithm_versions() -> RetrievalAlgorithmVersions:
    return RetrievalAlgorithmVersions(
        resource='retrieval-resource-v1', normalization='nfc-v1', tokenizer='lexical-han-gram-v1',
        unicode='15.0.0', ranking='scope-coverage-v1', locator='whole-block-v1',
    )


def scope_sha256(workspace_id: str, refs: list[dm.ContentRef]) -> str:
    return sha256_bytes(canonical_bytes({
        'version': 'retrieval-scope-v1', 'workspace_id': workspace_id,
        'scope_refs': [ref.model_dump(mode='json') for ref in normalize_scope_refs(refs)],
    }))


class RetrievalRefState(RetrievalModel):
    ref: dm.ContentRef
    current_ref: dm.ContentRef
    lifecycle: Literal['active', 'archived']

    @model_validator(mode='after')
    def current_identity(self) -> Self:
        if (self.ref.entity not in {'course', 'lesson', 'block'}
                or (self.current_ref.entity, self.current_ref.id) != (self.ref.entity, self.ref.id)):
            raise ValueError('current pointer must identify the same public object')
        return self


class RetrievalBlockDescriptor(RetrievalModel):
    ref: dm.ContentRef
    title: str
    body_sha256: dm.Sha256
    body_bytes: Annotated[int, Field(ge=0, le=SCOPE_BYTE_BUDGET)]
    provenance: RetrievalProvenance
    source_descriptor_sha256: dm.Sha256
    parent_paths: Annotated[list[RetrievalScopePath], Field(min_length=1, max_length=MAX_PATHS)]

    @model_validator(mode='after')
    def block_bindings(self) -> Self:
        if self.ref.entity != 'block' or any(path.block_ref != self.ref for path in self.parent_paths):
            raise ValueError('descriptor paths must terminate at its exact block')
        if self.source_descriptor_sha256 != sha256_bytes(canonical_bytes(self.provenance)):
            raise ValueError('source descriptor hash must bind all provenance facts')
        keys = [path_sort_key(path) for path in self.parent_paths]
        if keys != sorted(set(keys)):
            raise ValueError('descriptor paths must be sorted and distinct')
        return self


class RetrievalCorpusDescriptor(RetrievalModel):
    version: Literal['retrieval-corpus-v1']
    workspace_id: dm.Id
    scope_sha256: dm.Sha256
    scope_refs: RetrievalScopeRefs
    graph: list[RetrievalRefState]
    blocks: Annotated[list[RetrievalBlockDescriptor], Field(min_length=1, max_length=MAX_BLOCKS)]
    versions: RetrievalAlgorithmVersions

    @model_validator(mode='after')
    def exact_graph_shape(self) -> Self:
        if self.scope_sha256 != scope_sha256(self.workspace_id, self.scope_refs):
            raise ValueError('scope hash must bind workspace and exact roots')
        graph_keys = [ref_sort_key(item.ref) for item in self.graph]
        block_keys = [ref_sort_key(item.ref) for item in self.blocks]
        if graph_keys != sorted(set(graph_keys)) or block_keys != sorted(set(block_keys)):
            raise ValueError('graph and blocks must be sorted and distinct')
        if {key for key in graph_keys if key[0] == 'block'} != set(block_keys):
            raise ValueError('descriptor blocks must equal the graph block set')
        if not {ref_sort_key(ref) for ref in self.scope_refs} <= set(graph_keys):
            raise ValueError('all explicit roots must be in the graph')
        paths = [path for block in self.blocks for path in block.parent_paths]
        if len(paths) > MAX_PATHS or sum(block.body_bytes for block in self.blocks) > SCOPE_BYTE_BUDGET:
            raise ValueError('complete scope exceeds path or body budget')
        for path in paths:
            if path.root_ref not in self.scope_refs:
                raise ValueError('path root must be explicitly selected')
            if any(ref_sort_key(ref) not in graph_keys for ref in
                   (path.root_ref, path.course_ref, path.lesson_ref, path.block_ref) if ref is not None):
                raise ValueError('every path node must belong to the exact graph')
        # The Content owner must meter expansion before constructing this model;
        # this final assertion cannot substitute for that bounded owner read.
        if len(canonical_bytes(self)) > SCOPE_BYTE_BUDGET:
            raise ValueError('complete encoded descriptor exceeds the resource budget')
        return self


class RetrievalScopeSnapshot(RetrievalModel):
    descriptor: RetrievalCorpusDescriptor
    corpus_sha256: dm.Sha256

    @model_validator(mode='after')
    def descriptor_hash(self) -> Self:
        if self.corpus_sha256 != sha256_bytes(canonical_bytes(self.descriptor)):
            raise ValueError('corpus hash must bind the complete descriptor')
        return self


class RetrievalBlockMaterial(RetrievalModel):
    scope_sha256: dm.Sha256
    corpus_sha256: dm.Sha256
    ref: dm.ContentRef
    body_sha256: dm.Sha256
    body: bytes = Field(repr=False)

    @model_validator(mode='after')
    def material_shape(self) -> Self:
        if self.ref.entity != 'block' or len(self.body) > SCOPE_BYTE_BUDGET:
            raise ValueError('material must be a bounded public block')
        if sha256_bytes(self.body) != self.body_sha256:
            raise ValueError('material hash does not bind its actual bytes')
        try:
            text = self.body.decode('utf-8', errors='strict')
        except UnicodeError:
            raise ValueError('material must be strict UTF-8') from None
        if '\r' in text:
            raise ValueError('material must preserve LF line endings')
        return self


class RetrievalIndexedBlock(RetrievalModel):
    ref: dm.ContentRef
    body_sha256: dm.Sha256
    body_bytes: NonNegativeInt
    body_codepoints: NonNegativeInt
    chunk_id: dm.Id
    terms_sha256: dm.Sha256
    term_count: NonNegativeInt


class RetrievalIndexManifest(RetrievalModel):
    version: Literal['retrieval-index-v1']
    index_version: dm.Id
    scope_sha256: dm.Sha256
    corpus_sha256: dm.Sha256
    descriptor: RetrievalCorpusDescriptor
    built_at: dm.UTC
    blocks: Annotated[list[RetrievalIndexedBlock], Field(min_length=1, max_length=MAX_BLOCKS)]

    @model_validator(mode='after')
    def generation_bindings(self) -> Self:
        if (self.scope_sha256 != self.descriptor.scope_sha256
                or self.corpus_sha256 != sha256_bytes(canonical_bytes(self.descriptor))):
            raise ValueError('manifest must bind its complete corpus descriptor')
        if [item.ref for item in self.blocks] != [item.ref for item in self.descriptor.blocks]:
            raise ValueError('manifest must contain exactly every descriptor block in order')
        if len({item.chunk_id for item in self.blocks}) != len(self.blocks):
            raise ValueError('each complete block must have its own chunk')
        for block, source in zip(self.blocks, self.descriptor.blocks, strict=True):
            if block.body_sha256 != source.body_sha256 or block.body_bytes != source.body_bytes:
                raise ValueError('indexed body facts must match the source descriptor')
        return self


class RetrievalIndexJobInput(RetrievalModel):
    version: Literal['retrieval-index-job-v1']
    workspace_id: dm.Id
    request_sha256: dm.Sha256
    scope_sha256: dm.Sha256
    expected_corpus_sha256: dm.Sha256
    descriptor: RetrievalCorpusDescriptor

    @model_validator(mode='after')
    def frozen_input(self) -> Self:
        if (self.workspace_id != self.descriptor.workspace_id or self.scope_sha256 != self.descriptor.scope_sha256
                or self.expected_corpus_sha256 != sha256_bytes(canonical_bytes(self.descriptor))):
            raise ValueError('job input must retain the exact accepted scope and corpus')
        return self


class RetrievalIndexJobResult(RetrievalModel):
    scope_sha256: dm.Sha256
    corpus_sha256: dm.Sha256
    index_version: dm.Id
    manifest_sha256: dm.Sha256
    indexed_block_count: Annotated[int, Field(ge=1, le=MAX_BLOCKS)]
    indexed_term_count: NonNegativeInt
    built_at: dm.UTC
