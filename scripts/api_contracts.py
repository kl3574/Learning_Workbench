"""Project actual registered OpenAPI operations into a typed client binding.

Missing product routes remain explicit backlog entries. No handlers are created
by generation, and transport-level unknown JSON is never used as a business DTO.
"""
from __future__ import annotations

import json
import re
from typing import Any

from scripts.schema_types import generate_types, typescript_type

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}
TRANSPORT_HEADERS = {"origin", "x-csrf-token"}


def runtime_openapi() -> dict[str, Any]:
    from services.api.app.main import create_app

    return create_app().openapi()


def json_schema(content: dict[str, Any]) -> dict[str, Any]:
    if set(content) != {"application/json"}:
        raise ValueError("Non-JSON transport needs an explicit generated adapter")
    return content["application/json"]["schema"]


def parameter_contract(parameter: dict[str, Any]) -> dict[str, Any]:
    """Only explicitly supported scalar URL/header serialization is admitted."""
    location = parameter.get("in")
    if location not in {"path", "query", "header"} or "schema" not in parameter:
        raise ValueError("Unsupported parameter location or content encoding")
    style = "form" if location == "query" else "simple"
    if parameter.get("style", style) != style or parameter.get("allowReserved", False):
        raise ValueError("Unsupported parameter serialization style")
    schema = parameter["schema"]
    options = schema.get("anyOf", [schema])
    non_null = [option for option in options if option.get("type") != "null"]
    nullable = len(non_null) != len(options)
    if len(non_null) != 1 or non_null[0].get("type") not in {"string", "integer", "number", "boolean"}:
        raise ValueError("Only scalar path/query/header parameters have a generated binding")
    scalar = non_null[0]
    required = parameter.get("required", False)
    if location == "path" and (not required or nullable):
        raise ValueError("Path parameters must be required and non-null")
    if required and nullable:
        raise ValueError("Required nullable parameters need an explicit null serialization")
    return {"name": parameter["name"], "required": required, "type": scalar["type"],
            "typescript": typescript_type(schema),
            **{name: scalar[name] for name in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum")
               if name in scalar}}


def operation_parameters(path: str, path_item: dict, operation: dict) -> dict[str, list[dict[str, Any]]]:
    # OpenAPI allows operation parameters to override a path-level declaration.
    merged = {}
    for owner in (path_item, operation):
        seen = set()
        for parameter in owner.get("parameters", []):
            if "$ref" in parameter:
                raise ValueError("Referenced parameters need explicit resolution")
            key = (parameter["in"], parameter["name"])
            if key in seen:
                raise ValueError("Duplicate parameter declaration")
            seen.add(key)
            merged[key] = parameter
    result: dict[str, list[dict[str, Any]]] = {"path": [], "query": [], "header": []}
    for (location, name), parameter in sorted(merged.items()):
        contract = parameter_contract(parameter)
        if location == "header" and name.lower() in TRANSPORT_HEADERS:
            continue
        result[location].append(contract)
    if set(re.findall(r"\{([^{}]+)\}", path)) != {item["name"] for item in result["path"]}:
        raise ValueError("Path template and required path parameters disagree")
    return result


def parameter_type(parameters: list[dict[str, Any]]) -> str:
    return "{ " + "; ".join(
        f"{json.dumps(item['name'])}{'' if item['required'] else '?'}: {item['typescript']}"
        for item in parameters
    ) + " }"


def request_contract(operation: dict, schemas: dict) -> tuple[str, str, list[dict]]:
    if "requestBody" not in operation:
        return "undefined", "json", []
    content = operation["requestBody"]["content"]
    if set(content) != {"multipart/form-data"}:
        return typescript_type(json_schema(content)), "json", []
    schema = content["multipart/form-data"]["schema"]
    if "$ref" not in schema:
        raise ValueError("Multipart requires an explicit generated adapter with a named strict DTO")
    model = schema["$ref"].rsplit("/", 1)[1]
    definition = schemas[model]
    if definition.get("additionalProperties") is not False:
        raise ValueError("Multipart requires an explicit generated adapter with closed fields")
    required = set(definition.get("required", []))
    fields = []
    for name, field in definition.get("properties", {}).items():
        options = [option for option in field.get("anyOf", [field]) if option.get("type") != "null"]
        if len(options) != 1 or options[0].get("type") != "string":
            raise ValueError("Multipart requires an explicit generated adapter for non-string fields")
        binary = options[0].get("format") == "binary" or options[0].get("contentMediaType") == "application/octet-stream"
        fields.append({"name": name, "required": name in required, "binary": binary})
    if not any(field["binary"] and field["required"] for field in fields):
        raise ValueError("Multipart requires an explicit generated adapter with a required binary file")
    return model, "multipart", fields


