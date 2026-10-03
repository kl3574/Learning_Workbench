"""Explicit publication intent; the owning service commits and verifies real results."""
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Request
from packages.contracts import domain_models as dm
from ..application.publication_admission_models import DraftPublishWrite
from .authoring_http import query_fields
from .http import current_identity, verify_write
from .practice_http import private_response
from .tutor_http import COMMAND_PARAMETER, command_key, unique_headers

if TYPE_CHECKING:
    from ..application.draft_publication import DraftPublicationService


def create_publication_router(service: 'DraftPublicationService') -> APIRouter:
    router = APIRouter(prefix='/api/v1', tags=['quality'], dependencies=[
        Depends(current_identity), Depends(unique_headers), Depends(private_response)])

    @router.post('/drafts/{id}/publish', response_model=dm.ContentRef, status_code=201,
                 dependencies=[Depends(verify_write)], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def publish(id: dm.Id, body: DraftPublishWrite, request: Request) -> dm.ContentRef:
        query_fields(request, set())
        return service.publish(request.state.identity, id, body, command_key(request))

    return router
