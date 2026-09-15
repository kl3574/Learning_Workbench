"""Actual retrieval router projection; mutated declarations must fail closed."""

from copy import deepcopy
from pathlib import Path
import json
import subprocess

import pytest

from packages.contracts import domain_models as dm
from packages.contracts.spec_catalog import spec_metadata
from scripts import generate_contracts as generator
from services.api.app.main import create_app

ROOT = Path(__file__).resolve().parents[2]
PORTS = (ROOT / 'packages/contracts/module-ports.ts').read_text()
PROVENANCE = spec_metadata(ROOT / 'PRODUCT_DESIGN.md')


def test_actual_three_operations_generate_an_exclusive_scalar_query_binding():
    output = generator.artifacts()
    binding = output[ROOT / 'packages/contracts/generated/retrieval-ports-binding.ts'].decode()
    client = output[ROOT / 'packages/contracts/generated/api-client.ts'].decode()
    assert 'RetrievalRuntimeDTOMap extends RetrievalApplicationDTOMap' in binding
    assert 'scope_refs: string; cursor?: never; limit?: never' in binding
    assert 'scope_refs?: never; cursor?: string; limit?: number' in binding
    assert 'query?: RetrievalIndexStatusQuery' in client
    api = create_app().openapi()
    status = api['paths']['/api/v1/index/status']['get']
    assert 'requestBody' not in status
    assert 'RetrievalIndexStatusQuery' not in api['components']['schemas']
    assert len(status['responses']['200']['content']['application/json']['schema']['oneOf']) == 2


def test_internal_content_binding_uses_real_models_and_bytes_outside_http():
    output = generator.artifacts()
    types = output[ROOT / 'packages/contracts/generated/retrieval-content-types.ts'].decode()
    binding = output[ROOT / 'packages/contracts/generated/retrieval-ports-binding.ts'].decode()
    assert 'RetrievalBodyBytes = Uint8Array' in types
    assert '"body": RetrievalBodyBytes' in types
    assert 'RetrievalScopeSnapshot: Content.RetrievalScopeSnapshot' in binding
    assert 'RetrievalBlockMaterial: Content.RetrievalBlockMaterial' in binding
    schemas = create_app().openapi()['components']['schemas']
    assert 'RetrievalScopeSnapshot' not in schemas and 'RetrievalBlockMaterial' not in schemas
    assert len(dm.CONTRACTS) == 54


@pytest.mark.parametrize('path,method', [('/api/v1/retrieval/query', 'post'),
    ('/api/v1/index/status', 'get'), ('/api/v1/index/rebuild', 'post')])
def test_missing_actual_operation_cannot_generate_application_binding(path, method):
    api = deepcopy(create_app().openapi())
    del api['paths'][path][method]
    with pytest.raises(ValueError, match='all three registered'):
        generator.retrieval_artifacts(PORTS, api, PROVENANCE)


@pytest.mark.parametrize('change', ['status', 'request', 'response', 'body', 'open', 'key',
    'query_key', 'missing_csrf', 'query_array', 'query_duplicate', 'limit', 'inline_union', 'fake_internal'])
def test_real_contract_mutations_cannot_invent_a_runtime_binding(change):
    api = deepcopy(create_app().openapi())
    query = api['paths']['/api/v1/retrieval/query']['post']
    rebuild = api['paths']['/api/v1/index/rebuild']['post']
    status = api['paths']['/api/v1/index/status']['get']
    if change == 'status':
        rebuild['responses']['200'] = rebuild['responses'].pop('202')
    elif change == 'request':
        query['requestBody']['required'] = False
    elif change == 'response':
        query['responses']['200']['content']['application/json']['schema'] = {'type': 'object'}
    elif change == 'body':
        status['requestBody'] = deepcopy(query['requestBody'])
    elif change == 'open':
        api['components']['schemas']['RetrievalQueryWrite']['additionalProperties'] = True
    elif change == 'key':
        rebuild['parameters'] = [p for p in rebuild['parameters'] if p['name'] != 'Idempotency-Key']
    elif change == 'query_key':
        query['parameters'].append(deepcopy(rebuild['parameters'][-1]))
    elif change == 'missing_csrf':
        query['parameters'] = [p for p in query['parameters'] if p['name'] != 'X-CSRF-Token']
    elif change == 'query_array':
        status['parameters'][0]['schema'] = {'type': 'array', 'items': {'type': 'string'}}
    elif change == 'query_duplicate':
        status['parameters'].append(deepcopy(status['parameters'][0]))
    elif change == 'limit':
        status['parameters'][-1]['schema']['maximum'] = 1000
    elif change == 'inline_union':
        status['responses']['200']['content']['application/json']['schema']['oneOf'][0] = {'type': 'object'}
    else:
        api['components']['schemas']['RetrievalBlockMaterial'] = {'type': 'object'}
    with pytest.raises(ValueError):
        generator.retrieval_artifacts(PORTS, api, PROVENANCE)


