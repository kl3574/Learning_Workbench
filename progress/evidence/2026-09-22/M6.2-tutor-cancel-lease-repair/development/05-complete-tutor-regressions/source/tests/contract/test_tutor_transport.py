"""Actual adapter/schema and emitted TypeScript execution; not Provider E2E."""
import json
from pathlib import Path
import subprocess

from fastapi import FastAPI
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator
import pytest

from packages.contracts.spec_catalog import route_catalog, spec_metadata
from scripts.api_contracts import api_artifacts, response_contract
from scripts.tutor_contracts import tutor_artifacts
from services.api.app.application.errors import ApiError
from services.api.app.interfaces.http import current_identity
from services.api.app.interfaces.tutor_http import create_tutor_router, encode_event, event_cursor
from services.api.app.tutor_dto import TutorAnswerDeltaEvent, TutorQueuedEvent
from starlette.requests import Request

ROOT = Path(__file__).resolve().parents[2]


class BoundariesOnly:
    """Not a business success stub: only fail-closed authorization is exercised."""
    def read(self, *_args):
        raise ApiError(403, 'POLICY_DENIED', 'synthetic restricted')

    def authorize(self, *_args, **_kwargs):
        raise ApiError(403, 'POLICY_DENIED', 'synthetic restricted')


def application():
    from packages.contracts.domain_models import ErrorEnvelope
    app = FastAPI(responses={status: {'model': ErrorEnvelope} for status in (400, 401, 403, 409, 422)})
    app.include_router(create_tutor_router(BoundariesOnly()))
    app.dependency_overrides[current_identity] = lambda: None
    from fastapi.responses import JSONResponse

    @app.exception_handler(ApiError)
    async def denied(_request, exc):
        return JSONResponse({'code': exc.code}, status_code=exc.status)

    @app.middleware('http')
    async def identity(request, call_next):
        request.state.identity = object()
        return await call_next(request)
    return app


def generated():
    api = application().openapi()
    provenance = spec_metadata(ROOT / 'PRODUCT_DESIGN.md')
    return {**api_artifacts(api, route_catalog(ROOT / 'PRODUCT_DESIGN.md'), provenance),
            **tutor_artifacts((ROOT / 'packages/contracts/module-ports.ts').read_text(), api, provenance)}


def test_actual_sse_schema_has_no_json_or_string_object_contradiction():
    api = application().openapi()
    operation = api['paths']['/api/v1/runs/{id}/events']['get']
    content = operation['responses']['200']['content']
    assert set(content) == {'text/event-stream'}
    assert content['text/event-stream']['schema']['type'] == 'object'
    assert len(content['text/event-stream']['schema']['oneOf']) == 10
    for code, response in operation['responses'].items():
        if int(code) >= 400:
            assert response['content'] == {'application/json': {
                'schema': {'$ref': '#/components/schemas/ErrorEnvelope'}}}
    response, kind, models = response_contract(operation)
    assert kind == 'sse' and response[0].startswith('AsyncIterable<') and len(models) == 10
    schemas = api['components']['schemas']
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)
    assert set(schemas['TutorRequestInput']['required']) == {
        'thread_id', 'workspace_id', 'message', 'intent', 'context', 'web_search', 'consent_id',
    }
    assert {'attached_refs', 'selection', 'attempt_id'} <= set(schemas['TutorViewContext']['required'])
    assert schemas['TutorRequestInput']['properties']['web_search']['const'] is False
    assert schemas['TutorRequestInput']['properties']['consent_id']['type'] == 'null'


def req(query='', headers=()):
    return Request({'type': 'http', 'method': 'GET', 'path': '/', 'query_string': query.encode(),
                    'headers': [(key.lower().encode(), value.encode()) for key, value in headers]})


