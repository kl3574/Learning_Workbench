"""Exercise emitted TypeScript at its real compile and transport boundaries."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess

import pytest

from scripts.api_contracts import api_artifacts

ROOT = Path(__file__).resolve().parents[2]
PROVENANCE = {"source": "PRODUCT_DESIGN.md", "spec_version": "3.0.0", "spec_sha256": "a" * 64}


def parameter(name, location, *, required=False, schema=None):
    return {"name": name, "in": location, "required": required, "schema": schema or {"type": "string"}}


def transport_fixture():
    json_response = {"description": "OK", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ResponseDTO"}}}}
    paths = {
        "/session": {"get": {"responses": {"200": json_response}}},
        "/bootstrap": {"post": {
            "parameters": [parameter("Idempotency-Key", "header", required=True)],
            "requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/RequestDTO"}}}},
            "responses": {"201": json_response},
        }},
        "/courses": {"get": {
            "parameters": [parameter("q", "query", schema={"anyOf": [{"type": "string"}, {"type": "null"}]}),
                           parameter("cursor", "query"), parameter("limit", "query", schema={"type": "integer", "minimum": 1, "maximum": 100})],
            "responses": {"200": json_response},
        }},
        "/courses/{id}": {"get": {
            "parameters": [parameter("id", "path", required=True),
                           parameter("revision", "query", required=True, schema={"type": "integer", "minimum": 1})],
            "responses": {"200": json_response},
        }},
        "/blocks/{id}/body": {"get": {
            "parameters": [parameter("id", "path", required=True),
                           parameter("revision", "query", required=True, schema={"type": "integer", "minimum": 1})],
            "responses": {"200": {"description": "Markdown", "content": {"text/markdown": {"schema": {"type": "string"}}}}},
        }},
    }
    schemas = {
        "RequestDTO": {"type": "object", "additionalProperties": False, "required": ["code"], "properties": {"code": {"type": "string"}}},
        "ResponseDTO": {"type": "object", "additionalProperties": False, "required": ["value"], "properties": {"value": {"type": "string"}}},
    }
    return {"openapi": "3.1.0", "paths": paths, "components": {"schemas": schemas}}


def artifacts(api):
    catalog = {"routes": [{"method": method.upper(), "path": path} for path, item in api["paths"].items()
                          for method in item if method in {"get", "post"}]}
    return api_artifacts(api, catalog, PROVENANCE)


def run_node(*args, cwd):
    result = subprocess.run(["bash", str(ROOT / "scripts/node.sh"), *map(str, args)], cwd=cwd, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_generated_types_and_executed_transport_preserve_old_calls_and_bind_exact_parameters(tmp_path):
    generated = artifacts(transport_fixture())
    for name in ("api-types.ts", "api-client.ts"):
        (tmp_path / name).write_text(generated[name])
    (tmp_path / "package.json").write_text(json.dumps({"type": "module"}))
    (tmp_path / "compile.ts").write_text('''import { createApiClient, type ApiResponse, type JsonTransport } from './api-client';
const oldTransport: JsonTransport = async (_path, _init) => ({ value: 'old caller' });
const request = createApiClient(oldTransport);
const oldRead: Promise<{ value: string }> = request('GET /session', undefined);
request('POST /bootstrap', { code: 'value' }, { 'Idempotency-Key': 'create-1' });
request('GET /courses', undefined);
request('GET /courses', undefined, undefined, { query: { q: '中文', limit: 20 } });
request('GET /courses/{id}', undefined, undefined, { path: { id: 'course' }, query: { revision: 1 } });
const markdown: Promise<string> = request('GET /blocks/{id}/body', undefined, undefined, { path: { id: 'block' }, query: { revision: 1 } });
const response: ApiResponse<'GET /blocks/{id}/body'> = 'Markdown';
// @ts-expect-error required path/query parameters cannot be omitted
request('GET /courses/{id}', undefined);
// @ts-expect-error revision is required
request('GET /courses/{id}', undefined, undefined, { path: { id: 'course' }, query: {} });
// @ts-expect-error revision is numeric
request('GET /courses/{id}', undefined, undefined, { path: { id: 'course' }, query: { revision: '1' } });
// @ts-expect-error path id must be declared with its required type
request('GET /courses/{id}', undefined, undefined, { path: { id: 1 }, query: { revision: 1 } });
// @ts-expect-error body is a strict named DTO
request('POST /bootstrap', { wrong: 'value' }, { 'Idempotency-Key': 'create-1' });
// @ts-expect-error old required headers remain required
request('POST /bootstrap', { code: 'value' });
// @ts-expect-error undeclared query keys have no client binding
request('GET /courses', undefined, undefined, { query: { latest: true } });
// @ts-expect-error Markdown transport returns string, never a copied JSON DTO
const incorrect: Promise<{ value: string }> = request('GET /blocks/{id}/body', undefined, undefined, { path: { id: 'block' }, query: { revision: 1 } });
''')
    run_node(ROOT / "apps/web/node_modules/.bin/tsc", "--strict", "--skipLibCheck", "--target", "ES2022",
             "--module", "ESNext", "--moduleResolution", "Bundler", "--lib", "ES2022,DOM", "--outDir", "out",
             "api-types.ts", "api-client.ts", "compile.ts", cwd=tmp_path)
    (tmp_path / "runtime.mjs").write_text('''import assert from 'node:assert/strict';
import { createApiClient } from './out/api-client.js';
const calls = [];
const request = createApiClient(async (path, init, kind) => {
  calls.push({ path, init, kind });
  return kind === 'text' ? '# Original Markdown\\n$ x^2 $\\n' : { value: 'ok' };
});
await request('GET /session', undefined);
assert.deepEqual(calls.pop(), { path: '/session', init: { method: 'GET' }, kind: 'json' });
await request('POST /bootstrap', { code: 'value' }, { 'Idempotency-Key': 'create-1' });
assert.deepEqual(calls.pop(), { path: '/bootstrap', init: { method: 'POST', body: '{"code":"value"}', headers: { 'Idempotency-Key': 'create-1' } }, kind: 'json' });
await request('GET /courses', undefined, undefined, { query: { q: undefined, cursor: undefined, limit: undefined } });
assert.equal(calls.pop().path, '/courses');
await request('GET /courses', undefined, undefined, { query: { q: null } });
assert.equal(calls.pop().path, '/courses');
await request('GET /courses', undefined, undefined, { query: { q: '中文 & ?', cursor: 'a/b+=', limit: 10 } });
const list = new URL(calls.pop().path, 'http://localhost');
assert.equal(list.searchParams.get('q'), '中文 & ?');
assert.equal(list.searchParams.get('cursor'), 'a/b+=');
assert.equal(list.searchParams.get('limit'), '10');
assert.equal([...list.searchParams].length, 3);
const body = await request('GET /blocks/{id}/body', undefined, undefined, { path: { id: 'a/b ?#中文' }, query: { revision: 2 } });
assert.equal(body, '# Original Markdown\\n$ x^2 $\\n');
assert.deepEqual(calls.pop(), { path: '/blocks/a%2Fb%20%3F%23%E4%B8%AD%E6%96%87/body?revision=2', init: { method: 'GET' }, kind: 'text' });
for (const parameters of [undefined, {}, { path: {} }, { path: { id: 'x' } }, { path: { id: 'x' }, query: { revision: '1' } },
  { path: { id: 'x' }, query: { revision: 0 } }, { path: { id: 'x' }, query: { revision: 1.5 } },
  { path: { id: 'x' }, query: { revision: NaN } }, { path: { id: 'x' }, query: { revision: Infinity } },
  { path: { id: null }, query: { revision: 1 } }, { path: { id: 'x' }, query: { revision: 1, latest: true } }]) {
  assert.throws(() => request('GET /courses/{id}', undefined, undefined, parameters), TypeError);
}
assert.throws(() => request('GET /courses', undefined, undefined, { query: { limit: 101 } }), TypeError);
assert.equal(calls.length, 0, 'Rejected inputs must not invoke transport');
''')
    run_node("node", "runtime.mjs", cwd=tmp_path)


@pytest.mark.parametrize("media_type", ["text/plain", "application/octet-stream", "text/html", "application/xml"])
def test_unimplemented_response_media_fail_closed(media_type):
    api = transport_fixture()
    content = api["paths"]["/blocks/{id}/body"]["get"]["responses"]["200"]["content"]
    content[media_type] = content.pop("text/markdown")
    with pytest.raises(ValueError, match="explicit generated adapter"):
        artifacts(api)


def test_multipart_and_ambiguous_success_transports_remain_rejected():
    api = transport_fixture()
    content = api["paths"]["/bootstrap"]["post"]["requestBody"]["content"]
    content["multipart/form-data"] = content.pop("application/json")
    with pytest.raises(ValueError, match="explicit generated adapter"):
        artifacts(api)
    api = transport_fixture()
    api["paths"]["/blocks/{id}/body"]["get"]["responses"]["201"] = deepcopy(api["paths"]["/session"]["get"]["responses"]["200"])
    with pytest.raises(ValueError, match="Mixed successful response"):
        artifacts(api)


@pytest.mark.parametrize("change", ["array", "object", "cookie", "optional_path", "nullable_path", "missing_path", "style", "reserved"])
def test_unimplemented_or_inconsistent_parameter_bindings_fail_closed(change):
    api = transport_fixture()
    parameters = api["paths"]["/courses/{id}"]["get"]["parameters"]
    if change in {"array", "object"}:
        parameters[1]["schema"] = {"type": change, "items": {"type": "string"}, "additionalProperties": False}
    elif change == "cookie":
        parameters[1]["in"] = "cookie"
    elif change == "optional_path":
        parameters[0]["required"] = False
    elif change == "nullable_path":
        parameters[0]["schema"] = {"anyOf": [{"type": "string"}, {"type": "null"}]}
    elif change == "missing_path":
        parameters.pop(0)
    elif change == "style":
        parameters[1]["style"] = "deepObject"
    elif change == "reserved":
        parameters[1]["allowReserved"] = True
    with pytest.raises(ValueError):
        artifacts(api)


def test_path_level_parameters_are_inherited_and_operation_overrides_are_respected():
    api = transport_fixture()
    path_item = api["paths"]["/courses/{id}"]
    path_item["parameters"] = [path_item["get"]["parameters"].pop(0),
                               parameter("revision", "query", schema={"type": "integer"})]
    client = artifacts(api)["api-client.ts"]
    course_line = next(line for line in client.splitlines() if '"GET /courses/{id}": { request:' in line)
    assert 'path: { "id": string }' in course_line
    assert 'query: { "revision": number }' in course_line
    assert "parametersRequired: true" in course_line