def test_generated_client_compiles_exact_query_union_and_executes_only_legal_scalar_modes(tmp_path):
    generated = tmp_path / 'generated'
    generated.mkdir()
    (tmp_path / 'module-ports.ts').write_text(PORTS)
    for path, value in generator.artifacts().items():
        if path.name in {'api-types.ts', 'api-client.ts', 'retrieval-ports-binding.ts', 'retrieval-content-types.ts'}:
            (generated / path.name).write_bytes(value)
    (tmp_path / 'package.json').write_text(json.dumps({'type': 'module'}))
    (tmp_path / 'compile.ts').write_text('''import { createApiClient } from './generated/api-client';
import type { ContentRetrievalRuntimeDTOMap } from './generated/retrieval-ports-binding';
const request = createApiClient(async () => ({}));
request('GET /api/v1/index/status', undefined);
request('GET /api/v1/index/status', undefined, undefined, { query: { scope_refs: '[]' } });
request('GET /api/v1/index/status', undefined, undefined, { query: { cursor: 'opaque', limit: 2 } });
request('POST /api/v1/retrieval/query', { query: '概率', scope_refs: [], limit: 10 });
// @ts-expect-error scope and overview pagination cannot mix
request('GET /api/v1/index/status', undefined, undefined, { query: { scope_refs: '[]', limit: 20 } });
// @ts-expect-error scope is a scalar JSON string, not an array transported as a body
request('GET /api/v1/index/status', undefined, undefined, { query: { scope_refs: [] } });
// @ts-expect-error omitted and explicit null are different
request('GET /api/v1/index/status', undefined, undefined, { query: { cursor: null } });
// @ts-expect-error rebuild requires the original command key
request('POST /api/v1/index/rebuild', { scope_refs: [], expected_corpus_sha256: 'a', provider_id: null, consent_id: null });
const bytes: ContentRetrievalRuntimeDTOMap['RetrievalBlockMaterial']['body'] = new Uint8Array([10]);
// @ts-expect-error internal Content bytes cannot be an HTTP blob or decoded string
const bad: typeof bytes = 'text';
''')
    command = ['bash', str(ROOT / 'scripts/node.sh'), str(ROOT / 'apps/web/node_modules/.bin/tsc'),
        '--strict', '--skipLibCheck', '--target', 'ES2022', '--module', 'ESNext',
        '--moduleResolution', 'Bundler', '--lib', 'ES2022,DOM', '--outDir', 'out', 'compile.ts']
    compiled = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True)
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    (tmp_path / 'runtime.mjs').write_text('''import assert from 'node:assert/strict';
import { createApiClient } from './out/generated/api-client.js';
const calls = [];
const request = createApiClient(async (path, init) => { calls.push({path, init}); return {}; });
const operation = 'GET /api/v1/index/status';
await request(operation, undefined);
assert.deepEqual(calls.pop(), {path: '/api/v1/index/status', init: {method: 'GET'}});
const scope = JSON.stringify([{entity:'block',id:'block_exact',revision:1,sha256:'a'.repeat(64)}]);
await request(operation, undefined, undefined, {query:{scope_refs:scope}});
const call = calls.pop();
assert.equal(new URL(call.path,'http://local').searchParams.get('scope_refs'), scope);
assert.equal(call.init.body, undefined);
await request(operation, undefined, undefined, {query:{cursor:'abc/?=', limit:2}});
assert.equal(new URL(calls.pop().path,'http://local').searchParams.get('limit'),'2');
for (const query of [{scope_refs:scope,limit:20}, {scope_refs:scope,cursor:undefined},
  {scope_refs:[]}, {scope_refs:undefined}, {cursor:null}, {limit:null}, {limit:0},
  {limit:101}, {limit:1.2}, {limit:true}, {limit:'1'}, {unknown:'x'}]) {
  assert.throws(() => request(operation,undefined,undefined,{query}),TypeError);
}
assert.equal(calls.length,0,'Rejected shapes must never invoke transport');
''')
    ran = subprocess.run(['bash', str(ROOT / 'scripts/node.sh'), 'node', 'runtime.mjs'],
                         cwd=tmp_path, capture_output=True, text=True)
    assert ran.returncode == 0, ran.stdout + ran.stderr
