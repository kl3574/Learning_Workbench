"""Private Codex owner facts. None of these records is an HTTP projection."""
from typing import Literal, Self

from pydantic import Field, model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes, sha256_bytes, strict_json
from ..codex_bootstrap_dto import (
    BootstrapModel, CodexBootstrapScope, CodexBootstrapPreparationView, CodexBootstrapDecisionAck,
    CodexSessionCreateAck, CodexSessionView,
)


class BootstrapFreeze(BootstrapModel):
    """The runtime owns and verifies its versioned, canonical private description.

    It contains only fixed deployment/control facts, never account/secret bytes.
    Keeping the exact canonical description also binds protocol frame byte order.
    """
    version: Literal['codex-bootstrap-freeze-v1']
    scope: CodexBootstrapScope
    description_json: str = Field(min_length=2, max_length=262144, repr=False)
    available: bool

    @model_validator(mode='after')
    def exact_description(self) -> Self:
        try:
            value = strict_json(self.description_json)
            raw = canonical_bytes(value)
        except (ValueError, UnicodeError, RecursionError):
            raise ValueError('Invalid frozen description') from None
        if (not isinstance(value, dict) or raw.decode() != self.description_json
                or sha256_bytes(raw) != self.scope.bootstrap_profile_sha256):
            raise ValueError('Frozen profile bytes do not match their public digest')
        return self


class BootstrapOperation(BootstrapModel):
    version: Literal['codex-bootstrap-operation-v1']
    workspace_id: dm.Id
    preparation_id: dm.Id
    actor_session_id: dm.Id
    created_at: dm.UTC
    expires_at: dm.UTC
    runtime: BootstrapFreeze


class BootstrapCommand(BootstrapModel):
    workspace_id: dm.Id
    actor_session_id: dm.Id
    route: Literal['prepare', 'decision', 'session']
    target_id: dm.Id | None
    key: str = Field(pattern=r'^[A-Za-z0-9_-]{1,128}$')
    body_json: str = Field(min_length=2, max_length=4096)

    @model_validator(mode='after')
    def canonical_request(self) -> Self:
        if canonical_bytes(strict_json(self.body_json)).decode() != self.body_json:
            raise ValueError('A command must preserve canonical validated request bytes')
        return self


class BootstrapOutcome(BootstrapModel):
    """Checked result of one registered instance; arbitrary exceptions are unknown."""
    status: Literal['ready', 'failed', 'unknown']
    thread_id: str | None = Field(min_length=1, max_length=240, repr=False)
    receipt_json: str | None = Field(max_length=131072, repr=False)
    error_code: Literal['CODEX_BOOTSTRAP_UNAVAILABLE', 'CODEX_SESSION_OUTCOME_UNKNOWN'] | None
    thread_start_attempted: bool

    @model_validator(mode='after')
    def actual_fact(self) -> Self:
        if self.status == 'ready':
            if self.thread_id is None or self.receipt_json is None or self.error_code is not None or not self.thread_start_attempted:
                raise ValueError('Ready requires the actual mapping and checked receipt')
            if canonical_bytes(strict_json(self.receipt_json)).decode() != self.receipt_json:
                raise ValueError('The receipt must preserve canonical checked facts')
        elif self.thread_id is not None or self.receipt_json is not None:
            raise ValueError('No mapping may be invented for failed or unknown results')
        elif self.status == 'failed':
            if self.thread_start_attempted or self.error_code != 'CODEX_BOOTSTRAP_UNAVAILABLE':
                raise ValueError('Failed requires a proved pre-thread termination')
        elif self.error_code != 'CODEX_SESSION_OUTCOME_UNKNOWN':
            raise ValueError('Uncertain execution has one safe error classification')
        return self


class PreparedEvent(BootstrapModel):
    kind: Literal['prepared']
    command: BootstrapCommand
    ack: CodexBootstrapPreparationView


class DecidedEvent(BootstrapModel):
    kind: Literal['decided']
    command: BootstrapCommand
    ack: CodexBootstrapDecisionAck


class ConsumedEvent(BootstrapModel):
    kind: Literal['consumed']
    command: BootstrapCommand
    session_id: dm.Id
    consent_id: dm.Id
    started_at: dm.UTC
    owner_id: dm.Id


class FinishedEvent(BootstrapModel):
    kind: Literal['finished']
    session_id: dm.Id
    finished_at: dm.UTC
    outcome: BootstrapOutcome
    ack: CodexSessionCreateAck | None


class BootstrapSnapshot(BootstrapModel):
    operation: BootstrapOperation
    operation_sha256: dm.Sha256
    prepared: PreparedEvent
    decided: DecidedEvent | None
    consumed: ConsumedEvent | None
    finished: FinishedEvent | None
    session: CodexSessionView | None


def uncertain_outcome() -> BootstrapOutcome:
    return BootstrapOutcome(status='unknown', thread_id=None, receipt_json=None,
                            error_code='CODEX_SESSION_OUTCOME_UNKNOWN', thread_start_attempted=True)
