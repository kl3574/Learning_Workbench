"""Internal Content-owned witness of exact retained dependency edges."""
from typing import Literal, Self
from pydantic import ConfigDict, Field, model_validator
from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes


class ContentDependencyEdge(dm.StrictModel):
    model_config = ConfigDict(hide_input_in_errors=True)
    owner_ref: dm.ContentRef
    target_ref: dm.ContentRef
    relation: Literal['reference', 'concept']


class ContentDependencyWitness(dm.StrictModel):
    model_config = ConfigDict(hide_input_in_errors=True)
    version: Literal['content-dependency-witness-v1']
    root_ref: dm.ContentRef
    edges: list[ContentDependencyEdge] = Field(max_length=100000)

    @model_validator(mode='after')
    def ordered(self) -> Self:
        keys = [canonical_bytes(edge) for edge in self.edges]
        if keys != sorted(set(keys)):
            raise ValueError('dependency witness must contain ordered unique original edges')
        return self

    def revised_root(self, ref: dm.ContentRef) -> 'ContentDependencyWitness':
        """Only the edited root advances; every target and descendant pin stays exact."""
        if ref.entity != self.root_ref.entity or ref.id != self.root_ref.id or ref.revision != self.root_ref.revision + 1:
            raise ValueError('dependency witness can only retain edges for the next same root revision')
        edges = [ContentDependencyEdge(owner_ref=ref if edge.owner_ref == self.root_ref else edge.owner_ref,
                 target_ref=edge.target_ref, relation=edge.relation) for edge in self.edges]
        return ContentDependencyWitness(version=self.version, root_ref=ref, edges=sorted(edges, key=canonical_bytes))
