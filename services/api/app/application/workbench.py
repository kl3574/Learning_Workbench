"""Workbench persists UI metadata separately from policy-redacted material selections."""

import hashlib
import sqlite3

from packages.contracts.domain_models import SavedTab, WorkbenchSession

from ..dto import WorkbenchSaveRequest, WorkspaceLayout
from ..infrastructure.database import Database, utc_now
from ..serialization import canonical_json
from .assessment_access import AssessmentAccess
from .errors import ApiError


def _policy(connection: sqlite3.Connection, workspace_id: str) -> str | None:
    access = AssessmentAccess(connection, workspace_id)
    active = access.active_independent()
    if active is not None:
        # An incomplete legacy allocation must remain fail closed.
        attempt = access.load(active)
        if attempt.status != "active" or attempt.policy.mode != "independent":
            raise ApiError(409, "ASSESSMENT_SNAPSHOT_INVALID", "测验策略快照无效。")
    return active


def _etag(workspace_id: str, revision: int, active: str | None) -> str:
    workspace = hashlib.sha256(workspace_id.encode()).hexdigest()
    policy = f"independent.{active}" if active else "full"
    return f'"wb.{workspace}.{revision}.{policy}"'


def _same_context(left: SavedTab, right: SavedTab) -> bool:
    return left.context.model_dump(exclude={"selection"}) == right.context.model_dump(exclude={"selection"})


def _projection(snapshot: WorkbenchSession, active: str | None) -> WorkbenchSession:
    if active is None:
        return snapshot
    return snapshot.model_copy(update={"tabs": [tab.model_copy(update={"context": tab.context.model_copy(update={"selection": None})}) for tab in snapshot.tabs]})


def _conflict() -> ApiError:
    return ApiError(412, "REVISION_MISMATCH", "工作台修订或测验策略已改变；请保留本机候选并重新比较服务端工作台。")


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
        return self.read_with_policy(workspace_id)[0]

    def read_with_policy(self, workspace_id: str) -> tuple[WorkbenchSession, str]:
        # One read snapshot for both policy and layout; this never writes data.
        with self.database.transaction() as connection:
            active = _policy(connection, workspace_id)
            snapshot = self._read(connection, workspace_id)
            return _projection(snapshot, active), _etag(workspace_id, snapshot.revision, active)

    def save(self, workspace_id: str, body: WorkbenchSaveRequest) -> WorkbenchSession:
        return self.save_with_policy(workspace_id, body, None)[0]

    def save_with_policy(self, workspace_id: str, body: WorkbenchSaveRequest, expected_etag: str | None) -> tuple[WorkbenchSession, str]:
        with self.database.transaction() as connection:
            active = _policy(connection, workspace_id)
            current = self._read(connection, workspace_id)
            if current.revision != body.expected_revision:
                raise _conflict()
            if expected_etag is not None:
                allowed = {_etag(workspace_id, current.revision, active)}
                if active is not None:
                    # Entering an independent attempt must allow adding its new tab.
                    allowed.add(_etag(workspace_id, current.revision, None))
                if expected_etag not in allowed:
                    raise _conflict()
            previous = {tab.id: tab for tab in current.tabs}
            tabs = []
            for tab in body.session.tabs:
                old = previous.get(tab.id)
                same = old is not None and _same_context(old, tab)
                if active is not None:
                    selection = old.context.selection if old is not None and same else None
                    tab = tab.model_copy(update={"context": tab.context.model_copy(update={"selection": selection})})
                elif expected_etag is None and same and old is not None and old.context.selection is not None and tab.context.selection is None:
                    # Legacy clients cannot prove whether null means explicit clear
                    # or a delayed redacted projection. A fresh full basis can.
                    raise _conflict()
                tabs.append(tab)
            updated = body.session.model_copy(update={"revision": body.expected_revision + 1, "tabs": tabs})
            changed = connection.execute("UPDATE workbench_sessions SET revision=?,session_json=?,updated_at=? WHERE workspace_id=? AND revision=?", (updated.revision, canonical_json(updated.model_dump()), utc_now(), workspace_id, body.expected_revision))
            if changed.rowcount != 1:
                raise _conflict()
            # Missing content remains an unresolved original ref, never created here.
            return _projection(updated, active), _etag(workspace_id, updated.revision, active)
