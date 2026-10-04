"""Versioned private preparation/control records; none is an execution proof."""
from typing import Annotated, Literal

from pydantic import Field
from packages.contracts import domain_models as dm
from ..codex_turn_dto import CodexTurnPrepareWrite, CodexTurnPreparationView, CodexLocalToolBudget
from ..import_dto import JobCancelRequest, JobSnapshot
from ..provider_dto import ProviderConfigView, ReferenceSummary
from ..serialization import content_sha256
from .retrieval_models import RetrievalScopeSnapshot


class TurnRuntimeBinding(dm.StrictModel):
    version: Literal['codex-turn-unavailable-profile-v1']
    implemented: Literal[False]
    bootstrap_sha256: dm.Sha256
    template_version: Literal['codex-local-task-v1']
    tools: CodexLocalToolBudget
    cpu_seconds: Literal[60]
    memory_bytes: Literal[2147483648]
    file_bytes: Literal[16777216]
    protocol_output_bytes: Literal[16777216]
    file_descriptors: Literal[128]
    processes: Literal[16]
    core_bytes: Literal[0]
    command_network: Literal['denied']
    writable_area: Literal['turn_outputs']


class TurnInput(dm.StrictModel):
    version: Literal['codex-turn-input-v1']
    workspace_id: dm.Id
    actor_session_id: dm.Id
    session_id: dm.Id
    turn_id: dm.Id
    job_id: dm.Id
    request: CodexTurnPrepareWrite
    provider: ProviderConfigView
    runtime: TurnRuntimeBinding


class TurnContext(dm.StrictModel):
    version: Literal['codex-turn-context-v1']
    input: TurnInput
    snapshot: dm.ContextSnapshot
    messages: Annotated[list[dm.GenerationMessage], Field(min_length=2, max_length=2)]
    evidence: Annotated[list[dm.EvidenceChunk], Field(max_length=8)]
    scopes: Annotated[list[RetrievalScopeSnapshot], Field(max_length=8)]
    materials: Annotated[list[ReferenceSummary], Field(max_length=8)]
    omitted_refs: Annotated[list[dm.ContentRef], Field(max_length=8)]
    omitted_scopes: Annotated[list[RetrievalScopeSnapshot], Field(max_length=8)]
    warnings: Annotated[list[dm.Warning], Field(max_length=32)]


def context_digest(value: TurnContext) -> str:
    body = value.model_dump(mode='json')
    del body['snapshot']['snapshot_sha256']
    return content_sha256(body)


class SessionAnchor(dm.StrictModel):
    version: Literal['codex-turn-session-v1']
    workspace_id: dm.Id
    session_id: dm.Id
    actor_session_id: dm.Id
    bootstrap_sha256: dm.Sha256
    thread_id: dm.Id
    created_at: dm.UTC


class PrepareCommand(dm.StrictModel):
    workspace_id: dm.Id
    actor_session_id: dm.Id
    route: Literal['prepare']
    target_id: dm.Id
    key: str
    body: CodexTurnPrepareWrite
    ack: CodexTurnPreparationView


class CancelCommand(dm.StrictModel):
    workspace_id: dm.Id
    actor_session_id: dm.Id
    route: Literal['cancel']
    target_id: dm.Id
    key: str
    body: JobCancelRequest
    ack: JobSnapshot


class TurnPrepared(dm.StrictModel):
    kind: Literal['prepared']
    input: TurnInput
    command: PrepareCommand


class TurnCancelled(dm.StrictModel):
    kind: Literal['cancelled', 'cancel_observed']
    turn_id: dm.Id
    requested_session_revision: dm.Revision | None
    terminal_session_revision: dm.Revision | None
    command: CancelCommand


TurnEvent = Annotated[TurnPrepared | TurnCancelled, Field(discriminator='kind')]


class EventEnvelope(dm.StrictModel):
    version: Literal['codex-turn-event-v1']
    workspace_id: dm.Id
    session_id: dm.Id
    seq: dm.Revision
    previous_sha256: dm.Sha256 | None
    occurred_at: dm.UTC
    event: TurnEvent


def preparation_digest(workspace: str, view: CodexTurnPreparationView) -> str:
    return content_sha256({'version': 'codex-turn-preparation-v1', 'workspace_id': workspace,
        'actor_session_id': view.actor_session_id, 'session_id': view.session_id, 'turn_id': view.turn_id,
        'job_id': view.job.id, 'request': view.request.model_dump(mode='json'),
        'summary': view.summary.model_dump(mode='json'), 'created_at': view.created_at})
