"""Declared general Draft create/edit routes backed by the editing owner."""
import re

from fastapi import APIRouter, Depends, Request

from packages.contracts import domain_models as dm
from ..application.draft_edits import DraftEditService
from ..application.draft_edit_models import EditDraftSnapshot, MAX_VERSIONS
from ..application.errors import ApiError
from ..draft_dto import DraftCreateWrite, DraftCreated, DraftPatchWrite, DraftPatched
from .content_http import query_fields as strict_query_fields
from .http import current_identity, verify_write
from .practice_http import private_response
from .tutor_http import COMMAND_PARAMETER, command_key, query_fields, unique_headers


OPTIONAL_COMMAND_PARAMETER = {**COMMAND_PARAMETER, 'required': False}
REVISION_PARAMETER = {'name': 'revision', 'in': 'query', 'required': False,
                      'schema': {'type': 'integer', 'minimum': 1}}


async def no_get_body(request: Request) -> None:
    async for chunk in request.stream():
        if chunk:
            raise ApiError(422, 'SCHEMA_INVALID', '编辑草稿读取不接受请求正文。')


def exact_revision(request: Request) -> int | None:
    strict_query_fields('revision')(request)
    raw = request.query_params.get('revision')
    if raw is None:
        return None
    if re.fullmatch(r'[1-9][0-9]*', raw) is None:
        raise ApiError(422, 'SCHEMA_INVALID', '修订号须为单个正整数。')
    if len(raw) > 16:
        return MAX_VERSIONS + 1  # Every such positive revision is beyond the bounded immutable history.
    return int(raw)


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

    @router.get('/draft-edits/{id}', response_model=EditDraftSnapshot,
                dependencies=[Depends(no_get_body)], openapi_extra={'parameters': [REVISION_PARAMETER]})
    def read_edit(id: dm.Id, request: Request) -> EditDraftSnapshot:
        return service.read_snapshot(request.state.identity, id, exact_revision(request))

    return router
