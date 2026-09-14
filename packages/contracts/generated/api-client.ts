// Generated from PRODUCT_DESIGN.md v3.0.0 and actual runtime OpenAPI; do not edit.
// spec_sha256: ab061119163b5b2a10411bb90d7cae45bf2e2b14082f4e9266f6c9452db3870c
import type { BlockReadResponse, BootstrapRequest, BootstrapResponse, ContentRef, Course, DirectorySearchResponse, EmptyRequest, HealthResponse, ImportCancelRequest, ImportCancelResponse, ImportCommitRequest, ImportCommitResponse, ImportDraftSnapshot, ImportPreview, ImportStaged, ImportUpload, JobCancelRequest, JobSnapshot, LearningActionRequest, LearningActionResponse, LearningProgress, Lesson, LogoutResponse, MutationAck, Note, NoteDeleted, OutlineResponse, PageCourse, PageNote, PageRevision, PreferencesRequest, ReadinessResponse, RoleRequest, SessionResponse, SourceResponse, WorkbenchSaveRequest, WorkbenchSession, WorkspaceResponse } from "./api-types";

export interface ApiEndpointMap {
  "GET /api/v1/artifacts/{id}/download": { request: undefined; response: Blob; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/blocks/{id}": { request: undefined; response: BlockReadResponse; headers: null; parameters: { path: { "id": string }; query: { "include_provenance"?: boolean; "revision": number } }; parametersRequired: true };
  "GET /api/v1/blocks/{id}/body": { request: undefined; response: string; headers: null; parameters: { path: { "id": string }; query: { "revision": number } }; parametersRequired: true };
  "GET /api/v1/courses": { request: undefined; response: PageCourse; headers: null; parameters: { query?: { "cursor"?: (string | null); "limit"?: number; "q"?: (string | null) } }; parametersRequired: false };
  "GET /api/v1/courses/{id}": { request: undefined; response: Course; headers: null; parameters: { path: { "id": string }; query: { "revision": number } }; parametersRequired: true };
  "GET /api/v1/courses/{id}/directory-search": { request: undefined; response: DirectorySearchResponse; headers: null; parameters: { path: { "id": string }; query: { "limit"?: number; "q": string; "revision": number } }; parametersRequired: true };
  "GET /api/v1/courses/{id}/outline": { request: undefined; response: OutlineResponse; headers: null; parameters: { path: { "id": string }; query: { "revision": number } }; parametersRequired: true };
  "GET /api/v1/drafts/{id}": { request: undefined; response: ImportDraftSnapshot; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/imports": { request: ImportUpload; response: ImportStaged; headers: { "Idempotency-Key": string }; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/imports/{id}": { request: undefined; response: ImportPreview; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/imports/{id}/cancel": { request: ImportCancelRequest; response: ImportCancelResponse; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/imports/{id}/commit": { request: ImportCommitRequest; response: ImportCommitResponse; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/jobs/{id}": { request: undefined; response: JobSnapshot; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/jobs/{id}/cancel": { request: JobCancelRequest; response: JobSnapshot; headers: { "Idempotency-Key": string }; parameters: { path: { "id": string } }; parametersRequired: true };
  "POST /api/v1/learning/actions": { request: LearningActionRequest; response: LearningActionResponse; headers: { "Idempotency-Key": string }; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/learning/progress": { request: undefined; response: LearningProgress; headers: null; parameters: { query?: { "course_id"?: (string | null) } }; parametersRequired: false };
  "GET /api/v1/lessons/{id}": { request: undefined; response: Lesson; headers: null; parameters: { path: { "id": string }; query: { "revision": number } }; parametersRequired: true };
  "GET /api/v1/notes": { request: undefined; response: PageNote; headers: null; parameters: { query?: { "cursor"?: (string | null); "limit"?: number; "ref_id"?: (string | null) } }; parametersRequired: false };
  "POST /api/v1/notes": { request: Note; response: ContentRef; headers: { "Idempotency-Key": string }; parameters: Record<string, never>; parametersRequired: false };
  "DELETE /api/v1/notes/{id}": { request: undefined; response: NoteDeleted; headers: { "Idempotency-Key": string; "If-Match"?: (string | null) }; parameters: { path: { "id": string } }; parametersRequired: true };
  "PATCH /api/v1/notes/{id}": { request: Note; response: ContentRef; headers: { "Idempotency-Key": string; "If-Match"?: (string | null) }; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/objects/{id}/current": { request: undefined; response: ContentRef; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/objects/{id}/revisions": { request: undefined; response: PageRevision; headers: null; parameters: { path: { "id": string }; query?: { "cursor"?: (string | null); "limit"?: number } }; parametersRequired: true };
  "GET /api/v1/readiness": { request: undefined; response: ReadinessResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/session": { request: undefined; response: SessionResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "POST /api/v1/session/bootstrap": { request: BootstrapRequest; response: BootstrapResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "POST /api/v1/session/logout": { request: EmptyRequest; response: LogoutResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "POST /api/v1/session/role": { request: RoleRequest; response: SessionResponse; headers: { "Idempotency-Key": string }; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/sources/{id}": { request: undefined; response: SourceResponse; headers: null; parameters: { path: { "id": string } }; parametersRequired: true };
  "GET /api/v1/workbench/session": { request: undefined; response: WorkbenchSession; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "PUT /api/v1/workbench/session": { request: WorkbenchSaveRequest; response: WorkbenchSession; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "GET /api/v1/workspace": { request: undefined; response: WorkspaceResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "PUT /api/v1/workspace/preferences": { request: PreferencesRequest; response: MutationAck; headers: null; parameters: Record<string, never>; parametersRequired: false };
  "GET /health": { request: undefined; response: HealthResponse; headers: null; parameters: Record<string, never>; parametersRequired: false };
}

export const API_ENDPOINTS = {
  "GET /api/v1/artifacts/{id}/download": {
    "method": "GET",
    "path": "/api/v1/artifacts/{id}/download",
    "responseKind": "blob",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/blocks/{id}": {
    "method": "GET",
    "path": "/api/v1/blocks/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": [
      {
        "name": "include_provenance",
        "required": false,
        "type": "boolean"
      },
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
    "requestKind": "json",
    "multipartFields": [],
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
    "requestKind": "json",
    "multipartFields": [],
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
    "requestKind": "json",
    "multipartFields": [],
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
  "GET /api/v1/courses/{id}/directory-search": {
    "method": "GET",
    "path": "/api/v1/courses/{id}/directory-search",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": [
      {
        "name": "limit",
        "required": false,
        "type": "integer",
        "minimum": 1,
        "maximum": 50
      },
      {
        "name": "q",
        "required": true,
        "type": "string"
      },
      {
        "name": "revision",
        "required": true,
        "type": "integer",
        "minimum": 1
      }
    ]
  },
  "GET /api/v1/courses/{id}/outline": {
    "method": "GET",
    "path": "/api/v1/courses/{id}/outline",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
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
  "GET /api/v1/drafts/{id}": {
    "method": "GET",
    "path": "/api/v1/drafts/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/imports": {
    "method": "POST",
    "path": "/api/v1/imports",
    "responseKind": "json",
    "requestKind": "multipart",
    "multipartFields": [
      {
        "name": "file",
        "required": true,
        "binary": true
      },
      {
        "name": "kind",
        "required": true,
        "binary": false
      },
      {
        "name": "target_course_id",
        "required": false,
        "binary": false
      }
    ],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/imports/{id}": {
    "method": "GET",
    "path": "/api/v1/imports/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/imports/{id}/cancel": {
    "method": "POST",
    "path": "/api/v1/imports/{id}/cancel",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/imports/{id}/commit": {
    "method": "POST",
    "path": "/api/v1/imports/{id}/commit",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/jobs/{id}": {
    "method": "GET",
    "path": "/api/v1/jobs/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/jobs/{id}/cancel": {
    "method": "POST",
    "path": "/api/v1/jobs/{id}/cancel",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "POST /api/v1/learning/actions": {
    "method": "POST",
    "path": "/api/v1/learning/actions",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/learning/progress": {
    "method": "GET",
    "path": "/api/v1/learning/progress",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": [
      {
        "name": "course_id",
        "required": false,
        "type": "string"
      }
    ]
  },
  "GET /api/v1/lessons/{id}": {
    "method": "GET",
    "path": "/api/v1/lessons/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
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
  "GET /api/v1/notes": {
    "method": "GET",
    "path": "/api/v1/notes",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
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
        "name": "ref_id",
        "required": false,
        "type": "string"
      }
    ]
  },
  "POST /api/v1/notes": {
    "method": "POST",
    "path": "/api/v1/notes",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "DELETE /api/v1/notes/{id}": {
    "method": "DELETE",
    "path": "/api/v1/notes/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "PATCH /api/v1/notes/{id}": {
    "method": "PATCH",
    "path": "/api/v1/notes/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/objects/{id}/current": {
    "method": "GET",
    "path": "/api/v1/objects/{id}/current",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
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
    "requestKind": "json",
    "multipartFields": [],
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
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/session": {
    "method": "GET",
    "path": "/api/v1/session",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "POST /api/v1/session/bootstrap": {
    "method": "POST",
    "path": "/api/v1/session/bootstrap",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "POST /api/v1/session/logout": {
    "method": "POST",
    "path": "/api/v1/session/logout",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "POST /api/v1/session/role": {
    "method": "POST",
    "path": "/api/v1/session/role",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/sources/{id}": {
    "method": "GET",
    "path": "/api/v1/sources/{id}",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [
      {
        "name": "id",
        "required": true,
        "type": "string"
      }
    ],
    "queryParameters": []
  },
  "GET /api/v1/workbench/session": {
    "method": "GET",
    "path": "/api/v1/workbench/session",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "PUT /api/v1/workbench/session": {
    "method": "PUT",
    "path": "/api/v1/workbench/session",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /api/v1/workspace": {
    "method": "GET",
    "path": "/api/v1/workspace",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "PUT /api/v1/workspace/preferences": {
    "method": "PUT",
    "path": "/api/v1/workspace/preferences",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
    "pathParameters": [],
    "queryParameters": []
  },
  "GET /health": {
    "method": "GET",
    "path": "/health",
    "responseKind": "json",
    "requestKind": "json",
    "multipartFields": [],
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

export type ResponseKind = 'json' | 'text' | 'blob';
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
    const paths = new Map(parameterEntries(endpoint.pathParameters, parameters.path));
    const path = endpoint.path.replace(/\{([^{}]+)\}/g, (_match, name: string) => encodeURIComponent(paths.get(name)!));
    const query = new URLSearchParams(parameterEntries(endpoint.queryParameters, parameters.query)).toString();
    const body = requestBody(endpoint, args[0]);
    return transport(path + (query ? `?${query}` : ''), {
      method: endpoint.method,
      ...(body !== undefined ? { body } : {}),
      ...(args[1] ? { headers: args[1] as Record<string, string> } : {}),
    }, endpoint.responseKind) as Promise<ApiResponse<K>>;
  };
}
