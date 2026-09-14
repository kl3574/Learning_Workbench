"""Offline readiness only reports capabilities that exist."""

from collections.abc import Callable

from ..dto import ReadinessResponse
from ..infrastructure.database import SCHEMA_VERSION, Database


class RuntimeService:
    def __init__(self, database: Database, worker_ready: Callable[[], bool] | None = None):
        self.database = database
        self.worker_ready = worker_ready

    def readiness(self, workspace_id: str) -> ReadinessResponse:
        with self.database.connect() as connection:
            pending = self.database.pending_migrations(connection)
            configured = connection.execute("SELECT 1 FROM provider_configs WHERE workspace_id=? LIMIT 1", (workspace_id,)).fetchone() is not None
        return ReadinessResponse(database_ready=not pending, worker_ready=self.worker_ready is not None and self.worker_ready(), data_schema_version=SCHEMA_VERSION, migrations_pending=bool(pending), providers_configured=configured)
