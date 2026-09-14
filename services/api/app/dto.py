"""Strict implemented inline HTTP DTOs from PRODUCT_DESIGN Appendix A."""

from typing import Literal

from pydantic import Field, model_validator

from packages.contracts.domain_models import Id, Revision, StrictModel, UTC, WorkbenchSession


class HealthResponse(StrictModel):
    status: Literal["ok"] = "ok"
    build_version: str = "0.1.0"


class ReadinessResponse(StrictModel):
    database_ready: bool
    worker_ready: bool
    data_schema_version: str
    migrations_pending: bool
    providers_configured: bool


class BootstrapRequest(StrictModel):
    one_time_code: str = Field(min_length=32, max_length=128)


class BootstrapResponse(StrictModel):
    workspace_id: Id
    csrf_token: str
    expires_at: UTC


class EmptyRequest(StrictModel):
    pass


class LogoutResponse(StrictModel):
    logged_out: Literal[True] = True


class RoleRequest(StrictModel):
    role: Literal["learner", "author"]


class SessionResponse(StrictModel):
    workspace_id: Id
    role: Literal["learner", "author"]
    csrf_token: str
    active_independent_attempt_id: Id | None


class WorkspacePreferences(StrictModel):
    language: str = Field(default="zh-CN", min_length=1, max_length=40)
    reader_font_size: int = Field(default=18, ge=14, le=28)
    default_learning_minutes: int = Field(default=30, ge=1, le=600)
    auto_attach_current_lesson: bool = True


class PreferencesPatch(StrictModel):
    language: str | None = Field(default=None, min_length=1, max_length=40)
    reader_font_size: int | None = Field(default=None, ge=14, le=28)
    default_learning_minutes: int | None = Field(default=None, ge=1, le=600)
    auto_attach_current_lesson: bool | None = None

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> "PreferencesPatch":
        if any(getattr(self, name) is None for name in self.model_fields_set):
            raise ValueError("Preference patches may omit fields but cannot null them.")
        return self


class PreferencesRequest(StrictModel):
    expected_revision: Revision
    preferences: PreferencesPatch


class WorkspaceLayout(StrictModel):
    nav_width: int
    agent_width: int
    nav_collapsed: bool
    agent_collapsed: bool


class WorkspaceResponse(StrictModel):
    id: Id
    title: str
    revision: Revision
    preferences: WorkspacePreferences
    layout: WorkspaceLayout
    data_schema_version: str


class WorkbenchSaveRequest(StrictModel):
    expected_revision: Revision
    session: WorkbenchSession

    @model_validator(mode="after")
    def consistent_snapshot(self) -> "WorkbenchSaveRequest":
        if self.session.revision != self.expected_revision:
            raise ValueError("Snapshot revision must equal the expected base revision.")
        ids = [tab.id for tab in self.session.tabs]
        if len(ids) != len(set(ids)):
            raise ValueError("Tab identifiers must be unique.")
        if self.session.active_tab_id is not None and self.session.active_tab_id not in ids:
            raise ValueError("The active tab must be present in the snapshot.")
        return self
