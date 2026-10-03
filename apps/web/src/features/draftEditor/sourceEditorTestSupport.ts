// jsdom has no layout engine. These test-only Range geometry methods allow the
// real CM state/view to run; browser acceptance verifies actual native geometry.
import { afterAll, beforeAll } from 'vitest'
import { EditorView } from '@codemirror/view'
import { act } from '@testing-library/react'

export function codeMirrorTestGeometry() {
  const original = new Map<string, PropertyDescriptor | undefined>()
  beforeAll(() => {
    for (const name of ['getClientRects', 'getBoundingClientRect']) {
      original.set(name, Object.getOwnPropertyDescriptor(Range.prototype, name))
      if (!(name in Range.prototype)) Object.defineProperty(Range.prototype, name, {
        configurable: true, value: () => name === 'getClientRects' ? [] : new DOMRect(),
      })
    }
  })
  afterAll(() => {
    for (const [name, descriptor] of original) {
      if (descriptor) Object.defineProperty(Range.prototype, name, descriptor)
      else Reflect.deleteProperty(Range.prototype, name)
    }
  })
}

export function sourceView(element: HTMLElement): EditorView {
  const view = EditorView.findFromDOM(element)
  if (!view) throw new Error('Expected the actual CodeMirror view')
  return view
}

export function replaceSource(element: HTMLElement, text: string) {
  const view = sourceView(element)
  act(() => view.dispatch({ changes: { from: 0, to: view.state.doc.length, insert: text }, userEvent: 'input' }))
}
