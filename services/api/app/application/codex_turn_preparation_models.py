"""Known original preparation facts, explicitly not a production request proof.

The new context decoder does not reinterpret any unavailable v1/v3 or runnable
v2 record. Bootstrap owns its snapshot; Provider owns configuration and completed
pair provenance. These private facts cannot grant execution authority.
"""
from typing import Annotated, Literal, Self

from pydantic import BeforeValidator, Field, model_validator
from packages.contracts import domain_models as dm

from ..codex_turn_dto import CodexTurnModel
from ..provider_dto import ProviderConfigView, ReferenceSummary
from ..serialization import content_sha256
from .codex_bootstrap_models import BootstrapSnapshot
from .codex_turn_execution_models import CodexCompletedHistory
from .codex_turn_models import TurnInput
from .retrieval_models import RetrievalScopeSnapshot


MissingQualification = Literal[
    'production_input_proof_unregistered',
    'production_turn_protocol_unregistered',
    'production_turn_runtime_unregistered',
]
MISSING_QUALIFICATIONS: tuple[MissingQualification, ...] = (
    'production_input_proof_unregistered',
    'production_turn_protocol_unregistered',
    'production_turn_runtime_unregistered',
)


def _false(value: object) -> object:
    if value is not False:
        raise ValueError('Only the explicit unavailable false literal is accepted')
    return value


class UnavailablePreparationClosure(CodexTurnModel):
    version: Literal['codex-unavailable-preparation-closure-v1']
    implemented: Annotated[Literal[False], BeforeValidator(_false)]
    bootstrap: BootstrapSnapshot
    bootstrap_sha256: dm.Sha256
    provider: ProviderConfigView
    missing: Annotated[list[MissingQualification], Field(min_length=3, max_length=3)]

    @model_validator(mode='after')
    def known_facts_only(self) -> Self:
        original = self.bootstrap
        if (tuple(self.missing) != MISSING_QUALIFICATIONS
                or self.bootstrap_sha256 != content_sha256(original)
                or original.session is None or original.session.status != 'ready'
                or original.session.revision != 2 or original.finished is None
                or original.finished.outcome.status != 'ready'):
            raise ValueError('Unavailable preparation requires exact original known facts')
        return self


class UnavailablePreparationContext(CodexTurnModel):
    version: Literal['codex-turn-context-v4']
    input: TurnInput
    snapshot: dm.ContextSnapshot
    messages: Annotated[list[dm.GenerationMessage], Field(min_length=2, max_length=6)]
    evidence: Annotated[list[dm.EvidenceChunk], Field(max_length=8)]
    scopes: Annotated[list[RetrievalScopeSnapshot], Field(max_length=8)]
    materials: Annotated[list[ReferenceSummary], Field(max_length=8)]
    omitted_refs: Annotated[list[dm.ContentRef], Field(max_length=8)]
    omitted_scopes: Annotated[list[RetrievalScopeSnapshot], Field(max_length=8)]
    warnings: Annotated[list[dm.Warning], Field(max_length=32)]
    history: Annotated[list[CodexCompletedHistory], Field(max_length=2)]
    omitted_history: Annotated[list[CodexCompletedHistory], Field(max_length=2)]
    closure: UnavailablePreparationClosure

    @model_validator(mode='after')
    def original_bindings(self) -> Self:
        original = self.closure.bootstrap
        if (original.operation.workspace_id != self.input.workspace_id
                or original.session is None or original.session.id != self.input.session_id
                or self.closure.bootstrap_sha256 != self.input.runtime.bootstrap_sha256
                or self.closure.provider != self.input.provider):
            raise ValueError('Known preparation facts must belong to this original input')
        # Current reader authority is not an original fact. The existing owners
        # independently verify their historical actor/mapping and current access.
        return self
