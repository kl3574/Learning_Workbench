// Generated from PRODUCT_DESIGN.md v3.0.0 and actual runtime OpenAPI; do not edit.
// spec_sha256: ab061119163b5b2a10411bb90d7cae45bf2e2b14082f4e9266f6c9452db3870c
import type { BootstrapRequest, BootstrapResponse, ContentBlock, ContentRef, Course, EmptyRequest, HealthResponse, Lesson, LogoutResponse, MutationAck, PageCourse, PageRevision, PreferencesRequest, ReadinessResponse, RoleRequest, SessionResponse, WorkbenchSaveRequest, WorkbenchSession, WorkspaceResponse } from "./api-types";

export interface ApiEndpointMap {
  "GET /api/v1/blocks/{id}": { request: undefined; response: ContentBlock; headers: null; parameters: { path: { "id": string }; query: { "revision": number } }; parametersRequired: true };
  "GET /api/v1/blocks/{id}/body": { request: undefined; response: string; headers: null; parameters: { path: { "id": string }; query: { "revision": number } }; parametersRequired: true };
  "GET /api/v1/courses": { request: undefined; response: PageCourse; headers: null; parameters: { query?: { "cursor"?: (string | null); "limit"?: number; "q"?: (string | null) } }; parametersRequired: false };
  "GET /api/v1/courses/{id}": { request: undefined; response: Course; headers: null; parameters: { path: { "id": string }; query: { "revision": number } }; parametersRequired: true };
  "GET /api/v1/lessons/{id}": { request: undefined; response: Lesson; headers: null; parameters: { path: { "id": string }; query: { "revision": number } }; parametersRequired: true };
  "GET /api/v1/objects/{id}/current": { request: undefined; response: ContentRef; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/objects/{id}/revisions": { request: undefined; response: PageRevision; headers: null; parameters: { path: { "id": string }; query?: { "cursor"?: (string | null); "limit"?: number } }; parametersRequired: true };
  "GET /api/v1/readiness": { request: undefined; response: ReadinessResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/session": { request: undefined; response: SessionResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "POST /api/v1/session/bootstrap": { request: BootstrapRequest; response: BootstrapResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "POST /api/v1/session/logout": { request: EmptyRequest; response: LogoutResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "POST /api/v1/session/role": { request: RoleRequest; response: SessionResponse; headers: { "Idempotency-Key": string }; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/workbench/session": { request: undefined; response: WorkbenchSession; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "PUT /api/v1/workbench/session": { request: WorkbenchSaveRequest; response: WorkbenchSession; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/workspace": { request: undefined; response: WorkspaceResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "PUT /api/v1/workspace/preferences": { request: PreferencesRequest; response: MutationAck; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "GET /health": { request: undefined; response: HealthResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
}

export const API_ENDPOINTS = {
  "GET /api/v1/blocks/{id}": {
    "method": "GET",
    "path": "/api/v1/blocks/{id}",
    "responseKind": "json",
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": [
      {
        "name": "revision",
        "required": true,
        "type": "integer",
        "minimum": 1
      }
    ]
  },
  "GET /api/v1/blocks/{id}/body": {
    "method": "GET",
    "path": "/api/v1/blocks/{id}/body",
    "responseKind": "text",
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": [
      {
        "name": "revision",
        "required": true,
        "type": "integer",
        "minimum": 1
      }
    ]
  },
  "GET /api/v1/courses": {
    "method": "GET",
    "path": "/api/v1/courses",
    "responseKind": "json",
    "pathParameters": [],
    "queryParameters": [
      {
        "name": "cursor",
        "required": false,
        "type": "string"
      },
      {
        "name": "limit",
        "required": false,
        "type": "integer",
        "minimum": 1,
        "maximum": 100
      },
      {
        "name": "q",
        "required": false,
        "type": "string"
      }
    ]
  },
  "GET /api/v1/courses/{id}": {
    "method": "GET",
    "path": "/api/v1/courses/{id}",
    "responseKind": "json",
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": [
      {
        "name": "revision",
        "required": true,
        "type": "integer",
        "minimum": 1
      }
    ]
  },
  "GET /api/v1/lessons/{id}": {
    "method": "GET",
    "path": "/api/v1/lessons/{id}",
    "responseKind": "json",
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": [
      {
        "name": "revision",
        "required": true,
        "type": "integer",
        "minimum": 1
      }
    ]
  },
  "GET /api/v1/objects/{id}/current": {
    "method": "GET",
    "path": "/api/v1/objects/{id}/current",
    "responseKind": "json",
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/objects/{id}/revisions": {
    "method": "GET",
    "path": "/api/v1/objects/{id}/revisions",
    "responseKind": "json",
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": [
      {
        "name": "cursor",
        "required": false,
        "type": "string"
      },
      {
        "name": "limit",
        "required": false,
        "type": "integer",
        "minimum": 1,
        "maximum": 100
      }
    ]
  },
  "GET /api/v1/readiness": {
    "method": "GET",
    "path": "/api/v1/readiness",
    "responseKind": "json",
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/session": {
    "method": "GET",
    "path": "/api/v1/session",
    "responseKind": "json",
    "pathParameters": [],
    "queryParameters": []
  },
  "POST /api/v1/session/bootstrap": {
    "method": "POST",
    "path": "/api/v1/session/bootstrap",
    "responseKind": "json",
    "pathParameters": [],
    "queryParameters": []
  },
  "POST /api/v1/session/logout": {
    "method": "POST",
    "path": "/api/v1/session/logout",
    "responseKind": "json",
    "pathParameters": [],
    "queryParameters": []
  },
  "POST /api/v1/session/role": {
    "method": "POST",
    "path": "/api/v1/session/role",
    "responseKind": "json",
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/workbench/session": {
    "method": "GET",
    "path": "/api/v1/workbench/session",
    "responseKind": "json",
    "pathParameters": [],
    "queryParameters": []
  },
  "PUT /api/v1/workbench/session": {
    "method": "PUT",
    "path": "/api/v1/workbench/session",
    "responseKind": "json",
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/workspace": {
    "method": "GET",
    "path": "/api/v1/workspace",
    "responseKind": "json",
    "pathParameters": [],
    "queryParameters": []
  },
  "PUT /api/v1/workspace/preferences": {
    "method": "PUT",
    "path": "/api/v1/workspace/preferences",
    "responseKind": "json",
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /health": {
    "method": "GET",
    "path": "/health",
    "responseKind": "json",
    "pathParameters": [],
    "queryParameters": []
  }
} as const;

export type EndpointKey = keyof ApiEndpointMap;
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

export type ResponseKind = 'json' | 'text';
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
  pathParameters: readonly Parameter[]; queryParameters: readonly Parameter[];
};

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
    const paths = new Map(parameterEntries(endpoint.pathParameters, parameters.path));
    const path = endpoint.path.replace(/\{([^{}]+)\}/g, (_match, name: string) => encodeURIComponent(paths.get(name)!));
    const query = new URLSearchParams(parameterEntries(endpoint.queryParameters, parameters.query)).toString();
    return transport(path + (query ? `?${query}` : ''), {
      method: endpoint.method,
      ...(args[0] !== undefined ? { body: JSON.stringify(args[0]) } : {}),
      ...(args[1] ? { headers: args[1] as Record<string, string> } : {}),
    }, endpoint.responseKind) as Promise<ApiResponse<K>>;
  };
}
