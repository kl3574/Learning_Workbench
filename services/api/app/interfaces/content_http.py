"""M2.1 content queries from PRODUCT_DESIGN Appendix A; no publication route."""

from typing import Annotated, Callable

from fastapi import APIRouter, Depends, Query, Request, Response

from packages.contracts import domain_models as dm
from packages.contracts.canonical import metadata_sha256

from ..application.content import ContentService
from ..content_dto import PageCourse, PageRevision
from ..database import Database
from ..errors import ApiError
from .http import current_identity

RevisionQuery = Annotated[int, Query(ge=1)]
LimitQuery = Annotated[int, Query(ge=1, le=100)]
CursorQuery = Annotated[str | None, Query(max_length=1024)]
SearchQuery = Annotated[str | None, Query(max_length=2000)]
ETAG_HEADERS = {"ETag": {"description": "Quoted SHA-256 of the exact stored bytes.", "schema": {"type": "string"}}}


def query_fields(*allowed: str) -> Callable[[Request], None]:
    def validate(request: Request) -> None:
        keys = [key for key, _ in request.query_params.multi_items()]
        if len(keys) != len(set(keys)) or set(keys) - set(allowed):
            raise ApiError(422, "SCHEMA_INVALID", "查询字段未知或重复。")

    return validate


class MarkdownResponse(Response):
    media_type = "text/markdown"


def create_content_router(database: Database) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["content"], dependencies=[Depends(current_identity)])
    service = ContentService(database)

    def read(request: Request, response: Response, entity: dm.Entity, id: str, revision: int):
        value = service.read(request.state.identity.workspace_id, entity, id, revision)
        response.headers["ETag"] = f'"{metadata_sha256(value)}"'
        return value

    @router.get("/courses", response_model=PageCourse, dependencies=[Depends(query_fields("q", "cursor", "limit"))])
    def courses(request: Request, q: SearchQuery = None, cursor: CursorQuery = None, limit: LimitQuery = 20) -> PageCourse:
        return service.courses(request.state.identity.workspace_id, q=q, limit=limit, cursor=cursor)

    @router.get("/courses/{id}", response_model=dm.Course, responses={200: {"headers": ETAG_HEADERS}}, dependencies=[Depends(query_fields("revision"))])
    def course(id: dm.Id, revision: RevisionQuery, request: Request, response: Response):
        return read(request, response, "course", id, revision)

    @router.get("/lessons/{id}", response_model=dm.Lesson, responses={200: {"headers": ETAG_HEADERS}}, dependencies=[Depends(query_fields("revision"))])
    def lesson(id: dm.Id, revision: RevisionQuery, request: Request, response: Response):
        return read(request, response, "lesson", id, revision)

    @router.get("/blocks/{id}", response_model=dm.ContentBlock, responses={200: {"headers": ETAG_HEADERS}}, dependencies=[Depends(query_fields("revision"))])
    def block(id: dm.Id, revision: RevisionQuery, request: Request, response: Response):
        return read(request, response, "block", id, revision)

    @router.get(
        "/blocks/{id}/body", response_class=Response,
        responses={200: {"headers": ETAG_HEADERS, "content": {"text/markdown": {"schema": {"type": "string"}}}}},
        dependencies=[Depends(query_fields("revision"))],
    )
    def body(id: dm.Id, revision: RevisionQuery, request: Request) -> Response:
        data, digest = service.body(request.state.identity.workspace_id, id, revision)
        return MarkdownResponse(data, headers={"ETag": f'"{digest}"'})

    @router.get("/objects/{id}/current", response_model=dm.ContentRef, dependencies=[Depends(query_fields())])
    def current(id: dm.Id, request: Request) -> dm.ContentRef:
        return service.current(request.state.identity.workspace_id, id)

    @router.get("/objects/{id}/revisions", response_model=PageRevision, dependencies=[Depends(query_fields("cursor", "limit"))])
    def revisions(id: dm.Id, request: Request, cursor: CursorQuery = None, limit: LimitQuery = 20) -> PageRevision:
        return service.revisions(request.state.identity.workspace_id, id, limit=limit, cursor=cursor)

    return router
