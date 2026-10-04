"""Five real local-control operations; bodyless reads never start recovery."""
from fastapi import APIRouter, Depends, Request

from packages.contracts import domain_models as dm
from ..application.codex_bootstrap import CodexBootstrapService
from ..application.errors import ApiError
from ..codex_bootstrap_dto import (
    CodexBootstrapPreparationWrite, CodexBootstrapPreparationView, CodexBootstrapDecisionAck,
    CodexSessionCreateWrite, CodexSessionCreateAck, CodexSessionView,
)
from .content_http import query_fields
from .http import current_identity, verify_write
from .practice_http import private_response
from .provider_http import unique_control_headers, command_key, COMMAND_PARAMETER


async def no_control_body(request: Request) -> None:
    if await request.body():
        raise ApiError(422, 'SCHEMA_INVALID', '本地控制读取不接受请求正文。')


def create_codex_bootstrap_router(service: CodexBootstrapService) -> APIRouter:
    router = APIRouter(prefix='/api/v1/codex', tags=['codex'], dependencies=[Depends(current_identity),
        Depends(unique_control_headers), Depends(private_response), Depends(query_fields())])

    @router.post('/session-preparations', response_model=CodexBootstrapPreparationView, status_code=201,
                 dependencies=[Depends(verify_write)], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def prepare(body: CodexBootstrapPreparationWrite, request: Request) -> CodexBootstrapPreparationView:
        return service.prepare(request.state.identity, body, command_key(request))

    @router.get('/session-preparations/{id}', response_model=CodexBootstrapPreparationView,
                dependencies=[Depends(no_control_body)])
    def preparation(id: dm.Id, request: Request) -> CodexBootstrapPreparationView:
        return service.read_preparation(request.state.identity, id)

    @router.post('/session-preparations/{id}/decision', response_model=CodexBootstrapDecisionAck, status_code=200,
                 dependencies=[Depends(verify_write)], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def decide(id: dm.Id, body: dm.ApprovalDecision, request: Request) -> CodexBootstrapDecisionAck:
        return service.decide(request.state.identity, id, body, command_key(request))

    @router.post('/sessions', response_model=CodexSessionCreateAck, status_code=201,
                 dependencies=[Depends(verify_write)], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def create(body: CodexSessionCreateWrite, request: Request) -> CodexSessionCreateAck:
        return service.create_session(request.state.identity, body, command_key(request))

    @router.get('/sessions/{id}', response_model=CodexSessionView, dependencies=[Depends(no_control_body)])
    def session(id: dm.Id, request: Request) -> CodexSessionView:
        return service.read_session(request.state.identity, id)

    return router
