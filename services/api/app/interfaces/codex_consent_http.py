"""Actual Provider-owned Codex preview, grant, read and revoke operations."""
from fastapi import APIRouter, Depends, Request
from packages.contracts import domain_models as dm

from ..application.provider_codex_consents import CodexConsentsService
from ..codex_turn_dto import (CodexOutboundPreviewWrite, CodexConsentProposalView, CodexConsentCreateWrite,
    CodexConsentCreateAck, CodexConsentView)
from ..provider_dto import ConsentRevoke
from .codex_bootstrap_http import no_control_body
from .content_http import query_fields
from .http import current_identity, verify_write
from .practice_http import private_response
from .provider_http import unique_control_headers, command_key, COMMAND_PARAMETER


def create_codex_consent_router(service: CodexConsentsService) -> APIRouter:
    router = APIRouter(prefix='/api/v1/codex', tags=['codex'], dependencies=[Depends(current_identity),
        Depends(unique_control_headers), Depends(private_response)])

    @router.post('/consent-previews', response_model=CodexConsentProposalView, status_code=201,
        dependencies=[Depends(verify_write), Depends(query_fields())], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def preview(body: CodexOutboundPreviewWrite, request: Request) -> CodexConsentProposalView:
        return service.preview(request.state.identity, body, command_key(request))

    @router.get('/consent-proposals/{id}', response_model=CodexConsentProposalView,
        dependencies=[Depends(no_control_body), Depends(query_fields())])
    def proposal(id: dm.Id, request: Request) -> CodexConsentProposalView:
        return service.proposal(request.state.identity, id)

    @router.post('/consents', response_model=CodexConsentCreateAck, status_code=201,
        dependencies=[Depends(verify_write), Depends(query_fields())], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def grant(body: CodexConsentCreateWrite, request: Request) -> CodexConsentCreateAck:
        return service.grant(request.state.identity, body, command_key(request))

    @router.get('/consents/{id}', response_model=CodexConsentView,
        dependencies=[Depends(no_control_body), Depends(query_fields())])
    def consent(id: dm.Id, request: Request) -> CodexConsentView:
        return service.consent(request.state.identity, id)

    @router.post('/consents/{id}/revoke', response_model=dm.MutationAck,
        dependencies=[Depends(verify_write), Depends(query_fields())], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def revoke(id: dm.Id, body: ConsentRevoke, request: Request) -> dm.MutationAck:
        return service.revoke(request.state.identity, id, body, command_key(request))

    return router