@pytest.mark.parametrize('query,headers,status', [
    ('after_seq=2', (), 409), ('after_seq=-1', (), 400), ('after_seq=+1', (), 400),
    ('after_seq=1e0', (), 400), ('after_seq=1.0', (), 400),
    ('after_seq=1&after_seq=1', (), 400), ('other=1', (), 400),
    ('after_seq=1', (('Last-Event-ID', 'other:1'),), 400),
    ('after_seq=1', (('Last-Event-ID', 'run_one:0'),), 400),
    ('', (('Last-Event-ID', 'run_one:1'), ('Last-Event-ID', 'run_one:1')), 400),
])
def test_cursor_rejects_future_or_ambiguous_text(query, headers, status):
    with pytest.raises(ApiError) as caught:
        event_cursor(req(query, headers), 'run_one', 1)
    assert caught.value.status == status


def test_exact_equal_header_and_query_and_whitespace_delta():
    assert event_cursor(req('after_seq=1', (('Last-Event-ID', 'run_one:1'),)), 'run_one', 1) == 1
    value = TutorAnswerDeltaEvent(run_id='run_one', seq=2, occurred_at='2026-09-15T00:00:00Z',
                                 type='answer_delta', text=' \n')
    wire = encode_event(value)
    assert b'data: ' in wire and wire.endswith(b'\n\n')
    assert wire.count(b'\n') == 4
    assert json.loads(wire.decode().split('data: ', 1)[1])['text'] == ' \n'


@pytest.mark.parametrize('path', [
    '/api/v1/runs/run_one/events?after_seq=invalid',
    '/api/v1/threads?unknown=1',
    '/api/v1/threads/thread_one/messages?cursor=',
])
def test_current_policy_precedes_bad_cursor_or_unknown_query(path):
    with TestClient(application()) as client:
        response = client.get(path)
        assert response.status_code == 403
        assert response.json() == {'code': 'POLICY_DENIED'}


