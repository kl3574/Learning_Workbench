"""Actual Tutor HTTP/SSE adapters; composition supplies the real owner service.

The adapter never creates work on GET. An SSE connection observes checked
persisted events, and closing it only cancels the observation.
"""
import asyncio
from collections.abc import AsyncIterator
import re
from typing import Protocol

from fastapi import APIRouter, Depends, Request
from starlette.concurrency import run_in_threadpool
from starlette.responses import StreamingResponse

from packages.contracts.canonical import canonical_bytes

from ..application.errors import ApiError
from ..infrastructure.security import SessionIdentity, authenticate
from ..tutor_dto import (
    TUTOR_EVENT_ADAPTER, TutorMessagePage, TutorPageQuery, TutorRunCancel,
    TutorRunControlView, TutorRunCreate, TutorRunView, TutorSSEEvent,
    TutorThreadCreate, TutorThreadPage, TutorThreadView,
)
from .http import current_identity, verify_write
from .practice_http import private_response


class TutorHTTPService(Protocol):
    def authorize(self, identity: SessionIdentity, thread_id: str | None = None,
                  run_id: str | None = None) -> None: ...
    def create_thread(self, identity: SessionIdentity, body: TutorThreadCreate,
                      key: str) -> TutorThreadView: ...
    def threads(self, identity: SessionIdentity, *, cursor: str | None = None,
                limit: int = 20) -> TutorThreadPage: ...
    def messages(self, identity: SessionIdentity, thread_id: str, *, cursor: str | None = None,
                 limit: int = 20) -> TutorMessagePage: ...
    def start(self, identity: SessionIdentity, body: TutorRunCreate, key: str) -> TutorRunView: ...
    def read(self, identity: SessionIdentity, run_id: str) -> TutorRunView: ...
    def cancel(self, identity: SessionIdentity, run_id: str, body: TutorRunCancel,
               key: str) -> TutorRunControlView: ...
    def events(self, identity: SessionIdentity, run_id: str, after_seq: int) -> list[TutorSSEEvent]: ...


COMMAND_PARAMETER = {
    'name': 'Idempotency-Key', 'in': 'header', 'required': True,
    'schema': {'type': 'string', 'pattern': '^[A-Za-z0-9_-]{1,128}$'},
}
PAGE_PARAMETERS = [
    {'name': 'cursor', 'in': 'query', 'required': False,
     'schema': {'type': 'string', 'minLength': 1}},
    {'name': 'limit', 'in': 'query', 'required': False,
     'schema': {'type': 'integer', 'minimum': 1, 'maximum': 100, 'default': 20}},
]
EVENT_PARAMETERS = [
    {'name': 'after_seq', 'in': 'query', 'required': False,
     'schema': {'type': 'integer', 'minimum': 0, 'default': 0}},
    {'name': 'Last-Event-ID', 'in': 'header', 'required': False,
     'schema': {'type': 'string', 'pattern': '^[A-Za-z][A-Za-z0-9_-]{0,79}:[0-9]+$'}},
]


def unique_headers(request: Request) -> None:
    for name in ('cookie', 'origin', 'x-csrf-token', 'content-type', 'content-length',
                 'authorization', 'idempotency-key'):
        if len(request.headers.getlist(name)) > 1:
            raise ApiError(400, 'SCHEMA_INVALID', '请求控制头不得重复。')


def query_fields(request: Request, allowed: set[str]) -> None:
    names = list(request.query_params)
    if (set(names) - allowed
            or any(len(request.query_params.getlist(name)) != 1 for name in names)):
        raise ApiError(400, 'SCHEMA_INVALID', '查询字段未知或重复。')


def decimal(value: str) -> int:
    if re.fullmatch(r'[0-9]+', value) is None or len(value) > 16:
        raise ApiError(400, 'SCHEMA_INVALID', '游标或分页数量必须是有界十进制非负整数。')
    number = int(value)
    if number > 9007199254740991:
        raise ApiError(400, 'SCHEMA_INVALID', '游标数值超过精确传输范围。')
    return number


def page_query(request: Request) -> TutorPageQuery:
    query_fields(request, {'cursor', 'limit'})
    cursor = request.query_params.get('cursor')
    if cursor is not None and not cursor.strip():
        raise ApiError(400, 'SCHEMA_INVALID', '分页游标不能为空白。')
    limit = decimal(request.query_params.get('limit', '20'))
    if not 1 <= limit <= 100:
        raise ApiError(400, 'SCHEMA_INVALID', '分页数量须在1到100之间。')
    return TutorPageQuery(**({'cursor': cursor} if cursor is not None else {}), limit=limit)


def event_cursor(request: Request, run_id: str, last_seq: int) -> int:
    if len(request.headers.getlist('last-event-id')) > 1:
        raise ApiError(400, 'SCHEMA_INVALID', '事件游标头不得重复。')
    query_fields(request, {'after_seq'})
    query = request.query_params.get('after_seq')
    header = request.headers.get('last-event-id')
    query_seq = decimal(query) if query is not None else None
    header_seq = None
    if header is not None:
        prefix, separator, number = header.rpartition(':')
        if not separator or prefix != run_id:
            raise ApiError(400, 'SCHEMA_INVALID', '事件游标必须属于当前任务。')
        header_seq = decimal(number)
    if query_seq is not None and header_seq is not None and query_seq != header_seq:
        raise ApiError(400, 'SCHEMA_INVALID', '两种事件游标不一致。')
    cursor = query_seq if query_seq is not None else (header_seq if header_seq is not None else 0)
    if cursor > last_seq:
        raise ApiError(409, 'CURSOR_AHEAD', '事件游标超出已持久化进度。')
    return cursor


