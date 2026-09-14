"""Four actual route endpoints from the unchanged product API inventory."""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response

from packages.contracts import domain_models as dm

from ..application.errors import ApiError
from ..application.routes import RouteService
from ..infrastructure.database import Database
from ..learning_dto import LearningActionResponse
from ..route_dto import PageRoute, RouteCompletionRequest
from .content_http import CursorQuery, ETAG_HEADERS, LimitQuery, query_fields
from .http import current_identity, verify_write

KeyHeader = Annotated[str, Header(alias='Idempotency-Key')]
MatchHeader = Annotated[str | None, Header(alias='If-Match')]


def create_route_router(database: Database) -> APIRouter:
    router = APIRouter(prefix='/api/v1', tags=['routes'], dependencies=[Depends(current_identity)],
        responses={428: {'model': dm.ErrorEnvelope}})
    service = RouteService(database)

    @router.get('/routes', response_model=PageRoute, dependencies=[Depends(query_fields('cursor', 'limit'))])
    def routes(request: Request, cursor: CursorQuery = None, limit: LimitQuery = 20) -> PageRoute:
        return service.list(request.state.identity.workspace_id, limit, cursor)

    @router.post('/routes', response_model=dm.ContentRef, status_code=201,
        dependencies=[Depends(verify_write), Depends(query_fields())], responses={201: {'headers': ETAG_HEADERS}})
    def create(body: dm.Route, request: Request, response: Response, idempotency_key: KeyHeader) -> dm.ContentRef:
        ref = service.create(request.state.identity, body, idempotency_key)
        response.headers['ETag'] = f'"{ref.sha256}"'
        return ref

    @router.put('/routes/{id}', response_model=dm.ContentRef, dependencies=[Depends(verify_write), Depends(query_fields())],
        responses={200: {'headers': ETAG_HEADERS}})
    def update(id: dm.Id, body: dm.Route, request: Request, response: Response,
               idempotency_key: KeyHeader, if_match: MatchHeader = None) -> dm.ContentRef:
        if if_match is None:
            raise ApiError(428, 'PRECONDITION_REQUIRED', '需要提供旧路线修订的 If-Match。')
        if len(request.headers.getlist('if-match')) != 1 or re.fullmatch(r'"[0-9a-f]{64}"', if_match) is None:
            raise ApiError(422, 'SCHEMA_INVALID', 'If-Match 必须是单个精确修订的强 ETag。')
        ref = service.update(request.state.identity, id, body, if_match[1:-1], idempotency_key)
        response.headers['ETag'] = f'"{ref.sha256}"'
        return ref

    @router.post('/routes/{id}/steps/{step_id}/complete', response_model=LearningActionResponse,
        dependencies=[Depends(verify_write), Depends(query_fields())])
    def complete(id: dm.Id, step_id: dm.Id, body: RouteCompletionRequest,
                 request: Request, idempotency_key: KeyHeader) -> LearningActionResponse:
        return service.complete(request.state.identity, id, step_id, body, idempotency_key)

    return router
