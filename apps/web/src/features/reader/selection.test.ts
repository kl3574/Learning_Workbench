import { afterEach, describe, expect, it } from 'vitest'
import type { ContentRef } from '../../../../../packages/contracts/generated/types'
import { selectionFromDOM, selectionFromSource, type SelectionResult } from './selection'

const ref: ContentRef = { entity: 'block', id: 'block_selection', revision: 7, sha256: 'a'.repeat(64) }

afterEach(() => { document.body.replaceChildren(); window.getSelection()?.removeAllRanges() })

function root() {
  const value = document.createElement('article')
  document.body.append(value)
  return value
}

function leaf(parent: HTMLElement, text: string, start: number, end = start + text.length) {
  const value = document.createElement('span')
  value.dataset.sourceStart = String(start); value.dataset.sourceEnd = String(end)
  value.textContent = text; parent.append(value)
  return value.firstChild as Text
}

function select(start: Node, from: number, end: Node, to: number) {
  const range = document.createRange()
  range.setStart(start, from); range.setEnd(end, to)
  const selection = window.getSelection()!
  selection.removeAllRanges(); selection.addRange(range)
  return selection
}

function selected(result: SelectionResult) {
  expect(result.kind).toBe('selected')
  if (result.kind !== 'selected') throw new Error('expected a real source selection')
  return result.selection
}

describe('DOM instance to exact Markdown selection', () => {
  it('selects the second repeated phrase rather than the first equal substring', () => {
    const container = root(), source = '重复句。\n\n重复句。'
    const first = leaf(container, '重复句。', 0)
    const second = leaf(container, '重复句。', 6)
    const anchor = selected(selectionFromDOM(container, select(second, 0, second, 3), ref, source))
    expect(anchor).toMatchObject({ exact_quote: '重复句', start_codepoint: 6, end_codepoint: 9, prefix: '重复句。\n\n', suffix: '。', ref })
    expect(selected(selectionFromDOM(container, select(first, 0, first, 3), ref, source)).start_codepoint).toBe(0)
  })

  it('converts non-BMP UTF-16 positions while preserving a combining sequence verbatim', () => {
    const container = root(), source = '首🧠字 e\u0301 中文'
    const text = leaf(container, source, 0)
    const anchor = selected(selectionFromDOM(container, select(text, 5, text, 7), ref, source))
    expect(anchor).toMatchObject({ exact_quote: 'e\u0301', start_codepoint: 4, end_codepoint: 6, prefix: '首🧠字 ', suffix: ' 中文' })
  })

  it('uses the ordered DOM Range for a backwards mouse selection', () => {
    const container = root(), text = leaf(container, '甲乙丙', 0), selection = window.getSelection()!
    selection.setBaseAndExtent(text, 3, text, 1)
    expect(selected(selectionFromDOM(container, selection, ref, '甲乙丙'))).toMatchObject({ exact_quote: '乙丙', start_codepoint: 1, end_codepoint: 3 })
  })

  it('rejects an actual DOM range cutting through a surrogate pair', () => {
    const container = root(), text = leaf(container, '🧠甲', 0)
    expect(selectionFromDOM(container, select(text, 1, text, 2), ref, '🧠甲').kind).toBe('rejected')
  })

  it('takes a continuous raw quote across separately positioned emphasis leaves', () => {
    const container = root(), source = '前 **重复** 后'
    const before = leaf(container, '前 ', 0)
    const strong = document.createElement('strong'); container.append(strong)
    leaf(strong, '重复', 4)
    const after = leaf(container, ' 后', 8)
    const anchor = selected(selectionFromDOM(container, select(before, 0, after, 2), ref, source))
    expect(anchor.exact_quote).toBe(source)
    expect(anchor.end_codepoint).toBe(10)
    expect(selected(selectionFromDOM(container, select(strong.firstChild!.firstChild!, 0, strong.firstChild!.firstChild!, 2), ref, source)).exact_quote).toBe('重复')
  })

  it('maps element-boundary ranges and split text nodes through their actual leaf instance', () => {
    const container = root(), source = '甲乙丙丁'
    const first = leaf(container, source, 0)
    const second = first.splitText(2)
    expect(selected(selectionFromDOM(container, select(second, 0, second, 1), ref, source))).toMatchObject({ exact_quote: '丙', start_codepoint: 2 })
    expect(selected(selectionFromDOM(container, select(container, 0, container, 1), ref, source)).exact_quote).toBe(source)
  })

  it('does not include an adjacent unselected unmapped node', () => {
    const container = root(), source = '已选'
    const text = leaf(container, source, 0)
    container.append(document.createTextNode('不可映射'))
    expect(selected(selectionFromDOM(container, select(text, 0, text, 2), ref, source)).exact_quote).toBe('已选')
  })

  it('permits structural whitespace only between exact mapped endpoints', () => {
    const container = root(), source = '甲\n\n乙'
    const first = leaf(container, '甲', 0)
    const spacer = document.createTextNode('\n'); container.append(spacer)
    const last = leaf(container, '乙', 3)
    expect(selected(selectionFromDOM(container, select(first, 0, last, 1), ref, source)).exact_quote).toBe(source)
    expect(selectionFromDOM(container, select(spacer, 0, last, 1), ref, source).kind).toBe('rejected')
  })

  it.each([
    ['&amp;', '&'], ['\\*', '*'], ['`a b`', 'a b'], ['`a\nb`', 'a b'],
  ])('uses explicit source fallback when rendered %s has transformed characters', (source, rendered) => {
    const container = root(), text = leaf(container, rendered, 0, source.length)
    const result = selectionFromDOM(container, select(text, 0, text, rendered.length), ref, source)
    expect(result.kind).toBe('rejected')
    if (result.kind === 'rejected') expect(result.message).toContain('原文')
    expect(selected(selectionFromSource(ref, source, 0, source.length)).exact_quote).toBe(source)
  })

  it('supports inline code when HAST has a reliable interior text offset', () => {
    const container = root(), code = document.createElement('code'); container.append(code)
    const text = leaf(code, 'a+b', 1)
    expect(selected(selectionFromDOM(container, select(text, 0, text, 3), ref, '`a+b`'))).toMatchObject({ exact_quote: 'a+b', start_codepoint: 1, end_codepoint: 4 })
  })

  it('rejects unpositioned middle text rather than skipping it', () => {
    const container = root(), first = leaf(container, '甲', 0)
    container.append(document.createTextNode('不可映射'))
    const last = leaf(container, '乙', 1)
    expect(selectionFromDOM(container, select(first, 0, last, 1), ref, '甲乙').kind).toBe('rejected')
  })

  it('rejects intervening mathematics even when SVG contains only paths and no text', () => {
    const container = root(), first = leaf(container, '甲', 0)
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
    svg.append(document.createElementNS(svg.namespaceURI, 'path')); container.append(svg)
    const last = leaf(container, '乙', 5)
    expect(selectionFromDOM(container, select(first, 0, last, 1), ref, '甲$x$ 乙').kind).toBe('rejected')
    expect(selected(selectionFromSource(ref, '甲$x$ 乙', 1, 4)).exact_quote).toBe('$x$')
  })

  it('rejects a range reaching another content block', () => {
    const firstRoot = root(), secondRoot = root()
    const first = leaf(firstRoot, '甲', 0), second = leaf(secondRoot, '乙', 0)
    expect(selectionFromDOM(firstRoot, select(first, 0, second, 1), ref, '甲').kind).toBe('rejected')
  })

  it('rejects reordered, overlapping, or stale annotations instead of searching the source', () => {
    const container = root(), first = leaf(container, '重复', 2), second = leaf(container, '重复', 0)
    expect(selectionFromDOM(container, select(first, 0, second, 2), ref, '重复重复').kind).toBe('rejected')
    second.parentElement!.dataset.sourceStart = '2'; second.parentElement!.dataset.sourceEnd = '4'
    expect(selectionFromDOM(container, select(first, 0, second, 2), ref, '重复重复').kind).toBe('rejected')
    first.data = '改动'
    expect(selectionFromDOM(container, select(first, 0, first, 2), ref, '重复重复').kind).toBe('rejected')
  })

  it.each(['-1', '1.5', 'NaN', '9007199254740992', '01'])('rejects invalid source marker %s', marker => {
    const container = root(), text = leaf(container, '甲', 0)
    text.parentElement!.dataset.sourceStart = marker
    expect(selectionFromDOM(container, select(text, 0, text, 1), ref, '甲').kind).toBe('rejected')
  })

  it('treats no selection and a collapsed caret as empty', () => {
    const container = root(), text = leaf(container, '甲', 0)
    expect(selectionFromDOM(container, null, ref, '甲')).toEqual({ kind: 'empty' })
    expect(selectionFromDOM(container, select(text, 1, text, 1), ref, '甲')).toEqual({ kind: 'empty' })
  })
})

