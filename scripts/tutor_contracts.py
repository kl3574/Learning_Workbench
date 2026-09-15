"""Generate Tutor binding/strict stream codec only from registered operations."""
import json
import re

from scripts.schema_types import generate_types

OPERATIONS = {
    ('/api/v1/threads', 'post'): ('TutorThreadCreate', 'TutorThreadView', '201'),
    ('/api/v1/threads', 'get'): (None, 'TutorThreadPage', '200'),
    ('/api/v1/threads/{id}/messages', 'get'): (None, 'TutorMessagePage', '200'),
    ('/api/v1/tutor/runs', 'post'): ('TutorRunCreate', 'TutorRunView', '202'),
    ('/api/v1/runs/{id}', 'get'): (None, 'TutorRunView', '200'),
    ('/api/v1/runs/{id}/cancel', 'post'): ('TutorRunCancel', 'TutorRunControlView', '200'),
    ('/api/v1/runs/{id}/events', 'get'): (None, 'TutorSSEEvent', '200'),
}

CODEC = r'''
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
'''


def tutor_artifacts(ports: str, openapi: dict, provenance: dict[str, str]) -> dict[str, str]:
    marker = 'export interface TutorApplicationDTOMap {'
    if ports.count(marker) != 1:
        raise ValueError('Tutor application map must be declared once')
    names = re.findall(r'\b(\w+): unknown;', ports.split(marker, 1)[1].split('}', 1)[0])
    query_names = {'TutorPageQuery', 'TutorEventsQuery'}
    wanted = {name for request, response, _ in OPERATIONS.values() for name in (request, response) if name} | query_names
    if len(names) != len(set(names)) or set(names) != wanted:
        raise ValueError('Tutor map must bind all seven actual operations and strict scalar queries')
    from services.api.app.tutor_dto import TUTOR_EVENT_ADAPTER
    expected_events = TUTOR_EVENT_ADAPTER.json_schema(ref_template='#/components/schemas/{model}')
    expected_events.pop('$defs', None)
    expected_events['type'] = 'object'
    schemas = openapi.get('components', {}).get('schemas', {})
    for (path, method), (request, response, code) in OPERATIONS.items():
        operation = openapi.get('paths', {}).get(path, {}).get(method)
        if operation is None:
            raise ValueError('Tutor binding requires all seven actual registered operations')
        content = operation['responses'].get(code, {}).get('content', {})
        if response == 'TutorSSEEvent':
            if set(content) != {'text/event-stream'}:
                raise ValueError('Tutor events require the real SSE transport')
            event_schema = content['text/event-stream']['schema']
            if event_schema.get('type') != 'object' or event_schema.get('discriminator', {}).get('propertyName') != 'type':
                raise ValueError('SSE decoded data must bind a strict discriminated event object')
            event_names = [item['$ref'].rsplit('/', 1)[1] for item in event_schema['oneOf']]
            if event_schema != expected_events or len(event_names) != 10 or len(set(event_names)) != 10:
                raise ValueError('Tutor SSE requires its ten closed event branches')
        elif content != {'application/json': {'schema': {'$ref': '#/components/schemas/' + response}}}:
            raise ValueError('Tutor response media type or named DTO differs from the actual contract')
        if {status for status in operation['responses'] if status.startswith('2')} != {code}:
            raise ValueError('Tutor successful status must match the declared operation')
        parameters = operation.get('parameters', [])
        identifiers = [(p.get('in'), p.get('name', '').lower()) for p in parameters]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError('Tutor parameters cannot repeat')
        headers = {p['name'].lower(): p for p in parameters if p.get('in') == 'header'}
        queries = {p['name']: p for p in parameters if p.get('in') == 'query'}
        expected_query = ({'cursor', 'limit'} if response in {'TutorThreadPage', 'TutorMessagePage'}
                          else {'after_seq'} if response == 'TutorSSEEvent' else set())
        if set(queries) != expected_query or any(p.get('required') for p in queries.values()):
            raise ValueError('Tutor query fields must match their actual scalar application contract')
        if 'limit' in queries and queries['limit'].get('schema') != {
                'type': 'integer', 'minimum': 1, 'maximum': 100, 'default': 20}:
            raise ValueError('Tutor pagination must keep its exact declared bound')
        if 'cursor' in queries and queries['cursor'].get('schema') != {'type': 'string', 'minLength': 1}:
            raise ValueError('Tutor page cursor is an optional non-null string')
        if 'after_seq' in queries and queries['after_seq'].get('schema') != {
                'type': 'integer', 'minimum': 0, 'default': 0}:
            raise ValueError('Tutor event cursor must retain its integer contract')
        if method == 'post':
            if any(headers.get(name, {}).get('required') is not True for name in ('origin', 'x-csrf-token')):
                raise ValueError('Tutor mutation requires real Origin/CSRF dependencies')
            key = headers.get('idempotency-key', {})
            if key.get('required') is not True or key.get('schema') != {
                    'type': 'string', 'pattern': '^[A-Za-z0-9_-]{1,128}$'}:
                raise ValueError('Tutor mutations require the declared original command key')
        elif 'idempotency-key' in headers:
            raise ValueError('Tutor read cannot acquire a mutation key')
        if response == 'TutorSSEEvent':
            last = headers.get('last-event-id', {})
            if last.get('required') is not False or last.get('schema') != {
                    'type': 'string', 'pattern': '^[A-Za-z][A-Za-z0-9_-]{0,79}:[0-9]+$'}:
                raise ValueError('Tutor Last-Event-ID must preserve its explicit matching contract')
        if operation.get('security') != [{'LocalSession': []}]:
            raise ValueError('Tutor operation requires its actual authenticated session dependency')
        if request is None:
            if 'requestBody' in operation:
                raise ValueError('Tutor reads are bodyless')
        elif operation.get('requestBody') != {'required': True, 'content': {
            'application/json': {'schema': {'$ref': '#/components/schemas/' + request}}}}:
            raise ValueError('Tutor writes require their actual strict body')
    for name in (wanted - query_names - {'TutorSSEEvent'}) | set(event_names):
        if schemas.get(name, {}).get('additionalProperties') is not False:
            raise ValueError('Tutor business objects must be closed actual OpenAPI components')
    event_types = ' | '.join('Api.' + name for name in event_names)
    header = '// Generated from PRODUCT_DESIGN.md v' + provenance['spec_version'] + '; do not edit.\n'
    header += '// spec_sha256: ' + provenance['spec_sha256'] + '\n'
    # The URL query DTOs are derived from the actual handler's scalar declarations
    # and their separately validated application classes, not fake HTTP bodies.
    from services.api.app.tutor_dto import TutorEventsQuery, TutorPageQuery
    query_types = generate_types({model.__name__: model.model_json_schema()
                                  for model in (TutorEventsQuery, TutorPageQuery)}, provenance)
    binding = [header, 'import type { TutorApplicationDTOMap } from "../module-ports";',
               'import type * as Api from "./api-types";',
               'import type { TutorSSEEvent } from "./tutor-sse";',
               'export type { TutorSSEEvent } from "./tutor-sse";', query_types,
               'export interface TutorRuntimeDTOMap extends TutorApplicationDTOMap {']
    binding.extend('  ' + name + ': ' + (name if name in query_names | {'TutorSSEEvent'} else 'Api.' + name) + ';'
                   for name in names)
    binding.append('}')
    # Only schemas reachable from the actual event response are emitted into the
    # runtime decoder; no private preparation/Provider bodies are exposed.
    selected: dict = {}
    def visit(value: object) -> None:
        if isinstance(value, dict):
            reference = value.get('$ref')
            if isinstance(reference, str):
                name = reference.rsplit('/', 1)[1]
                if name not in selected:
                    selected[name] = schemas[name]
                    visit(schemas[name])
            for item in value.values():
                visit(item)
        elif isinstance(value, list):
            for item in value:
                visit(item)
    visit(event_schema)
    codec = (header + 'import type * as Api from "./api-types";\n'
             + 'import { createApiClient } from "./api-client";\n'
             + 'export type TutorSSEEvent = ' + event_types + ';\n'
             + 'const SCHEMAS: Record<string, Schema> = ' + json.dumps(selected, ensure_ascii=False) + ';\n'
             + 'const EVENT_SCHEMA: Schema = ' + json.dumps(event_schema, ensure_ascii=False) + ';\n' + CODEC)
    return {'tutor-ports-binding.ts': '\n'.join(binding) + '\n', 'tutor-sse.ts': codec}
