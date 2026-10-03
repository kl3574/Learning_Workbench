import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { RestoreNumericMaterialEditor } from './RestoreNumericMaterialEditor'
import { numericFormFixture } from './restoreNumericFormFixtures'

afterEach(cleanup)
test.each(['\n', '\r\n', '\r'])('independent real textarea selection maps its normalized DOM offsets back to original %j source codepoints', newline => {
  const body = `🧮 原文 e\u0301${newline}Given x=2, formula x+1 has expected 3.`, change = vi.fn()
  render(<RestoreNumericMaterialEditor body={body} value={numericFormFixture()} disabled={false} change={change} />)
  const input = screen.getByRole('textbox', { name: '本恢复候选的完整原正文' }) as HTMLTextAreaElement
  input.focus(); const visibleStart = input.value.indexOf('2'); input.setSelectionRange(visibleStart, visibleStart + 1); fireEvent.select(input)
  expect(input.value.slice(input.selectionStart, input.selectionEnd)).toBe('2')
  fireEvent.click(screen.getByRole('button', { name: '将明确选中的原文用于变量 1 的数值出处' }))
  const originalStart = [...body.slice(0, body.indexOf('2'))].length
  expect(change.mock.lastCall?.[0].variables[0].source).toEqual({ start: String(originalStart), end: String(originalStart + 1), quote: '2' })
})
