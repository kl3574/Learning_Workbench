"""Closed, owned-free local interrupt frames, not a runtime or transport proof.

Only empty-item terminal payloads with no error object are supported. Exact raw
frames are private facts; even a paired terminal notification proves neither
process exit nor a stable artifact directory. No model here grants authority.
"""
from typing import Annotated, Final, Literal, Self

from pydantic import BeforeValidator, Field, model_validator

from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes, strict_json
from .codex_turn_protocol_models import (
    ClosedTurnInterruptParams, OfflineTurnProtocolCatalog, ProtocolModel, verify_internal_refs,
)
from ..provider_dto import FalseOnly, Zero

InterruptSchemaPath = Literal[
    'RequestId.json', 'JSONRPCRequest.json', 'JSONRPCResponse.json', 'JSONRPCNotification.json',
    'ClientRequest.json', 'ServerNotification.json', 'v2/TurnInterruptResponse.json',
    'v2/TurnCompletedNotification.json',
]
INTERRUPT_SCHEMA_FILES: Final[tuple[tuple[InterruptSchemaPath, int, str], ...]] = (
    ('RequestId.json', 197, '9c72d59a306d827113020c6d31a14c326d55210d9bd6954f825196a52009f1c7'),
    ('JSONRPCRequest.json', 1093, '31bd6f360b2dd8a7ceaf682708105d40d38cb0b9d0821357a04da67028438f73'),
    ('JSONRPCResponse.json', 520, '4796738c04c74288213a08fb8d820c7b4df19e0977cdcd35b65ffcb43cfc93ab'),
    ('JSONRPCNotification.json', 303, 'c2b43f26880db331393fe09f34bdd76dfeb4dc30d8418d1c26e18db166d6c8c8'),
    ('ClientRequest.json', 207447, '1c7fec8758deb95ffe967060130e8d1ddb7a0a5a437ee9b64086dddbed8f5831'),
    ('ServerNotification.json', 206667, 'd3479ecf59ca421a8b052d3d15e8196d23d297a0bd85ae5a270a34ddd9c865c9'),
    ('v2/TurnInterruptResponse.json', 114, '531de6be06fe979b5963f249bab82498a175e614bf65ac12fb2e849dfe60bcf1'),
    ('v2/TurnCompletedNotification.json', 56916, '016870158603b0f84bd9f8f65f927161c9fd5128e5ec632087616462dc44e085'),
)
INTERRUPT_PROJECTION_SHA256: Final = '9bbb226ad6cf51c1d5fee39beb389ba37d5438d0722cd308c642bdc0fd0cf9c9'
MAX_FRAME_BYTES: Final = 16384


def _integer(value: object) -> object:
    if type(value) is not int:
        raise ValueError('An integer literal is required')
    return value


Int64 = Annotated[int, BeforeValidator(_integer), Field(ge=-(2**63), le=2**63-1)]
RequestId = Annotated[str, Field(min_length=1, max_length=240)] | Int64


class InterruptSchemaIdentity(ProtocolModel):
    path: InterruptSchemaPath
    size: Annotated[int, Field(ge=1, le=262144)]
    sha256: dm.Sha256

    @model_validator(mode='after')
    def exact_identity(self) -> Self:
        if (self.path, self.size, self.sha256) not in INTERRUPT_SCHEMA_FILES:
            raise ValueError('The exact selected interrupt schema identity is required')
        return self


def _members(members: list[InterruptSchemaIdentity]) -> None:
    if tuple((m.path, m.size, m.sha256) for m in members) != INTERRUPT_SCHEMA_FILES:
        raise ValueError('All eight selected interrupt schemas in original order are required')


class InterruptSchemaOriginal(InterruptSchemaIdentity):
    raw_utf8: Annotated[str, Field(min_length=2, max_length=262144, repr=False)]

    @model_validator(mode='after')
    def exact_bytes(self) -> Self:
        raw = self.raw_utf8.encode('utf-8')
        if len(raw) != self.size or sha256_bytes(raw) != self.sha256:
            raise ValueError('The selected original interrupt schema bytes differ')
        schema = strict_json(raw)
        if not isinstance(schema, dict):
            raise ValueError('An original schema object is required')
        verify_internal_refs(schema)
        return self


class InterruptSourceSummary(ProtocolModel):
    version: Literal['codex-offline-interrupt-source-summary-v1']
    scope: Literal['manually_checked_selected8_only']
    original_receipt_sha256: Literal['b64f43cd1b5a7024bcdcb421292cef93b61721ba76a4f325e7663be93931cd9c']
    original_receipt_size: Annotated[Literal[55893], BeforeValidator(_integer)]
    historical_cli_version: Literal['codex-cli0.160.0']
    historical_binary_sha256: Literal['12eb3e81114588aca3b7998f4f19e8997b056aca08e57a7ca7c8a3ec8c652aad']
    export_profile: Literal['nonexperimental']
    historical_generated_files: Annotated[Literal[314], BeforeValidator(_integer)]
    historical_exit_code: Zero
    historical_generated_at: Literal['2026-10-03T01:09:05.594701+00:00']
    selected_files: Annotated[list[InterruptSchemaIdentity], Field(min_length=8, max_length=8)]

    @model_validator(mode='after')
    def whole_selected_source(self) -> Self:
        _members(self.selected_files)
        return self