def response_contract(operation: dict) -> tuple[list[str], str, set[str]]:
    response_types: list[str] = []
    kinds: set[str] = set()
    models = set()
    for status, response in operation["responses"].items():
        if not str(status).startswith("2"):
            continue
        content = response.get("content")
        if not content:
            response_types.append("undefined")
            kinds.add("json")
        elif set(content) == {"text/event-stream"}:
            schema = content["text/event-stream"].get("schema", {})
            alternatives = schema.get("oneOf", [])
            if (schema.get("type") != "object" or not alternatives
                    or any(set(item) != {"$ref"} for item in alternatives)
                    or schema.get("discriminator", {}).get("propertyName") != "type"):
                raise ValueError("SSE needs an explicit generated adapter with closed event union")
            names = [item["$ref"].rsplit("/", 1)[1] for item in alternatives]
            response_types.append("AsyncIterable<" + " | ".join(names) + ">")
            models.update(names)
            kinds.add("sse")
        elif set(content) == {"text/markdown"}:
            if content["text/markdown"].get("schema", {}).get("type") != "string":
                raise ValueError("Markdown responses require an explicit string schema")
            response_types.append("string")
            kinds.add("text")
        elif set(content) == {"application/octet-stream"}:
            schema = content["application/octet-stream"].get("schema", {})
            if schema.get("type") != "string" or schema.get("format") != "binary":
                raise ValueError("Binary response needs an explicit generated adapter and binary schema")
            response_types.append("Blob")
            kinds.add("blob")
        else:
            schema = json_schema(content)
            model = typescript_type(schema)
            response_types.append(model)
            alternatives = schema.get('oneOf', schema.get('anyOf', [schema]))
            if any('$ref' not in item for item in alternatives):
                raise ValueError('Endpoint response requires named strict DTO union members')
            models.update(item['$ref'].rsplit('/', 1)[1] for item in alternatives)
            kinds.add("json")
    if not response_types:
        raise ValueError("Runtime operation has no declared successful response")
    if len(kinds) != 1:
        raise ValueError("Mixed successful response transports need a status-aware adapter")
    return list(dict.fromkeys(response_types)), kinds.pop(), models


