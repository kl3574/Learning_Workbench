import schemas from '../../../../../packages/contracts/generated/restore-numeric-schemas.json'
import type { ApprovalDecision, ContentRestoreDraftSnapshot, NumericCheckDecisionAck } from '../../../../../packages/contracts/generated/api-types'
import type { NumericPlan, RestoreNumericCheckPreviewWrite, RestoreNumericCheckView, RestoreNumericMaterialWrite, RestoreNumericSourceSpan } from '../../../../../packages/contracts/generated/restore-numeric-types'
import { checkedProvider, sameValue } from '../providers/providerSchema'
import { canonical, digest } from '../retrieval/retrievalModel'
import { restoreSnapshot } from './restoreSchema'

type Shape = { $ref?: string; $defs?: Record<string, Shape>; type?: string; properties?: Record<string, Shape>; required?: string[];
  additionalProperties?: boolean; const?: unknown; enum?: unknown[]; anyOf?: Shape[]; oneOf?: Shape[]; items?: Shape;
  minItems?: number; maxItems?: number; minimum?: number; maximum?: number; exclusiveMinimum?: number; exclusiveMaximum?: number;
  minLength?: number; maxLength?: number; pattern?: string }
const generated = schemas as Record<string, Shape>
const invalid = (): never => { throw new Error('恢复数值记录、原文定位或原操作依据不一致；原件保留。') }

