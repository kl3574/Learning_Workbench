"""Project actual registered OpenAPI operations into a typed client binding.

Missing product routes remain explicit backlog entries. No handlers are created
by generation, and transport-level unknown JSON is never used as a business DTO.
"""
from __future__ import annotations

import json
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
            request_type = "undefined"
            if "requestBody" in operation:
                request_type = typescript_type(json_schema(operation["requestBody"]["content"]))
                models_needed.add(request_type)
            response_types = []
            for status, response in operation["responses"].items():
                if status.startswith("2"):
                    response_types.append(typescript_type(json_schema(response["content"])) if "content" in response else "undefined")
            if not response_types:
                raise ValueError("Runtime operation has no declared successful response")
            models_needed.update(response_types)
            headers = {}
            for parameter in operation.get("parameters", []):
                if parameter["in"] != "header":
                    raise ValueError("Path/query parameters need an explicit generated binding")
                if parameter["name"].lower() not in TRANSPORT_HEADERS:
                    headers[parameter["name"]] = {"required": parameter.get("required", False),
                                                   "type": typescript_type(parameter["schema"])}
            header_type = "null" if not headers else "{ " + "; ".join(
                f"{json.dumps(name)}{'' if value['required'] else '?'}: {value['type']}" for name, value in headers.items()
            ) + " }"
            key = method.upper() + " " + path
            endpoints[key] = {"method": method.upper(), "path": path}
            entries.append(f"  {json.dumps(key)}: {{ request: {request_type}; response: {' | '.join(response_types)}; headers: {header_type} }};")
    if models_needed - {"undefined"} - set(schemas):
        raise ValueError("Endpoint request/response requires a named strict DTO")
    types = generate_types(schemas, provenance)
    binding = [f"// Generated from PRODUCT_DESIGN.md v{provenance['spec_version']} and actual runtime OpenAPI; do not edit.",
               f"// spec_sha256: {provenance['spec_sha256']}",
               "import type { " + ", ".join(sorted(models_needed - {"undefined"})) + ' } from "./api-types";', "",
               "export interface ApiEndpointMap {", *entries, "}", "",
               "export const API_ENDPOINTS = " + json.dumps(endpoints, ensure_ascii=False, indent=2) + " as const;", "",
               "export type EndpointKey = keyof ApiEndpointMap;",
               "export type ApiRequest<K extends EndpointKey> = ApiEndpointMap[K]['request'];",
               "export type ApiResponse<K extends EndpointKey> = ApiEndpointMap[K]['response'];",
               "type Args<K extends EndpointKey> = ApiEndpointMap[K]['headers'] extends null",
               "  ? [body: ApiRequest<K>] : [body: ApiRequest<K>, headers: NonNullable<ApiEndpointMap[K]['headers']>];", "",
               "// The caller owns same-origin session/CSRF and HTTP error handling.",
               "export type JsonTransport = (path: string, init: RequestInit) => Promise<unknown>;",
               "export function createApiClient(transport: JsonTransport) {",
               "  return function request<K extends EndpointKey>(operation: K, ...args: Args<K>): Promise<ApiResponse<K>> {",
               "    const endpoint = API_ENDPOINTS[operation];",
               "    return transport(endpoint.path, {",
               "      method: endpoint.method,",
               "      ...(args[0] !== undefined ? { body: JSON.stringify(args[0]) } : {}),",
               "      ...(args[1] ? { headers: args[1] as Record<string, string> } : {}),",
               "    }) as Promise<ApiResponse<K>>;",
               "  };", "}", ""]
    registered = set(endpoints)
    coverage = {**provenance, "scope": "runtime_registration_and_schema_projection_only",
                "registered_operations": sorted(registered),
                "not_registered_operations": sorted(f"{method} {path}" for method, path in declared if f"{method} {path}" not in registered),
                "product_acceptance": "NOT_RUN",
                "projection_test": "tests/contract/test_api_projection.py"}
    return {"openapi.json": {**openapi, "x-source-spec": provenance}, "api-types.ts": types,
            "api-client.ts": "\n".join(binding), "runtime-route-coverage.json": coverage}