describe('raw source selection bounds and generated anchor contract', () => {
  it('uses forty codepoints of context and snapshots the full reference', () => {
    const mutable = { ...ref }, source = '🧠'.repeat(45) + 'e\u0301' + '中'.repeat(45)
    const anchor = selected(selectionFromSource(mutable, source, 90, 92))
    mutable.revision = 99; mutable.sha256 = 'b'.repeat(64)
    expect(anchor).toMatchObject({ ref, exact_quote: 'e\u0301', start_codepoint: 45, end_codepoint: 47, prefix: '🧠'.repeat(40), suffix: '中'.repeat(40) })
  })

  it.each([[1, 2], [0, 1], [-1, 0], [0, 4], [2, 0], [0.5, 2]])('rejects invalid or surrogate-splitting range [%s,%s]', (start, end) => {
    expect(selectionFromSource(ref, '🧠x', start, end).kind).toBe('rejected')
  })

  it('accepts a complete non-BMP scalar and keeps CRLF and combining text unchanged', () => {
    expect(selected(selectionFromSource(ref, '🧠x', 0, 2))).toMatchObject({ exact_quote: '🧠', start_codepoint: 0, end_codepoint: 1 })
    expect(selected(selectionFromSource(ref, '甲\r\ne\u0301', 1, 5)).exact_quote).toBe('\r\ne\u0301')
    expect(selectionFromSource(ref, '\ud800', 0, 1).kind).toBe('rejected')
    expect(selectionFromSource(ref, '\udc00', 0, 1).kind).toBe('rejected')
  })

  it('applies the 12000-codepoint bound rather than a UTF-16 length bound', () => {
    const allowed = '🧠'.repeat(12000), oversized = allowed + '中'
    expect(selected(selectionFromSource(ref, allowed, 0, allowed.length)).end_codepoint).toBe(12000)
    expect(selectionFromSource(ref, oversized, 0, oversized.length).kind).toBe('rejected')
  })

  it('rejects missing precision and non-block targets', () => {
    for (const invalid of [{ ...ref, revision: 0 }, { ...ref, sha256: 'latest' }, { ...ref, id: '../file' }, { ...ref, entity: 'lesson' as const }]) {
      expect(selectionFromSource(invalid, '甲', 0, 1).kind).toBe('rejected')
    }
  })
})
