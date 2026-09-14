"""Workbench owns UI snapshots and their compare-and-swap persistence."""

import sqlite3

from packages.contracts.domain_models import WorkbenchSession

from ..dto import WorkbenchSaveRequest, WorkspaceLayout
from ..infrastructure.database import Database, utc_now
from ..infrastructure.security import guard_subject_access
from ..serialization import canonical_json
from .errors import ApiError


class WorkbenchService:
    def __init__(self, database: Database):
        self.database = database

    def _read(self, connection: sqlite3.Connection, workspace_id: str) -> WorkbenchSession:
        row = connection.execute("SELECT session_json FROM workbench_sessions WHERE workspace_id=?", (workspace_id,)).fetchone()
        if row is None:
            raise ApiError(404, "REFERENCE_MISSING", "工作台会话不存在。")
        return WorkbenchSession.model_validate_json(row["session_json"])

    def layout(self, workspace_id: str) -> WorkspaceLayout:
        with self.database.connect() as connection:
            snapshot = self._read(connection, workspace_id)
        return WorkspaceLayout(nav_width=snapshot.nav_width, agent_width=snapshot.agent_width, nav_collapsed=snapshot.nav_collapsed, agent_collapsed=snapshot.agent_collapsed)

    def read(self, workspace_id: str) -> WorkbenchSession:
        with self.database.connect() as connection:
            guard_subject_access(connection, workspace_id)
            return self._read(connection, workspace_id)

    def save(self, workspace_id: str, body: WorkbenchSaveRequest) -> WorkbenchSession:
        updated = body.session.model_copy(update={"revision": body.expected_revision + 1})
        with self.database.transaction() as connection:
            guard_subject_access(connection, workspace_id)
            changed = connection.execute("UPDATE workbench_sessions SET revision=?,session_json=?,updated_at=? WHERE workspace_id=? AND revision=?", (updated.revision, canonical_json(updated.model_dump()), utc_now(), workspace_id, body.expected_revision))
            if changed.rowcount != 1:
                raise ApiError(412, "REVISION_MISMATCH", "工作台已在其他页面更改；当前草稿需要解决修订冲突。")
        # Missing content is retained as an unresolved original reference, never created here.
        return updated
