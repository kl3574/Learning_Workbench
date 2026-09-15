"""Named real Authoring operations; preview, approval and reads stay separate."""
import re

from fastapi import APIRouter, Depends, Request, Response
from packages.contracts import domain_models as dm
from ..application.authoring import AuthoringService
from ..application.authoring_numeric_service import NumericService
from ..application.errors import ApiError
from ..authoring_dto import (
    AuthoringDraftView, AuthoringJobPage, AuthoringJobView, AuthoringPrepareWrite,
    NumericCheckDecisionAck, NumericCheckPreviewWrite, NumericCheckView,
)
from .http import current_identity, verify_write
from .practice_http import private_response
from .tutor_http import COMMAND_PARAMETER, PAGE_PARAMETERS, command_key, unique_headers


def query_fields(request: Request, allowed: set[str]) -> None:
    if (set(request.query_params) - allowed or
            any(len(request.query_params.getlist(name)) != 1 for name in request.query_params)):
        raise ApiError(422, 'SCHEMA_INVALID', '查询字段未知或重复。')


def create_authoring_router(service: AuthoringService, numeric: NumericService) -> APIRouter:
    router = APIRouter(prefix='/api/v1', tags=['authoring'], dependencies=[
        Depends(current_identity), Depends(unique_headers), Depends(private_response)])

    @router.post('/authoring/jobs', response_model=dm.JobRef, status_code=202,
                 dependencies=[Depends(verify_write)], openapi_extra={'parameters':[COMMAND_PARAMETER]})
    def prepare(body: AuthoringPrepareWrite, request: Request) -> dm.JobRef:
        query_fields(request, set())
        return service.prepare(request.state.identity, body, command_key(request))

    @router.get('/authoring/jobs', response_model=AuthoringJobPage,
                openapi_extra={'parameters':PAGE_PARAMETERS})
    def jobs(request: Request) -> AuthoringJobPage:
        query_fields(request, {'cursor','limit'})
        cursor = request.query_params.get('cursor')
        limit = request.query_params.get('limit', '20')
        if (cursor is not None and not cursor.strip() or re.fullmatch(r'[0-9]{1,3}', limit) is None
                or not 1 <= int(limit) <= 100):
            raise ApiError(422, 'SCHEMA_INVALID', '分页须使用非空游标和1至100的整数。')
        return service.jobs(request.state.identity, cursor, int(limit))

    @router.get('/authoring/jobs/{id}', response_model=AuthoringJobView)
    def read(id: str, request: Request) -> AuthoringJobView:
        result = service.read(request.state.identity, id)
        query_fields(request, set())
        return result

    @router.get('/authoring/drafts/{id}', response_model=AuthoringDraftView)
    def draft(id: str, request: Request) -> AuthoringDraftView:
        result = service.draft(request.state.identity, id)
        query_fields(request, set())
        return result

    @router.post('/authoring/drafts/{id}/numeric-checks', response_model=NumericCheckView, status_code=201,
                 dependencies=[Depends(verify_write)], openapi_extra={'parameters':[COMMAND_PARAMETER]})
    def preview(id: str, body: NumericCheckPreviewWrite, request: Request) -> NumericCheckView:
        query_fields(request, set())
        return numeric.preview(request.state.identity, id, body, command_key(request))

    @router.get('/authoring/numeric-checks/{id}', response_model=NumericCheckView)
    def numeric_read(id: str, request: Request) -> NumericCheckView:
        result = numeric.read(request.state.identity, id)
        query_fields(request, set())
        return result

    @router.post('/authoring/numeric-checks/{id}/decision', response_model=NumericCheckDecisionAck,
                 status_code=202, responses={200:{'model':NumericCheckDecisionAck}},
                 dependencies=[Depends(verify_write)], openapi_extra={'parameters':[COMMAND_PARAMETER]})
    def decision(id: str, body: dm.ApprovalDecision, request: Request, response: Response) -> NumericCheckDecisionAck:
        query_fields(request, set())
        result = numeric.decide(request.state.identity, id, body, command_key(request))
        response.status_code = 202 if result.decision == 'approve_once' else 200
        return result

    return router
