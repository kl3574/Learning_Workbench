"""Six implemented M2.4 note and explicit learning-action endpoints."""

import re
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query, Request, Response

from packages.contracts import domain_models as dm

from ..application.errors import ApiError
from ..application.evidence import EvidenceService
from ..application.eligibility_models import Skill
from ..application.learning import LearningService
from ..application.notes import NotesService
from ..infrastructure.database import Database
from ..learning_dto import LearningActionRequest, LearningActionResponse, LearningProgress, NoteDeleted, PageEvidence, PageNote
from .content_http import CursorQuery, LimitQuery, query_fields
from .http import current_identity, verify_write

KeyHeader = Annotated[str, Header(alias="Idempotency-Key")]
MatchHeader = Annotated[str | None, Header(alias="If-Match")]
IdQuery = Annotated[dm.Id | None, Query()]


def expected_digest(value: str | None, request: Request) -> str:
    if value is None:
        raise ApiError(428, "PRECONDITION_REQUIRED", "需要提供旧笔记修订的 If-Match。")
    if len(request.headers.getlist("if-match")) != 1 or re.fullmatch(r'"[0-9a-f]{64}"', value) is None:
        raise ApiError(422, "SCHEMA_INVALID", "If-Match 必须是单个精确修订的强 ETag。")
    return value[1:-1]


async def reject_delete_body(request: Request) -> None:
    if await request.body():
        raise ApiError(422, "SCHEMA_INVALID", "删除笔记不接受请求正文。")


def create_learning_router(database: Database) -> APIRouter:
    router = APIRouter(prefix="/api/v1", tags=["learning"], dependencies=[Depends(current_identity)],
                      responses={428: {"model": dm.ErrorEnvelope}})
    notes = NotesService(database)
    learning = LearningService(database)
    evidence = EvidenceService(database)

    @router.get('/learning/evidence', response_model=PageEvidence, dependencies=[Depends(query_fields('concept_id', 'skill', 'cursor', 'limit'))])
    def evidence_page(request: Request, concept_id: IdQuery = None, skill: Annotated[Skill | None, Query()] = None,
                      cursor: CursorQuery = None, limit: LimitQuery = 20) -> PageEvidence:
        return evidence.page(request.state.identity.workspace_id, concept_id, skill, cursor, limit)

    @router.get("/notes", response_model=PageNote, dependencies=[Depends(query_fields("ref_id", "cursor", "limit"))])
    def list_notes(request: Request, ref_id: IdQuery = None, cursor: CursorQuery = None, limit: LimitQuery = 20) -> PageNote:
        return notes.list(request.state.identity.workspace_id, ref_id, limit, cursor)

    @router.post("/notes", response_model=dm.ContentRef, status_code=201, dependencies=[Depends(verify_write), Depends(query_fields())])
    def create_note(body: dm.Note, request: Request, response: Response, idempotency_key: KeyHeader) -> dm.ContentRef:
        result = notes.create(request.state.identity, body, idempotency_key)
        response.headers["ETag"] = f'"{result.sha256}"'
        return result

    @router.patch("/notes/{id}", response_model=dm.ContentRef, dependencies=[Depends(verify_write), Depends(query_fields())])
    def update_note(id: dm.Id, body: dm.Note, request: Request, response: Response,
                    idempotency_key: KeyHeader, if_match: MatchHeader = None) -> dm.ContentRef:
        result = notes.update(request.state.identity, id, body, expected_digest(if_match, request), idempotency_key)
        response.headers["ETag"] = f'"{result.sha256}"'
        return result

    @router.delete("/notes/{id}", response_model=NoteDeleted, dependencies=[Depends(verify_write), Depends(query_fields()), Depends(reject_delete_body)])
    def delete_note(id: dm.Id, request: Request, idempotency_key: KeyHeader, if_match: MatchHeader = None) -> NoteDeleted:
        return notes.delete(request.state.identity, id, expected_digest(if_match, request), idempotency_key)

    @router.get("/learning/progress", response_model=LearningProgress, dependencies=[Depends(query_fields("course_id"))])
    def progress(request: Request, course_id: IdQuery = None) -> LearningProgress:
        return learning.progress(request.state.identity.workspace_id, course_id)

    @router.post("/learning/actions", response_model=LearningActionResponse, dependencies=[Depends(verify_write), Depends(query_fields())])
    def action(body: LearningActionRequest, request: Request, idempotency_key: KeyHeader) -> LearningActionResponse:
        return learning.action(request.state.identity, body, idempotency_key)

    return router
