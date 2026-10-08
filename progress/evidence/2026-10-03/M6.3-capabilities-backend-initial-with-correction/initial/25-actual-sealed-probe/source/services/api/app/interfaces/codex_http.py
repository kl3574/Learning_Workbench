"""The already specified, strictly read-only M6.3 capabilities endpoint."""
from fastapi import APIRouter, Depends, Request
from ..application.codex_capabilities import CodexCapabilitiesService
from ..application.errors import ApiError
from ..codex_dto import CodexCapabilities
from .content_http import query_fields
from .http import current_identity
from .practice_http import private_response
from .provider_http import unique_control_headers


async def no_body(request: Request) -> None:
    if await request.body():
        raise ApiError(422, 'SCHEMA_INVALID', 'Codex 能力读取不接受请求正文。')


def create_codex_router(service: CodexCapabilitiesService) -> APIRouter:
    router = APIRouter(prefix='/api/v1/codex', tags=['codex'], dependencies=[
        Depends(current_identity), Depends(unique_control_headers), Depends(private_response), Depends(query_fields()),
        Depends(no_body),
    ])

    @router.get('/capabilities', response_model=CodexCapabilities)
    def capabilities(request: Request) -> CodexCapabilities:
        return service.read(request.state.identity)

    return router
