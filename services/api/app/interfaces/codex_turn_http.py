"""Real local preparation, consent consumption and checked control reads."""
import asyncio
from collections.abc import AsyncIterator
from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse
from packages.contracts import domain_models as dm
from packages.contracts.canonical import canonical_bytes
from ..application.codex_turn import CodexTurnService
from ..application.errors import ApiError
from ..codex_turn_dto import CodexTurnPrepareWrite, CodexTurnPreparationView, CodexTurnPage, CodexTurnControlView, CodexTurnStartWrite, CodexTurnStartAck, CodexTurnResultView, CodexInterruptWrite, CodexInterruptAck
from ..codex_turn_dto import CodexArtifactManifestView, CodexTurnEvent
from ..infrastructure.security import authenticate
from .codex_bootstrap_http import no_control_body
from .content_http import query_fields
from .http import current_identity, verify_write
from .practice_http import private_response
from .provider_http import unique_control_headers, command_key, COMMAND_PARAMETER
from .tutor_http import PAGE_PARAMETERS, EVENT_PARAMETERS, event_cursor


class CodexStreamResponse(StreamingResponse):
    media_type = 'text/event-stream'


def encode_event(value: CodexTurnEvent) -> bytes:
    checked = CodexTurnEvent.model_validate(value.model_dump(mode='json'))
    return (f'id: {checked.run_id}:{checked.seq}\nevent: {checked.payload.type}\ndata: '.encode()
        + canonical_bytes(checked.model_dump(mode='json')) + b'\n\n')


def create_codex_turn_router(service: CodexTurnService) -> APIRouter:
    router = APIRouter(prefix='/api/v1/codex', tags=['codex'], dependencies=[Depends(current_identity),
        Depends(unique_control_headers), Depends(private_response)])

    @router.post('/sessions/{id}/turn-preparations', response_model=CodexTurnPreparationView, status_code=202,
        dependencies=[Depends(verify_write), Depends(query_fields())], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def prepare(id: dm.Id, body: CodexTurnPrepareWrite, request: Request) -> CodexTurnPreparationView:
        return service.prepare_turn(request.state.identity, id, body, command_key(request))

    @router.post('/sessions/{id}/turns', response_model=CodexTurnStartAck, status_code=202,
        dependencies=[Depends(verify_write),Depends(query_fields())],openapi_extra={'parameters':[COMMAND_PARAMETER]})
    def start(id: dm.Id, body: CodexTurnStartWrite, request: Request) -> CodexTurnStartAck:
        return service.start_turn(request.state.identity,id,body,command_key(request))

    @router.post('/sessions/{id}/interrupt', response_model=CodexInterruptAck,
        dependencies=[Depends(verify_write), Depends(query_fields())], openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def interrupt(id: dm.Id, body: CodexInterruptWrite, request: Request) -> CodexInterruptAck:
        return service.interrupt(request.state.identity, id, body, command_key(request))

    @router.get('/turn-preparations/{id}', response_model=CodexTurnPreparationView,
        dependencies=[Depends(no_control_body), Depends(query_fields())])
    def preparation(id: dm.Id, request: Request) -> CodexTurnPreparationView:
        return service.read_preparation(request.state.identity, id)

    @router.get('/turns/{id}', response_model=CodexTurnControlView,
        dependencies=[Depends(no_control_body), Depends(query_fields())])
    def turn(id: dm.Id, request: Request) -> CodexTurnControlView:
        return service.read_control(request.state.identity, id)

    @router.get('/turns/{id}/result', response_model=CodexTurnResultView,
        dependencies=[Depends(no_control_body), Depends(query_fields())])
    def result(id: dm.Id, request: Request) -> CodexTurnResultView:
        return service.read_result(request.state.identity,id)

    @router.get('/turns/{id}/events', response_model=CodexTurnEvent,
        response_class=CodexStreamResponse, dependencies=[Depends(no_control_body)],
        responses={200: {'content': {'text/event-stream': {'schema': {
            'type':'object', '$ref':'#/components/schemas/CodexTurnEvent'}}}},
            **{code: {'model': None, 'content': {'application/json': {
                'schema': {'$ref': '#/components/schemas/ErrorEnvelope'}}}}
                for code in (400, 401, 403, 404, 405, 409, 412, 413, 422, 500, 503)}},
        openapi_extra={'parameters': EVENT_PARAMETERS})
    async def events(id: dm.Id, request: Request) -> CodexStreamResponse:
        # Original ownership/Policy/history admission precedes cursor parsing.
        current, _ = await run_in_threadpool(service.event_snapshot, request.state.identity, id)
        cursor = event_cursor(request, current.job.id, current.last_seq)
        initial = request.state.identity

        async def observe() -> AsyncIterator[bytes]:
            nonlocal cursor
            while not await request.is_disconnected():
                try:
                    fresh = await run_in_threadpool(authenticate, request.app.state.database, request)
                    if (fresh.id, fresh.workspace_id, fresh.role) != (initial.id, initial.workspace_id, initial.role):
                        return
                    view, stored = await run_in_threadpool(service.event_snapshot, fresh, id)
                    for item in stored:
                        if item.seq <= cursor:
                            continue
                        delivery = await run_in_threadpool(authenticate, request.app.state.database, request)
                        if (delivery.id, delivery.workspace_id, delivery.role) != (initial.id, initial.workspace_id, initial.role):
                            return
                        await run_in_threadpool(service.authorize_events, delivery, id)
                        if (item.turn_id != id or item.run_id != view.job.id or item.seq != cursor + 1):
                            raise ApiError(409, 'CODEX_HISTORY_DAMAGED', '任务事件顺序未通过核验。')
                        cursor = item.seq
                        yield encode_event(item)
                        if item.payload.type == 'terminal':
                            return
                    if view.execution == 'terminal' and cursor == view.last_seq:
                        return
                except ApiError:
                    # No synthetic failure event/body after headers. Closing
                    # this observer never cancels or starts the actual Job.
                    return
                await asyncio.sleep(0.25)

        return CodexStreamResponse(observe(), headers={
            'Cache-Control':'no-store', 'Vary':'Cookie', 'X-Accel-Buffering':'no',
        })

    @router.get('/sessions/{id}/turns/{turn_id}/artifacts', response_model=CodexArtifactManifestView,
        dependencies=[Depends(no_control_body), Depends(query_fields())])
    def manifest(id: dm.Id, turn_id: dm.Id, request: Request) -> CodexArtifactManifestView:
        if service.artifacts is None:
            raise ApiError(503, 'CODEX_RUNTIME_UNAVAILABLE', '产物所有者暂不可用。')
        return service.artifacts.read_manifest(request.state.identity, id, turn_id)

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
