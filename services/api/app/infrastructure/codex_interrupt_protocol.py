"""Pure local interrupt exchange pairing; never an RPC sender or owner port.

All eight added originals and selected9 are rechecked. Closed local models are
conservative subsets of the actual schemas. Rejection receipts retain bounded
private raw bytes and do not erase earlier observed facts. No process/DB/secret,
freeze, network, approval, Job terminal or registry is touched here.
"""
from pathlib import Path

from jsonschema import Draft7Validator  # type: ignore[import-untyped]
from jsonschema.exceptions import ValidationError as SchemaError

from packages.contracts.canonical import sha256_bytes, strict_json
from ..application.codex_interrupt_protocol_models import (
    INTERRUPT_PROJECTION_SHA256, INTERRUPT_SCHEMA_FILES, MAX_FRAME_BYTES, CapturedInterruptRequest,
    InterruptExchange, InterruptObservation, InterruptProtocolSource, InterruptReply, InterruptRequest,
    InterruptSchemaOriginal, InterruptSourceSummary, ObservedInterruptReply, ObservedTerminalNotification,
    PrivateProtocolFrame, RejectionReason, TerminalNotification, observation_membership_sha256,
)
from .codex_turn_protocol_catalog import _read_member, read_catalog

PACKAGE_DIRECTORY = Path(__file__).with_name('codex_interrupt_protocol')


def read_interrupt_source() -> InterruptProtocolSource:
    """Read reviewed historical originals, never run a CLI or qualify a runtime."""
    summary_raw = _read_member(PACKAGE_DIRECTORY / 'source-summary.json', 8192)
    summary = InterruptSourceSummary.model_validate(strict_json(summary_raw))
    originals = [InterruptSchemaOriginal(path=path, size=size, sha256=sha,
        raw_utf8=_read_member(PACKAGE_DIRECTORY / path, size).decode('utf-8'))
        for path, size, sha in INTERRUPT_SCHEMA_FILES]
    return InterruptProtocolSource(version='codex-offline-interrupt-source-v1', implemented=False,
        production_qualification='unregistered', selected9=read_catalog(), source_summary=summary,
        source_summary_sha256=INTERRUPT_PROJECTION_SHA256, source_summary_utf8=summary_raw.decode('utf-8'), schemas=originals)


def verify_interrupt_source(source: InterruptProtocolSource) -> InterruptProtocolSource:
    if not isinstance(source, InterruptProtocolSource):
        raise ValueError('A checked offline interrupt source is required')
    return InterruptProtocolSource.model_validate(source.model_dump())


def _schemas(source: InterruptProtocolSource) -> dict[str, dict]:
    return {member.path: strict_json(member.raw_utf8) for member in source.schemas}


def _validate_request(schemas: dict[str, dict], body: dict) -> None:
    Draft7Validator(schemas['JSONRPCRequest.json']).validate(body)
    Draft7Validator(schemas['ClientRequest.json']).validate(body)


def _validate_frame(schemas: dict[str, dict], body: dict, kind: str) -> None:
    if kind == 'control_reply':
        Draft7Validator(schemas['JSONRPCResponse.json']).validate(body)
        Draft7Validator(schemas['v2/TurnInterruptResponse.json']).validate(body['result'])
    else:
        Draft7Validator(schemas['JSONRPCNotification.json']).validate(body)
        Draft7Validator(schemas['ServerNotification.json']).validate(body)
        Draft7Validator(schemas['v2/TurnCompletedNotification.json']).validate(body['params'])


def _frame(raw: bytes) -> PrivateProtocolFrame:
    # Overbound/empty/non-byte input is not admitted as a frame. The caller owns
    # its input; we never truncate a raw fact or claim the prefix was complete.
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_FRAME_BYTES:
        raise ValueError('A complete bounded byte frame is required')
    return PrivateProtocolFrame(raw=raw, sha256=sha256_bytes(raw))


def prepare_interrupt(source: InterruptProtocolSource, raw_request: bytes) -> InterruptExchange:
    """Check locally supplied request bytes, not an owned mapping or send grant."""
    checked = verify_interrupt_source(source)
    frame = _frame(raw_request)
    body = strict_json(frame.raw)
    wire = InterruptRequest.model_validate(body)
    _validate_request(_schemas(checked), body)
    return InterruptExchange(version='codex-local-interrupt-exchange-v1', scope='locally_supplied_frames_only',
        implemented=False, production_qualification='unregistered', source_summary_sha256=checked.source_summary_sha256,
        request=CapturedInterruptRequest(frame=frame, wire=wire), observations=[], observation_count=0,
        observations_sha256=observation_membership_sha256(frame.sha256, []))


def verify_interrupt_exchange(source: InterruptProtocolSource, exchange: InterruptExchange) -> InterruptExchange:
    checked = verify_interrupt_source(source)
    if not isinstance(exchange, InterruptExchange):
        raise ValueError('An original local interrupt exchange is required')
    original = InterruptExchange.model_validate(exchange.model_dump(by_alias=True))
    schemas = _schemas(checked)
    _validate_request(schemas, strict_json(original.request.frame.raw))
    for member in original.observations:
        _validate_frame(schemas, strict_json(member.frame.raw), member.kind)
    return original


def observe_interrupt(source: InterruptProtocolSource, exchange: InterruptExchange, raw_frame: bytes) -> InterruptObservation:
    """Pair one raw frame, keeping empty ACK and terminal notification distinct.

    Neither ordering is assumed. An unsupported/unpaired/duplicate frame is a
    private rejected receipt with the unchanged original exchange. This pure
    interface does not persist it, dispatch anything, or infer cleanup success.
    """
    original = verify_interrupt_exchange(source, exchange)
    frame = _frame(raw_frame)

    def rejected(reason: RejectionReason) -> InterruptObservation:
        return InterruptObservation(accepted=False, reason=reason, frame=frame, exchange=original)

    try:
        body = strict_json(frame.raw)
    except (ValueError, RecursionError):
        return rejected('invalid_json')
    if not isinstance(body, dict):
        return rejected('unsupported_shape')
    if 'method' in body and body['method'] != 'turn/completed':
        return rejected('unknown_method')
    try:
        if 'method' in body:
            terminal = TerminalNotification.model_validate(body)
            member: ObservedInterruptReply | ObservedTerminalNotification = ObservedTerminalNotification(
                kind='terminal_notification', frame=frame, wire=terminal)
            matches = (terminal.params.thread_id == original.request.wire.params.thread_id
                       and terminal.params.turn.id == original.request.wire.params.turn_id)
        else:
            reply = InterruptReply.model_validate(body)
            member = ObservedInterruptReply(kind='control_reply', frame=frame, wire=reply)
            matches = type(reply.id) is type(original.request.wire.id) and reply.id == original.request.wire.id
        _validate_frame(_schemas(source), body, member.kind)
    except (ValueError, SchemaError):
        return rejected('unsupported_shape')
    if not matches:
        return rejected('unpaired')
    if any(m.kind == member.kind for m in original.observations):
        return rejected('duplicate')
    members = [*original.observations, member]
    advanced = InterruptExchange(**{**original.model_dump(by_alias=True), 'observations': members,
        'observation_count': len(members), 'observations_sha256': observation_membership_sha256(original.request.frame.sha256, members)})
    return InterruptObservation(accepted=True, reason=None, frame=frame, exchange=advanced)
