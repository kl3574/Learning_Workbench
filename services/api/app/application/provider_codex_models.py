"""Versioned Provider-owned Codex consent/dispatch history, never credentials."""
from typing import Annotated, Literal

from pydantic import Field
from packages.contracts import domain_models as dm
from ..codex_turn_dto import (
    CodexTurnModel, CodexOutboundPreviewWrite, CodexConsentProposalView,
    CodexConsentCreateWrite, CodexConsentCreateAck, SafeCode, Outcome,
)
from ..provider_dto import ConsentRevoke
from .provider_codex_ports import CodexOutboundMaterial
from .provider_models import DispatchLease, UsageSnapshot
from .provider_codex_execution import CodexExecutionResult


class CodexPreviewCommand(CodexTurnModel):
    route: Literal['preview']
    actor_session_id: dm.Id
    key: Annotated[str, Field(pattern=r'^[A-Za-z0-9_-]{1,128}$')]
    body: CodexOutboundPreviewWrite
    ack: CodexConsentProposalView


class CodexGrantCommand(CodexTurnModel):
    route: Literal['grant']
    actor_session_id: dm.Id
    key: Annotated[str, Field(pattern=r'^[A-Za-z0-9_-]{1,128}$')]
    body: CodexConsentCreateWrite
    ack: CodexConsentCreateAck


class CodexRevokeCommand(CodexTurnModel):
    route: Literal['revoke']
    actor_session_id: dm.Id
    key: Annotated[str, Field(pattern=r'^[A-Za-z0-9_-]{1,128}$')]
    body: ConsentRevoke
    ack: dm.MutationAck


class CodexProposed(CodexTurnModel):
    kind: Literal['proposed']
    material: CodexOutboundMaterial
    request_body: Annotated[str, Field(min_length=1, max_length=16777216)]
    command: CodexPreviewCommand


class CodexGranted(CodexTurnModel):
    kind: Literal['granted']
    command: CodexGrantCommand


class CodexRevoked(CodexTurnModel):
    kind: Literal['revoked', 'revoke_observed']
    command: CodexRevokeCommand


class CodexDispatchQueued(CodexTurnModel):
    kind: Literal['queued']
    dispatch_id: dm.Id
    consent_id: dm.Id
    start_command_sha256: dm.Sha256


class CodexDispatchStarted(CodexTurnModel):
    kind: Literal['started']
    dispatch_id: dm.Id
    request_body_sha256: dm.Sha256
    lease: DispatchLease
    execution_owner_id: Annotated[dm.Id, Field(pattern=r'^codex_owner_[a-f0-9]{32}$')]


class CodexDispatchFinished(CodexTurnModel):
    kind: Literal['terminal']
    dispatch_id: dm.Id
    outcome: Outcome
    error_code: SafeCode | None
    answer: Annotated[str, Field(max_length=400000)]
    usage: UsageSnapshot
    elapsed_ms: Annotated[int, Field(strict=True, ge=0)] | None
    execution_result: CodexExecutionResult | None


CodexProviderEvent = Annotated[
    CodexProposed | CodexGranted | CodexRevoked | CodexDispatchQueued |
    CodexDispatchStarted | CodexDispatchFinished, Field(discriminator='kind')]


class CodexProviderEnvelope(CodexTurnModel):
    version: Literal['provider-codex-ledger-v1']
    workspace_id: dm.Id
    turn_id: dm.Id
    seq: dm.Revision
    previous_sha256: dm.Sha256 | None
    occurred_at: dm.UTC
    event: CodexProviderEvent
