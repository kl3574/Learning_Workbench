"""Owned transaction seams for frozen outbound requests (sole spec 3.0.2).

These private envelopes are not authorization tokens. Checked dispatch must
reload and verify the source, proposal, consent and durable dispatch ledger.
Constructing one of these objects never authorizes transport.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
import sqlite3
from typing import Protocol

from packages.contracts import domain_models as dm

from ..infrastructure.security import SessionIdentity
from ..provider_dto import (
    CostEstimate, FrozenOutboundBudget, FrozenOutboundSummary, InputTokenAssurance,
    JobRef, ProviderConfigView, ReferenceSummary,
)
from .errors import ApiError
from .provider_models import DispatchLease, PreparedOutboundMaterial, ProviderTerminalReceipt


@dataclass(frozen=True)
class PreparedProviderRequest:
    body: bytes = field(repr=False)
    adapter_version: str
    input_character_count: int
    input_token_assurance: InputTokenAssurance
    cost_estimate: CostEstimate


@dataclass(frozen=True)
class DispatchRecord:
    id: str
    job_id: str
    consent_id: str
    proposal_id: str
    request_body_sha256: str
    started_at: str
    terminal: ProviderTerminalReceipt | None


class SourcePreparationChanged(ApiError):
    """The owner verified both preparations and confirmed a real revision change.

    Corrupt, missing or unverified material must raise a different error. The
    typed signal permits a stale projection; a matching string code alone does not.
    """
    def __init__(self) -> None:
        super().__init__(409, 'OUTBOUND_SOURCE_CHANGED', '来源准备版本已改变，需要重新预览。')


class ProviderRequestPreparer(Protocol):
    def prepare(self, config: ProviderConfigView, material: PreparedOutboundMaterial,
                budget: FrozenOutboundBudget) -> PreparedProviderRequest: ...

    def verify(self, config: ProviderConfigView, material: PreparedOutboundMaterial,
               summary: FrozenOutboundSummary, body: bytes) -> None: ...

    def capabilities(self, config: ProviderConfigView, secret_available: bool) -> dm.ProviderCapabilities: ...


class OutboundSourcePort(Protocol):
    """Every read validates the owner's real records in the caller transaction."""

    def read_prepared(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                      job_id: str, expected_job_revision: int) -> PreparedOutboundMaterial: ...

    def verify_prepared(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                        material: PreparedOutboundMaterial) -> None: ...

    def reference_summaries(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                            material: PreparedOutboundMaterial) -> list[ReferenceSummary]: ...

    def bind_authorization(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                           job_id: str, prepared_input_sha256: str, consent_id: str) -> None: ...

    def verify_dispatch(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                        material: PreparedOutboundMaterial, lease: DispatchLease,
                        consent_id: str) -> JobRef: ...

    def read_job(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                 job_id: str) -> JobRef: ...


class OutboundSourceRegistry:
    """Explicit registrations only; an empty production registry is unavailable.

    Test owners are injected by tests, never discovered from files, environment,
    arbitrary request input, or a fallback for unknown job kinds.
    """

    def __init__(self, sources: Mapping[str, OutboundSourcePort] | None = None):
        self._sources = dict(sources or {})
        if any(not kind.strip() or kind in {'import', 'assessment_grading'} for kind in self._sources):
            raise ValueError('outbound sources must explicitly own generation job kinds')

    def resolve(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                job_id: str) -> OutboundSourcePort:
        from .jobs import outbound_source_kind
        kind = outbound_source_kind(transaction, identity.workspace_id, job_id)
        source = self._sources.get(kind)
        if source is None:
            raise ApiError(409, 'OUTBOUND_SOURCE_UNAVAILABLE', '此任务尚无可用的外发准备来源。')
        return source

    @property
    def has_sources(self) -> bool:
        return bool(self._sources)


class AbortSignal(Protocol):
    """Cancellation request; it does not prove remote cancellation or refund."""

    def is_set(self) -> bool: ...

    async def wait(self) -> object: ...
