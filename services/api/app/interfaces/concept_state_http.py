"""Exact concept/skill state projection; sources retain their distinct count units."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from packages.contracts import domain_models as dm

from ..application.concept_states import ConceptStateService
from ..concept_state_dto import ConceptStateResponse
from ..infrastructure.database import Database
from .content_http import query_fields
from .http import current_identity
from .practice_http import private_response, unique_headers


def create_concept_state_router(database: Database) -> APIRouter:
    router = APIRouter(prefix='/api/v1', tags=['learning-state'],
        dependencies=[Depends(current_identity), Depends(unique_headers), Depends(private_response)])
    service = ConceptStateService(database)

    @router.get('/learning/concept-states', response_model=ConceptStateResponse,
        dependencies=[Depends(query_fields('course_id'))])
    def read(request: Request, course_id: Annotated[dm.Id | None, Query()] = None) -> ConceptStateResponse:
        return service.read(request.state.identity.workspace_id, course_id)

    return router
