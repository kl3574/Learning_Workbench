"""Strict HTTP projections of implemented application ports."""

from typing import Annotated, Callable

from fastapi import APIRouter, Depends, Header, Request, Response, Security
from fastapi.security import APIKeyCookie

from packages.contracts.domain_models import MutationAck, WorkbenchSession

from ..application.runtime import RuntimeService
from ..application.sessions import SessionService
from ..application.workbench import WorkbenchService
from ..application.workspace import WorkspaceService
from ..config import Settings
from ..database import Database
from ..dto import (
    BootstrapRequest,
    BootstrapResponse,
    EmptyRequest,
    HealthResponse,
    LogoutResponse,
    PreferencesRequest,
    ReadinessResponse,
    RoleRequest,
    SessionResponse,
    WorkbenchSaveRequest,
    WorkspaceResponse,
)
from ..errors import ApiError
from ..security import COOKIE_NAME, SessionIdentity, check_csrf, consume_bootstrap

local_cookie = APIKeyCookie(name=COOKIE_NAME, auto_error=False, scheme_name="LocalSession")


def reject_query_fields(request: Request) -> None:
    # Every currently implemented route has an explicitly empty query contract.
    # Future query-bearing routers must declare their own strict query DTO instead.
    if request.query_params:
        raise ApiError(422, "SCHEMA_INVALID", "此接口不接受 URL 查询字段。")


def current_identity(request: Request, cookie: Annotated[str | None, Security(local_cookie)]) -> SessionIdentity:
    identity = getattr(request.state, "identity", None)
    if identity is None or not cookie:
        raise ApiError(401, "SESSION_REQUIRED", "需要通过本机启动器建立会话。")
    return identity


def verify_write(request: Request, origin: Annotated[str, Header(alias="Origin")], csrf: Annotated[str, Header(alias="X-CSRF-Token")]) -> None:
    check_csrf(request, request.state.identity)


def create_router(settings: Settings, database: Database, worker_ready: Callable[[], bool] | None = None) -> APIRouter:
    router = APIRouter(dependencies=[Depends(reject_query_fields)])
    protected = APIRouter(prefix="/api/v1", dependencies=[Depends(current_identity)])
    workbench_service = WorkbenchService(database)
    workspace_service = WorkspaceService(database, workbench_service)
    session_service = SessionService(database)
    runtime_service = RuntimeService(database, worker_ready)

    @router.get("/health", response_model=HealthResponse, tags=["runtime"])
    def health() -> HealthResponse:
        return HealthResponse()

    @router.post("/api/v1/session/bootstrap", response_model=BootstrapResponse, tags=["session"])
    def bootstrap(body: BootstrapRequest, response: Response, origin: Annotated[str, Header(alias="Origin")]) -> BootstrapResponse:
        token, identity = consume_bootstrap(database, body.one_time_code)
        response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="strict", secure=False, path="/", max_age=settings.session_seconds)
        return BootstrapResponse(workspace_id=identity.workspace_id, csrf_token=identity.csrf_token, expires_at=identity.expires_at)

    @protected.get("/session", response_model=SessionResponse, tags=["session"])
    def read_session(request: Request) -> SessionResponse:
        return session_service.read(request.state.identity)

    @protected.post("/session/logout", response_model=LogoutResponse, tags=["session"], dependencies=[Depends(verify_write)])
    def logout(body: EmptyRequest, request: Request, response: Response) -> LogoutResponse:
        session_service.logout(request.state.identity)
        response.delete_cookie(COOKIE_NAME, httponly=True, samesite="strict", path="/")
        return LogoutResponse()

    @protected.post("/session/role", response_model=SessionResponse, tags=["session"], dependencies=[Depends(verify_write)])
    def switch_role(body: RoleRequest, request: Request, idempotency_key: Annotated[str, Header(alias="Idempotency-Key")]) -> SessionResponse:
        return session_service.switch_role(request.state.identity, body, idempotency_key)

    @protected.get("/readiness", response_model=ReadinessResponse, tags=["runtime"])
    def readiness(request: Request) -> ReadinessResponse:
        return runtime_service.readiness(request.state.identity.workspace_id)

    @protected.get("/workspace", response_model=WorkspaceResponse, tags=["workspace"])
    def workspace(request: Request) -> WorkspaceResponse:
        return workspace_service.read(request.state.identity.workspace_id)

    @protected.put("/workspace/preferences", response_model=MutationAck, tags=["workspace"], dependencies=[Depends(verify_write)])
    def save_preferences(body: PreferencesRequest, request: Request) -> MutationAck:
        return workspace_service.save_preferences(request.state.identity.workspace_id, body)

    @protected.get("/workbench/session", response_model=WorkbenchSession, tags=["workbench"], responses={200: {"headers": {"ETag": {"description": "Workbench revision and selection projection basis; preserve unchanged for If-Match.", "schema": {"type": "string"}}}}})
    def read_workbench(request: Request, response: Response) -> WorkbenchSession:
        snapshot, etag = workbench_service.read_with_policy(request.state.identity.workspace_id)
        response.headers.update({"ETag": etag, "Cache-Control": "no-store", "Vary": "Cookie"})
        return snapshot

    @protected.put("/workbench/session", response_model=WorkbenchSession, tags=["workbench"], dependencies=[Depends(verify_write)], responses={200: {"headers": {"ETag": {"description": "Saved Workbench revision and selection projection basis.", "schema": {"type": "string"}}}}})
    def save_workbench(body: WorkbenchSaveRequest, request: Request, response: Response,
                       if_match: Annotated[str | None, Header(alias="If-Match", max_length=256)] = None) -> WorkbenchSession:
        snapshot, etag = workbench_service.save_with_policy(request.state.identity.workspace_id, body, if_match)
        response.headers.update({"ETag": etag, "Cache-Control": "no-store", "Vary": "Cookie"})
        return snapshot

    router.include_router(protected)
    return router
