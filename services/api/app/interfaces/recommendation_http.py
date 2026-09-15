"""Strict recommendation reads and explicit, conditional decision commands."""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from packages.contracts import domain_models as dm

from ..application.errors import ApiError
from ..application.recommendations import RecommendationService
from ..infrastructure.database import Database
from ..recommendation_dto import RecommendationDecisionWrite, RecommendationPage
from .content_http import CursorQuery, LimitQuery, query_fields
from .http import current_identity, verify_write
from .practice_http import IdQuery, private_response


def command_headers(request: Request) -> tuple[str, str]:
    keys = request.headers.getlist('idempotency-key')
    matches = request.headers.getlist('if-match')
    if len(keys) != 1 or re.fullmatch(r'[A-Za-z0-9_-]{1,128}', keys[0]) is None:
        raise ApiError(400, 'IDEMPOTENCY_KEY_INVALID', '推荐决定需要单个有效的原命令幂等键。')
    if len(matches) != 1 or re.fullmatch(r'"[0-9a-f]{64}"', matches[0]) is None:
        raise ApiError(400, 'IF_MATCH_INVALID', '推荐决定需要单个带引号的决定版本 SHA-256。')
    return keys[0], matches[0][1:-1]


def unique_identity_headers(request: Request) -> None:
    if any(len(request.headers.getlist(name)) > 1 for name in
           ('cookie', 'origin', 'x-csrf-token', 'content-type', 'content-length')):
        raise ApiError(422, 'SCHEMA_INVALID', '身份或请求内容类型头不得重复。')


def create_recommendation_router(database: Database) -> APIRouter:
    router = APIRouter(prefix='/api/v1', tags=['recommendations'],
        dependencies=[Depends(current_identity), Depends(unique_identity_headers), Depends(private_response)])
    service = RecommendationService(database)

    @router.get('/recommendations', response_model=RecommendationPage,
        dependencies=[Depends(query_fields('course_id', 'recommendation_id', 'cursor', 'limit'))])
    def page(request: Request, course_id: IdQuery = None, recommendation_id: IdQuery = None,
             cursor: CursorQuery = None, limit: LimitQuery = 20) -> RecommendationPage:
        if recommendation_id is not None and (course_id is not None or cursor is not None):
            raise ApiError(422, 'SCHEMA_INVALID', '按推荐 ID 回读不能同时指定课程或分页游标。')
        return service.page(request.state.identity.workspace_id, course_id=course_id,
                            recommendation_id=recommendation_id, cursor=cursor, limit=limit)

    @router.post('/recommendations/{id}/decision', response_model=dm.MutationAck,
        dependencies=[Depends(verify_write), Depends(query_fields())], openapi_extra={'parameters': [
            {'name': 'Idempotency-Key', 'in': 'header', 'required': True,
             'schema': {'type': 'string', 'pattern': '^[A-Za-z0-9_-]{1,128}$'}},
            {'name': 'If-Match', 'in': 'header', 'required': True,
             'description': 'Quoted strong SHA-256 of the current decision version.',
             'schema': {'type': 'string', 'pattern': '^"[0-9a-f]{64}"$'}},
        ]})
    def decide(id: dm.Id, body: RecommendationDecisionWrite, request: Request,
               command: Annotated[tuple[str, str], Depends(command_headers)]) -> dm.MutationAck:
        key, expected_sha256 = command
        return service.decide(request.state.identity, id, body, key, expected_sha256)

    return router