def run_node(*args, cwd):
    result = subprocess.run(['bash', str(ROOT / 'scripts/node.sh'), *map(str, args)],
                            cwd=cwd, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_emitted_sse_codec_real_typescript_and_stream_execution(tmp_path):
    values = generated()
    for name in ['api-types.ts', 'api-client.ts', 'tutor-sse.ts']:
        (tmp_path / name).write_text(values[name])
    (tmp_path / 'package.json').write_text('{"type":"module"}')
    run_node(ROOT / 'apps/web/node_modules/.bin/tsc', '--strict', '--skipLibCheck', '--target', 'ES2022',
             '--module', 'ESNext', '--moduleResolution', 'Bundler', '--lib', 'ES2022,DOM',
             '--outDir', 'out', 'api-types.ts', 'api-client.ts', 'tutor-sse.ts', cwd=tmp_path)
    # Node native ESM requires explicit extensions, unlike browser bundler.
    codec = tmp_path / 'out/tutor-sse.js'
    codec.write_text(codec.read_text().replace('"./api-client"', '"./api-client.js"'))
    queued = TutorQueuedEvent(run_id='run_one', seq=1, occurred_at='2026-09-15T00:00:00Z', type='queued')
    (tmp_path / 'queued.json').write_text(queued.model_dump_json())
    (tmp_path / 'runtime.mjs').write_text(r'''
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { decodeTutorEvents, createTutorEventsClient, TutorStreamHTTPError } from './out/tutor-sse.js';
const queued = JSON.parse(readFileSync('queued.json', 'utf8'));
const frame = e => 'id: ' + e.run_id + ':' + e.seq + '\nevent: ' + e.type + '\ndata: ' + JSON.stringify(e) + '\n\n';
function stream(text, split = 1) {
 const bytes = new TextEncoder().encode(text);
 return new ReadableStream({start(c) {for (let i=0;i<bytes.length;i+=split)c.enqueue(bytes.slice(i,i+split));c.close();}});
}
async function read(text, split = 1, after = 0) {
 const values = []; for await (const item of decodeTutorEvents(stream(text,split),'run_one',after)) values.push(item);
 return values;
}
const delta = {...queued,seq:2,type:'answer_delta',text:'中文 \n'};
const completed = {...queued,seq:3,type:'completed'};
const text = ': heartbeat\n\n' + frame(queued) + frame(delta) + frame(delta) + frame(completed);
assert.deepEqual(await read(text),[queued,delta,completed]);
assert.deepEqual(await read(text.replaceAll('\n','\r\n'),2),[queued,delta,completed]);
assert.deepEqual(await read(frame(delta)+frame(completed),1,1),[delta,completed]);
for (const bad of [
 frame({...queued,type:'completed',text:'unrelated'}),
 frame({...queued,type:'answer_delta',text:''}),
 frame({...queued,seq:true}), frame({...queued,occurred_at:'2026-02-31T00:00:00Z'}),
 frame({...queued,run_id:'other'}), frame({...queued,seq:2}),
 frame({...queued,type:'usage',input_tokens:null,output_tokens:null}),
 frame(queued).replace('event: queued','event: completed'),
 frame(queued).replace('"type":"queued"','"type":"failed","type":"queued"'),
 frame(queued).replace('data:','data: {}\ndata:'),
 frame(queued).replace('\n\n','\n'),
 frame(queued)+frame({...queued,type:'usage',seq:2,input_tokens:2,output_tokens:1})
 +frame({...queued,type:'usage',seq:3,input_tokens:null,output_tokens:1}),
 frame(queued)+frame({...queued,seq:2,type:'completed'})+frame({...delta,seq:3}),
]) await assert.rejects(read(bad));
let calls = 0;
const controller = new AbortController();
const client = createTutorEventsClient(async (path,init) => {
 calls++;assert.equal(path,'/api/v1/runs/run_one/events?after_seq=0');
 assert.equal(init.credentials,'same-origin');assert.equal(init.cache,'no-store');
 assert.equal(init.method,'GET');assert.equal(init.body,undefined);assert.equal(init.signal,controller.signal);
 assert.equal(init.headers.Accept,'text/event-stream');
 return new Response(stream(frame(queued)+frame({...completed,seq:2})),{headers:{'Content-Type':'text/event-stream; charset=utf-8'}});
});
const actual=[];for await(const e of client('run_one',0,controller.signal))actual.push(e);
assert.equal(calls,1);assert.equal(actual.length,2);
const failed=createTutorEventsClient(async()=>new Response('',{status:410}));
await assert.rejects(async()=>{for await(const e of failed('run_one'))void e;},
 error=>error instanceof TutorStreamHTTPError&&error.status===410);
''')
    run_node('node', 'runtime.mjs', cwd=tmp_path)


@pytest.mark.parametrize('damage', ['missing_route', 'json_stream', 'nullable_cursor', 'no_key', 'open_event'])
def test_generator_refuses_invented_or_weakened_runtime_binding(damage):
    api = application().openapi()
    if damage == 'missing_route':
        del api['paths']['/api/v1/threads']['post']
    elif damage == 'json_stream':
        value = api['paths']['/api/v1/runs/{id}/events']['get']['responses']['200']['content']
        value['application/json'] = value.pop('text/event-stream')
    elif damage == 'nullable_cursor':
        parameters = api['paths']['/api/v1/threads']['get']['parameters']
        cursor = next(item for item in parameters if item['name'] == 'cursor')
        cursor['schema'] = {'anyOf': [cursor['schema'], {'type': 'null'}]}
    elif damage == 'no_key':
        operation = api['paths']['/api/v1/tutor/runs']['post']
        operation['parameters'] = [item for item in operation['parameters'] if item['name'] != 'Idempotency-Key']
    else:
        api['components']['schemas']['TutorAnswerDeltaEvent']['additionalProperties'] = True
    with pytest.raises(ValueError):
        tutor_artifacts((ROOT / 'packages/contracts/module-ports.ts').read_text(), api,
                        spec_metadata(ROOT / 'PRODUCT_DESIGN.md'))
