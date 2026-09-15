"""Generate deterministic schemas, TS types and source-linked tracking from the spec."""
# Imports below follow repo-root bootstrapping for standalone CLI execution.
# ruff: noqa: E402
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from packages.contracts import domain_models as dm
from packages.contracts.canonical import sha256_bytes
from packages.contracts.spec_catalog import route_catalog, spec_metadata, traceability
from scripts.extract_spec import PATTERN
from scripts.schema_types import generate_types
from scripts.api_contracts import api_artifacts, runtime_openapi
from scripts.tutor_contracts import tutor_artifacts
from scripts.authoring_contracts import authoring_artifacts


PROVIDER_OPERATIONS = {
    ('/api/v1/providers/capabilities', 'get'): (None, 'ProviderCapabilitiesResponse', '200'),
    ('/api/v1/providers/{id}/config', 'get'): (None, 'ProviderConfigView', '200'),
    ('/api/v1/providers/{id}/config', 'put'): ('ProviderConfigWrite', 'ProviderConfigAck', '200'),
    ('/api/v1/providers/{id}/secret', 'post'): ('ProviderSecretWrite', 'ProviderSecretAck', '200'),
    ('/api/v1/providers/{id}/secret', 'delete'): (None, 'ProviderSecretAck', '200'),
    ('/api/v1/consents/preview', 'post'): ('ConsentPreviewWrite', 'ConsentProposalView', '201'),
    ('/api/v1/consents/preview/{id}', 'get'): (None, 'ConsentProposalView', '200'),
    ('/api/v1/consents', 'post'): ('ConsentCreate', 'ConsentCreateAck', '201'),
    ('/api/v1/consents', 'get'): (None, 'ConsentPage', '200'),
    ('/api/v1/consents/{id}/revoke', 'post'): ('ConsentRevoke', 'MutationAck', '200'),
}


def provider_ports_binding(ports: str, openapi: dict, provenance: dict[str, str]) -> str:
    """Bind the separate map only to all ten implemented, closed operations.

    The URL query union is the scalar transport contract, not an invented body
    component. A declaration alone cannot supply a runtime application binding.
    """
    marker = 'export interface ProviderApplicationDTOMap {'
    if ports.count(marker) != 1:
        raise ValueError('provider application map must be explicitly declared once')
    block = ports.split(marker, 1)[1].split('}', 1)[0]
    names = re.findall(r'\b(\w+): unknown;', block)
    expected_names = {name for request, response, _ in PROVIDER_OPERATIONS.values()
                      for name in (request, response) if name is not None}
    if (len(names) != len(set(names)) or set(names) != expected_names
            or re.sub(r'\b\w+: unknown;', '', block).strip()):
        raise ValueError('provider application map has unmapped or duplicate DTOs')
    schemas = openapi.get('components', {}).get('schemas', {})
    for (path, method), (request_name, response_name, status) in PROVIDER_OPERATIONS.items():
        operation = openapi.get('paths', {}).get(path, {}).get(method)
        if operation is None:
            raise ValueError('provider application binding requires all ten registered runtime operations')
        response = operation.get('responses', {}).get(status, {}).get('content', {})
        if response != {'application/json': {'schema': {'$ref': f'#/components/schemas/{response_name}'}}}:
            raise ValueError('provider runtime response must bind its declared DTO, media type and status')
        if request_name is None:
            if 'requestBody' in operation:
                raise ValueError('provider bodyless operation cannot accept an undocumented body')
        else:
            request = operation.get('requestBody', {})
            if (request.get('required') is not True or request.get('content') != {
                    'application/json': {'schema': {'$ref': f'#/components/schemas/{request_name}'}}}):
                raise ValueError('provider runtime request must bind its declared required DTO')
        parameters = operation.get('parameters', [])
        identities = [(value.get('in'), value.get('name', '').lower()) for value in parameters]
        if len(identities) != len(set(identities)):
            raise ValueError('provider operation declares duplicate transport parameters')
        headers = {value.get('name', '').lower(): value for value in parameters if value.get('in') == 'header'}
        if method != 'get':
            key = headers.get('idempotency-key', {})
            if (key.get('required') is not True or key.get('schema', {}).get('type') != 'string'
                    or key.get('schema', {}).get('pattern') != '^[A-Za-z0-9_-]{1,128}$'):
                raise ValueError('provider mutation requires its declared original command key')
        if method == 'delete':
            match = headers.get('if-match', {})
            if (match.get('required') is not True or match.get('schema', {}).get('type') != 'string'
                    or match.get('schema', {}).get('pattern') != '^"[0-9a-f]{64}"$'):
                raise ValueError('provider secret deletion requires its strong configuration version')
        queries = {value['name']: value for value in parameters if value.get('in') == 'query'}
        if (path, method) == ('/api/v1/consents', 'get'):
            if set(queries) != {'consent_id', 'cursor', 'limit'} or any(value.get('required') for value in queries.values()):
                raise ValueError('provider consent query must bind the three actual optional scalar parameters')
            limit = queries['limit'].get('schema', {})
            if limit.get('type') != 'integer' or limit.get('minimum') != 1 or limit.get('maximum') != 100 or limit.get('default') != 20:
                raise ValueError('provider consent query has an incorrect pagination bound')
        elif queries:
            raise ValueError('provider operation declares undocumented query fields')
    for name in names:
        schema = schemas.get(name, {})
        if schema.get('type') != 'object' or schema.get('additionalProperties') is not False:
            raise ValueError('provider application DTO must be a registered closed object')
    lines = [f"// Generated from PRODUCT_DESIGN.md v{provenance['spec_version']} and runtime OpenAPI; do not edit.",
             f"// spec_sha256: {provenance['spec_sha256']}",
             'import type { ProviderApplicationDTOMap } from "../module-ports";',
             'import type * as Api from "./api-types";', '',
             'export type { ProviderConsentQuery } from "../module-ports";', '',
             'export interface ProviderRuntimeDTOMap extends ProviderApplicationDTOMap {']
    lines.extend(f'  {name}: Api.{name};' for name in names)
    lines.append('}')
    return '\n'.join(lines) + '\n'


