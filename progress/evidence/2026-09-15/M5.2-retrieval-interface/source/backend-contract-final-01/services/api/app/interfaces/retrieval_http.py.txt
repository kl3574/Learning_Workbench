"""Three actual M5.2 operations; scope status uses scalar JSON in the URL."""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request, Response
from pydantic import TypeAdapter, ValidationError

from packages.contracts import domain_models as dm
from packages.contracts.canonical import strict_json

from ..application.errors import ApiError
from ..application.retrieval import RetrievalService, json_bytes
from ..database import Database
from ..retrieval_dto import (
    RetrievalIndexRebuildWrite, RetrievalIndexStatusView, RetrievalQueryView,
    RetrievalQueryWrite, RetrievalScopeRefs,
)
from .content_http import query_fields
from .http import current_identity, verify_write
from .practice_http import private_response


SCOPE_REFS = TypeAdapter(RetrievalScopeRefs)
COMMAND_PARAMETER = {
    'name': 'Idempotency-Key', 'in': 'header', 'required': True,
    'schema': {'type': 'string', 'pattern': '^[A-Za-z0-9_-]{1,128}$'},
}


def unique_headers(request: Request) -> None:
    if any(len(request.headers.getlist(name)) > 1 for name in (
        'cookie', 'origin', 'x-csrf-token', 'content-type', 'content-length',
        'authorization', 'idempotency-key', 'if-match',
    )):
        raise ApiError(422, 'SCHEMA_INVALID', '身份或请求控制头不得重复。')


def command_key(request: Request) -> str:
    values = request.headers.getlist('idempotency-key')
    if len(values) != 1 or re.fullmatch(r'[A-Za-z0-9_-]{1,128}', values[0]) is None:
        raise ApiError(400, 'IDEMPOTENCY_KEY_INVALID', '重建索引需要单个有效的原命令幂等键。')
    return values[0]


def status_query_shape(request: Request) -> None:
    query_fields('scope_refs', 'cursor', 'limit')(request)
    fields = request.query_params
    if 'scope_refs' in fields and ('cursor' in fields or 'limit' in fields):
        raise ApiError(422, 'SCHEMA_INVALID', '范围状态与索引总览分页字段不能混用。')
    if 'limit' in fields and (not fields['limit'].isascii() or not fields['limit'].isdecimal()):
        raise ApiError(422, 'SCHEMA_INVALID', '分页数量必须是十进制整数。')
    if 'cursor' in fields and not fields['cursor'].strip():
        raise ApiError(422, 'SCHEMA_INVALID', '分页游标不能为空白。')


def create_retrieval_router(database: Database) -> APIRouter:
    service = RetrievalService(database)
    router = APIRouter(prefix='/api/v1', tags=['retrieval'], dependencies=[
        Depends(current_identity), Depends(unique_headers), Depends(private_response),
    ])

    @router.post('/retrieval/query', response_model=RetrievalQueryView,
                 dependencies=[Depends(verify_write), Depends(query_fields())])
    def query(body: RetrievalQueryWrite, request: Request) -> Response:
        # Preserve the same complete JSON encoding measured by the service's
        # response budget; returning a Response cannot silently re-encode it.
        return Response(json_bytes(service.query(request.state.identity, body)),
                        media_type='application/json',
                        headers={'Cache-Control': 'no-store', 'Vary': 'Cookie'})

    @router.get('/index/status', response_model=RetrievalIndexStatusView,
                dependencies=[Depends(status_query_shape)])
    def status(request: Request,
               scope_refs: Annotated[str | None, Query(min_length=1)] = None,
               cursor: Annotated[str | None, Query(min_length=1, max_length=1024)] = None,
               limit: Annotated[int, Query(ge=1, le=100)] = 20) -> RetrievalIndexStatusView:
        if scope_refs is not None:
            try:
                refs = SCOPE_REFS.validate_python(strict_json(scope_refs.encode('utf-8')))
            except (ValueError, ValidationError):
                raise ApiError(422, 'SCHEMA_INVALID', '范围必须是单个严格 JSON 内容引用数组。') from None
            return service.scope_status(request.state.identity, refs)
        return service.overview(request.state.identity, cursor=cursor, limit=limit)

    @router.post('/index/rebuild', response_model=dm.JobRef, status_code=202,
                 dependencies=[Depends(verify_write), Depends(query_fields())],
                 openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def rebuild(body: RetrievalIndexRebuildWrite, request: Request,
                key: Annotated[str, Depends(command_key)]) -> dm.JobRef:
        return service.rebuild(request.state.identity, body, key)

    return router
