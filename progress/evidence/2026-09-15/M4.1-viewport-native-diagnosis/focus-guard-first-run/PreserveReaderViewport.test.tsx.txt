import { useLayoutEffect, useRef } from 'react'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'
import { cleanup, render } from '@testing-library/react'
import type { SavedTab } from '../../../../packages/contracts/generated/types'
import { PreserveReaderViewport, readerViewportOwner } from './PreserveReaderViewport'

// jsdom has no layout. These tests control the pane geometry while exercising
// real React before/after-commit lifecycle; native tests verify browser layout.
beforeEach(() => {
  vi.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockImplementation(function (this: HTMLElement) {
    if (this.tagName === 'BUTTON' && this.parentElement?.classList.contains('reader-scroll')) {
      const pane = this.parentElement, top = pane.getBoundingClientRect().top
      return new DOMRect(10, top + 1064 - pane.scrollTop, 100, 40)
    }
    if (!this.classList.contains('reader-scroll')) return new DOMRect()
    const panel = this.closest('.app-shell')?.querySelector('[data-conflict]')
    const top = panel ? 493 : 94
    const width = panel?.hasAttribute('data-resized') ? 360 : 390
    return new DOMRect(0, top, width, 818 - top)
  })
})
afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.unstubAllGlobals() })

function Pane({ restore, focus }: { restore?: number; focus?: boolean }) {
  const node = useRef<HTMLDivElement>(null)
  useLayoutEffect(() => {
    if (restore !== undefined) node.current!.scrollTop = restore
    if (focus) node.current!.querySelector('button')!.focus()
  }, [restore, focus])
  return <div className="reader-scroll" ref={node}><button>当前内容</button></div>
}
type LayoutProps = { owner?: string | null; conflict?: boolean; nodeKey?: string; restore?: number; focus?: boolean; resized?: boolean }
function Layout({ owner = 'workspace/tab/full-ref', conflict = false, nodeKey = 'same', restore, focus, resized }: LayoutProps) {
  return <PreserveReaderViewport owner={owner} conflict={conflict} className="app-shell">
    {conflict && <section data-conflict data-resized={resized || undefined}>真实冲突比较保持显示</section>}
    <div className="workbench-grid"><main className="reader-main"><Pane key={nodeKey} restore={restore} focus={focus} /></main></div>
  </PreserveReaderViewport>
}

test('an inserted conflict panel preserves screen position once and leaves the panel present', () => {
  const view = render(<Layout />), node = view.container.querySelector<HTMLElement>('.reader-scroll')!
  node.scrollTop = 958
  view.rerender(<Layout conflict />)
  expect(node.scrollTop).toBe(1357)
  expect(view.getByText('真实冲突比较保持显示')).not.toBeNull()
  view.rerender(<Layout conflict />)
  expect(node.scrollTop).toBe(1357)
})

test('initial display and an unscrolled reader do not acquire a synthetic scroll position', () => {
  const view = render(<Layout conflict />), node = view.container.querySelector<HTMLElement>('.reader-scroll')!
  expect(node.scrollTop).toBe(0)
  view.rerender(<Layout />)
  view.rerender(<Layout conflict />)
  expect(node.scrollTop).toBe(0)
})

test.each([null, 'another-workspace/tab/full-ref', 'workspace/other-tab/full-ref'])('an owner change to %s leaves the next view position alone', owner => {
  const view = render(<Layout />), node = view.container.querySelector<HTMLElement>('.reader-scroll')!
  node.scrollTop = 958
  view.rerender(<Layout owner={owner} conflict />)
  expect(node.scrollTop).toBe(958)
})

test('a replaced reader node retains its own restored position', () => {
  const view = render(<Layout />), old = view.container.querySelector<HTMLElement>('.reader-scroll')!
  old.scrollTop = 958
  view.rerender(<Layout nodeKey="replacement" conflict restore={24} />)
  const current = view.container.querySelector<HTMLElement>('.reader-scroll')!
  expect(current).not.toBe(old)
  expect(current.scrollTop).toBe(24)
})

test.each([24, 1357])('child restoration or native anchoring to %s is not compensated twice', restore => {
  const view = render(<Layout />), node = view.container.querySelector<HTMLElement>('.reader-scroll')!
  node.scrollTop = 958
  view.rerender(<Layout conflict restore={restore} />)
  expect(node.scrollTop).toBe(restore)
})

test('focus movement and concurrent width reflow retain their own layout behavior', () => {
  const view = render(<Layout />), node = view.container.querySelector<HTMLElement>('.reader-scroll')!
  node.scrollTop = 958
  view.rerender(<Layout conflict focus />)
  expect(document.activeElement).toBe(view.getByRole('button'))
  expect(node.scrollTop).toBe(958)
  view.rerender(<Layout focus />)
  view.rerender(<Layout conflict focus resized />)
  expect(node.scrollTop).toBe(958)
})

test('preserving a lower reading position never pushes the same visible focused control behind the new panel', () => {
  const view = render(<Layout />), node = view.container.querySelector<HTMLElement>('.reader-scroll')!
  node.scrollTop = 958
  const control = view.getByRole('button')
  control.focus()
  expect(control.getBoundingClientRect().top).toBeGreaterThan(node.getBoundingClientRect().top)
  view.rerender(<Layout conflict />)
  expect(document.activeElement).toBe(control)
  expect(control.getBoundingClientRect().top).toBeGreaterThanOrEqual(node.getBoundingClientRect().top)
  expect(control.getBoundingClientRect().bottom).toBeLessThanOrEqual(node.getBoundingClientRect().bottom)
  expect(view.getByText('真实冲突比较保持显示')).not.toBeNull()
})

test('ownership distinguishes exact references and attempts, independently of saved offsets', () => {
  const tab: SavedTab = { id: 'tab', pinned: true, scroll_offset: 10, context: {
    view_kind: 'assessment_help', active_ref: { entity: 'assessment', id: 'assessment', revision: 1, sha256: 'a'.repeat(64) },
    attached_refs: [{ entity: 'course', id: 'course', revision: 1, sha256: 'b'.repeat(64) }], attempt_id: 'attempt_one',
  } }
  const key = readerViewportOwner('workspace', tab)
  expect(readerViewportOwner('workspace', { ...tab, scroll_offset: 20 })).toBe(key)
  expect(readerViewportOwner('workspace', { ...tab, context: { ...tab.context, attempt_id: 'attempt_two' } })).not.toBe(key)
  expect(readerViewportOwner('workspace', { ...tab, context: { ...tab.context, active_ref: { ...tab.context.active_ref, sha256: 'c'.repeat(64) } } })).not.toBe(key)
  expect(readerViewportOwner('workspace', { ...tab, context: { ...tab.context, attached_refs: [{ ...tab.context.attached_refs![0], revision: 2 }] } })).not.toBe(key)
  expect(readerViewportOwner('another-workspace', tab)).not.toBe(key)
})