def command_key(request: Request) -> str:
    values = request.headers.getlist('idempotency-key')
    if len(values) != 1 or re.fullmatch(r'[A-Za-z0-9_-]{1,128}', values[0]) is None:
        raise ApiError(400, 'IDEMPOTENCY_KEY_INVALID', '需要单个有效的原命令幂等键。')
    return values[0]


def encode_event(value: TutorSSEEvent) -> bytes:
    checked = TUTOR_EVENT_ADAPTER.validate_python(value.model_dump(mode='json'))
    payload = canonical_bytes(checked.model_dump(mode='json'))
    return (f'id: {checked.run_id}:{checked.seq}\nevent: {checked.type}\ndata: '.encode()
            + payload + b'\n\n')


class TutorStreamResponse(StreamingResponse):
    media_type = 'text/event-stream'


def create_tutor_router(service: TutorHTTPService) -> APIRouter:
    router = APIRouter(prefix='/api/v1', tags=['tutor'], dependencies=[
        Depends(current_identity), Depends(unique_headers), Depends(private_response),
    ])

    @router.post('/threads', response_model=TutorThreadView, status_code=201,
                 dependencies=[Depends(verify_write)],
                 openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def create(body: TutorThreadCreate, request: Request) -> TutorThreadView:
        query_fields(request, set())
        return service.create_thread(request.state.identity, body, command_key(request))

    @router.get('/threads', response_model=TutorThreadPage,
                openapi_extra={'parameters': PAGE_PARAMETERS})
    def threads(request: Request) -> TutorThreadPage:
        service.authorize(request.state.identity)
        query = page_query(request)
        return service.threads(request.state.identity, cursor=query.cursor, limit=query.limit)

    @router.get('/threads/{id}/messages', response_model=TutorMessagePage,
                openapi_extra={'parameters': PAGE_PARAMETERS})
    def messages(id: str, request: Request) -> TutorMessagePage:
        service.authorize(request.state.identity, thread_id=id)
        query = page_query(request)
        return service.messages(request.state.identity, id, cursor=query.cursor, limit=query.limit)

    @router.post('/tutor/runs', response_model=TutorRunView, status_code=202,
                 dependencies=[Depends(verify_write)],
                 openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def start(body: TutorRunCreate, request: Request) -> TutorRunView:
        query_fields(request, set())
        return service.start(request.state.identity, body, command_key(request))

    @router.get('/runs/{id}', response_model=TutorRunView)
    def read(id: str, request: Request) -> TutorRunView:
        service.authorize(request.state.identity, run_id=id)
        query_fields(request, set())
        return service.read(request.state.identity, id)

    @router.post('/runs/{id}/cancel', response_model=TutorRunControlView,
                 dependencies=[Depends(verify_write)],
                 openapi_extra={'parameters': [COMMAND_PARAMETER]})
    def cancel(id: str, body: TutorRunCancel, request: Request) -> TutorRunControlView:
        query_fields(request, set())
        return service.cancel(request.state.identity, id, body, command_key(request))

    schema = TUTOR_EVENT_ADAPTER.json_schema(ref_template='#/components/schemas/{model}')
    schema.pop('$defs', None)
    schema['type'] = 'object'

    @router.get('/runs/{id}/events', response_model=TutorSSEEvent,
                response_class=TutorStreamResponse,
                responses={200: {'content': {'text/event-stream': {'schema': schema}}},
                           **{status: {'model': None, 'content': {'application/json': {
                               'schema': {'$ref': '#/components/schemas/ErrorEnvelope'}}}}
                              for status in (400, 401, 403, 404, 405, 409, 412, 413, 422, 500, 503)}},
                openapi_extra={'parameters': EVENT_PARAMETERS})
    async def events(id: str, request: Request) -> TutorStreamResponse:
        # Own/Policy/history validation precedes even a malformed cursor.
        view = await run_in_threadpool(service.read, request.state.identity, id)
        cursor = event_cursor(request, id, view.run.last_seq)

        async def observe() -> AsyncIterator[bytes]:
            nonlocal cursor
            while not await request.is_disconnected():
                try:
                    fresh = await run_in_threadpool(authenticate, request.app.state.database, request)
                    initial = request.state.identity
                    if (fresh.id, fresh.workspace_id, fresh.role) != (initial.id, initial.workspace_id, initial.role):
                        return
                    batch = await run_in_threadpool(service.events, fresh, id, cursor)
                    for item in batch:
                        # A batch can pause under backpressure. Revalidate the
                        # actual cookie and subject scope before each delivery,
                        # not just before the earlier database read.
                        delivery = await run_in_threadpool(authenticate, request.app.state.database, request)
                        if (delivery.id, delivery.workspace_id, delivery.role) != (
                                initial.id, initial.workspace_id, initial.role):
                            return
                        await run_in_threadpool(service.authorize, delivery, run_id=id)
                        if item.run_id != id or item.seq != cursor + 1:
                            raise ApiError(409, 'TUTOR_INTEGRITY_ERROR', '任务事件顺序未通过校验。')
                        cursor = item.seq
                        yield encode_event(item)
                        if item.type in {'completed', 'failed', 'cancelled'}:
                            return
                    current = await run_in_threadpool(service.read, request.state.identity, id)
                    if current.run.status in {'completed', 'failed', 'cancelled'} and cursor == current.run.last_seq:
                        return
                except ApiError:
                    # Headers have already been sent. End this observer without
                    # fabricating a persisted failed event or leaking error data.
                    return
                await asyncio.sleep(0.25)

        return TutorStreamResponse(observe(), headers={
            'Cache-Control': 'no-store', 'Vary': 'Cookie', 'X-Accel-Buffering': 'no',
        })

    return router
