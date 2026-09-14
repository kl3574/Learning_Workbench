"""Authenticated local-role transitions and atomic revocation."""

import sqlite3
from typing import Any, Literal

from ..dto import RoleRequest, SessionResponse
from ..infrastructure.database import Database, utc_now
from ..infrastructure.idempotency import execute_idempotent
from ..infrastructure.security import SessionIdentity, active_independent_attempt, guard_subject_access


class SessionService:
    def __init__(self, database: Database):
        self.database = database

    def _read(self, identity: SessionIdentity, connection: sqlite3.Connection, role: Literal["learner", "author"] | None = None) -> SessionResponse:
        return SessionResponse(workspace_id=identity.workspace_id, role=role or identity.role, csrf_token=identity.csrf_token, active_independent_attempt_id=active_independent_attempt(connection, identity.workspace_id))

    def read(self, identity: SessionIdentity) -> SessionResponse:
        with self.database.connect() as connection:
            return self._read(identity, connection)

    def logout(self, identity: SessionIdentity) -> None:
        with self.database.transaction() as connection:
            connection.execute("UPDATE local_sessions SET revoked_at=? WHERE id=? AND revoked_at IS NULL", (utc_now(), identity.id))

    def switch_role(self, identity: SessionIdentity, body: RoleRequest, key: str | None) -> SessionResponse:
        with self.database.transaction() as connection:
            if body.role == "author":
                guard_subject_access(connection, identity.workspace_id)

            def operation() -> dict[str, Any]:
                connection.execute("UPDATE local_sessions SET role=? WHERE id=?", (body.role, identity.id))
                # Persist a non-secret result; CSRF is projected from the authenticated cookie.
                return {"role": body.role}

            result = execute_idempotent(connection, actor=identity.id, route="POST /session/role", key=key, payload=body.model_dump(), operation=operation)
            return self._read(identity, connection, RoleRequest.model_validate(result).role)
