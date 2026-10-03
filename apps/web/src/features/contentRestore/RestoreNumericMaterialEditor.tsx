import { useState } from 'react'
import type { RestoreNumericForm, SpanFields } from './restoreNumericForm'
import { blankAssertion, blankSymbol, blankVariable, selectedSourceSpan } from './restoreNumericForm'

function SourceFields({ label, value, selected, disabled, change }: { label: string; value: SpanFields; selected: SpanFields | null; disabled: boolean; change: (value: SpanFields) => void }) {
  return <fieldset><legend>{label}</legend><p>码点位置从 0 开始，终点不包含在片段内；必须逐字对应下面的原正文。</p>
    <label>起点<input inputMode="numeric" disabled={disabled} value={value.start} onChange={event => change({ ...value, start: event.target.value })} /></label>
    <label>终点<input inputMode="numeric" disabled={disabled} value={value.end} onChange={event => change({ ...value, end: event.target.value })} /></label>
    <label>原文片段<textarea disabled={disabled} value={value.quote} onChange={event => change({ ...value, quote: event.target.value })} /></label>
    <button disabled={disabled || !selected} onClick={() => { if (selected) change({ ...selected }) }}>将明确选中的原文用于{label}</button>
  </fieldset>
}
export function RestoreNumericMaterialEditor({ body, value, disabled, change }: { body: string; value: RestoreNumericForm; disabled: boolean; change: (value: RestoreNumericForm) => void }) {
  const [selected, setSelected] = useState<SpanFields | null>(null)
  const update = (next: RestoreNumericForm) => change({ ...next, confirmed: false })
  return <section aria-label="手工提供恢复例题数值材料"><h4>手工提供本次有限算术材料</h4>
    <p>逐项填写变量、表达式、期望值与容差，并明确选择或填写原文定位。不会从历史正文抽取计划或继承旧批准。无法核验十进制输入或期望值时保留阻断。</p>
    <label>本恢复候选的完整原正文<textarea readOnly rows={10} value={body} onSelect={event => setSelected(selectedSourceSpan(body, event.currentTarget.selectionStart, event.currentTarget.selectionEnd))} /></label>
    {selected && <p>当前明确选中：[{selected.start}, {selected.end}) · <code>{selected.quote}</code></p>}
    <fieldset><legend>符号声明</legend>{value.symbols.map((symbol, index) => <fieldset key={index}><legend>符号 {index + 1}</legend>
      {(['name', 'tex', 'domain', 'dimension'] as const).map((field, fieldIndex) => <label key={field}>{['变量名', 'LaTeX 记号', '取值域', '量纲说明'][fieldIndex]}<input disabled={disabled} value={symbol[field]} onChange={event => update({ ...value, symbols: value.symbols.map((item, i) => i === index ? { ...item, [field]: event.target.value } : item) })} /></label>)}
      <button disabled={disabled} onClick={() => update({ ...value, symbols: value.symbols.filter((_, i) => i !== index) })}>移除符号 {index + 1}</button>
    </fieldset>)}<button disabled={disabled || value.symbols.length >= 64} onClick={() => update({ ...value, symbols: [...value.symbols, blankSymbol()] })}>添加符号</button></fieldset>
    <fieldset><legend>本次数值输入</legend>{value.variables.map((variable, index) => <fieldset key={index}><legend>变量 {index + 1}</legend>
      {(['name', 'value', 'unit'] as const).map((field, fieldIndex) => <label key={field}>{['变量名', '明确输入值', '单位标签'][fieldIndex]}<input disabled={disabled} value={variable[field]} onChange={event => update({ ...value, variables: value.variables.map((item, i) => i === index ? { ...item, [field]: event.target.value } : item) })} /></label>)}
      <SourceFields label={`变量 ${index + 1} 的数值出处`} value={variable.source} selected={selected} disabled={disabled} change={source => update({ ...value, variables: value.variables.map((item, i) => i === index ? { ...item, source } : item) })} />
      <button disabled={disabled} onClick={() => update({ ...value, variables: value.variables.filter((_, i) => i !== index) })}>移除变量 {index + 1}</button>
    </fieldset>)}<button disabled={disabled || value.variables.length >= 32} onClick={() => update({ ...value, variables: [...value.variables, blankVariable()] })}>添加数值变量</button></fieldset>
    <fieldset><legend>本次算术断言</legend>{value.assertions.map((assertion, index) => <fieldset key={index}><legend>断言 {index + 1}</legend>
      {(['id', 'expression', 'expected', 'atol', 'rtol', 'unit'] as const).map((field, fieldIndex) => <label key={field}>{['断言标识', '有限算术表达式', '明确期望值', '绝对容差', '相对容差', '单位标签'][fieldIndex]}<input disabled={disabled} value={assertion[field]} onChange={event => update({ ...value, assertions: value.assertions.map((item, i) => i === index ? { ...item, [field]: event.target.value } : item) })} /></label>)}
      <SourceFields label={`断言 ${index + 1} 的公式出处`} value={assertion.expressionSource} selected={selected} disabled={disabled} change={expressionSource => update({ ...value, assertions: value.assertions.map((item, i) => i === index ? { ...item, expressionSource } : item) })} />
      <SourceFields label={`断言 ${index + 1} 的期望值出处`} value={assertion.expectedSource} selected={selected} disabled={disabled} change={expectedSource => update({ ...value, assertions: value.assertions.map((item, i) => i === index ? { ...item, expectedSource } : item) })} />
      <button disabled={disabled} onClick={() => update({ ...value, assertions: value.assertions.filter((_, i) => i !== index) })}>移除断言 {index + 1}</button>
    </fieldset>)}<button disabled={disabled || value.assertions.length >= 32} onClick={() => update({ ...value, assertions: [...value.assertions, blankAssertion()] })}>添加算术断言</button></fieldset>
    <label>数值材料提供理由<textarea disabled={disabled} value={value.reason} onChange={event => update({ ...value, reason: event.target.value })} /></label>
    <label><input type="checkbox" disabled={disabled} checked={value.confirmed} onChange={event => change({ ...value, confirmed: event.target.checked })} />我已逐项提供并核对这份计划和原文定位，明确请求冻结预览；本次不批准执行。</label>
  </section>
}
