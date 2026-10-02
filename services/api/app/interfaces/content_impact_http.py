"""Content-owned impact report and explicit per-object decisions."""
import re
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from packages.contracts import domain_models as dm
from ..application.content_impact_decisions import ContentImpactDecisionService
from ..application.errors import ApiError
from ..content_impact_dto import ContentImpactPage, ContentImpactView, ImpactObjectDecisionReceipt, ImpactObjectDecisionWrite
from .content_http import query_fields
from .http import current_identity, verify_write
from .practice_http import private_response
from .tutor_http import COMMAND_PARAMETER, command_key, unique_headers


async def no_body(request: Request) -> None:
    async for chunk in request.stream():
        if chunk:
            raise ApiError(422, 'SCHEMA_INVALID', '内容影响读取不接受请求正文。')


def create_content_impact_router(service: ContentImpactDecisionService) -> APIRouter:
    router = APIRouter(prefix='/api/v1', tags=['content'], dependencies=[
        Depends(current_identity), Depends(unique_headers), Depends(private_response)])

    @router.get('/content/impacts', response_model=ContentImpactPage,
                dependencies=[Depends(no_body), Depends(query_fields('changed_object_id', 'cursor', 'limit'))])
    def discover(request: Request,
                 changed_object_id: Annotated[dm.Id | None, Query()] = None,
                 cursor: Annotated[str | None, Query(min_length=1, max_length=1024)] = None,
                 limit: Annotated[int, Query(ge=1, le=100)] = 20) -> ContentImpactPage:
        if 'limit' in request.query_params and re.fullmatch(r'[1-9][0-9]*', request.query_params['limit']) is None:
            raise ApiError(422, 'SCHEMA_INVALID', '分页大小必须为单个正整数。')
        return service.discover(request.state.identity, changed_object_id=changed_object_id, limit=limit, cursor=cursor)

    @router.get('/content/impacts/{event_id}', response_model=ContentImpactView,
                dependencies=[Depends(no_body), Depends(query_fields('target_id', 'cursor', 'limit'))])
    def read(event_id: dm.Id, request: Request,
             target_id: Annotated[dm.Id | None, Query()] = None,
             cursor: Annotated[str | None, Query(min_length=1, max_length=1024)] = None,
             limit: Annotated[int, Query(ge=1, le=100)] = 20) -> ContentImpactView:
        if 'limit' in request.query_params and re.fullmatch(r'[1-9][0-9]*', request.query_params['limit']) is None:
            raise ApiError(422, 'SCHEMA_INVALID', '分页大小必须为单个正整数。')
        return service.read(request.state.identity, event_id, target_id=target_id, limit=limit, cursor=cursor)

    @router.post('/content/impacts/{event_id}/decisions', response_model=ImpactObjectDecisionReceipt,
                 dependencies=[Depends(verify_write), Depends(query_fields())],
                 openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def decide(event_id: dm.Id, body: ImpactObjectDecisionWrite, request: Request) -> ImpactObjectDecisionReceipt:
        return service.decide(request.state.identity, event_id, body, command_key(request))

    return router
