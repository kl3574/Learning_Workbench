"""Strict restore routes; read is zero-write and a distinct owner snapshot."""
from fastapi import APIRouter, Depends, Request
from packages.contracts import domain_models as dm
from ..content_restore_dto import ContentRestoreDraftCreateWrite, ContentRestoreDraftCreateAck, ContentRestoreDraftSnapshot
from .http import current_identity, verify_write
from .practice_http import private_response
from .content_http import query_fields
from .draft_http import no_get_body
from .tutor_http import COMMAND_PARAMETER, command_key, unique_headers


def create_content_restore_router(service):
    router = APIRouter(prefix='/api/v1', tags=['quality'], dependencies=[Depends(current_identity), Depends(unique_headers), Depends(private_response)])

    @router.post('/content/restore-drafts', response_model=ContentRestoreDraftCreateAck, status_code=201,
        dependencies=[Depends(verify_write)], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def create(body: ContentRestoreDraftCreateWrite, request: Request):
        query_fields()(request)
        return service.create(request.state.identity, body, command_key(request))

    @router.get('/content/restore-drafts/{id}', response_model=ContentRestoreDraftSnapshot, dependencies=[Depends(no_get_body)])
    def read(id: dm.Id, request: Request):
        query_fields()(request)
        return service.read(request.state.identity, id)

    return router
