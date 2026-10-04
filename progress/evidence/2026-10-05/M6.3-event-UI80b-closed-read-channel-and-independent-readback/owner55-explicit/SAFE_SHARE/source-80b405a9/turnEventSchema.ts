import type { CodexTurnEvent } from '../../../../../packages/contracts/generated/codex-turn-types'
import generated from '../../../../../packages/contracts/generated/codex-turn-schemas.json'

type Shape = { $ref?: string; type?: string; const?: unknown; enum?: unknown[]; anyOf?: Shape[]; oneOf?: Shape[];
 properties?: Record<string, Shape>; required?: string[]; additionalProperties?: boolean;
 minLength?: number; pattern?: string; minimum?: number }
const schema = generated.schemas.CodexTurnEvent, definitions: Record<string, Shape> = schema.$defs
const invalid = (): never => { throw new Error('Codex 事件不符合已生成的闭合契约。') }
/** Codex event strings are raw Unicode, including whitespace-only deltas. */
function check(shape: Shape, value: unknown, depth = 0): void {
 if (depth > 20) invalid()
 if (shape.$ref) { const target = definitions[shape.$ref.split('/').at(-1)!]; if (!target) invalid(); return check(target, value, depth + 1) }
 if (shape.anyOf || shape.oneOf) {
  let matches = 0
  for (const arm of shape.anyOf ?? shape.oneOf ?? []) { try { check(arm, value, depth + 1); matches++ } catch { /* Closed arm did not match. */ } }
  if (!matches || shape.oneOf && matches !== 1) invalid()
  return
 }
 if ('const' in shape && value !== shape.const || shape.enum && !shape.enum.includes(value)) invalid()
 switch (shape.type) {
  case 'null': if (value !== null) invalid(); return
  case 'integer':
   if (typeof value !== 'number' || !Number.isSafeInteger(value) || shape.minimum !== undefined && value < shape.minimum) invalid()
   return
  case 'string':
   if (typeof value !== 'string' || new TextDecoder().decode(new TextEncoder().encode(value)) !== value
    || shape.minLength !== undefined && Array.from(value).length < shape.minLength || shape.pattern && !new RegExp(shape.pattern).test(value)) invalid()
   return
  case 'object': {
   if (!value || typeof value !== 'object' || Array.isArray(value) || shape.additionalProperties !== false) invalid()
   const object = value as Record<string, unknown>, properties = shape.properties ?? {}
   if (shape.required?.some(key => !Object.hasOwn(object, key))) invalid()
   for (const [key, item] of Object.entries(object)) { if (!Object.hasOwn(properties, key)) invalid(); check(properties[key], item, depth + 1) }
   return
  }
  default: invalid()
 }
}
export function checkedCodexEvent(raw: unknown): CodexTurnEvent {
 check(schema, raw)
 const value = structuredClone(raw) as CodexTurnEvent
 const match = /^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.\d+)?Z$/.exec(value.occurred_at)
 const millis = Date.parse(match?.[1] + 'Z')
 if (!match || value.occurred_at.startsWith('0000') || !Number.isFinite(millis) || new Date(millis).toISOString().slice(0, 19) !== match[1]
  || value.payload.type === 'status' && value.payload.job.id !== value.run_id
  || value.payload.type === 'terminal' && value.payload.outcome === 'completed' && value.payload.error_code !== null) invalid()
 return value
}
