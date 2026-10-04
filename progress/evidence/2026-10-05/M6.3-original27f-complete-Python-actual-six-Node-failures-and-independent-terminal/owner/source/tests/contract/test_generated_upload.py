"""Compile and execute the generated binary boundaries using native Web APIs."""

import json

import pytest

from test_generated_transport import ROOT, artifacts, parameter, run_node, transport_fixture


def upload_api():
    api = transport_fixture()
    api["components"]["schemas"]["Upload"] = {
        "type": "object", "additionalProperties": False, "required": ["file", "kind"],
        "properties": {"file": {"type": "string", "format": "binary"},
                       "kind": {"type": "string", "enum": ["auto", "markdown"]},
                       "target_course_id": {"anyOf": [{"type": "string"}, {"type": "null"}]}},
    }
    api["paths"]["/imports"] = {"post": {
        "parameters": [parameter("Idempotency-Key", "header", required=True)],
        "requestBody": {"content": {"multipart/form-data": {"schema": {"$ref": "#/components/schemas/Upload"}}}},
        "responses": api["paths"]["/bootstrap"]["post"]["responses"],
    }}
    api["paths"]["/artifacts/{id}/download"] = {"get": {
        "parameters": [parameter("id", "path", required=True)],
        "responses": {"200": {"description": "Download", "content": {
            "application/octet-stream": {"schema": {"type": "string", "format": "binary"}},
        }}},
    }}
    return api


@pytest.mark.parametrize("binary_schema", [{"format": "binary"}, {"contentMediaType": "application/octet-stream"}])
def test_multipart_roundtrip_keeps_original_bytes_filename_and_binary_response(tmp_path, binary_schema):
    api = upload_api()
    api["components"]["schemas"]["Upload"]["properties"]["file"] = {"type": "string", **binary_schema}
    generated = artifacts(api)
    for name in ("api-types.ts", "api-client.ts"):
        (tmp_path / name).write_text(generated[name])
    (tmp_path / "package.json").write_text(json.dumps({"type": "module"}))
    (tmp_path / "compile.ts").write_text('''import { createApiClient } from './api-client';
const request = createApiClient(async () => new Blob());
request('POST /imports', {file: new File(['x'], '合成.md'), kind: 'markdown'}, {'Idempotency-Key': 'upload'});
const file: Promise<Blob> = request('GET /artifacts/{id}/download', undefined, undefined, {path: {id: 'artifact_a'}});
// @ts-expect-error file bytes are not a JSON string
request('POST /imports', {file: 'text', kind: 'auto'}, {'Idempotency-Key': 'upload'});
// @ts-expect-error file upload requires an explicit kind
request('POST /imports', {file: new Blob()}, {'Idempotency-Key': 'upload'});
// @ts-expect-error unknown form fields cannot be sent
request('POST /imports', {file: new Blob(), kind: 'auto', execute: true}, {'Idempotency-Key': 'upload'});
// @ts-expect-error binary result is not JSON or Markdown
const wrong: Promise<string> = request('GET /artifacts/{id}/download', undefined, undefined, {path: {id: 'artifact_a'}});
''')
    run_node(ROOT / "apps/web/node_modules/.bin/tsc", "--strict", "--skipLibCheck", "--target", "ES2022",
             "--module", "ESNext", "--moduleResolution", "Bundler", "--lib", "ES2022,DOM", "--outDir", "out",
             "api-types.ts", "api-client.ts", "compile.ts", cwd=tmp_path)
    (tmp_path / "runtime.mjs").write_text('''import assert from 'node:assert/strict';
import { createApiClient } from './out/api-client.js';
const bytes = new Uint8Array([0, 255, 13, 10, 65]);
const calls = [];
const request = createApiClient(async (path, init, kind) => {
  calls.push({path, init, kind});
  return kind === 'blob' ? new Blob([bytes]) : {value: 'staged'};
});
await request('POST /imports', {file: new File([bytes], '合成.md'), kind: 'markdown', target_course_id: null}, {'Idempotency-Key': 'upload'});
const upload = calls.pop();
assert.equal(upload.path, '/imports'); assert.equal(upload.kind, 'json');
assert.ok(upload.init.body instanceof FormData);
const encoded = new Request('http://127.0.0.1/imports', upload.init);
assert.match(encoded.headers.get('content-type'), /^multipart\\/form-data; boundary=/);
assert.equal(encoded.headers.get('Idempotency-Key'), 'upload');
const decoded = await encoded.formData();
assert.deepEqual([...decoded.keys()], ['file', 'kind']);
assert.equal(decoded.get('file').name, '合成.md');
assert.deepEqual(new Uint8Array(await decoded.get('file').arrayBuffer()), bytes);
assert.equal(decoded.get('kind'), 'markdown');
const received = await request('GET /artifacts/{id}/download', undefined, undefined, {path: {id: 'artifact_a'}});
assert.ok(received instanceof Blob); assert.deepEqual(new Uint8Array(await received.arrayBuffer()), bytes);
assert.equal(calls.pop().kind, 'blob');
for (const body of [undefined, null, [], {file: 'data', kind: 'auto'}, {file: null, kind: 'auto'}, {file: new Blob(), kind: 'auto', extra: 'bad'}]) {
  assert.throws(() => request('POST /imports', body, {'Idempotency-Key': 'invalid'}), TypeError);
}
assert.equal(calls.length, 0, 'Invalid upload values must not reach transport');
''')
    run_node("node", "runtime.mjs", cwd=tmp_path)