def recommendation_ports_binding(ports: str, openapi: dict, provenance: dict[str, str]) -> str:
    """Bind the application map only after both real recommendation routes exist."""
    marker = 'export interface RecommendationDTOMap {'
    if ports.count(marker) != 1:
        raise ValueError('recommendation application map must be explicitly declared once')
    block = ports.split(marker, 1)[1].split('}', 1)[0]
    names = re.findall(r'\b(\w+): unknown;', block)
    if (len(names) != len(set(names))
            or set(names) != {'RecommendationPage', 'RecommendationDecisionWrite', 'MutationAck'}
            or re.sub(r'\b\w+: unknown;', '', block).strip()):
        raise ValueError('recommendation application map has unmapped or duplicate DTOs')
    expected = {
        ('/api/v1/recommendations', 'get'): (None, 'RecommendationPage'),
        ('/api/v1/recommendations/{id}/decision', 'post'): ('RecommendationDecisionWrite', 'MutationAck'),
    }
    schemas = openapi.get('components', {}).get('schemas', {})
    for (path, method), (request_name, response_name) in expected.items():
        operation = openapi.get('paths', {}).get(path, {}).get(method)
        if operation is None:
            raise ValueError('recommendation application binding requires both registered runtime operations')
        response = operation.get('responses', {}).get('200', {}).get('content', {}).get('application/json', {}).get('schema', {})
        if response != {'$ref': f'#/components/schemas/{response_name}'}:
            raise ValueError('recommendation runtime response does not bind its declared strict DTO')
        if request_name is not None:
            request = operation.get('requestBody', {}).get('content', {}).get('application/json', {}).get('schema', {})
            if request != {'$ref': f'#/components/schemas/{request_name}'}:
                raise ValueError('recommendation runtime request does not bind its declared strict DTO')
    for name in names:
        schema = schemas.get(name, {})
        if schema.get('type') != 'object' or schema.get('additionalProperties') is not False:
            raise ValueError('recommendation application DTO must be a registered closed object')
    lines = [f"// Generated from PRODUCT_DESIGN.md v{provenance['spec_version']} and runtime OpenAPI; do not edit.",
             f"// spec_sha256: {provenance['spec_sha256']}",
             'import type { RecommendationDTOMap } from "../module-ports";',
             'import type * as Api from "./api-types";', '',
             'export interface RecommendationApplicationDTOMap extends RecommendationDTOMap {']
    lines.extend(f'  {name}: Api.{name};' for name in names)
    lines.append('}')
    return '\n'.join(lines) + '\n'



