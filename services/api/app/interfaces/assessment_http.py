"""Seven actual ungraded assessment routes; no result or pretend-grading endpoint."""

from fastapi import APIRouter, Depends, Request

from packages.contracts import domain_models as dm

from ..application.assessment import AssessmentService
from ..assessment_dto import AssessmentAttemptCreate, AttemptResponses, AttemptSnapshot, PageAssessment
from ..infrastructure.database import Database
from .content_http import CursorQuery, LimitQuery, query_fields
from .http import current_identity, verify_write
from .practice_http import IdQuery, Key, private_response, unique_headers


def create_assessment_router(database: Database) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["assessment"],
                       dependencies=[Depends(current_identity), Depends(unique_headers), Depends(private_response)])
    service = AssessmentService(database)

    @router.get("/assessments", response_model=PageAssessment,
                dependencies=[Depends(query_fields("course_id", "limit", "cursor"))])
    def list_assessments(request: Request, course_id: IdQuery = None, limit: LimitQuery = 20, cursor: CursorQuery = None) -> PageAssessment:
        return service.list_assessments(request.state.identity, course_id=course_id, limit=limit, cursor=cursor)

    @router.post("/assessments/{id}/attempts", response_model=AttemptSnapshot, status_code=201,
                 dependencies=[Depends(verify_write), Depends(query_fields())])
    def create(id: dm.Id, body: AssessmentAttemptCreate, request: Request, key: Key) -> AttemptSnapshot:
        return service.create_attempt(request.state.identity, id, body, key)

    @router.get("/attempts/{id}", response_model=AttemptSnapshot, dependencies=[Depends(query_fields())])
    def get(id: dm.Id, request: Request) -> AttemptSnapshot:
        return service.get_attempt(request.state.identity, id)

    @router.get("/attempts/{id}/responses", response_model=AttemptResponses, dependencies=[Depends(query_fields())])
    def responses(id: dm.Id, request: Request) -> AttemptResponses:
        return service.get_responses(request.state.identity, id)

    @router.put("/attempts/{id}/responses", response_model=AttemptSnapshot,
                dependencies=[Depends(verify_write), Depends(query_fields())])
    def save(id: dm.Id, body: dm.ResponsesWrite, request: Request, key: Key) -> AttemptSnapshot:
        return service.save_responses(request.state.identity, id, body, key)

    @router.post("/attempts/{id}/submit", response_model=AttemptSnapshot, status_code=202,
                 dependencies=[Depends(verify_write), Depends(query_fields())])
    def submit(id: dm.Id, body: dm.AttemptSubmit, request: Request, key: Key) -> AttemptSnapshot:
        return service.submit(request.state.identity, id, body, key)

    @router.post("/attempts/{id}/abandon", response_model=AttemptSnapshot,
                 dependencies=[Depends(verify_write), Depends(query_fields())])
    def abandon(id: dm.Id, body: dm.AttemptSubmit, request: Request, key: Key) -> AttemptSnapshot:
        return service.abandon(request.state.identity, id, body, key)

    return router
