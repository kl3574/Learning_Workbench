import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { RestoreNumericMaterialEditor } from './RestoreNumericMaterialEditor'
import { numericFormFixture } from './restoreNumericFormFixtures'

afterEach(cleanup)
test.each(['\n', '\r\n', '\r', '\r\n\r\n', '\r\n\r\n\n'])('actual textarea selection preserves original codepoints after %j', newline => {
  const body = `🧮 原文 e\u0301${newline}Given x=2, formula x+1 has expected 3.`, change = vi.fn()
  render(<RestoreNumericMaterialEditor body={body} value={numericFormFixture()} disabled={false} change={change} />)
  const input = screen.getByRole('textbox', { name: '本恢复候选的完整原正文' }) as HTMLTextAreaElement
  input.focus(); const visibleStart = input.value.indexOf('2'); input.setSelectionRange(visibleStart, visibleStart + 1); fireEvent.select(input)
  expect(input.value.slice(input.selectionStart, input.selectionEnd)).toBe('2')
  fireEvent.click(screen.getByRole('button', { name: '将明确选中的原文用于变量 1 的数值出处' }))
  const originalStart = [...body.slice(0, body.indexOf('2'))].length
  expect(change.mock.lastCall?.[0].variables[0].source).toEqual({ start: String(originalStart), end: String(originalStart + 1), quote: '2' })
  expect(change.mock.lastCall?.[0].confirmed).toBe(false)
})
test('a selected formula spanning normalized line breaks retains the exact original quote', () => {
  const body = '🧮\r\nx +\r\n 1 = 3', change = vi.fn()
  render(<RestoreNumericMaterialEditor body={body} value={numericFormFixture()} disabled={false} change={change} />)
  const input = screen.getByRole('textbox', { name: '本恢复候选的完整原正文' }) as HTMLTextAreaElement
  input.focus(); input.setSelectionRange(input.value.indexOf('x'), input.value.indexOf(' =')); fireEvent.select(input)
  fireEvent.click(screen.getByRole('button', { name: '将明确选中的原文用于断言 1 的公式出处' }))
  expect(change.mock.lastCall?.[0].assertions[0].expressionSource).toEqual({ start: '3', end: '10', quote: 'x +\r\n 1' })
})