def retrieval_artifacts(ports: str, openapi: dict, provenance: dict[str, str]) -> dict[str, str | dict]:
    """Bind three real operations and a separate non-HTTP Content byte port."""
    from copy import deepcopy
    from services.api.app.application.retrieval_models import RetrievalBlockMaterial, RetrievalScopeSnapshot

    expected = {
        ('/api/v1/retrieval/query', 'post'): ('RetrievalQueryWrite', 'RetrievalQueryView', '200'),
        ('/api/v1/index/rebuild', 'post'): ('RetrievalIndexRebuildWrite', 'JobRef', '202'),
        ('/api/v1/index/status', 'get'): (None, None, '200'),
    }
    application = {'RetrievalQueryWrite', 'RetrievalQueryView', 'RetrievalIndexRebuildWrite',
                   'RetrievalIndexStatusQuery', 'RetrievalIndexStatusView'}
    internal = {'RetrievalScopeSnapshot', 'RetrievalBlockMaterial'}
    for interface, wanted in [('RetrievalApplicationDTOMap', application), ('ContentRetrievalDTOMap', internal)]:
        marker = f'export interface {interface} {{'
        if ports.count(marker) != 1:
            raise ValueError('retrieval DTO maps must be declared once')
        block = ports.split(marker, 1)[1].split('}', 1)[0]
        names = re.findall(r'\b(\w+): unknown;', block)
        if (len(names) != len(set(names)) or set(names) != wanted
                or re.sub(r'\b\w+: unknown;', '', block).strip()):
            raise ValueError('retrieval map has unmapped or duplicate DTOs')
    schemas = openapi.get('components', {}).get('schemas', {})
    for (path, method), (request_name, response_name, code) in expected.items():
        operation = openapi.get('paths', {}).get(path, {}).get(method)
        if operation is None:
            raise ValueError('retrieval binding requires all three registered runtime operations')
        if {status for status in operation.get('responses', {}) if status.startswith('2')} != {code}:
            raise ValueError('retrieval operation has an incorrect successful status')
        response = operation['responses'][code].get('content', {})
        if set(response) != {'application/json'}:
            raise ValueError('retrieval responses require the actual JSON transport')
        response_schema = response['application/json'].get('schema', {})
        if response_name is not None:
            if response_schema != {'$ref': f'#/components/schemas/{response_name}'}:
                raise ValueError('retrieval response must bind its actual named DTO')
        else:
            members = ['RetrievalIndexScopeStatus', 'RetrievalIndexOverview']
            if (response_schema.get('oneOf') != [{'$ref': f'#/components/schemas/{name}'} for name in members]
                    or response_schema.get('discriminator') != {'propertyName': 'kind', 'mapping': {
                        'scope': '#/components/schemas/RetrievalIndexScopeStatus',
                        'overview': '#/components/schemas/RetrievalIndexOverview'}}):
                raise ValueError('retrieval status must preserve its discriminated response union')
        if request_name is None:
            if 'requestBody' in operation:
                raise ValueError('retrieval status is a scalar URL query, not a JSON body')
        elif operation.get('requestBody') != {'required': True, 'content': {
                'application/json': {'schema': {'$ref': f'#/components/schemas/{request_name}'}}}}:
            raise ValueError('retrieval request must bind its required closed DTO')
        parameters = operation.get('parameters', [])
        identifiers = [(p.get('in'), p.get('name', '').lower()) for p in parameters]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError('retrieval parameters must not repeat')
        headers = {p['name'].lower(): p for p in parameters if p.get('in') == 'header'}
        if method == 'post':
            if any(headers.get(name, {}).get('required') is not True for name in ('origin', 'x-csrf-token')):
                raise ValueError('retrieval POST requires the actual session/CSRF boundary')
        key = headers.get('idempotency-key')
        if path.endswith('/rebuild'):
            if (key is None or key.get('required') is not True or key.get('schema') != {
                    'type': 'string', 'pattern': '^[A-Za-z0-9_-]{1,128}$'}):
                raise ValueError('rebuild requires its single original command key')
        elif key is not None:
            raise ValueError('read-only query/status cannot acquire an idempotency requirement')
        if 'if-match' in headers:
            raise ValueError('retrieval corpus CAS belongs to the rebuild body')
        queries = {p['name']: p for p in parameters if p.get('in') == 'query'}
        if method == 'get':
            if set(queries) != {'scope_refs', 'cursor', 'limit'} or any(p.get('required') for p in queries.values()):
                raise ValueError('retrieval status requires its three optional scalar query fields')
            for name in ('scope_refs', 'cursor'):
                schema = queries[name].get('schema', {})
                choices = [v for v in schema.get('anyOf', [schema]) if v.get('type') != 'null']
                if len(choices) != 1 or choices[0].get('type') != 'string':
                    raise ValueError('retrieval scope_refs and cursor must be scalar strings')
            limit = queries['limit'].get('schema', {})
            if (limit.get('type'), limit.get('minimum'), limit.get('maximum'), limit.get('default')) != ('integer', 1, 100, 20):
                raise ValueError('retrieval overview pagination bound is incorrect')
        elif queries:
            raise ValueError('retrieval POST does not accept query parameters')
    concrete = application - {'RetrievalIndexStatusQuery', 'RetrievalIndexStatusView'}
    for name in concrete | {'RetrievalIndexScopeStatus', 'RetrievalIndexOverview', 'JobRef'}:
        if schemas.get(name, {}).get('type') != 'object' or schemas[name].get('additionalProperties') is not False:
            raise ValueError('retrieval runtime DTO must be a closed named object')
    if internal & set(schemas) or {'RetrievalIndexStatusQuery', 'RetrievalIndexStatusView'} & set(schemas):
        raise ValueError('internal ports and scalar query unions are not fabricated HTTP components')
    raw_internal = {model.__name__: model.model_json_schema() for model in (RetrievalScopeSnapshot, RetrievalBlockMaterial)}
    if (RetrievalBlockMaterial.model_fields['body'].annotation is not bytes
            or raw_internal['RetrievalBlockMaterial']['properties']['body'].get('format') != 'binary'):
        raise ValueError('Content material bytes must retain the actual Python bytes annotation')
    ts_internal = deepcopy(raw_internal)
    ts_internal['RetrievalBlockMaterial']['properties']['body'] = {'$ref': '#/$defs/RetrievalBodyBytes'}
    internal_types = generate_types(ts_internal, provenance) + '\nexport type RetrievalBodyBytes = Uint8Array;\n'
    lines = [f"// Generated from PRODUCT_DESIGN.md v{provenance['spec_version']} and real registered contracts; do not edit.",
             f"// spec_sha256: {provenance['spec_sha256']}",
             'import type { RetrievalApplicationDTOMap, ContentRetrievalDTOMap } from "../module-ports";',
             'import type * as Api from "./api-types";',
             'import type * as Content from "./retrieval-content-types";', '',
             'export type RetrievalIndexStatusQuery =',
             '  | { scope_refs: string; cursor?: never; limit?: never }',
             '  | { scope_refs?: never; cursor?: string; limit?: number };',
             'export type RetrievalIndexStatusView = Api.RetrievalIndexScopeStatus | Api.RetrievalIndexOverview;', '',
             'export interface RetrievalRuntimeDTOMap extends RetrievalApplicationDTOMap {',
             *[f'  {name}: Api.{name};' for name in sorted(concrete)],
             '  RetrievalIndexStatusQuery: RetrievalIndexStatusQuery;',
             '  RetrievalIndexStatusView: RetrievalIndexStatusView;', '}', '',
             'export interface ContentRetrievalRuntimeDTOMap extends ContentRetrievalDTOMap {',
             *[f'  {name}: Content.{name};' for name in sorted(internal)], '}', '']
    return {'retrieval-ports-binding.ts': '\n'.join(lines),
            'retrieval-content-types.ts': internal_types,
            'retrieval-content-schemas.json': {**provenance, 'scope': 'internal_content_port_not_http_transport',
                'byte_binding': {'RetrievalBlockMaterial.body': 'Python bytes / TypeScript Uint8Array'},
                'schemas': raw_internal}}


