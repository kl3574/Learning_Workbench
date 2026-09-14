// Generated from PRODUCT_DESIGN.md v3.0.0 and actual runtime OpenAPI; do not edit.
// spec_sha256: ab061119163b5b2a10411bb90d7cae45bf2e2b14082f4e9266f6c9452db3870c
import type { BootstrapRequest, BootstrapResponse, EmptyRequest, HealthResponse, LogoutResponse, MutationAck, PreferencesRequest, ReadinessResponse, RoleRequest, SessionResponse, WorkbenchSaveRequest, WorkbenchSession, WorkspaceResponse } from "./api-types";

export interface ApiEndpointMap {
  "GET /api/v1/readiness": { request: undefined; response: ReadinessResponse; headers: null };
  "GET /api/v1/session": { request: undefined; response: SessionResponse; headers: null };
  "POST /api/v1/session/bootstrap": { request: BootstrapRequest; response: BootstrapResponse; headers: null };
  "POST /api/v1/session/logout": { request: EmptyRequest; response: LogoutResponse; headers: null };
  "POST /api/v1/session/role": { request: RoleRequest; response: SessionResponse; headers: { "Idempotency-Key": string } };
  "GET /api/v1/workbench/session": { request: undefined; response: WorkbenchSession; headers: null };
  "PUT /api/v1/workbench/session": { request: WorkbenchSaveRequest; response: WorkbenchSession; headers: null };
  "GET /api/v1/workspace": { request: undefined; response: WorkspaceResponse; headers: null };
  "PUT /api/v1/workspace/preferences": { request: PreferencesRequest; response: MutationAck; headers: null };
  "GET /health": { request: undefined; response: HealthResponse; headers: null };
}

export const API_ENDPOINTS = {
  "GET /api/v1/readiness": {
    "method": "GET",
    "path": "/api/v1/readiness"
  },
  "GET /api/v1/session": {
    "method": "GET",
    "path": "/api/v1/session"
  },
  "POST /api/v1/session/bootstrap": {
    "method": "POST",
    "path": "/api/v1/session/bootstrap"
  },
  "POST /api/v1/session/logout": {
    "method": "POST",
    "path": "/api/v1/session/logout"
  },
  "POST /api/v1/session/role": {
    "method": "POST",
    "path": "/api/v1/session/role"
  },
  "GET /api/v1/workbench/session": {
    "method": "GET",
    "path": "/api/v1/workbench/session"
  },
  "PUT /api/v1/workbench/session": {
    "method": "PUT",
    "path": "/api/v1/workbench/session"
  },
  "GET /api/v1/workspace": {
    "method": "GET",
    "path": "/api/v1/workspace"
  },
  "PUT /api/v1/workspace/preferences": {
    "method": "PUT",
    "path": "/api/v1/workspace/preferences"
  },
  "GET /health": {
    "method": "GET",
    "path": "/health"
  }
} as const;

export type EndpointKey = keyof ApiEndpointMap;
export type ApiRequest<K extends EndpointKey> = ApiEndpointMap[K]['request'];
export type ApiResponse<K extends EndpointKey> = ApiEndpointMap[K]['response'];
type Args<K extends EndpointKey> = ApiEndpointMap[K]['headers'] extends null
  ? [body: ApiRequest<K>] : [body: ApiRequest<K>, headers: NonNullable<ApiEndpointMap[K]['headers']>];

// The caller owns same-origin session/CSRF and HTTP error handling.
export type JsonTransport = (path: string, init: RequestInit) => Promise<unknown>;
export function createApiClient(transport: JsonTransport) {
  return function request<K extends EndpointKey>(operation: K, ...args: Args<K>): Promise<ApiResponse<K>> {
    const endpoint = API_ENDPOINTS[operation];
    return transport(endpoint.path, {
      method: endpoint.method,
      ...(args[0] !== undefined ? { body: JSON.stringify(args[0]) } : {}),
      ...(args[1] ? { headers: args[1] as Record<string, string> } : {}),
    }) as Promise<ApiResponse<K>>;
  };
}
