import { useState } from 'react'
import { act, cleanup, render, screen } from '@testing-library/react'
import { afterEach, expect, test, vi } from 'vitest'
import { redo, undo, undoDepth } from '@codemirror/commands'
import { MarkdownSourceEditor } from './MarkdownSourceEditor'
import { codeMirrorTestGeometry, replaceSource, sourceView } from './sourceEditorTestSupport'

codeMirrorTestGeometry()
afterEach(cleanup)
const original = '# 原始 🧠 e\u0301\n\n\\[\\frac{α}{β}+x_1^2\\]\n\n'

test('actual CM transactions preserve Unicode, TeX and every newline with undo/redo and controlled echoes', () => {
  const changes = vi.fn()
  function Controlled() {
    const [value, setValue] = useState(original)
    return <MarkdownSourceEditor label="源码" value={value} sourceIdentity="draft-a" onChange={text => { changes(text); setValue(text) }} />
  }
  render(<Controlled />)
  const element = screen.getByRole('textbox', { name: '源码' }), view = sourceView(element)
  expect(element.getAttribute('contenteditable')).toBe('true')
  expect(view.state.doc.toString()).toBe(original)
  expect(changes).not.toHaveBeenCalled()
  const modified = original + '\n第二行 \\LaTeX{原样}\n'
  replaceSource(element, modified)
  expect(changes).toHaveBeenLastCalledWith(modified)
  expect(sourceView(element)).toBe(view)
  expect(undoDepth(view.state)).toBe(1)
  act(() => { expect(undo(view)).toBe(true) }); expect(changes).toHaveBeenLastCalledWith(original)
  act(() => { expect(redo(view)).toBe(true) }); expect(changes).toHaveBeenLastCalledWith(modified)
})

test('external replacement emits no edit and cannot undo into the replaced source', () => {
  const changed = vi.fn()
  const root = render(<MarkdownSourceEditor label="源码" value={original} sourceIdentity="same" onChange={changed} />)
  const view = sourceView(screen.getByLabelText('源码'))
  replaceSource(view.contentDOM, '本机临时\n')
  const external = '服务端重新核验\n\n\\alpha\n'
  root.rerender(<MarkdownSourceEditor label="源码" value={external} sourceIdentity="same" onChange={changed} />)
  expect(view.state.doc.toString()).toBe(external)
  expect(changed).toHaveBeenCalledTimes(1)
  expect(undoDepth(view.state)).toBe(0)
  act(() => { expect(undo(view)).toBe(false) })
})

test('disabled transactions and undo cannot mutate the document; enabled state keeps its legitimate history', () => {
  const changed = vi.fn(), props = { label: '源码', sourceIdentity: 'same', onChange: changed }
  const root = render(<MarkdownSourceEditor {...props} value={original} />)
  const view = sourceView(screen.getByLabelText('源码'))
  replaceSource(view.contentDOM, '本机修改\n')
  root.rerender(<MarkdownSourceEditor {...props} value={'本机修改\n'} disabled />)
  expect(view.state.readOnly).toBe(true)
  expect(view.contentDOM.getAttribute('contenteditable')).toBe('false')
  expect(view.contentDOM.getAttribute('aria-disabled')).toBe('true')
  replaceSource(view.contentDOM, '禁止写入')
  act(() => { expect(undo(view)).toBe(false) })
  expect(view.state.doc.toString()).toBe('本机修改\n')
  expect(changed).toHaveBeenCalledTimes(1)
  root.rerender(<MarkdownSourceEditor {...props} value={'本机修改\n'} />)
  act(() => { expect(undo(view)).toBe(true) }); expect(changed).toHaveBeenLastCalledWith(original)
})

test('source identity change and unmount empty the old view and fence stale dispatch callbacks', () => {
  const changed = vi.fn()
  const root = render(<MarkdownSourceEditor label="源码" value={original} sourceIdentity="source-a" onChange={changed} />)
  const old = sourceView(screen.getByLabelText('源码'))
  replaceSource(old.contentDOM, '仅属于旧草稿的文字')
  root.rerender(<MarkdownSourceEditor label="源码" value={'新的精确草稿\n'} sourceIdentity="source-b" onChange={changed} />)
  const current = sourceView(screen.getByLabelText('源码'))
  expect(current).not.toBe(old)
  expect(old.state.doc.toString()).toBe('')
  expect(undoDepth(current.state)).toBe(0)
  act(() => old.dispatch({ changes: { from: 0, insert: '晚到的旧文字' } }))
  expect(changed).toHaveBeenCalledTimes(1)
  expect(current.state.doc.toString()).toBe('新的精确草稿\n')
  root.unmount()
  expect(current.state.doc.toString()).toBe('')
  act(() => current.dispatch({ changes: { from: 0, insert: '卸载后文字' } }))
  expect(changed).toHaveBeenCalledTimes(1)
  expect(screen.queryByRole('textbox')).toBeNull()
})