class InterruptProtocolSource(ProtocolModel):
    version: Literal['codex-offline-interrupt-source-v1']
    implemented: FalseOnly
    production_qualification: Literal['unregistered']
    selected9: OfflineTurnProtocolCatalog
    source_summary: InterruptSourceSummary
    source_summary_sha256: Literal['9bbb226ad6cf51c1d5fee39beb389ba37d5438d0722cd308c642bdc0fd0cf9c9']
    source_summary_utf8: Annotated[str, Field(min_length=2, max_length=8192, repr=False)]
    schemas: Annotated[list[InterruptSchemaOriginal], Field(min_length=8, max_length=8)]

    @model_validator(mode='after')
    def whole_source(self) -> Self:
        _members(list(self.schemas))
        raw = self.source_summary_utf8.encode('utf-8')
        if (sha256_bytes(raw) != self.source_summary_sha256
                or InterruptSourceSummary.model_validate(strict_json(raw)) != self.source_summary):
            raise ValueError('The reviewed nonsecret interrupt source summary differs')
        return self


class PrivateProtocolFrame(ProtocolModel):
    raw: Annotated[bytes, Field(min_length=1, max_length=MAX_FRAME_BYTES, repr=False)]
    sha256: dm.Sha256

    @model_validator(mode='after')
    def original_bytes(self) -> Self:
        if sha256_bytes(self.raw) != self.sha256:
            raise ValueError('The private original frame bytes differ')
        return self


class InterruptRequest(ProtocolModel):
    id: RequestId
    method: Literal['turn/interrupt']
    params: ClosedTurnInterruptParams


class EmptyInterruptResult(ProtocolModel):
    pass


class InterruptReply(ProtocolModel):
    id: RequestId
    result: EmptyInterruptResult


class EmptyItemTerminalTurn(ProtocolModel):
    id: Annotated[str, Field(min_length=1, max_length=240)]
    items: Annotated[list[EmptyInterruptResult], Field(max_length=0)]
    status: Literal['completed', 'interrupted', 'failed']
    error: None = None
    completed_at: Int64 | None = Field(default=None, alias='completedAt')
    duration_ms: Int64 | None = Field(default=None, alias='durationMs')
    started_at: Int64 | None = Field(default=None, alias='startedAt')
    items_view: Literal['full', 'summary', 'notLoaded'] | None = Field(default=None, alias='itemsView')


class TerminalParams(ProtocolModel):
    thread_id: Annotated[str, Field(min_length=1, max_length=240)] = Field(alias='threadId')
    turn: EmptyItemTerminalTurn


class TerminalNotification(ProtocolModel):
    method: Literal['turn/completed']
    params: TerminalParams


class CapturedInterruptRequest(ProtocolModel):
    frame: PrivateProtocolFrame
    wire: InterruptRequest

    @model_validator(mode='after')
    def exact_decoding(self) -> Self:
        if InterruptRequest.model_validate(strict_json(self.frame.raw)) != self.wire:
            raise ValueError('The request decoding differs from its original bytes')
        return self


class ObservedInterruptReply(ProtocolModel):
    kind: Literal['control_reply']
    frame: PrivateProtocolFrame
    wire: InterruptReply

    @model_validator(mode='after')
    def exact_decoding(self) -> Self:
        if InterruptReply.model_validate(strict_json(self.frame.raw)) != self.wire:
            raise ValueError('The reply decoding differs from its original bytes')
        return self


class ObservedTerminalNotification(ProtocolModel):
    kind: Literal['terminal_notification']
    frame: PrivateProtocolFrame
    wire: TerminalNotification

    @model_validator(mode='after')
    def exact_decoding(self) -> Self:
        if TerminalNotification.model_validate(strict_json(self.frame.raw)) != self.wire:
            raise ValueError('The notification decoding differs from its original bytes')
        return self


class InterruptExchange(ProtocolModel):
    version: Literal['codex-local-interrupt-exchange-v1']
    scope: Literal['locally_supplied_frames_only']
    implemented: FalseOnly
    production_qualification: Literal['unregistered']
    source_summary_sha256: Literal['9bbb226ad6cf51c1d5fee39beb389ba37d5438d0722cd308c642bdc0fd0cf9c9']
    request: CapturedInterruptRequest
    observations: Annotated[list[ObservedInterruptReply | ObservedTerminalNotification], Field(max_length=2)]

    @model_validator(mode='after')
    def paired_originals(self) -> Self:
        kinds = [m.kind for m in self.observations]
        if len(kinds) != len(set(kinds)):
            raise ValueError('A control reply or terminal observation cannot be repeated')
        for member in self.observations:
            if isinstance(member, ObservedInterruptReply):
                if type(member.wire.id) is not type(self.request.wire.id) or member.wire.id != self.request.wire.id:
                    raise ValueError('The reply request ID does not match the original request')
            elif (member.wire.params.thread_id != self.request.wire.params.thread_id
                  or member.wire.params.turn.id != self.request.wire.params.turn_id):
                raise ValueError('The notification thread/turn do not match the original request')
        return self

    @property
    def control_reply_observed(self) -> bool:
        return any(m.kind == 'control_reply' for m in self.observations)

    @property
    def terminal_notification_observed(self) -> bool:
        return any(m.kind == 'terminal_notification' for m in self.observations)


RejectionReason = Literal['invalid_json', 'unsupported_shape', 'unknown_method', 'unpaired', 'duplicate']


class InterruptObservation(ProtocolModel):
    accepted: bool
    reason: RejectionReason | None
    frame: PrivateProtocolFrame
    exchange: InterruptExchange

    @model_validator(mode='after')
    def bounded_outcome(self) -> Self:
        if self.accepted != (self.reason is None):
            raise ValueError('The observation decision and safe reason differ')
        if self.accepted and (not self.exchange.observations or self.exchange.observations[-1].frame != self.frame):
            raise ValueError('An accepted observation must be the exact final member')
        return self
