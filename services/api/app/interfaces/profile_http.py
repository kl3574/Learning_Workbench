"""Strict read/write profile boundary with server-owned provenance and timestamps."""

from fastapi import APIRouter, Depends, Request

from packages.contracts import domain_models as dm

from ..application.profile import ProfileService
from ..infrastructure.database import Database
from ..profile_dto import ProfileWrite
from .content_http import query_fields
from .http import current_identity, verify_write
from .practice_http import Key, private_response, unique_headers


def create_profile_router(database: Database) -> APIRouter:
    router = APIRouter(prefix='/api/v1', tags=['learner-profile'],
        dependencies=[Depends(current_identity), Depends(unique_headers), Depends(private_response), Depends(query_fields())])
    service = ProfileService(database)

    @router.get('/learner/profile', response_model=dm.LearnerProfile)
    def read(request: Request) -> dm.LearnerProfile:
        return service.read(request.state.identity.workspace_id)

    @router.put('/learner/profile', response_model=dm.LearnerProfile, dependencies=[Depends(verify_write)])
    def write(body: ProfileWrite, request: Request, key: Key) -> dm.LearnerProfile:
        return service.save(request.state.identity, body, key)

    return router
