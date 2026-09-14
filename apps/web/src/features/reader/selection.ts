import type { ContentRef, Selection as SelectionAnchor } from '../../../../../packages/contracts/generated/types'
import selectionSchema from '../../../../../packages/contracts/generated/schemas/Selection.schema.json'

export type SelectionResult =
  | { kind: 'selected'; selection: SelectionAnchor }
  | { kind: 'empty' }
  | { kind: 'rejected'; message: string }

const sourceSelector = '[data-source-start][data-source-end]'
const unsupportedSelector = 'svg,math,[data-tex],.formula,[data-selection-unsupported],textarea,input'
const unsupportedMessage = '此选区无法可靠对应原 Markdown；请展开原文，重新选择 Markdown 或 LaTeX 源文。'
const refSchema = selectionSchema.$defs.ContentRef
const idPattern = new RegExp(refSchema.properties.id.pattern)
const hashPattern = new RegExp(refSchema.properties.sha256.pattern)

const rejected = (message = unsupportedMessage): SelectionResult => ({ kind: 'rejected', message })

function scalarBoundary(source: string, offset: number): boolean {
  if (!Number.isSafeInteger(offset) || offset < 0 || offset > source.length) return false
  if (offset === 0 || offset === source.length) return true
  const before = source.charCodeAt(offset - 1), after = source.charCodeAt(offset)
  return !(before >= 0xd800 && before <= 0xdbff && after >= 0xdc00 && after <= 0xdfff)
}

function validUnicode(source: string): boolean {
  for (let index = 0; index < source.length; index += 1) {
    const unit = source.charCodeAt(index)
    if (unit >= 0xd800 && unit <= 0xdbff) {
      const next = source.charCodeAt(++index)
      if (!(next >= 0xdc00 && next <= 0xdfff)) return false
    } else if (unit >= 0xdc00 && unit <= 0xdfff) return false
  }
  return true
}

/** Textarea offsets are UTF-16; the persisted contract uses Unicode codepoints. */
export function selectionFromSource(ref: ContentRef, source: string, startUtf16: number, endUtf16: number): SelectionResult {
  if (ref.entity !== 'block' || !idPattern.test(ref.id) || !hashPattern.test(ref.sha256)
      || !Number.isSafeInteger(ref.revision) || ref.revision < refSchema.properties.revision.minimum) {
    return rejected('选区需要内容块的完整精确修订引用。')
  }
  if (!scalarBoundary(source, startUtf16) || !scalarBoundary(source, endUtf16) || endUtf16 < startUtf16 || !validUnicode(source)) {
    return rejected('选区边界无效或切断了 Unicode 字符；请重新选择完整字符。')
  }
  if (startUtf16 === endUtf16) return { kind: 'empty' }
  const quote = source.slice(startUtf16, endUtf16)
  const quoteLength = Array.from(quote).length
  if (quoteLength > selectionSchema.properties.exact_quote.maxLength) return rejected('选区超过 12000 个 Unicode 字符，请缩小范围。')
  const before = Array.from(source.slice(0, startUtf16))
  const selection: SelectionAnchor = {
    ref: Object.freeze({ entity: ref.entity, id: ref.id, revision: ref.revision, sha256: ref.sha256 }),
    exact_quote: quote,
    prefix: before.slice(-40).join(''),
    suffix: Array.from(source.slice(endUtf16)).slice(0, 40).join(''),
    start_codepoint: before.length,
    end_codepoint: before.length + quoteLength,
  }
  return { kind: 'selected', selection: Object.freeze(selection) }
}

function compare(document: Document, left: Node, leftOffset: number, right: Node, rightOffset: number): number {
  const a = document.createRange(), b = document.createRange()
  a.setStart(left, leftOffset); a.collapse(true)
  b.setStart(right, rightOffset); b.collapse(true)
  return a.compareBoundaryPoints(0, b) // START_TO_START, in this owner document.
}

function overlaps(range: Range, node: Node): boolean {
  const document = node.ownerDocument
  if (!document) return false
  const contents = document.createRange()
  contents.selectNodeContents(node)
  return compare(document, range.endContainer, range.endOffset, contents.startContainer, contents.startOffset) > 0
    && compare(document, range.startContainer, range.startOffset, contents.endContainer, contents.endOffset) < 0
}

type SourcePart = { start: number; end: number }

function sourcePart(root: HTMLElement, node: Text, from: number, to: number, source: string): SourcePart | null {
  const marker = node.parentElement?.closest<HTMLElement>(sourceSelector)
  if (!marker || !root.contains(marker)) return null
  const rawStart = marker.getAttribute('data-source-start') ?? '', rawEnd = marker.getAttribute('data-source-end') ?? ''
  if (!/^(0|[1-9]\d*)$/.test(rawStart) || !/^(0|[1-9]\d*)$/.test(rawEnd)) throw new Error('invalid source marker')
  const start = Number(rawStart), end = Number(rawEnd)
  if (end < start || !scalarBoundary(source, start) || !scalarBoundary(source, end)
      || marker.textContent !== source.slice(start, end)) throw new Error('transformed source text')
  // The DOM instance, including split text nodes, determines the position. No
  // substring search is used, so repeated phrases retain their actual offsets.
  const prefix = root.ownerDocument.createRange()
  prefix.setStart(marker, 0); prefix.setEnd(node, from)
  const selectedStart = start + prefix.toString().length
  return { start: selectedStart, end: selectedStart + to - from }
}

/** `root` must be the rendered container of one exact ContentBlock. */
export function selectionFromDOM(root: HTMLElement, selection: globalThis.Selection | null, ref: ContentRef, source: string): SelectionResult {
  if (!selection || selection.rangeCount === 0 || selection.isCollapsed) return { kind: 'empty' }
  if (selection.rangeCount !== 1) return rejected('请选择同一内容块内的一段连续文本。')
  const range = selection.getRangeAt(0)
  if (!root.contains(range.startContainer) || !root.contains(range.endContainer)) return rejected('选区跨出了当前内容块，请在一个内容块内重新选择。')
  try {
    if (root.matches(unsupportedSelector)) return rejected()
    for (const node of root.querySelectorAll(unsupportedSelector)) if (overlaps(range, node)) return rejected()
    const walker = root.ownerDocument.createTreeWalker(root, 4) // SHOW_TEXT
    const parts: (SourcePart | null)[] = []
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const text = node as Text
      if (!text.length || !overlaps(range, text)) continue
      const from = range.startContainer === text ? range.startOffset : 0
      const to = range.endContainer === text ? range.endOffset : text.length
      if (to <= from) continue
      const part = sourcePart(root, text, from, to, source)
      // Rehype may insert unpositioned whitespace between positioned elements.
      // It is only safe inside a range with independently mapped endpoints.
      if (!part && text.data.slice(from, to).trim()) return rejected()
      parts.push(part)
    }
    if (!parts.length) return rejected()
    const first = parts[0], last = parts[parts.length - 1]
    if (!first || !last) return rejected()
    let previousEnd = first.start
    for (const part of parts) {
      if (!part) continue
      if (part.start < previousEnd || part.end < part.start) return rejected()
      previousEnd = part.end
    }
    // Internal Markdown punctuation stays in the raw, continuous source quote.
    return selectionFromSource(ref, source, first.start, last.end)
  } catch {
    return rejected()
  }
}
