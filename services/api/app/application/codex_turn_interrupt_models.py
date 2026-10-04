"""Interrupt commands and their actual private Jobs stop facts, version four.

The private stop route is not a public Jobs idempotency namespace. Its complete
command and original snapshot travel with the enclosing interrupt forever.
"""
from typing import Annotated, Literal

from pydantic import Field
from packages.contracts import domain_models as dm
from ..codex_turn_dto import CodexInterruptWrite, CodexInterruptAck
from ..import_dto import JobCancelRequest, JobSnapshot


class InterruptCommand(dm.StrictModel):
    workspace_id: dm.Id
    actor_session_id: dm.Id
    route: Literal['interrupt']
    target_id: dm.Id
    key: str
    body: CodexInterruptWrite
    ack: CodexInterruptAck


class InterruptStopCommand(dm.StrictModel):
    workspace_id: dm.Id
    actor_session_id: dm.Id
    route: Literal['interrupt_stop']
    target_id: dm.Id
    key: str
    body: JobCancelRequest
    ack: JobSnapshot


class InterruptCancelled(dm.StrictModel):
    kind: Literal['cancelled', 'cancel_observed']
    turn_id: dm.Id
    requested_session_revision: dm.Revision | None
    terminal_session_revision: dm.Revision | None
    command: InterruptStopCommand


class InterruptCancelRequested(dm.StrictModel):
    kind: Literal['cancel_requested', 'cancel_request_observed']
    turn_id: dm.Id
    session_revision: dm.Revision | None
    command: InterruptStopCommand


class TurnInterruptRecorded(dm.StrictModel):
    kind: Literal['interrupt_recorded']
    turn_id: dm.Id
    command: InterruptCommand
    stop: Annotated[InterruptCancelled | InterruptCancelRequested, Field(discriminator='kind')]


class InterruptEventEnvelope(dm.StrictModel):
    version: Literal['codex-turn-event-v4']
    workspace_id: dm.Id
    session_id: dm.Id
    seq: dm.Revision
    previous_sha256: dm.Sha256 | None
    occurred_at: dm.UTC
    event: TurnInterruptRecorded
