"""Declared general Draft create/edit routes backed by the editing owner."""
from fastapi import APIRouter, Depends, Request

from packages.contracts import domain_models as dm
from ..application.draft_edits import DraftEditService
from ..draft_dto import DraftCreateWrite, DraftCreated, DraftPatchWrite, DraftPatched
from .http import current_identity, verify_write
from .practice_http import private_response
from .tutor_http import COMMAND_PARAMETER, command_key, query_fields, unique_headers


OPTIONAL_COMMAND_PARAMETER = {**COMMAND_PARAMETER, 'required': False}


def create_draft_router(service: DraftEditService) -> APIRouter:
    router = APIRouter(prefix='/api/v1', tags=['quality'], dependencies=[
        Depends(current_identity), Depends(unique_headers), Depends(private_response)])

    @router.post('/drafts', response_model=DraftCreated, status_code=201,
                 dependencies=[Depends(verify_write)], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def create(body: DraftCreateWrite, request: Request) -> DraftCreated:
        query_fields(request, set())
        return service.create(request.state.identity, body, command_key(request))

    @router.patch('/drafts/{id}', response_model=DraftPatched,
                  dependencies=[Depends(verify_write)], openapi_extra={'parameters': [OPTIONAL_COMMAND_PARAMETER]})
    def patch(id: dm.Id, body: DraftPatchWrite, request: Request) -> DraftPatched:
        query_fields(request, set())
        return service.patch(request.state.identity, id, body, request.headers.get('idempotency-key'))

    return router
