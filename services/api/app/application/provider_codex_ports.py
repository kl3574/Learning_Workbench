"""Provider-owned Codex request source; never a text-adapter impersonation."""
import sqlite3
from typing import Annotated, Literal, Protocol
from pydantic import Field

from packages.contracts import domain_models as dm
from ..codex_turn_dto import CodexTurnPreparationView, CodexTurnControlView
from ..infrastructure.security import SessionIdentity
from .codex_turn_models import TurnContext, TurnInput, TurnProviderBound, TurnStarted, TurnLifecycle
from .provider_models import DispatchLease
from .codex_turn_execution_models import RunnableTurnInput, RunnableTurnContext, UnavailableHistoryContext


class CodexOutboundMaterial(dm.StrictModel):
    version: Literal['codex-outbound-material-v1']
    workspace_id: dm.Id
    actor_session_id: dm.Id
    preparation: CodexTurnPreparationView
    job_revision: dm.Revision
    input: Annotated[TurnInput | RunnableTurnInput, Field(discriminator='version')]
    context: Annotated[TurnContext | RunnableTurnContext | UnavailableHistoryContext, Field(discriminator='version')]


class CodexOutboundSourceState(dm.StrictModel):
    material: CodexOutboundMaterial
    control: CodexTurnControlView
    provider_bindings: list[TurnProviderBound]
    start: TurnStarted | None
    lifecycle: list[TurnLifecycle]
    active_lease: DispatchLease | None


class CodexOutboundSourcePort(Protocol):
    """Only real owner reads in the caller's active SQLite transaction."""

    def read_outbound_preparation(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                                 preparation_id: str, expected_job_revision: int) -> CodexOutboundMaterial: ...

    def outbound_sources(self, transaction: sqlite3.Connection, identity: SessionIdentity) -> dict[str, CodexOutboundSourceState]: ...

    def owned_outbound_sources(self, transaction: sqlite3.Connection, workspace_id: str) -> dict[str, CodexOutboundSourceState]: ...

    def bind_outbound_event(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                            event: TurnProviderBound, occurred_at: str) -> None: ...

    def verify_dispatch_lease(self, transaction: sqlite3.Connection, workspace_id: str, job_id: str,
                              lease: DispatchLease) -> None: ...

    def current_outbound_material(self, transaction: sqlite3.Connection, identity: SessionIdentity,
                                  material: CodexOutboundMaterial) -> bool: ...