CLIENT_RUNTIME = '''export type EndpointKey = keyof ApiEndpointMap;
export type ApiRequest<K extends EndpointKey> = ApiEndpointMap[K]['request'];
export type ApiResponse<K extends EndpointKey> = ApiEndpointMap[K]['response'];
export type ApiParameters<K extends EndpointKey> = ApiEndpointMap[K]['parameters'];
export type ApiHeaders<K extends EndpointKey> = ApiEndpointMap[K]['headers'] extends null
  ? undefined : ApiEndpointMap[K]['headers'];
export type ApiArgs<K extends EndpointKey> = ApiEndpointMap[K]['parametersRequired'] extends true
  ? [body: ApiRequest<K>, headers: ApiHeaders<K>, parameters: ApiParameters<K>]
  : ApiEndpointMap[K]['headers'] extends null
    ? [body: ApiRequest<K>, headers?: undefined, parameters?: ApiParameters<K>]
    : [body: ApiRequest<K>, headers: ApiHeaders<K>, parameters?: ApiParameters<K>];

export type ResponseKind = 'json' | 'text' | 'blob' | 'sse';
// The caller owns same-origin session/CSRF and HTTP error handling.
// Raw transport data is unknown; endpoint results always use generated DTOs.
export type ApiTransport = (path: string, init: RequestInit, responseKind?: ResponseKind) => Promise<unknown>;
export type JsonTransport = ApiTransport;
type Scalar = string | number | boolean | null | undefined;
type UrlParameters = { path?: Record<string, Scalar>; query?: Record<string, Scalar> };
type Parameter = {
  name: string; required: boolean; type: 'string' | 'integer' | 'number' | 'boolean';
  minimum?: number; maximum?: number; exclusiveMinimum?: number; exclusiveMaximum?: number;
};
type Endpoint = {
  method: string; path: string; responseKind: ResponseKind;
  requestKind: 'json' | 'multipart';
  multipartFields: readonly { name: string; required: boolean; binary: boolean }[];
  pathParameters: readonly Parameter[]; queryParameters: readonly Parameter[];
  queryMode?: 'retrieval-status';
};

function requestBody(endpoint: Endpoint, value: unknown): BodyInit | undefined {
  if (endpoint.requestKind === 'json') return value === undefined ? undefined : JSON.stringify(value);
  if (typeof value !== 'object' || value === null || Array.isArray(value)) throw new TypeError('Multipart body required');
  const fields = value as Record<string, unknown>;
  const declared = new Set(endpoint.multipartFields.map(field => field.name));
  if (Object.keys(fields).some(name => !declared.has(name))) throw new TypeError('Undeclared multipart field');
  const form = new FormData();
  for (const field of endpoint.multipartFields) {
    const item = Object.hasOwn(fields, field.name) ? fields[field.name] : undefined;
    if (item === undefined || item === null) {
      if (field.required) throw new TypeError(`Missing multipart field: ${field.name}`);
      continue;
    }
    if (field.binary) {
      if (!(item instanceof Blob)) throw new TypeError(`Binary file required: ${field.name}`);
      form.append(field.name, item);
    } else {
      if (typeof item !== 'string') throw new TypeError(`String form field required: ${field.name}`);
      form.append(field.name, item);
    }
  }
  return form;
}

function parameterValue(parameter: Parameter, value: Scalar): string | undefined {
  if (value === undefined || value === null) {
    if (parameter.required) throw new TypeError(`Missing required parameter: ${parameter.name}`);
    return undefined;
  }
  const expected = parameter.type === 'integer' ? 'number' : parameter.type;
  if (typeof value !== expected) throw new TypeError(`Invalid parameter type: ${parameter.name}`);
  if (typeof value === 'number' && (!Number.isFinite(value)
      || (parameter.type === 'integer' && !Number.isSafeInteger(value))
      || (parameter.minimum !== undefined && value < parameter.minimum)
      || (parameter.maximum !== undefined && value > parameter.maximum)
      || (parameter.exclusiveMinimum !== undefined && value <= parameter.exclusiveMinimum)
      || (parameter.exclusiveMaximum !== undefined && value >= parameter.exclusiveMaximum))) {
    throw new TypeError(`Invalid numeric parameter: ${parameter.name}`);
  }
  return String(value);
}

function parameterEntries(definitions: readonly Parameter[], values: Record<string, Scalar> = {}): [string, string][] {
  const allowed = new Set(definitions.map(parameter => parameter.name));
  for (const name of Object.keys(values)) {
    if (!allowed.has(name)) throw new TypeError(`Undeclared parameter: ${name}`);
  }
  return definitions.flatMap(parameter => {
    const value = parameterValue(parameter, Object.hasOwn(values, parameter.name) ? values[parameter.name] : undefined);
    return value === undefined ? [] : [[parameter.name, value] as [string, string]];
  });
}

export function createApiClient(transport: ApiTransport) {
  return function request<K extends EndpointKey>(operation: K, ...args: ApiArgs<K>): Promise<ApiResponse<K>> {
    const endpoint: Endpoint = API_ENDPOINTS[operation];
    const parameters = (args[2] ?? {}) as UrlParameters;
    if (endpoint.queryMode === 'retrieval-status') {
      const query = parameters.query ?? {};
      if ((Object.hasOwn(query, 'scope_refs') && (Object.hasOwn(query, 'cursor') || Object.hasOwn(query, 'limit')))
          || Object.values(query).some(value => value === null)
          || (Object.hasOwn(query, 'scope_refs') && typeof query.scope_refs !== 'string')) {
        throw new TypeError('Scope status and overview parameters cannot be mixed or null');
      }
    }
    const paths = new Map(parameterEntries(endpoint.pathParameters, parameters.path));
    const path = endpoint.path.replace(/\\{([^{}]+)\\}/g, (_match, name: string) => encodeURIComponent(paths.get(name)!));
    const query = new URLSearchParams(parameterEntries(endpoint.queryParameters, parameters.query)).toString();
    const body = requestBody(endpoint, args[0]);
    return transport(path + (query ? `?${query}` : ''), {
      method: endpoint.method,
      ...(body !== undefined ? { body } : {}),
      ...(args[1] ? { headers: args[1] as Record<string, string> } : {}),
    }, endpoint.responseKind) as Promise<ApiResponse<K>>;
  };
}
'''