def artifacts(root: Path = ROOT) -> dict[Path, bytes]:
    spec = root / "PRODUCT_DESIGN.md"
    provenance = spec_metadata(spec)
    schemas = {name: model.model_json_schema() for name, model in sorted(dm.CONTRACTS.items())}
    output: dict[Path, bytes] = {}

    def add_json(path: str, data: object) -> None:
        output[root / path] = (json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()

    for name, schema in schemas.items():
        add_json(f"packages/contracts/generated/schemas/{name}.schema.json", {
            "$schema": "https://json-schema.org/draft/2020-12/schema", "$comment": "Generated; do not edit.",
            "x-source-spec": provenance, **schema,
        })
    add_json("packages/contracts/generated/manifest.json", {**provenance, "models": sorted(schemas)})
    embedded = [{"path": path, "source_block_sha256": sha256_bytes((body + "\n").encode("utf-8"))}
                for path, body in PATTERN.findall(spec.read_text(encoding="utf-8"))]
    add_json("packages/contracts/generated/spec-sources.json", {**provenance, "embedded_files": embedded,
             "note": "Embedded source hashes preserve provenance; evolved implementation files need not remain byte-identical."})
    output[root / "packages/contracts/generated/types.ts"] = generate_types(schemas, provenance).encode()
    ports = (root / "packages/contracts/module-ports.ts").read_text(encoding="utf-8")
    dto_block = ports.split("export interface DTOMap {", 1)[1].split("}", 1)[0]
    names = re.findall(r"\b(\w+): unknown;", dto_block)
    if not names or set(names) - set(schemas):
        raise ValueError("module ports require unmapped shared models")
    binding = [f"// Generated from PRODUCT_DESIGN.md v{provenance['spec_version']}; do not edit.",
               f"// spec_sha256: {provenance['spec_sha256']}",
               'import type { DTOMap } from "../module-ports";',
               'import type * as Model from "./types";', "", "export interface DomainDTOMap extends DTOMap {"]
    binding.extend(f"  {name}: Model.{name};" for name in names)
    binding.append("}")
    output[root / "packages/contracts/generated/module-ports-binding.ts"] = ("\n".join(binding) + "\n").encode()
    tracking = traceability(spec)
    add_json("docs/requirements/traceability.json", tracking)
    catalog = route_catalog(spec)
    add_json("docs/requirements/routes.json", catalog)
    openapi = runtime_openapi()
    application_binding = recommendation_ports_binding(ports, openapi, provenance)
    output[root / 'packages/contracts/generated/recommendation-ports-binding.ts'] = application_binding.encode()
    provider_binding = provider_ports_binding(ports, openapi, provenance)
    output[root / 'packages/contracts/generated/provider-ports-binding.ts'] = provider_binding.encode()
    for name, value in {**api_artifacts(openapi, catalog, provenance),
                        **retrieval_artifacts(ports, openapi, provenance),
                        **tutor_artifacts(ports, openapi, provenance),
                        **authoring_artifacts(ports, openapi, provenance)}.items():
        target = "packages/contracts/generated/" + name
        if isinstance(value, str):
            output[root / target] = value.encode("utf-8")
        else:
            add_json(target, value)
    lines = ["# 派生需求追踪（不是产品验收结果）", "", f"来源：PRODUCT_DESIGN.md v{provenance['spec_version']}",
             f"spec_sha256: `{provenance['spec_sha256']}`", "", "由 `scripts/generate_contracts.py` 生成；实现和测试事实见 progress/state.json。",
             "", "| 需求 | 优先级 | 任务 | 目标场景 |", "|---|---|---|---|"]
    for req in tracking["requirements"]:
        lines.append(f"| {req['id']} {req['title']} | {req['priority']} | {', '.join(req['task_ids'])} | {', '.join(req['scenario_ids'])} |")
    output[root / "docs/requirements/README.md"] = ("\n".join(lines) + "\n").encode()
    return output


def generate(root: Path = ROOT, check: bool = False) -> int:
    result = artifacts(root)
    mismatches = []
    for path, data in result.items():
        if check:
            if not path.exists() or path.read_bytes() != data:
                mismatches.append(str(path.relative_to(root)))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    expected_schemas = {path for path in result if path.suffix == ".json" and path.parent.name == "schemas"}
    existing_schemas = set((root / "packages/contracts/generated/schemas").glob("*.json"))
    if existing_schemas - expected_schemas:
        mismatches.extend(str(path.relative_to(root)) for path in existing_schemas - expected_schemas)
    if mismatches:
        raise ValueError("generated artifacts are stale: " + ", ".join(sorted(mismatches)))
    return len(result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    print(f"{'Checked' if args.check else 'Generated'} {generate(check=args.check)} artifacts")
