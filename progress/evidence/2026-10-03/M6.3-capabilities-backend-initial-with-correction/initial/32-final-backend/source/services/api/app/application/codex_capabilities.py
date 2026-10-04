"""Authenticated control read; a probe never grants a turn or tool permission."""
from typing import Protocol
from pydantic import ValidationError

from ..codex_dto import CodexCapabilities
from ..infrastructure.database import Database
from ..infrastructure.security import SessionIdentity, current_session_identity, guard_subject_access
from .errors import ApiError


class CodexCapabilityProbe(Protocol):
    def read(self) -> object: ...


class CodexCapabilitiesService:
    def __init__(self, database: Database, probe: CodexCapabilityProbe):
        self.database, self.probe = database, probe

    def _current(self, identity: SessionIdentity) -> None:
        with self.database.transaction(immediate=False) as connection:
            current_session_identity(connection, identity)
            guard_subject_access(connection, identity.workspace_id)

    def read(self, identity: SessionIdentity) -> CodexCapabilities:
        self._current(identity)
        try:
            value = self.probe.read()
            if isinstance(value, CodexCapabilities):
                value = value.model_dump(mode='python')
            result = CodexCapabilities.model_validate(value)
        except ValidationError:
            raise ApiError(502, 'CODEX_PROTOCOL_INVALID', '本机 Codex 能力响应无法核验，未启动生成。') from None
        finally:
            # A bounded local process can outlive a role/Policy transition.
            # No business transaction is kept open while observing the process.
            self._current(identity)
        return result
