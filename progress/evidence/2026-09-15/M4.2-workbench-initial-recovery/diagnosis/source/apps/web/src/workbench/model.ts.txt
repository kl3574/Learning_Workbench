import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'
import type { ContentRef, SavedTab, ViewContext, WorkbenchSession } from '../../../../packages/contracts/generated/types'
export type { ContentRef, ViewContext }
export type Session = Required<WorkbenchSession>
export type Tab = Required<SavedTab>
export type Navigation = Session['navigation']
export const navigationItems = [
  { id: 'route', label: '学习路线', glyph: '↗' },
  { id: 'textbook', label: '教材', glyph: '▤' },
  { id: 'practice', label: '习题', glyph: '✎' },
  { id: 'assessment', label: '测试题', glyph: '☑' },
] as const
export function emptySession(): Session {
  return { revision: 1, course_ref: null, navigation: 'route', tabs: [], active_tab_id: null, expanded_keys: [], directory_scroll: 0, nav_width: 300, agent_width: 368, nav_collapsed: false, agent_collapsed: false }
}
export function normalizeSession(value: WorkbenchSession): Session { return { ...emptySession(), ...value } }
export function tabIdentity(context: ViewContext): string {
  const ref = context.active_ref
  return `tab_${bytesToHex(sha256(new TextEncoder().encode(JSON.stringify([context.view_kind, ref.entity, ref.id, ref.revision, context.attempt_id ?? 'learning']))))}`
}
export function openTab(session: Session, context: ViewContext, pinned: boolean, hasDraft: (id: string) => boolean): Session {
  const id = tabIdentity(context)
  const existing = session.tabs.find(tab => tab.id === id)
  if (existing) return { ...session, active_tab_id: id, tabs: session.tabs.map(tab => tab.id === id ? { ...tab, pinned: tab.pinned || pinned } : tab) }
  const preview = session.tabs.find(tab => !tab.pinned && !hasDraft(tab.id))
  const tab: Tab = { id, context, pinned, scroll_offset: 0 }
  return { ...session, active_tab_id: id, tabs: preview ? session.tabs.map(item => item.id === preview.id ? tab : item) : [...session.tabs, tab] }
}
export function resizeValue(side: 'nav' | 'agent', value: number, viewport: number, otherWidth: number): number {
  const [min, max] = side === 'nav' ? [260, 360] : [320, 480]
  return Math.max(min, Math.min(max, viewport >= 1280 ? viewport - otherWidth - 492 : max, Math.round(value)))
}
export type FrozenRequest = Readonly<{ threadId: string; message: string; context: ViewContext }>
export function freezeContext(context: ViewContext, message: string): FrozenRequest {
  const copy = structuredClone(context)
  Object.freeze(copy.active_ref)
  for (const ref of copy.attached_refs ?? []) Object.freeze(ref)
  Object.freeze(copy.attached_refs)
  if (copy.selection) { Object.freeze(copy.selection.ref); Object.freeze(copy.selection) }
  Object.freeze(copy)
  return Object.freeze({ threadId: tabIdentity(copy), message, context: copy })
}
export class ContextBridge {
  readonly replies = new Map<string, { request: FrozenRequest; text: string }[]>()
  async send(context: ViewContext, message: string, execute: (request: FrozenRequest) => Promise<string>): Promise<string> {
    const request = freezeContext(context, message)
    const text = await execute(request)
    this.replies.set(request.threadId, [...(this.replies.get(request.threadId) ?? []), { request, text }])
    return request.threadId
  }
}
