"""Six real group operations; private answers require a separate protected read."""
from fastapi import APIRouter, Depends, Request, Response

from packages.contracts import domain_models as dm
from ..application.authoring_group import AuthoringGroupService
from ..application.authoring_group_numeric_service import GroupNumericService
from ..authoring_dto import NumericCheckDecisionAck
from ..authoring_group_dto import (
    AuthoringGroupDraftView, AuthoringGroupNumericCheckView, AuthoringGroupNumericPreviewWrite,
    AuthoringGroupPrepareWrite, AuthoringPrivateSolutionView,
)
from .authoring_http import query_fields
from .http import current_identity, verify_write
from .practice_http import private_response
from .tutor_http import COMMAND_PARAMETER, command_key, unique_headers


def create_authoring_group_router(service: AuthoringGroupService, numeric: GroupNumericService) -> APIRouter:
    router = APIRouter(prefix='/api/v1', tags=['authoring'], dependencies=[
        Depends(current_identity), Depends(unique_headers), Depends(private_response)])

    @router.post('/authoring/group-jobs', response_model=dm.JobRef, status_code=202,
                 dependencies=[Depends(verify_write)], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def prepare(body: AuthoringGroupPrepareWrite, request: Request) -> dm.JobRef:
        query_fields(request, set())
        return service.prepare(request.state.identity, body, command_key(request))

    @router.get('/authoring/draft-groups/{id}', response_model=AuthoringGroupDraftView)
    def draft(id: str, request: Request) -> AuthoringGroupDraftView:
        result = service.draft(request.state.identity, id)
        query_fields(request, set())
        return result

    @router.get('/authoring/draft-groups/{id}/solutions/{member_key}', response_model=AuthoringPrivateSolutionView)
    def solution(id: str, member_key: str, request: Request) -> AuthoringPrivateSolutionView:
        result = service.solution(request.state.identity, id, member_key)
        query_fields(request, set())
        return result

    @router.post('/authoring/draft-groups/{id}/members/{member_key}/numeric-checks',
                 response_model=AuthoringGroupNumericCheckView, status_code=201,
                 dependencies=[Depends(verify_write)], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def preview(id: str, member_key: str, body: AuthoringGroupNumericPreviewWrite,
                request: Request) -> AuthoringGroupNumericCheckView:
        query_fields(request, set())
        return numeric.preview(request.state.identity, id, member_key, body, command_key(request))

    @router.get('/authoring/group-numeric-checks/{id}', response_model=AuthoringGroupNumericCheckView)
    def read(id: str, request: Request) -> AuthoringGroupNumericCheckView:
        result = numeric.read(request.state.identity, id)
        query_fields(request, set())
        return result

    @router.post('/authoring/group-numeric-checks/{id}/decision', response_model=NumericCheckDecisionAck,
                 status_code=202, responses={200: {'model': NumericCheckDecisionAck}},
                 dependencies=[Depends(verify_write)], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def decide(id: str, body: dm.ApprovalDecision, request: Request, response: Response) -> NumericCheckDecisionAck:
        query_fields(request, set())
        result = numeric.decide(request.state.identity, id, body, command_key(request))
        response.status_code = 202 if result.decision == 'approve_once' else 200
        return result

    return router
