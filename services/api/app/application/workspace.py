"""Workspace owns preferences; layout is read through the Workbench port."""

import json
from typing import Protocol

from packages.contracts.domain_models import MutationAck

from ..dto import PreferencesRequest, WorkspaceLayout, WorkspacePreferences, WorkspaceResponse
from ..infrastructure.database import SCHEMA_VERSION, Database
from ..serialization import canonical_json
from .errors import ApiError


class LayoutReader(Protocol):
    def layout(self, workspace_id: str) -> WorkspaceLayout: ...


class WorkspaceService:
    def __init__(self, database: Database, workbench: LayoutReader):
        self.database = database
        self.workbench = workbench

    def read(self, workspace_id: str) -> WorkspaceResponse:
        with self.database.connect() as connection:
            row = connection.execute("SELECT id,title,revision,preferences_json FROM workspace WHERE id=?", (workspace_id,)).fetchone()
        if row is None:
            raise ApiError(404, "REFERENCE_MISSING", "工作区不存在。")
        return WorkspaceResponse(id=row["id"], title=row["title"], revision=row["revision"], preferences=WorkspacePreferences.model_validate(json.loads(row["preferences_json"])), layout=self.workbench.layout(workspace_id), data_schema_version=SCHEMA_VERSION)

    def save_preferences(self, workspace_id: str, body: PreferencesRequest) -> MutationAck:
        with self.database.transaction() as connection:
            row = connection.execute("SELECT preferences_json,revision FROM workspace WHERE id=?", (workspace_id,)).fetchone()
            if row is None:
                raise ApiError(404, "REFERENCE_MISSING", "工作区不存在。")
            if row["revision"] != body.expected_revision:
                raise ApiError(412, "REVISION_MISMATCH", "工作区设置已更改，请读取当前修订后解决冲突。")
            preferences = WorkspacePreferences.model_validate({**json.loads(row["preferences_json"]), **body.preferences.model_dump(exclude_unset=True)})
            connection.execute("UPDATE workspace SET revision=revision+1,preferences_json=? WHERE id=? AND revision=?", (canonical_json(preferences.model_dump()), workspace_id, body.expected_revision))
        return MutationAck(id=workspace_id, revision=body.expected_revision + 1, applied=True)
