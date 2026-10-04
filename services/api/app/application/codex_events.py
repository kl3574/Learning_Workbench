"""Stable public SSE projection of already checked immutable owner facts.

The private versioned Run decoder, old command ACKs and session revision remain
unchanged. No clock, process, write or repair is available to this projection.
"""
from typing import TYPE_CHECKING

from ..codex_turn_dto import (
    CodexTurnEvent, CodexTurnStatusEvent, CodexTurnAnswerEvent,
    CodexTurnUsageEvent, CodexTurnApprovalEvent, CodexTurnManifestEvent,
    CodexTurnTerminalEvent,
)
from .codex_approval_models import TurnApprovalBound
from .codex_operation_models import TurnOperationBound
from .codex_artifact_models import TurnManifestReady
from .codex_turn_models import (
    TurnPrepared, TurnStarted, TurnLifecycle, TurnCancelled, TurnCancelRequested,
)
from .codex_turn_execution_models import RunnableTurnPrepared
from .codex_turn_interrupt_models import (
    TurnInterruptRecorded, InterruptCancelled, InterruptCancelRequested,
)
from .codex_turn_context import damaged

if TYPE_CHECKING:
    from ..infrastructure.codex_turn_repository import CheckedSession, CheckedTurn
    from .provider_codex_models import CodexDispatchFinished


def project_events(state: 'CheckedSession', turn: 'CheckedTurn',
                   finished: 'CodexDispatchFinished | None') -> list[CodexTurnEvent]:
    result: list[CodexTurnEvent] = []
    terminal = False

    def emit(now, payload):
        result.append(CodexTurnEvent(turn_id=turn.control.id, run_id=turn.control.job.id,
            seq=len(result) + 1, occurred_at=now, payload=payload))

    for envelope in state.envelopes:
        event: object = envelope.event
        if isinstance(event, (TurnPrepared, RunnableTurnPrepared)):
            if event.input.turn_id == turn.control.id:
                emit(envelope.occurred_at, CodexTurnStatusEvent(type='status',
                    job=event.command.ack.job, run_revision=1))
            continue
        if isinstance(event, TurnInterruptRecorded):
            event = event.stop
        if getattr(event, 'turn_id', None) != turn.control.id or terminal:
            continue
        now = envelope.occurred_at
        if isinstance(event, TurnStarted):
            emit(now, CodexTurnStatusEvent(type='status', job=event.command.ack.job, run_revision=2))
        elif isinstance(event, (TurnApprovalBound, TurnOperationBound)):
            if event.approval_seq == 1:
                emit(now, CodexTurnApprovalEvent(type='approval_required', approval_id=event.control.id))
        elif isinstance(event, TurnManifestReady):
            emit(now, CodexTurnManifestEvent(type='manifest_ready', manifest_id=event.manifest.manifest.id,
                manifest_sha256=event.manifest.manifest_sha256))
        elif isinstance(event, (TurnCancelRequested, InterruptCancelRequested)):
            if event.kind == 'cancel_requested':
                ack = event.command.ack
                from packages.contracts import domain_models as dm
                emit(now, CodexTurnStatusEvent(type='status',
                    job=dm.JobRef(id=ack.id, status=ack.status), run_revision=ack.revision))
        elif isinstance(event, TurnLifecycle):
            if event.phase == 'claim':
                emit(now, CodexTurnStatusEvent(type='status', job=event.control.job,
                    run_revision=event.control.run_revision))
            else:
                # The Provider receipt has already passed its own hash/member
                # and consumer lifecycle checks in this same read transaction.
                if finished is None or event.control.outcome is None:
                    raise damaged()
                if finished.answer:
                    emit(now, CodexTurnAnswerEvent(type='answer_delta', text=finished.answer))
                emit(now, CodexTurnUsageEvent(type='usage', usage=finished.usage))
                emit(now, CodexTurnTerminalEvent(type='terminal', outcome=event.control.outcome,
                    error_code=event.control.error_code))
                terminal = True
        elif isinstance(event, (TurnCancelled, InterruptCancelled)) and event.kind == 'cancelled':
            emit(now, CodexTurnTerminalEvent(type='terminal', outcome='cancelled', error_code='CODEX_CANCELLED'))
            terminal = True
    if not result or terminal != (turn.control.execution == 'terminal'):
        raise damaged()
    return result
