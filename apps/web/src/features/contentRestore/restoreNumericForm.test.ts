import { expect, test } from 'vitest'
import { blankRestoreNumericForm, enteredFiniteNumber, enteredSpan, restoreNumericFormMaterial, selectedSourceSpan } from './restoreNumericForm'
import { numericMaterial, numericSnapshot, numericText } from './restoreNumericFixtures'
import { numericFormFixture } from './restoreNumericFormFixtures'

test('manual finite arithmetic fields preserve the exact authored plan and original codepoint spans', () => {
  expect(restoreNumericFormMaterial(numericFormFixture(), numericSnapshot)).toEqual(numericMaterial)
  expect(() => restoreNumericFormMaterial(blankRestoreNumericForm(), numericSnapshot)).toThrow()
})
test.each(['', ' ', ' 2', '2 ', '+2', '02', 'NaN', 'Infinity', '1e9999', '2%', '2 kg', '\\frac{1}{2}', 'true'])('invalid finite input %j is never coerced into a default number', raw => expect(() => enteredFiniteNumber(raw)).toThrow())
test.each(['0', '-0', '2.5', '-2e-2', '1E+2'])('valid explicitly entered finite input %j is accepted', raw => expect(enteredFiniteNumber(raw)).toBe(Number(raw)))
test.each(['', '-1', '1.5', ' 1', '01', 'Infinity', '9007199254740992'])('bad original position %j is refused', start => expect(() => enteredSpan({ start, end: '3', quote: '2' })).toThrow())
test('explicit text selection counts Unicode codepoints without normalizing original text', () => {
  const start = numericText.indexOf('e\u0301'), quote = 'e\u0301'
  expect(selectedSourceSpan(numericText, start, start + quote.length)).toEqual({ start: String([...numericText.slice(0, start)].length), end: String([...numericText.slice(0, start)].length + 2), quote })
  expect(selectedSourceSpan(numericText, 0, 1)).toBeNull()
  expect(selectedSourceSpan(numericText, 1, 2)).toBeNull()
  expect(selectedSourceSpan(numericText, 0, 0)).toBeNull()
})
test('hand entered expectation must match its actual original decimal quote', () => {
  const form = numericFormFixture(); form.assertions[0].expected = '4'
  expect(() => restoreNumericFormMaterial(form, numericSnapshot)).toThrow()
})
