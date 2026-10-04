"""Named runtime seam; inspection and execution have deliberately separate methods."""
from typing import Literal, Protocol

from .codex_bootstrap_models import BootstrapFreeze, BootstrapOutcome


class CodexBootstrapRuntime(Protocol):
    def freeze(self, sandbox_root_id: str) -> BootstrapFreeze: ...

    def validate_frozen(self, frozen: BootstrapFreeze) -> None:
        """Verify original structure/hashes without current-environment authority."""
        ...

    def validity(self, frozen: BootstrapFreeze) -> Literal['current', 'changed', 'unavailable']:
        """Read facts only: no CLI, directory creation, config repair or DB writes."""
        ...

    def execute(self, frozen: BootstrapFreeze, permit_id: str) -> BootstrapOutcome:
        """Run the unique persisted instance once; no retry or alternative profile."""
        ...

    def validate_outcome(self, frozen: BootstrapFreeze, permit_id: str, outcome: BootstrapOutcome) -> None:
        """Validate a persisted receipt against its original deployment and instance."""
        ...
