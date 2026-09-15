import openapi from '../../../../../packages/contracts/generated/openapi.json'

type Shape = {
  $ref?: string; type?: string; properties?: Record<string, Shape>; required?: string[]
  additionalProperties?: boolean | Shape; const?: unknown; enum?: unknown[]
  anyOf?: Shape[]; oneOf?: Shape[]; items?: Shape; minItems?: number; maxItems?: number
  minimum?: number; maximum?: number; exclusiveMinimum?: number; exclusiveMaximum?: number
  minLength?: number; maxLength?: number; pattern?: string
}
const definitions = openapi.components.schemas as Record<string, Shape>
const fail = (): never => { throw new Error('检索记录不符合当前生成契约；未采用响应。') }
function check(shape: Shape, value: unknown, depth = 0): void {
  if (depth > 40) fail()
  if (shape.$ref) { const next = definitions[shape.$ref.split('/').at(-1)!]; if (!next) fail(); check(next, value, depth + 1); return }
  if (shape.anyOf || shape.oneOf) {
    let matches = 0
    for (const choice of shape.anyOf ?? shape.oneOf ?? []) { try { check(choice, value, depth + 1); matches++ } catch { /* Only a complete union arm qualifies. */ } }
    if (!matches || shape.oneOf && matches !== 1) fail()
    return
  }
  if ('const' in shape && value !== shape.const || shape.enum && !shape.enum.includes(value)) fail()
  switch (shape.type) {
    case 'null': if (value !== null) fail(); return
    case 'boolean': if (typeof value !== 'boolean') fail(); return
    case 'integer':
    case 'number': {
      if (typeof value !== 'number' || !Number.isFinite(value) || shape.type === 'integer' && !Number.isSafeInteger(value)) fail()
      const number = value as number
      if (shape.minimum !== undefined && number < shape.minimum || shape.maximum !== undefined && number > shape.maximum || shape.exclusiveMinimum !== undefined && number <= shape.exclusiveMinimum || shape.exclusiveMaximum !== undefined && number >= shape.exclusiveMaximum) fail()
      return
    }
    case 'string': {
      if (typeof value !== 'string') fail()
      const text = value as string, length = Array.from(text).length
      if (new TextDecoder().decode(new TextEncoder().encode(text)) !== text || shape.minLength !== undefined && (length < shape.minLength || shape.minLength > 0 && !text.trim()) || shape.maxLength !== undefined && length > shape.maxLength || shape.pattern && !new RegExp(shape.pattern).test(text)) fail()
      return
    }
    case 'array': {
      if (!Array.isArray(value) || !shape.items) fail()
      const array = value as unknown[]
      if (shape.minItems !== undefined && array.length < shape.minItems || shape.maxItems !== undefined && array.length > shape.maxItems) fail()
      array.forEach(item => check(shape.items!, item, depth + 1)); return
    }
    case 'object': {
      if (!value || typeof value !== 'object' || Array.isArray(value)) fail()
      const record = value as Record<string, unknown>, properties = shape.properties ?? {}
      if (shape.required?.some(key => !(key in record))) fail()
      for (const [key, item] of Object.entries(record)) {
        if (properties[key]) check(properties[key], item, depth + 1)
        else if (typeof shape.additionalProperties === 'object') check(shape.additionalProperties, item, depth + 1)
        else fail()
      }
      return
    }
    default: fail()
  }
}
/** Wire shape only. Hash/proof/source truth is verified by the owning server. */
export function checkedShape<T>(name: string, value: unknown): T {
  const schema = definitions[name]
  if (!schema) throw new Error('检索契约尚未生成，未猜测响应类型。')
  check(schema, value)
  return structuredClone(value) as T
}
