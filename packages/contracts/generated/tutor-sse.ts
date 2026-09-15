// Generated from PRODUCT_DESIGN.md v3.0.5; do not edit.
// spec_sha256: 2bfd471933be478a7cac51363a0482a87c81ec113c3e6cbdec88cfd139d43f37
import type * as Api from "./api-types";
import { createApiClient } from "./api-client";
export type TutorSSEEvent = Api.TutorQueuedEvent | Api.TutorContextReadyEvent | Api.TutorRetrievalCompletedEvent | Api.TutorAnswerDeltaEvent | Api.TutorCitationEvent | Api.TutorApprovalRequiredEvent | Api.TutorUsageEvent | Api.TutorCompletedEvent | Api.TutorFailedEvent | Api.TutorCancelledEvent;
const SCHEMAS: Record<string, Schema> = {"TutorQueuedEvent": {"properties": {"run_id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_-]{0,79}$", "title": "Run Id"}, "seq": {"type": "integer", "minimum": 1.0, "title": "Seq"}, "occurred_at": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$", "title": "Occurred At"}, "type": {"type": "string", "const": "queued", "title": "Type"}}, "additionalProperties": false, "type": "object", "required": ["run_id", "seq", "occurred_at", "type"], "title": "TutorQueuedEvent"}, "TutorContextReadyEvent": {"properties": {"run_id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_-]{0,79}$", "title": "Run Id"}, "seq": {"type": "integer", "minimum": 1.0, "title": "Seq"}, "occurred_at": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$", "title": "Occurred At"}, "type": {"type": "string", "const": "context_ready", "title": "Type"}, "context_snapshot_id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_-]{0,79}$", "title": "Context Snapshot Id"}}, "additionalProperties": false, "type": "object", "required": ["run_id", "seq", "occurred_at", "type", "context_snapshot_id"], "title": "TutorContextReadyEvent"}, "TutorRetrievalCompletedEvent": {"properties": {"run_id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_-]{0,79}$", "title": "Run Id"}, "seq": {"type": "integer", "minimum": 1.0, "title": "Seq"}, "occurred_at": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$", "title": "Occurred At"}, "type": {"type": "string", "const": "retrieval_completed", "title": "Type"}}, "additionalProperties": false, "type": "object", "required": ["run_id", "seq", "occurred_at", "type"], "title": "TutorRetrievalCompletedEvent"}, "TutorAnswerDeltaEvent": {"properties": {"run_id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_-]{0,79}$", "title": "Run Id"}, "seq": {"type": "integer", "minimum": 1.0, "title": "Seq"}, "occurred_at": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$", "title": "Occurred At"}, "type": {"type": "string", "const": "answer_delta", "title": "Type"}, "text": {"type": "string", "minLength": 1, "title": "Text"}}, "additionalProperties": false, "type": "object", "required": ["run_id", "seq", "occurred_at", "type", "text"], "title": "TutorAnswerDeltaEvent"}, "TutorCitationEvent": {"properties": {"run_id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_-]{0,79}$", "title": "Run Id"}, "seq": {"type": "integer", "minimum": 1.0, "title": "Seq"}, "occurred_at": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$", "title": "Occurred At"}, "type": {"type": "string", "const": "citation", "title": "Type"}, "citation": {"$ref": "#/components/schemas/Citation"}}, "additionalProperties": false, "type": "object", "required": ["run_id", "seq", "occurred_at", "type", "citation"], "title": "TutorCitationEvent"}, "Citation": {"properties": {"id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_-]{0,79}$", "title": "Id"}, "title": {"type": "string", "title": "Title"}, "url": {"anyOf": [{"type": "string"}, {"type": "null"}], "title": "Url"}, "locator": {"type": "string", "title": "Locator"}, "source_sha256": {"anyOf": [{"type": "string", "pattern": "^[a-f0-9]{64}$"}, {"type": "null"}], "title": "Source Sha256"}, "verification": {"type": "string", "enum": ["verified", "unverified", "user_supplied"], "title": "Verification"}}, "additionalProperties": false, "type": "object", "required": ["id", "title", "locator", "verification"], "title": "Citation"}, "TutorApprovalRequiredEvent": {"properties": {"run_id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_-]{0,79}$", "title": "Run Id"}, "seq": {"type": "integer", "minimum": 1.0, "title": "Seq"}, "occurred_at": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$", "title": "Occurred At"}, "type": {"type": "string", "const": "approval_required", "title": "Type"}, "approval_id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_-]{0,79}$", "title": "Approval Id"}}, "additionalProperties": false, "type": "object", "required": ["run_id", "seq", "occurred_at", "type", "approval_id"], "title": "TutorApprovalRequiredEvent"}, "TutorUsageEvent": {"properties": {"run_id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_-]{0,79}$", "title": "Run Id"}, "seq": {"type": "integer", "minimum": 1.0, "title": "Seq"}, "occurred_at": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$", "title": "Occurred At"}, "type": {"type": "string", "const": "usage", "title": "Type"}, "input_tokens": {"anyOf": [{"type": "integer", "minimum": 0.0}, {"type": "null"}], "title": "Input Tokens"}, "output_tokens": {"anyOf": [{"type": "integer", "minimum": 0.0}, {"type": "null"}], "title": "Output Tokens"}}, "additionalProperties": false, "type": "object", "required": ["run_id", "seq", "occurred_at", "type", "input_tokens", "output_tokens"], "title": "TutorUsageEvent"}, "TutorCompletedEvent": {"properties": {"run_id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_-]{0,79}$", "title": "Run Id"}, "seq": {"type": "integer", "minimum": 1.0, "title": "Seq"}, "occurred_at": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$", "title": "Occurred At"}, "type": {"type": "string", "const": "completed", "title": "Type"}}, "additionalProperties": false, "type": "object", "required": ["run_id", "seq", "occurred_at", "type"], "title": "TutorCompletedEvent"}, "TutorFailedEvent": {"properties": {"run_id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_-]{0,79}$", "title": "Run Id"}, "seq": {"type": "integer", "minimum": 1.0, "title": "Seq"}, "occurred_at": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$", "title": "Occurred At"}, "type": {"type": "string", "const": "failed", "title": "Type"}, "error_code": {"anyOf": [{"type": "string", "enum": ["CAPABILITY_UNSUPPORTED", "PROVIDER_CONFIGURATION_CHANGED", "PROVIDER_SECRET_UNAVAILABLE", "OUTBOUND_SOURCE_CHANGED", "OUTBOUND_SOURCE_UNAVAILABLE", "CONSENT_REQUIRED", "CONSENT_REVOKED", "CONSENT_EXPIRED", "OUTBOUND_BUDGET_EXCEEDED", "PROVIDER_TIMEOUT", "PROVIDER_CANCELLED", "PROVIDER_TRANSPORT_ERROR", "PROVIDER_PROTOCOL_ERROR", "PROVIDER_OUTCOME_UNKNOWN", "PROVIDER_USAGE_INCONSISTENT", "PROVIDER_REFUSAL", "PROVIDER_INCOMPLETE"]}, {"type": "string", "enum": ["POLICY_DENIED", "ASSESSMENT_ACTIVE", "TUTOR_CONTEXT_INVALID", "TUTOR_CONTEXT_CHANGED", "TUTOR_CONTEXT_UNAVAILABLE", "TUTOR_CONTEXT_BUDGET_EXCEEDED", "TUTOR_OUTPUT_INVALID", "TUTOR_OUTPUT_EMPTY", "TUTOR_INTEGRITY_ERROR", "TUTOR_OUTCOME_UNKNOWN"]}], "title": "Error Code"}}, "additionalProperties": false, "type": "object", "required": ["run_id", "seq", "occurred_at", "type", "error_code"], "title": "TutorFailedEvent"}, "TutorCancelledEvent": {"properties": {"run_id": {"type": "string", "pattern": "^[A-Za-z][A-Za-z0-9_-]{0,79}$", "title": "Run Id"}, "seq": {"type": "integer", "minimum": 1.0, "title": "Seq"}, "occurred_at": {"type": "string", "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}(\\.\\d+)?Z$", "title": "Occurred At"}, "type": {"type": "string", "const": "cancelled", "title": "Type"}}, "additionalProperties": false, "type": "object", "required": ["run_id", "seq", "occurred_at", "type"], "title": "TutorCancelledEvent"}};
const EVENT_SCHEMA: Schema = {"type": "object", "discriminator": {"mapping": {"answer_delta": "#/components/schemas/TutorAnswerDeltaEvent", "approval_required": "#/components/schemas/TutorApprovalRequiredEvent", "cancelled": "#/components/schemas/TutorCancelledEvent", "citation": "#/components/schemas/TutorCitationEvent", "completed": "#/components/schemas/TutorCompletedEvent", "context_ready": "#/components/schemas/TutorContextReadyEvent", "failed": "#/components/schemas/TutorFailedEvent", "queued": "#/components/schemas/TutorQueuedEvent", "retrieval_completed": "#/components/schemas/TutorRetrievalCompletedEvent", "usage": "#/components/schemas/TutorUsageEvent"}, "propertyName": "type"}, "oneOf": [{"$ref": "#/components/schemas/TutorQueuedEvent"}, {"$ref": "#/components/schemas/TutorContextReadyEvent"}, {"$ref": "#/components/schemas/TutorRetrievalCompletedEvent"}, {"$ref": "#/components/schemas/TutorAnswerDeltaEvent"}, {"$ref": "#/components/schemas/TutorCitationEvent"}, {"$ref": "#/components/schemas/TutorApprovalRequiredEvent"}, {"$ref": "#/components/schemas/TutorUsageEvent"}, {"$ref": "#/components/schemas/TutorCompletedEvent"}, {"$ref": "#/components/schemas/TutorFailedEvent"}, {"$ref": "#/components/schemas/TutorCancelledEvent"}]};

type Schema = {
  [annotation: string]: unknown;
  $ref?: string; type?: string; const?: unknown; enum?: readonly unknown[];
  oneOf?: readonly Schema[]; anyOf?: readonly Schema[];
  properties?: Record<string, Schema>; required?: readonly string[];
  additionalProperties?: boolean; items?: Schema; pattern?: string;
  minimum?: number; maximum?: number; minLength?: number; maxLength?: number;
};
function fail(): never { throw new TypeError('Invalid Tutor SSE framing or typed event'); }
function unicode(text: string): boolean {
  for (let i = 0; i < text.length; i++) {
    const cp = text.charCodeAt(i);
    if (cp >= 0xd800 && cp <= 0xdbff) {
      const next = text.charCodeAt(++i);
      if (!(next >= 0xdc00 && next <= 0xdfff)) return false;
    } else if (cp >= 0xdc00 && cp <= 0xdfff) return false;
  }
  return true;
}
function checked(schema: Schema, value: unknown): boolean {
  if (schema.$ref) {
    const target = SCHEMAS[schema.$ref.split('/').at(-1)!];
    return target !== undefined && checked(target, value);
  }
  if (schema.oneOf && schema.oneOf.filter(item => checked(item, value)).length !== 1) return false;
  if (schema.anyOf && !schema.anyOf.some(item => checked(item, value))) return false;
  if (Object.hasOwn(schema, 'const') && value !== schema.const) return false;
  if (schema.enum && !schema.enum.includes(value)) return false;
  if (schema.type === 'null') return value === null;
  if (schema.type === 'string') return typeof value === 'string' && unicode(value)
    && (schema.minLength === undefined || [...value].length >= schema.minLength)
    && (schema.maxLength === undefined || [...value].length <= schema.maxLength)
    && (schema.pattern === undefined || new RegExp(schema.pattern).test(value));
  if (schema.type === 'integer' || schema.type === 'number') return typeof value === 'number'
    && Number.isFinite(value) && (schema.type !== 'integer' || Number.isSafeInteger(value))
    && (schema.minimum === undefined || value >= schema.minimum)
    && (schema.maximum === undefined || value <= schema.maximum);
  if (schema.type === 'boolean') return typeof value === 'boolean';
  if (schema.type === 'array') return Array.isArray(value)
    && (schema.items === undefined || value.every(item => checked(schema.items!, item)));
  if (schema.type === 'object') {
    if (typeof value !== 'object' || value === null || Array.isArray(value)) return false;
    const fields = value as Record<string, unknown>, properties = schema.properties ?? {};
    if (schema.required?.some(name => !Object.hasOwn(fields, name))) return false;
    if (schema.additionalProperties === false && Object.keys(fields).some(name => !Object.hasOwn(properties, name))) return false;
    return Object.entries(fields).every(([name, item]) => !Object.hasOwn(properties, name) || checked(properties[name], item));
  }
  return schema.oneOf !== undefined || schema.anyOf !== undefined || Object.hasOwn(schema, 'const') || schema.enum !== undefined;
}
function utc(value: string): boolean {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?Z$/.exec(value);
  if (!m) return false;
  const [year, month, day, hour, minute, second] = m.slice(1).map(Number);
  const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  return year >= 1 && month >= 1 && month <= 12 && day >= 1 && day <= days[month - 1]
    && hour <= 23 && minute <= 59 && second <= 59;
}
function parseJSON(text: string): unknown {
  const value: unknown = JSON.parse(text);
  // JSON.parse otherwise silently discards duplicate property names. Scan the
  // already-valid grammar to reject this ambiguity without replacing JSON.
  const stack: Array<Set<string> | null> = [];
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '{') stack.push(new Set());
    else if (c === '[') stack.push(null);
    else if (c === '}' || c === ']') stack.pop();
    else if (c === '"') {
      const start = i++;
      while (i < text.length && text[i] !== '"') { if (text[i] === '\\') i++; i++; }
      let next = i + 1;
      while (/\s/.test(text[next] ?? '') && next < text.length) next++;
      if (text[next] === ':') {
        const keys = stack.at(-1), key: unknown = JSON.parse(text.slice(start, i + 1));
        if (!keys || typeof key !== 'string' || keys.has(key)) return fail();
        keys.add(key);
      }
    }
  }
  return value;
}
function eventValue(value: unknown): TutorSSEEvent {
  if (!checked(EVENT_SCHEMA, value)) return fail();
  const event = value as TutorSSEEvent;
  if (!utc(event.occurred_at)) return fail();
  if (event.type === 'usage' && event.input_tokens === null && event.output_tokens === null) return fail();
  return event;
}
function integer(value: number): void {
  if (!Number.isSafeInteger(value) || value < 0) fail();
}
function identity(runId: string): void {
  if (!/^[A-Za-z][A-Za-z0-9_-]{0,79}$/.test(runId)) fail();
}
export class TutorStreamHTTPError extends Error {
  constructor(readonly status: number) { super('Tutor event stream HTTP ' + status); this.name = 'TutorStreamHTTPError'; }
}
export async function* decodeTutorEvents(
  stream: ReadableStream<Uint8Array>, runId: string, afterSeq = 0,
): AsyncGenerator<TutorSSEEvent> {
  identity(runId); integer(afterSeq);
  const reader = stream.getReader(), decoder = new TextDecoder('utf-8', { fatal: true });
  let buffer = '', lines: string[] = [], frameSize = 0, last = afterSeq, terminal = false;
  let input: number | null = null, output: number | null = null;
  const observed = new Map<number, string>();
  function frame(): TutorSSEEvent | null {
    const fields: Record<string, string> = {};
    for (const line of lines) {
      if (line.startsWith(':')) continue;
      const split = line.indexOf(':');
      if (split < 1) return fail();
      const name = line.slice(0, split), raw = line.slice(split + 1);
      if (!['id', 'event', 'data'].includes(name) || Object.hasOwn(fields, name)) return fail();
      fields[name] = raw.startsWith(' ') ? raw.slice(1) : raw;
    }
    lines = []; frameSize = 0;
    if (Object.keys(fields).length === 0) return null;
    if (Object.keys(fields).length !== 3) return fail();
    const event = eventValue(parseJSON(fields.data));
    if (event.run_id !== runId || fields.id !== runId + ':' + event.seq || fields.event !== event.type) return fail();
    const stable = JSON.stringify(Object.fromEntries(Object.entries(event).sort(([a], [b]) => a.localeCompare(b))));
    if (event.seq <= last) {
      if (observed.has(event.seq) && observed.get(event.seq) !== stable) return fail();
      return null;
    }
    if (terminal || event.seq !== last + 1) return fail();
    if (event.type === 'usage') {
      if ((input !== null && (event.input_tokens === null || event.input_tokens < input))
          || (output !== null && (event.output_tokens === null || event.output_tokens < output))) return fail();
      input = event.input_tokens; output = event.output_tokens;
    }
    last = event.seq; observed.set(last, stable);
    terminal = ['completed', 'failed', 'cancelled'].includes(event.type);
    return event;
  }
  try {
    let done = false;
    while (!done) {
      const chunk = await reader.read();
      done = chunk.done;
      buffer += done ? decoder.decode() : decoder.decode(chunk.value, { stream: true });
      // A transport safety bound, not an answer truncation strategy.
      if (buffer.length > 4 * 1024 * 1024) return fail();
      while (true) {
        const match = /[\r\n]/.exec(buffer);
        if (!match) break;
        const position = match.index;
        if (buffer[position] === '\r' && position + 1 === buffer.length && !done) break;
        const line = buffer.slice(0, position);
        const skip = buffer[position] === '\r' && buffer[position + 1] === '\n' ? 2 : 1;
        buffer = buffer.slice(position + skip);
        if (line.length > 0 && !line.startsWith(':')) {
          frameSize += line.length;
          if (frameSize > 4 * 1024 * 1024 || lines.length >= 3) return fail();
          lines.push(line);
        } else if (line.length === 0) { const event = frame(); if (event !== null) yield event; }
      }
    }
    if (buffer.length > 0 || lines.length > 0) return fail();
  } finally {
    await reader.cancel().catch(() => undefined);
    reader.releaseLock();
  }
}
export function createTutorEventsClient(fetcher: typeof fetch = fetch) {
  return async function* events(runId: string, afterSeq = 0, signal?: AbortSignal): AsyncGenerator<TutorSSEEvent> {
    identity(runId); integer(afterSeq);
    const client = createApiClient(async (path, init, kind) => {
      if (kind !== 'sse') return fail();
      const response = await fetcher(path, { ...init, credentials: 'same-origin', cache: 'no-store', signal,
        headers: { ...init.headers, Accept: 'text/event-stream' } });
      if (!response.ok) throw new TutorStreamHTTPError(response.status);
      if (response.headers.get('Content-Type')?.split(';', 1)[0].trim().toLowerCase() !== 'text/event-stream'
          || !response.body) return fail();
      return decodeTutorEvents(response.body, runId, afterSeq);
    });
    yield* await client('GET /api/v1/runs/{id}/events', undefined, {}, {
      path: { id: runId }, query: { after_seq: afterSeq },
    });
  };
}
