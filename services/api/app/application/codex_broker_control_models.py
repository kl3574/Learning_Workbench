"""Private synthetic Broker facts; never a production execution qualification."""
from typing import Annotated, Literal

from pydantic import Field, model_validator
from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from ..provider_dto import FalseOnly
from .provider_models import DispatchLease
from .codex_interrupt_protocol_models import RejectionReason


class BrokerMapping(dm.StrictModel):
    version: Literal['codex-synthetic-broker-mapping-v1']
    scope: Literal['synthetic_peer_only']
    production_qualified: FalseOnly
    workspace_id: dm.Id
    session_id: dm.Id
    turn_id: dm.Id
    job_id: dm.Id
    actor_session_id: dm.Id
    local_thread_id: dm.Id
    upstream_thread_id: Annotated[str, Field(min_length=1, max_length=240, repr=False)]
    upstream_turn_id: Annotated[str, Field(pattern=r'^synthetic-turn-[a-zA-Z0-9_-]{1,160}$', repr=False)]
    bootstrap_sha256: dm.Sha256
    preparation_sha256: dm.Sha256
    claim_provider_sha256: dm.Sha256
    execution_owner_id: Annotated[dm.Id, Field(pattern=r'^codex_owner_[a-f0-9]{32}$')]
    claim_lease: DispatchLease


class BrokerMappingBound(dm.StrictModel):
    kind: Literal['mapping_bound']
    mapping: BrokerMapping


class BrokerRawFrame(dm.StrictModel):
    # Hex preserves arbitrary admitted bytes without lossy UTF-8 conversion.
    raw_hex: Annotated[str, Field(min_length=2, max_length=32768, pattern=r'^(?:[0-9a-f]{2})+$', repr=False)]
    sha256: dm.Sha256

    @model_validator(mode='after')
    def exact_bytes(self):
        if sha256_bytes(bytes.fromhex(self.raw_hex)) != self.sha256:
            raise ValueError('The complete private frame differs')
        return self

    @property
    def raw(self) -> bytes:
        return bytes.fromhex(self.raw_hex)


class BrokerInterruptPrepared(dm.StrictModel):
    kind: Literal['interrupt_prepared']
    intent_seq: dm.Revision
    intent_sha256: dm.Sha256
    request: BrokerRawFrame


class BrokerInterruptStarted(dm.StrictModel):
    kind: Literal['interrupt_started']
    request_sha256: dm.Sha256


class BrokerFrameObserved(dm.StrictModel):
    kind: Literal['frame_observed']
    frame: BrokerRawFrame
    accepted: bool
    reason: RejectionReason | None


class BrokerControlClosed(dm.StrictModel):
    kind: Literal['control_closed']
    reason: Literal['live_mapping_lost', 'adapter_returned', 'transport_unknown']


BrokerEvent = Annotated[BrokerMappingBound | BrokerInterruptPrepared | BrokerInterruptStarted |
    BrokerFrameObserved | BrokerControlClosed, Field(discriminator='kind')]


class BrokerControlEnvelope(dm.StrictModel):
    version: Literal['codex-broker-control-event-v1']
    workspace_id: dm.Id
    turn_id: dm.Id
    ordinal: dm.Revision
    previous_sha256: dm.Sha256 | None
    occurred_at: dm.UTC
    event: BrokerEvent


class TurnBrokerControlBound(dm.StrictModel):
    kind: Literal['broker_control_bound']
    turn_id: dm.Id
    ordinal: dm.Revision
    record_sha256: dm.Sha256


class BrokerControlBindingEnvelope(dm.StrictModel):
    version: Literal['codex-turn-event-v7']
    workspace_id: dm.Id
    session_id: dm.Id
    seq: dm.Revision
    previous_sha256: dm.Sha256 | None
    occurred_at: dm.UTC
    event: TurnBrokerControlBound
