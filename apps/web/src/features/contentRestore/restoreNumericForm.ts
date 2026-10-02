import type { ContentRestoreDraftSnapshot } from '../../../../../packages/contracts/generated/api-types'
import type { RestoreNumericMaterialWrite, RestoreNumericSourceSpan, WorkedExampleSymbol } from '../../../../../packages/contracts/generated/restore-numeric-types'
import { restoreNumericMaterial } from './restoreNumericSchema'

export type SpanFields = { start: string; end: string; quote: string }
export type VariableFields = { name: string; value: string; unit: string; source: SpanFields }
export type AssertionFields = { id: string; expression: string; expected: string; atol: string; rtol: string; unit: string; expressionSource: SpanFields; expectedSource: SpanFields }
export type RestoreNumericForm = { symbols: WorkedExampleSymbol[]; variables: VariableFields[]; assertions: AssertionFields[]; reason: string; confirmed: boolean }
export const blankSpan = (): SpanFields => ({ start: '', end: '', quote: '' })
export const blankSymbol = (): WorkedExampleSymbol => ({ name: '', tex: '', domain: '', dimension: '' })
export const blankVariable = (): VariableFields => ({ name: '', value: '', unit: '', source: blankSpan() })
export const blankAssertion = (): AssertionFields => ({ id: '', expression: '', expected: '', atol: '', rtol: '', unit: '', expressionSource: blankSpan(), expectedSource: blankSpan() })
export const blankRestoreNumericForm = (): RestoreNumericForm => ({ symbols: [blankSymbol()], variables: [], assertions: [blankAssertion()], reason: '', confirmed: false })
export function enteredFiniteNumber(raw: string): number {
  if (!/^-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?$/.test(raw) || !Number.isFinite(Number(raw))) throw new Error('数值须为完整有限十进制字面量，不接受空白、单位或 LaTeX。')
  return Number(raw)
}
export function enteredSpan(value: SpanFields): RestoreNumericSourceSpan {
  if (![value.start, value.end].every(raw => /^(?:0|[1-9][0-9]*)$/.test(raw) && Number.isSafeInteger(Number(raw)))) throw new Error('原文定位须为明确填写的非负整数码点位置。')
  return { start_codepoint: Number(value.start), end_codepoint: Number(value.end), quote: value.quote }
}
export function restoreNumericFormMaterial(value: RestoreNumericForm, snapshot: ContentRestoreDraftSnapshot): RestoreNumericMaterialWrite {
  return restoreNumericMaterial({ version: 'restore-numeric-material-v1', symbols: value.symbols,
    plan: { version: 'finite-arithmetic-v1', seed: null,
      variables: value.variables.map(item => ({ name: item.name, value: enteredFiniteNumber(item.value), unit: item.unit })),
      assertions: value.assertions.map(item => ({ id: item.id, expression: item.expression, expected: enteredFiniteNumber(item.expected), atol: enteredFiniteNumber(item.atol), rtol: enteredFiniteNumber(item.rtol), unit: item.unit })) },
    variable_bindings: value.variables.map(item => ({ variable_name: item.name, value_source: enteredSpan(item.source) })),
    assertion_bindings: value.assertions.map(item => ({ assertion_id: item.id, expression_source: enteredSpan(item.expressionSource), expected_source: enteredSpan(item.expectedSource) })), reason: value.reason }, snapshot)
}

// A textarea reports UTF-16 offsets. Only an explicit user selection is copied;
// no values, formulas, plans or numerical permissions are inferred from it.
export function selectedSourceSpan(body: string, start: number, end: number): SpanFields | null {
  if (!Number.isInteger(start) || !Number.isInteger(end) || start < 0 || end <= start || end > body.length) return null
  const quote = body.slice(start, end)
  if (new TextDecoder().decode(new TextEncoder().encode(quote)) !== quote || [...quote].length > 512) return null
  return { start: String([...body.slice(0, start)].length), end: String([...body.slice(0, end)].length), quote }
}
