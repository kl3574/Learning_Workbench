import type { RestoreNumericForm } from './restoreNumericForm'
import { numericMaterial } from './restoreNumericFixtures'

export function numericFormFixture(): RestoreNumericForm {
  const span = (value: typeof numericMaterial.variable_bindings[number]['value_source']) => ({ start: String(value.start_codepoint), end: String(value.end_codepoint), quote: value.quote })
  return { symbols: structuredClone(numericMaterial.symbols), variables: numericMaterial.plan.variables.map((item, i) => ({ ...item, value: String(item.value), source: span(numericMaterial.variable_bindings[i].value_source) })),
    assertions: numericMaterial.plan.assertions.map((item, i) => ({ ...item, expected: String(item.expected), atol: String(item.atol), rtol: String(item.rtol), expressionSource: span(numericMaterial.assertion_bindings[i].expression_source), expectedSource: span(numericMaterial.assertion_bindings[i].expected_source) })), reason: numericMaterial.reason, confirmed: true }
}
