"""Strict applicability read and command routes; GET is private and read-only."""

import re

from fastapi import APIRouter, Depends, Request
from pydantic import TypeAdapter, ValidationError

from packages.contracts import domain_models as dm
from ..application.errors import ApiError
from ..application.evidence_applicability import EvidenceApplicabilityService
from ..evidence_applicability_dto import (
    EvidenceApplicabilityDecisionView, EvidenceImpactDecisionReceipt, EvidenceImpactDecisionWrite,
)
from .authoring_http import query_fields
from .http import current_identity, verify_write
from .practice_http import private_response
from .tutor_http import COMMAND_PARAMETER, PAGE_PARAMETERS, command_key, unique_headers

EVENT_PARAMETER = {'name': 'event_id', 'in': 'query', 'required': False, 'schema': TypeAdapter(dm.Id).json_schema()}


async def no_get_body(request: Request) -> None:
    async for chunk in request.stream():
        if chunk:
            raise ApiError(422, 'SCHEMA_INVALID', '证据适用性读取不接受请求正文。')


def create_evidence_applicability_router(service: EvidenceApplicabilityService) -> APIRouter:
    router = APIRouter(prefix='/api/v1', tags=['learning'], dependencies=[
        Depends(current_identity), Depends(unique_headers), Depends(private_response)])

    @router.get('/learning/evidence/{id}/applicability', response_model=EvidenceApplicabilityDecisionView,
                dependencies=[Depends(no_get_body)], openapi_extra={'parameters': [EVENT_PARAMETER, *PAGE_PARAMETERS]})
    def read(id: dm.Id, request: Request) -> EvidenceApplicabilityDecisionView:
        query_fields(request, {'event_id', 'cursor', 'limit'})
        event_id, cursor = request.query_params.get('event_id'), request.query_params.get('cursor')
        raw_limit = request.query_params.get('limit', '20')
        if (re.fullmatch(r'[0-9]{1,3}', raw_limit) is None or not 1 <= int(raw_limit) <= 100
                or cursor is not None and not cursor.strip()):
            raise ApiError(422, 'SCHEMA_INVALID', '分页须使用非空游标和1至100的整数。')
        if event_id is not None:
            try:
                TypeAdapter(dm.Id).validate_python(event_id)
            except ValidationError:
                raise ApiError(422, 'SCHEMA_INVALID', '事件标识无效。') from None
        return service.read(request.state.identity, id, event_id, cursor, int(raw_limit))

    @router.post('/learning/evidence/{id}/applicability-decisions', response_model=EvidenceImpactDecisionReceipt,
                 dependencies=[Depends(verify_write)], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def decide(id: dm.Id, body: EvidenceImpactDecisionWrite, request: Request) -> EvidenceImpactDecisionReceipt:
        query_fields(request, set())
        return service.decide(request.state.identity, id, body, command_key(request))

    return router
