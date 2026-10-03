"""Explicit review commands; current access and complete history live in Quality."""
from typing import TYPE_CHECKING

from fastapi import APIRouter, Depends, Request
from packages.contracts import domain_models as dm
from ..application.review_history_models import ReviewJobAck, StoredReviewReceipt
from ..review_dto import DraftReviewWrite, ReviewDecisionWrite
from .authoring_http import query_fields
from .http import current_identity, verify_write
from .practice_http import private_response
from .tutor_http import COMMAND_PARAMETER, command_key, unique_headers

if TYPE_CHECKING:
    from ..application.review_service import ReviewService


def create_review_router(service: 'ReviewService') -> APIRouter:
    router = APIRouter(prefix='/api/v1', tags=['quality'], dependencies=[
        Depends(current_identity), Depends(unique_headers), Depends(private_response)])

    @router.post('/drafts/{id}/review', response_model=ReviewJobAck, status_code=202,
                 dependencies=[Depends(verify_write)], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def create(id: dm.Id, body: DraftReviewWrite, request: Request) -> ReviewJobAck:
        query_fields(request, set())
        return service.create(request.state.identity, id, body, command_key(request))

    @router.get('/reviews/{id}', response_model=StoredReviewReceipt)
    def read(id: dm.Id, request: Request) -> StoredReviewReceipt:
        query_fields(request, set())
        return service.read(request.state.identity, id)

    @router.post('/reviews/{id}/decision', response_model=StoredReviewReceipt,
                 dependencies=[Depends(verify_write)], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def decide(id: dm.Id, body: ReviewDecisionWrite, request: Request) -> StoredReviewReceipt:
        query_fields(request, set())
        return service.decide(request.state.identity, id, body, command_key(request))

    return router
