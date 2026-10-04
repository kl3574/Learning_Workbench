"""Strict generic tool-approval routes, distinct from every other approval owner."""
from fastapi import APIRouter, Depends, Request
from packages.contracts import domain_models as dm
from ..application.codex_approvals import CodexApprovalsService
from ..codex_turn_dto import GenericApprovalView, GenericApprovalDecisionAck
from .codex_bootstrap_http import no_control_body
from .content_http import query_fields
from .http import current_identity, verify_write
from .practice_http import private_response
from .provider_http import unique_control_headers, command_key, COMMAND_PARAMETER


def create_codex_approval_router(service: CodexApprovalsService) -> APIRouter:
    router = APIRouter(prefix='/api/v1/approvals', tags=['codex'], dependencies=[
        Depends(current_identity), Depends(unique_control_headers), Depends(private_response)])

    @router.get('/{id}', response_model=GenericApprovalView,
        dependencies=[Depends(no_control_body), Depends(query_fields())])
    def read(id: dm.Id, request: Request) -> GenericApprovalView:
        return service.read(request.state.identity, id)

    @router.post('/{id}/decision', response_model=GenericApprovalDecisionAck,
        dependencies=[Depends(verify_write), Depends(query_fields())], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def decide(id: dm.Id, body: dm.ApprovalDecision, request: Request) -> GenericApprovalDecisionAck:
        return service.decide(request.state.identity, id, body, command_key(request))

    return router
