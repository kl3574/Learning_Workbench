"""New execution-capable records; original unavailable v1 decoders stay fixed."""
from typing import Annotated, Literal

from pydantic import Field
from packages.contracts import domain_models as dm
from ..codex_turn_dto import CodexTurnModel
from ..codex_turn_dto import CodexTurnPrepareWrite
from ..provider_dto import ProviderConfigView, ReferenceSummary
from .retrieval_models import RetrievalScopeSnapshot
from .provider_codex_profile import CodexRuntimeProfile
from .codex_turn_models import (
    PrepareCommand, TurnInput, TurnCancelled, TurnProviderBound, TurnStarted, TurnLifecycle, TurnCancelRequested,
)


class CodexCompletedHistory(CodexTurnModel):
    turn_id: dm.Id
    user: Annotated[str, Field(min_length=1, max_length=8000)]
    answer: Annotated[str, Field(max_length=400000)]
    receipt_sha256: dm.Sha256
    output_sha256: dm.Sha256 | None


class RunnableTurnInput(dm.StrictModel):
    version: Literal['codex-turn-input-v2']
    workspace_id: dm.Id
    actor_session_id: dm.Id
    session_id: dm.Id
    turn_id: dm.Id
    job_id: dm.Id
    request: CodexTurnPrepareWrite
    provider: ProviderConfigView
    runtime: CodexRuntimeProfile


class RunnableTurnContext(dm.StrictModel):
    version: Literal['codex-turn-context-v2']
    input: RunnableTurnInput
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


class UnavailableHistoryContext(dm.StrictModel):
    """New frozen context version; old unavailable v1 decoder stays exact."""
    version: Literal['codex-turn-context-v3']
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


class RunnableTurnPrepared(dm.StrictModel):
    kind: Literal['prepared']
    creation_sequence: dm.Revision
    input: RunnableTurnInput
    command: PrepareCommand


NewTurnEvent = Annotated[RunnableTurnPrepared | TurnProviderBound | TurnStarted | TurnLifecycle | TurnCancelRequested | TurnCancelled,
                         Field(discriminator='kind')]


class ControlEventEnvelope(dm.StrictModel):
    version: Literal['codex-turn-event-v2']
    workspace_id: dm.Id
    session_id: dm.Id
    seq: dm.Revision
    previous_sha256: dm.Sha256 | None
    occurred_at: dm.UTC
    event: NewTurnEvent
