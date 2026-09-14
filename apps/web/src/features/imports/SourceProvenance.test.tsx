import { cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, it } from 'vitest'
import { SourceProvenance, sourceLocatorLabel } from './SourceProvenance'

afterEach(cleanup)

it('shows an exact original page and hash without claiming mathematical approval', () => {
  render(<SourceProvenance citations={[{ id: 'citation_test', title: 'Original synthetic PDF', locator: 'source:source_test;pdf:page:2', source_sha256: 'a'.repeat(64), verification: 'user_supplied' }]} />)
  expect(screen.getByText('原件定位：PDF 第 2 页')).toBeTruthy()
  expect(screen.getByText('a'.repeat(64))).toBeTruthy()
  expect(screen.getByText(/尚未独立核实/)).toBeTruthy()
  expect(screen.getByText('source:source_test;pdf:page:2')).toBeTruthy()
})

it('formats only exact supplied DOCX nodes and never invents page numbers', () => {
  expect(sourceLocatorLabel('source:source_test;docx:part:word/document.xml;node:/w:document/w:body/w:p[4]')).toBe('DOCX 正文第 4 个段落节点')
  expect(sourceLocatorLabel('source:source_test;docx:part:word/document.xml;node:/w:document/w:body/w:tbl[2]/w:tr[1]/w:tc[3]')).toBe('DOCX 第 2 张表 · 第 1 行 · 第 3 个单元格')
  expect(sourceLocatorLabel('unknown-node:do-not-infer')).toBe('unknown-node:do-not-infer')
})

it('retains an explicit unknown source instead of inheriting another candidate location', () => {
  render(<SourceProvenance citations={[]} />)
  expect(screen.getByText(/不会按候选顺序推算/)).toBeTruthy()
})

it('renders untrusted citation text as text and acknowledges a missing original hash', () => {
  const view = render(<SourceProvenance citations={[{ id: 'citation_test', title: '<script>bad()</script>', locator: '<img src="https://external.invalid/">', source_sha256: null, verification: 'unverified' }]} />)
  expect(view.container.querySelector('script,img')).toBeNull()
  expect(screen.getByText(/未提供原件哈希/)).toBeTruthy()
})