def api_artifacts(openapi: dict, catalog: dict, provenance: dict[str, str]) -> dict[str, str | dict]:
    schemas = openapi["components"]["schemas"]
    declared = {(route["method"], route["path"]) for route in catalog["routes"]}
    endpoints = {}
    models_needed: set[str] = set()
    entries = []
    for path, methods in sorted(openapi["paths"].items()):
        for method, operation in sorted(methods.items()):
            if method not in HTTP_METHODS:
                continue
            if (method.upper(), path) not in declared:
                raise ValueError("Runtime route is not declared in the single specification")
            request_type, request_kind, multipart_fields = request_contract(operation, schemas)
            if request_type != "undefined":
                models_needed.add(request_type)
            response_types, response_kind, response_models = response_contract(operation)
            if response_kind == "sse" and (method, path) != ("get", "/api/v1/runs/{id}/events"):
                raise ValueError("SSE operation requires its explicit generated adapter")
            models_needed.update(response_models)
            parameters = operation_parameters(path, methods, operation)
            header_type = parameter_type(parameters["header"]) if parameters["header"] else "null"
            parameter_fields = []
            for location in ("path", "query"):
                if parameters[location]:
                    required = any(item["required"] for item in parameters[location])
                    parameter_fields.append(f"{location}{'' if required else '?'}: {parameter_type(parameters[location])}")
            params_type = "{ " + "; ".join(parameter_fields) + " }" if parameter_fields else "Record<string, never>"
            retrieval_status = (method, path) == ('get', '/api/v1/index/status')
            if retrieval_status:
                params_type = '{ query?: RetrievalIndexStatusQuery }'
            required_params = any(item["required"] for location in ("path", "query") for item in parameters[location])
            key = method.upper() + " " + path
            endpoints[key] = {"method": method.upper(), "path": path, "responseKind": response_kind,
                              **({'queryMode': 'retrieval-status'} if retrieval_status else {}),
                              "requestKind": request_kind, "multipartFields": multipart_fields,
                              **{location + "Parameters": [{name: value for name, value in item.items() if name != "typescript"}
                                                            for item in parameters[location]] for location in ("path", "query")}}
            entries.append(f"  {json.dumps(key)}: {{ request: {request_type}; response: {' | '.join(response_types)}; "
                           f"headers: {header_type}; parameters: {params_type}; parametersRequired: {str(required_params).lower()} }};")
    if models_needed - {"undefined"} - set(schemas):
        raise ValueError("Endpoint request/response requires a named strict DTO")
    types = generate_types(schemas, provenance)
    binding = [f"// Generated from PRODUCT_DESIGN.md v{provenance['spec_version']} and actual runtime OpenAPI; do not edit.",
               f"// spec_sha256: {provenance['spec_sha256']}",
               ("import type { " + ", ".join(sorted(models_needed - {"undefined"})) + ' } from "./api-types";')
               if models_needed - {"undefined"} else "", "",
               ('import type { RetrievalIndexStatusQuery } from "./retrieval-ports-binding";')
               if 'GET /api/v1/index/status' in endpoints else '',
               "export interface ApiEndpointMap {", *entries, "}", "",
               "export const API_ENDPOINTS = " + json.dumps(endpoints, ensure_ascii=False, indent=2) + " as const;", "",
               CLIENT_RUNTIME]
    registered = set(endpoints)
    coverage = {**provenance, "scope": "runtime_registration_and_schema_projection_only",
                "registered_operations": sorted(registered),
                "not_registered_operations": sorted(f"{method} {path}" for method, path in declared if f"{method} {path}" not in registered),
                "product_acceptance": "NOT_RUN",
                "projection_test": "tests/contract/test_api_projection.py"}
    return {"openapi.json": {**openapi, "x-source-spec": provenance}, "api-types.ts": types,
            "api-client.ts": "\n".join(binding), "runtime-route-coverage.json": coverage}
