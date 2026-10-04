"""Authenticated local control and frozen outbound consent operations."""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from packages.contracts import domain_models as dm

from ..application.consents import ConsentsService
from ..application.errors import ApiError
from ..application.providers import ProviderService
from ..provider_dto import (
    ConsentCreate, ConsentCreateAck, ConsentPage, ConsentPreviewWrite,
    ConsentProposalView, ConsentRevoke, ProviderCapabilitiesResponse,
    ProviderConfigAck, ProviderConfigView, ProviderConfigWrite,
    ProviderSecretAck, ProviderSecretWrite,
)
from .content_http import query_fields
from .http import current_identity, verify_write
from .practice_http import private_response


COMMAND_PARAMETER = {
    'name': 'Idempotency-Key', 'in': 'header', 'required': True,
    'schema': {'type': 'string', 'pattern': '^[A-Za-z0-9_-]{1,128}$'},
}
MATCH_PARAMETER = {
    'name': 'If-Match', 'in': 'header', 'required': True,
    'schema': {'type': 'string', 'pattern': '^"[0-9a-f]{64}"$'},
}


def unique_control_headers(request: Request) -> None:
    if any(len(request.headers.getlist(name)) > 1 for name in
           ('cookie', 'origin', 'x-csrf-token', 'content-type', 'content-length', 'authorization')):
        raise ApiError(422, 'SCHEMA_INVALID', '身份或请求内容类型头不得重复。')


def command_key(request: Request) -> str:
    keys = request.headers.getlist('idempotency-key')
    if len(keys) != 1 or re.fullmatch(r'[A-Za-z0-9_-]{1,128}', keys[0]) is None:
        raise ApiError(400, 'IDEMPOTENCY_KEY_INVALID', '操作需要单个有效的原命令幂等键。')
    return keys[0]


def config_match(request: Request) -> str:
    values = request.headers.getlist('if-match')
    if len(values) != 1 or re.fullmatch(r'"[0-9a-f]{64}"', values[0]) is None:
        raise ApiError(400, 'IF_MATCH_INVALID', '操作需要单个带引号的配置版本 SHA-256。')
    return values[0][1:-1]


async def no_delete_body(request: Request) -> None:
    if await request.body():
        raise ApiError(422, 'SCHEMA_INVALID', '删除密钥引用的操作不接受请求正文。')


def consent_query_shape(request: Request) -> None:
    query_fields('consent_id', 'cursor', 'limit')(request)
    fields = request.query_params
    if 'consent_id' in fields and ('cursor' in fields or 'limit' in fields):
        raise ApiError(422, 'SCHEMA_INVALID', '按许可 ID 回读不能同时指定分页字段。')
    if 'limit' in fields and (not fields['limit'].isascii() or not fields['limit'].isdecimal()):
        raise ApiError(422, 'SCHEMA_INVALID', '分页数量必须是十进制整数。')
    if 'cursor' in fields and not fields['cursor'].strip():
        raise ApiError(422, 'SCHEMA_INVALID', '分页游标不能为空白。')


def create_provider_router(providers: ProviderService, consents: ConsentsService) -> APIRouter:
    router = APIRouter(prefix='/api/v1', tags=['providers'], dependencies=[
        Depends(current_identity), Depends(unique_control_headers), Depends(private_response),
    ])

    @router.get('/providers/capabilities', response_model=ProviderCapabilitiesResponse,
                dependencies=[Depends(query_fields())])
    def capabilities(request: Request) -> ProviderCapabilitiesResponse:
        return providers.capabilities(request.state.identity)

    @router.get('/providers/{id}/config', response_model=ProviderConfigView,
                dependencies=[Depends(query_fields())])
    def config(id: dm.Id, request: Request) -> ProviderConfigView:
        return providers.read_config(request.state.identity, id)

    @router.put('/providers/{id}/config', response_model=ProviderConfigAck,
                dependencies=[Depends(verify_write), Depends(query_fields())],
                openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def save_config(id: dm.Id, body: ProviderConfigWrite, request: Request,
                    key: Annotated[str, Depends(command_key)]) -> ProviderConfigAck:
        return providers.save_config(request.state.identity, id, body, key)

    @router.post('/providers/{id}/secret', response_model=ProviderSecretAck,
                 dependencies=[Depends(verify_write), Depends(query_fields())],
                 openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def save_secret(id: dm.Id, body: ProviderSecretWrite, request: Request,
                    key: Annotated[str, Depends(command_key)]) -> ProviderSecretAck:
        return providers.save_secret(request.state.identity, id, body, key)

    @router.delete('/providers/{id}/secret', response_model=ProviderSecretAck,
                   dependencies=[Depends(verify_write), Depends(query_fields()), Depends(no_delete_body)],
                   openapi_extra={'parameters': [COMMAND_PARAMETER, MATCH_PARAMETER]})
    def delete_secret(id: dm.Id, request: Request, key: Annotated[str, Depends(command_key)],
                      expected_sha256: Annotated[str, Depends(config_match)]) -> ProviderSecretAck:
        return providers.delete_secret(request.state.identity, id, expected_sha256, key)

    @router.post('/consents/preview', response_model=ConsentProposalView, status_code=201,
                 dependencies=[Depends(verify_write), Depends(query_fields())],
                 openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def preview(body: ConsentPreviewWrite, request: Request,
                key: Annotated[str, Depends(command_key)]) -> ConsentProposalView:
        return consents.preview(request.state.identity, body, key)

    @router.get('/consents/preview/{id}', response_model=ConsentProposalView,
                dependencies=[Depends(query_fields())])
    def proposal(id: dm.Id, request: Request) -> ConsentProposalView:
        return consents.proposal(request.state.identity, id)

    @router.post('/consents', response_model=ConsentCreateAck, status_code=201,
                 dependencies=[Depends(verify_write), Depends(query_fields())],
                 openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def grant(body: ConsentCreate, request: Request,
              key: Annotated[str, Depends(command_key)]) -> ConsentCreateAck:
        return consents.grant(request.state.identity, body, key)

    @router.get('/consents', response_model=ConsentPage, dependencies=[Depends(consent_query_shape)])
    def page(request: Request,
             consent_id: Annotated[dm.Id | None, Query()] = None,
             cursor: Annotated[str | None, Query(min_length=1, max_length=1024)] = None,
             limit: Annotated[int, Query(ge=1, le=100)] = 20) -> ConsentPage:
        return consents.page(request.state.identity, consent_id=consent_id, cursor=cursor, limit=limit)

    @router.post('/consents/{id}/revoke', response_model=dm.MutationAck,
                 dependencies=[Depends(verify_write), Depends(query_fields())],
                 openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def revoke(id: dm.Id, body: ConsentRevoke, request: Request,
               key: Annotated[str, Depends(command_key)]) -> dm.MutationAck:
        return consents.revoke(request.state.identity, id, body, key)

    return router
