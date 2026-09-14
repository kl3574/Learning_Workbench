"""Offline readiness only reports capabilities that exist."""

from ..dto import ReadinessResponse
from ..infrastructure.database import SCHEMA_VERSION, Database


class RuntimeService:
    def __init__(self, database: Database):
        self.database = database

    def readiness(self, workspace_id: str) -> ReadinessResponse:
        with self.database.connect() as connection:
            pending = self.database.pending_migrations(connection)
            configured = connection.execute("SELECT 1 FROM provider_configs WHERE workspace_id=? LIMIT 1", (workspace_id,)).fetchone() is not None
        return ReadinessResponse(database_ready=not pending, worker_ready=False, data_schema_version=SCHEMA_VERSION, migrations_pending=bool(pending), providers_configured=configured)
