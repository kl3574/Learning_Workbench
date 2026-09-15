import { Component, createRef, type ReactNode } from 'react'
import type { ContentRef, SavedTab } from '../../../../packages/contracts/generated/types'

const refKey = (ref: ContentRef) => [ref.entity, ref.id, ref.revision, ref.sha256]
export function readerViewportOwner(workspace: string | null, tab: SavedTab | undefined): string | null {
  if (!workspace || !tab) return null
  const context = tab.context
  return JSON.stringify([workspace, tab.id, context.view_kind, refKey(context.active_ref), (context.attached_refs ?? []).map(refKey), context.attempt_id ?? null])
}

type Props = { owner: string | null; conflict: boolean; className: string; children: ReactNode }
type Snapshot = { node: HTMLElement; rect: DOMRect; top: number; viewport: string; focus: Element | null; visibleFocus: boolean } | null
function viewport() {
  const visual = window.visualViewport
  return JSON.stringify([innerWidth, innerHeight, visual?.width, visual?.height, visual?.offsetLeft, visual?.offsetTop, visual?.scale])
}

/** Capture before React inserts the protection panel, then preserve the same scrolled content.
 * A layout effect alone would read the already-displaced pane. No deferred scrolling is scheduled.
 */
export class PreserveReaderViewport extends Component<Props> {
  private root = createRef<HTMLDivElement>()
  private reader() { return this.root.current?.querySelector<HTMLElement>(':scope > .workbench-grid > .reader-main > .reader-scroll') ?? null }

  getSnapshotBeforeUpdate(previous: Props): Snapshot {
    if (!this.props.owner || previous.owner !== this.props.owner || previous.conflict || !this.props.conflict) return null
    const node = this.reader()
    if (!node || node.scrollTop <= 1) return null
    const rect = node.getBoundingClientRect()
    if (rect.width <= 0 || rect.height <= 0) return null
    const focus = document.activeElement
    const focusRect = focus && focus !== node && node.contains(focus) ? focus.getBoundingClientRect() : null
    const visibleFocus = !!focusRect && focusRect.bottom > rect.top && focusRect.top < rect.bottom && focusRect.right > rect.left && focusRect.left < rect.right
    return { node, rect, top: node.scrollTop, viewport: viewport(), focus, visibleFocus }
  }

  componentDidUpdate(_previous: Props, _state: unknown, snapshot: Snapshot) {
    if (!snapshot || snapshot.node !== this.reader() || !snapshot.node.isConnected || snapshot.viewport !== viewport() || snapshot.focus !== document.activeElement) return
    const node = snapshot.node, rect = node.getBoundingClientRect(), delta = rect.top - snapshot.rect.top
    // Respect a child's focus/restoration or browser anchoring, as well as simultaneous resizing.
    if (node.scrollTop !== snapshot.top || delta <= 1 || rect.height <= 0 || Math.abs(rect.left - snapshot.rect.left) > 1 || Math.abs(rect.width - snapshot.rect.width) > 1 || Math.abs(rect.bottom - snapshot.rect.bottom) > 1) return
    // A focused control near the old pane top may now occupy the space below
    // the panel. Do not scroll that still-visible control back behind the panel.
    const adjustment = snapshot.visibleFocus && snapshot.focus
      ? Math.min(delta, Math.max(0, snapshot.focus.getBoundingClientRect().top - rect.top))
      : delta
    node.scrollTop = snapshot.top + adjustment
    // The browser's ordinary scroll event continues through each Reader's existing persistence path.
  }

  render() { return <div ref={this.root} className={this.props.className}>{this.props.children}</div> }
}
