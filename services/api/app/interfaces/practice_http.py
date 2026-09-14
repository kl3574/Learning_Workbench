"""Seven practice routes; authenticated application ports own all business writes."""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response

from packages.contracts import domain_models as dm

from ..application.errors import ApiError
from ..application.practice import PracticeService
from ..infrastructure.database import Database
from ..practice_dto import (
    PagePracticeSet,
    PracticeHint,
    PracticeHintRequest,
    PracticeResponsesSaved,
    PracticeSession,
    PracticeSessionCreate,
    PracticeSessionCreated,
    PracticeSolution,
    PracticeSolutionRequest,
    PracticeSubmitted,
    PracticeSubmitRequest,
)
from .content_http import CursorQuery, LimitQuery, query_fields
from .http import current_identity, verify_write

IdQuery = Annotated[dm.Id | None, Query()]


def idempotency_key(request: Request, value: Annotated[str, Header(alias="Idempotency-Key")]) -> str:
    if len(request.headers.getlist("idempotency-key")) != 1 or re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value) is None:
        raise ApiError(422, "SCHEMA_INVALID", "幂等键必须是单个有效值。")
    return value


def private_response(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Vary"] = "Cookie"


def unique_headers(request: Request) -> None:
    names = ("cookie", "origin", "x-csrf-token", "idempotency-key", "content-type", "content-length", "if-match")
    if any(len(request.headers.getlist(name)) > 1 for name in names):
        raise ApiError(422, "SCHEMA_INVALID", "身份、内容类型或并发控制头不得重复。")


Key = Annotated[str, Depends(idempotency_key)]


def create_practice_router(database: Database) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["practice"],
                       dependencies=[Depends(current_identity), Depends(unique_headers), Depends(private_response)])
    service = PracticeService(database)

    @router.get("/practice/sets", response_model=PagePracticeSet,
                dependencies=[Depends(query_fields("course_id", "lesson_id", "cursor", "limit"))])
    def list_sets(request: Request, course_id: IdQuery = None, lesson_id: IdQuery = None,
                  cursor: CursorQuery = None, limit: LimitQuery = 20) -> PagePracticeSet:
        return service.list_sets(request.state.identity, course_id=course_id, lesson_id=lesson_id, cursor=cursor, limit=limit)

    @router.post("/practice/sessions", status_code=201, response_model=PracticeSessionCreated,
                 dependencies=[Depends(verify_write), Depends(query_fields())])
    def create_session(body: PracticeSessionCreate, request: Request, key: Key) -> PracticeSessionCreated:
        result = service.create_session(request.state.identity, body, key)
        return PracticeSessionCreated.model_validate(result.model_dump(mode="python"))

    @router.get("/practice/sessions/{id}", response_model=PracticeSession,
                dependencies=[Depends(query_fields())])
    def get_session(id: dm.Id, request: Request) -> PracticeSession:
        return service.get_session(request.state.identity, id)

    @router.put("/practice/sessions/{id}/responses", response_model=PracticeResponsesSaved,
                dependencies=[Depends(verify_write), Depends(query_fields())])
    def save_responses(id: dm.Id, body: dm.ResponsesWrite, request: Request, key: Key) -> PracticeResponsesSaved:
        return service.save_responses(request.state.identity, id, body, key)

    @router.post("/practice/sessions/{id}/submit", response_model=PracticeSubmitted,
                 dependencies=[Depends(verify_write), Depends(query_fields())])
    def submit(id: dm.Id, body: PracticeSubmitRequest, request: Request, key: Key) -> PracticeSubmitted:
        return service.submit(request.state.identity, id, body, key)

    @router.post("/practice/sessions/{id}/hints", response_model=PracticeHint,
                 dependencies=[Depends(verify_write), Depends(query_fields())])
    def hint(id: dm.Id, body: PracticeHintRequest, request: Request, key: Key) -> PracticeHint:
        return service.hint(request.state.identity, id, body, key)

    @router.post("/practice/sessions/{id}/solutions", response_model=PracticeSolution,
                 dependencies=[Depends(verify_write), Depends(query_fields())])
    def solution(id: dm.Id, body: PracticeSolutionRequest, request: Request, key: Key) -> PracticeSolution:
        return service.solution(request.state.identity, id, body, key)

    return router
