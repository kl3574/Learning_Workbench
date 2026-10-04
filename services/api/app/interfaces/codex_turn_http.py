"""Four real preparation/control routes; no fake execution endpoints."""
from fastapi import APIRouter, Depends, Request
from packages.contracts import domain_models as dm
from ..application.codex_turn import CodexTurnService
from ..application.errors import ApiError
from ..codex_turn_dto import CodexTurnPrepareWrite, CodexTurnPreparationView, CodexTurnPage, CodexTurnControlView
from .codex_bootstrap_http import no_control_body
from .content_http import query_fields
from .http import current_identity, verify_write
from .practice_http import private_response
from .provider_http import unique_control_headers, command_key, COMMAND_PARAMETER
from .tutor_http import PAGE_PARAMETERS


def create_codex_turn_router(service: CodexTurnService) -> APIRouter:
    router = APIRouter(prefix='/api/v1/codex', tags=['codex'], dependencies=[Depends(current_identity),
        Depends(unique_control_headers), Depends(private_response)])

    @router.post('/sessions/{id}/turn-preparations', response_model=CodexTurnPreparationView, status_code=202,
        dependencies=[Depends(verify_write), Depends(query_fields())], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def prepare(id: dm.Id, body: CodexTurnPrepareWrite, request: Request) -> CodexTurnPreparationView:
        return service.prepare_turn(request.state.identity, id, body, command_key(request))

    @router.get('/turn-preparations/{id}', response_model=CodexTurnPreparationView,
        dependencies=[Depends(no_control_body), Depends(query_fields())])
    def preparation(id: dm.Id, request: Request) -> CodexTurnPreparationView:
        return service.read_preparation(request.state.identity, id)

    @router.get('/turns/{id}', response_model=CodexTurnControlView,
        dependencies=[Depends(no_control_body), Depends(query_fields())])
    def turn(id: dm.Id, request: Request) -> CodexTurnControlView:
        return service.read_control(request.state.identity, id)

    @router.get('/sessions/{id}/turns', response_model=CodexTurnPage,
        dependencies=[Depends(no_control_body), Depends(query_fields('cursor', 'limit'))],
        openapi_extra={'parameters': PAGE_PARAMETERS})
    def turns(id: dm.Id, request: Request) -> CodexTurnPage:
        raw = request.query_params.get('limit', '20')
        cursor = request.query_params.get('cursor')
        if not raw.isascii() or not raw.isdecimal() or not 1 <= len(raw) <= 3 or not 1 <= int(raw) <= 100 or cursor == '':
            raise ApiError(422, 'SCHEMA_INVALID', '分页参数无效。')
        return service.turns(request.state.identity, id, cursor, int(raw))

    return router