// This is a schema interpreter, not a second hand-maintained DTO. The named
// generated models are available before their actual HTTP registration.
function shapeCheck(shape: Shape, value: unknown, definitions: Record<string, Shape>, depth = 0): void {
  if (depth > 40) invalid()
  if (shape.$ref) {
    const next = definitions[shape.$ref.split('/').at(-1)!]
    if (!next) invalid()
    shapeCheck(next, value, definitions, depth + 1); return
  }
  if (shape.anyOf || shape.oneOf) {
    const matches = (shape.anyOf ?? shape.oneOf ?? []).filter(choice => {
      try { shapeCheck(choice, value, definitions, depth + 1); return true } catch { return false }
    }).length
    if (!matches || shape.oneOf && matches !== 1) invalid()
    return
  }
  if ('const' in shape && value !== shape.const || shape.enum && !shape.enum.includes(value)) invalid()
  switch (shape.type) {
    case 'null': if (value !== null) invalid(); return
    case 'boolean': if (typeof value !== 'boolean') invalid(); return
    case 'integer':
    case 'number': {
      if (typeof value !== 'number' || !Number.isFinite(value) || shape.type === 'integer' && !Number.isSafeInteger(value)) invalid()
      const number = value as number
      if (shape.minimum !== undefined && number < shape.minimum || shape.maximum !== undefined && number > shape.maximum
          || shape.exclusiveMinimum !== undefined && number <= shape.exclusiveMinimum || shape.exclusiveMaximum !== undefined && number >= shape.exclusiveMaximum) invalid()
      return
    }
    case 'string': {
      if (typeof value !== 'string') invalid()
      const text = value as string, length = [...text].length, match = shape.pattern ? new RegExp(shape.pattern, 'u').exec(text) : null
      if (new TextDecoder().decode(new TextEncoder().encode(text)) !== text
          || shape.minLength !== undefined && (length < shape.minLength || shape.minLength > 0 && !text.trim())
          || shape.maxLength !== undefined && length > shape.maxLength
          || shape.pattern && (!match || match[0].length !== text.length)) invalid()
      return
    }
    case 'array': {
      if (!Array.isArray(value) || !shape.items) invalid()
      const items = value as unknown[]
      if (shape.minItems !== undefined && items.length < shape.minItems || shape.maxItems !== undefined && items.length > shape.maxItems) invalid()
      items.forEach(item => shapeCheck(shape.items!, item, definitions, depth + 1)); return
    }
    case 'object': {
      if (!value || typeof value !== 'object' || Array.isArray(value) || shape.additionalProperties !== false) invalid()
      const record = value as Record<string, unknown>, properties = shape.properties ?? {}
      if (shape.required?.some(name => !Object.hasOwn(record, name))) invalid()
      for (const [name, item] of Object.entries(record)) {
        if (!Object.hasOwn(properties, name)) invalid()
        shapeCheck(properties[name], item, definitions, depth + 1)
      }
      return
    }
    default: invalid()
  }
}
export function checkedRestoreNumeric<T>(name: string, raw: unknown): T {
  const shape = generated[name]
  if (!shape) invalid()
  shapeCheck(shape, raw, { ...generated, ...shape.$defs })
  return structuredClone(raw) as T
}
function unique(values: string[]): void { if (new Set(values).size !== values.length) invalid() }
function planRelations(plan: NumericPlan): void {
  unique(plan.variables.map(value => value.name)); unique(plan.assertions.map(value => value.id))
}
function spanRelations(span: RestoreNumericSourceSpan, text?: string[]): void {
  if (span.end_codepoint <= span.start_codepoint || span.end_codepoint - span.start_codepoint > 512) invalid()
  if (text && (span.end_codepoint > text.length || text.slice(span.start_codepoint, span.end_codepoint).join('') !== span.quote)) invalid()
}
const decimal = (text: string): number => {
  if (!/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$/.test(text) || text.trim() !== text || !Number.isFinite(Number(text))) invalid()
  return Number(text)
}
export function restoreNumericMaterial(raw: unknown, snapshot?: ContentRestoreDraftSnapshot): RestoreNumericMaterialWrite {
  const value = checkedRestoreNumeric<RestoreNumericMaterialWrite>('RestoreNumericMaterialWrite', raw)
  planRelations(value.plan)
  const names = value.symbols.map(symbol => symbol.name), variableNames = value.plan.variables.map(variable => variable.name)
  unique(names); unique(value.variable_bindings.map(binding => binding.variable_name)); unique(value.assertion_bindings.map(binding => binding.assertion_id))
  if (variableNames.some(name => !names.includes(name)) || value.variable_bindings.length !== variableNames.length
      || value.variable_bindings.some(binding => !variableNames.includes(binding.variable_name))
      || value.assertion_bindings.length !== value.plan.assertions.length
      || value.assertion_bindings.some(binding => !value.plan.assertions.some(assertion => assertion.id === binding.assertion_id))) invalid()
  const text = snapshot ? [...snapshot.body_markdown] : undefined
  if (snapshot && (snapshot.owner !== 'authoring_restore' || snapshot.proposed_block.kind !== 'worked_example')) invalid()
  value.variable_bindings.forEach(binding => {
    spanRelations(binding.value_source, text)
    if (text && decimal(binding.value_source.quote) !== value.plan.variables.find(variable => variable.name === binding.variable_name)!.value) invalid()
  })
  value.assertion_bindings.forEach(binding => {
    spanRelations(binding.expression_source, text); spanRelations(binding.expected_source, text)
    if (text && decimal(binding.expected_source.quote) !== value.plan.assertions.find(assertion => assertion.id === binding.assertion_id)!.expected) invalid()
  })
  return value
}
export function restoreNumericSnapshot(raw: unknown, id?: string): ContentRestoreDraftSnapshot {
  const value = restoreSnapshot(raw, id), material = value.numeric_material
  unique(value.numeric_check_ids)
  if ((material !== null) !== (value.numeric_check_ids.length > 0)) invalid()
  if (material) {
    checkedRestoreNumeric('RestoreNumericMaterialView', material)
    if (!sameValue(material.candidate, value.candidate) || !sameValue(material.source_ref, value.source_ref)
        || material.body_sha256 !== value.proposed_block.body_sha256 || material.source_material_sha256 !== value.source_material_sha256) invalid()
    restoreNumericMaterial(material.material, value)
  }
  return value
}
export function restoreNumericCheck(raw: unknown, id?: string, snapshot?: ContentRestoreDraftSnapshot): RestoreNumericCheckView {
  const value = checkedRestoreNumeric<RestoreNumericCheckView>('RestoreNumericCheckView', raw)
  planRelations(value.plan)
  const created = Date.parse(value.created_at), expires = Date.parse(value.expires_at)
  if (id && value.id !== id || !Number.isFinite(created) || !Number.isFinite(expires) || expires - created !== 600_000
      || value.revision !== (value.decision === 'pending' ? 1 : 2)
      || (value.job !== null) !== (value.decision === 'approve_once') || (value.job_revision !== null) !== (value.decision === 'approve_once')) invalid()
  if (snapshot) {
    const current = restoreNumericSnapshot(snapshot), material = current.numeric_material
    if (!material || !current.numeric_check_ids.includes(value.id) || !sameValue(value.candidate, current.candidate)
        || material.numeric_material_sha256 !== value.numeric_material_sha256 || !sameValue(value.plan, material.material.plan)) invalid()
  }
  const result = value.result, job = value.job
  if (!result) { if (job && ['completed', 'failed', 'cancelled'].includes(job.status)) invalid(); return value }
  const completed = ['passed', 'mismatch', 'evaluation_error'].includes(result.outcome)
  const status = completed ? 'completed' : result.outcome === 'cancelled' ? 'cancelled' : 'failed'
  const verdict = result.outcome === 'passed' ? 'PASS' : completed ? 'FAIL' : 'BLOCKED'
  const { result_sha256: resultHash, ...facts } = result
  if (!job || job.id !== result.job_id || job.status !== status || value.operation_sha256 !== result.operation_sha256
      || result.verdict !== verdict || digest(canonical(facts)) !== resultHash
      || result.started_at !== null && Date.parse(result.started_at) > Date.parse(result.finished_at)) invalid()
  unique(result.assertions.map(assertion => assertion.id))
  const passing = result.assertions.every(assertion => assertion.passed), errors = result.assertions.some(assertion => assertion.error_code !== null)
  if (completed && (!result.started_at || !sameValue(result.assertions.map(assertion => assertion.id), value.plan.assertions.map(assertion => assertion.id))
      || result.outcome === 'passed' && (!passing || result.exit_code !== 0 || !result.output_sha256)
      || result.outcome === 'mismatch' && (passing || errors) || result.outcome === 'evaluation_error' && !errors)) invalid()
  result.assertions.forEach(assertion => {
    const expected = value.plan.assertions.find(item => item.id === assertion.id)
    if (!expected || assertion.error_code !== null && (assertion.actual !== null || assertion.passed)
        || assertion.error_code === null && assertion.actual === null) invalid()
    if (assertion.actual !== null) {
      const difference = Math.abs(assertion.actual - expected!.expected), product = expected!.rtol * Math.abs(expected!.expected), tolerance = expected!.atol + product
      if (![difference, product, tolerance].every(Number.isFinite) || assertion.passed !== (difference <= tolerance)) invalid()
    }
  })
  return value
}
export function restoreNumericPreviewAck(raw: unknown, body: RestoreNumericCheckPreviewWrite): RestoreNumericCheckView {
  const value = restoreNumericCheck(raw)
  if (!sameValue(value.candidate, body.candidate) || !sameValue(value.plan, body.material.plan) || value.revision !== 1
      || value.decision !== 'pending' || value.job !== null || value.job_revision !== null || value.result !== null || value.expired) invalid()
  return value
}
export function restoreNumericDecisionAck(raw: unknown, id: string, body: ApprovalDecision): NumericCheckDecisionAck {
  const value = checkedProvider<NumericCheckDecisionAck>('NumericCheckDecisionAck', raw)
  if (value.id !== id || value.operation_sha256 !== body.operation_sha256 || value.decision !== body.decision
      || value.revision !== body.expected_revision + 1 || value.revision !== 2 || (value.job !== null) !== (value.decision === 'approve_once')
      || value.job !== null && value.job.status !== 'queued') invalid()
  return value
}
