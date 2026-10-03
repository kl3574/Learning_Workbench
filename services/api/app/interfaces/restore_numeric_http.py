"""Closed Restore numeric transport; composition supplies the actual owner.

Reading observes checked persisted facts. Preview and decision have independent
commands and never derive approval from a candidate or a previous check.
"""
from typing import Protocol

from fastapi import APIRouter, Depends, Request, Response

from packages.contracts import domain_models as dm
from ..authoring_dto import NumericCheckDecisionAck
from ..infrastructure.security import SessionIdentity
from ..restore_numeric_dto import RestoreNumericCheckPreviewWrite, RestoreNumericCheckView
from .content_http import query_fields
from .draft_http import no_get_body
from .http import current_identity, verify_write
from .practice_http import private_response
from .tutor_http import COMMAND_PARAMETER, command_key, unique_headers


class RestoreNumericHTTPService(Protocol):
    def preview(self, identity: SessionIdentity, draft_id: str,
                body: RestoreNumericCheckPreviewWrite, key: str) -> RestoreNumericCheckView: ...

    def read(self, identity: SessionIdentity, check_id: str) -> RestoreNumericCheckView: ...

    def decide(self, identity: SessionIdentity, check_id: str,
               body: dm.ApprovalDecision, key: str) -> NumericCheckDecisionAck: ...


def create_restore_numeric_router(service: RestoreNumericHTTPService) -> APIRouter:
    router = APIRouter(prefix='/api/v1', tags=['quality'], dependencies=[
        Depends(current_identity), Depends(unique_headers), Depends(private_response), Depends(query_fields())])

    @router.post('/content/restore-drafts/{id}/numeric-checks',
                 response_model=RestoreNumericCheckView, status_code=201,
                 dependencies=[Depends(verify_write)], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def preview(id: dm.Id, body: RestoreNumericCheckPreviewWrite, request: Request) -> RestoreNumericCheckView:
        return service.preview(request.state.identity, id, body, command_key(request))

    @router.get('/content/restore-numeric-checks/{id}', response_model=RestoreNumericCheckView,
                dependencies=[Depends(no_get_body)])
    def read(id: dm.Id, request: Request) -> RestoreNumericCheckView:
        return service.read(request.state.identity, id)

    @router.post('/content/restore-numeric-checks/{id}/decision', response_model=NumericCheckDecisionAck,
                 status_code=202, responses={200: {'model': NumericCheckDecisionAck}},
                 dependencies=[Depends(verify_write)], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def decide(id: dm.Id, body: dm.ApprovalDecision, request: Request, response: Response) -> NumericCheckDecisionAck:
        result = service.decide(request.state.identity, id, body, command_key(request))
        response.status_code = 202 if result.decision == 'approve_once' else 200
        return result

    return router
