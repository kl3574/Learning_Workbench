import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { RestoreNumericMaterialEditor } from './RestoreNumericMaterialEditor'
import { numericFormFixture } from './restoreNumericFormFixtures'

afterEach(cleanup)
const select = (body: string, start: number, end: number) => {
  const change = vi.fn()
  render(<RestoreNumericMaterialEditor body={body} value={numericFormFixture()} disabled={false} change={change} />)
  const input = screen.getByRole('textbox', { name: '本恢复候选的完整原正文' }) as HTMLTextAreaElement
  input.focus(); input.setSelectionRange(start, end); fireEvent.select(input)
  return { change, input, button: screen.getByRole('button', { name: '将明确选中的原文用于变量 1 的数值出处' }) as HTMLButtonElement }
}
test.each([
  ['CRLF after astral and combining', '🧮 原文 e\u0301\r\nGiven x=2', '2', '2'],
  ['lone CR', '🧮\rGiven x=2', '2', '2'],
  ['mixed CRLF and lone CR before target', '🧮\r\nline\rGiven x=2', '2', '2'],
  ['span across CRLF', '🧮 e\u0301\r\nx+1\r\n=3', 'e\u0301\nx+1\n', 'e\u0301\r\nx+1\r\n'],
  ['span across lone CR', '🧮 e\u0301\rx+1\r=3', 'e\u0301\nx+1\n', 'e\u0301\rx+1\r'],
  ['span beginning and ending exactly on CRLF', 'a\r\nb', '\n', '\r\n'],
  ['span beginning and ending exactly on CR', 'a\rb', '\n', '\r'],
  ['astral quote after CRLF', 'e\u0301\r\n🧮2', '🧮', '🧮'],
  ['combining pair after CRLF', '🧮\r\ne\u0301=2', 'e\u0301', 'e\u0301'],
  ['individual combining codepoint preserved', '🧮\r\ne\u0301=2', '\u0301', '\u0301'],
])('independent extended exact DOM-to-original mapping: %s', (_label, body, shown, quote) => {
  const domBody = body.replace(/\r\n?/g, '\n'), start = domBody.indexOf(shown), f = select(body, start, start + shown.length)
  expect(f.input.value.slice(f.input.selectionStart, f.input.selectionEnd)).toBe(shown)
  expect(f.button.disabled).toBe(false); fireEvent.click(f.button)
  const originalStart = [...body.slice(0, body.indexOf(quote))].length
  expect(f.change.mock.lastCall?.[0].variables[0].source).toEqual({ start: String(originalStart), end: String(originalStart + [...quote].length), quote })
})
test.each([
  ['empty', 'a\r\nb', 2, 2],
  ['high surrogate only', '🧮\r\n2', 0, 1],
  ['low surrogate only', '🧮\r\n2', 1, 2],
  ['over 512 original codepoints after LF normalization', ('a\r\n').repeat(171), 0, 342],
])('independent extended rejected selection: %s', (_label, body, start, end) => {
  const f = select(body as string, start as number, end as number)
  expect(f.button.disabled).toBe(true); fireEvent.click(f.button); expect(f.change).not.toHaveBeenCalled()
})
