import type { ContentRef, ViewContext } from '../../../../../packages/contracts/generated/types'
import { exactRef } from '../assessment/target'
import { openTab, tabIdentity, type Session } from '../../workbench/model'
import { sameFrozenReferences } from '../reader/navigation'
export function routeContext(ref: ContentRef): ViewContext { return { view_kind: 'route', active_ref: ref, attached_refs: [], selection: null, attempt_id: null } }
export function routeTarget(context: ViewContext): ContentRef | null { return context.view_kind === 'route' && exactRef(context.active_ref, 'route') ? context.active_ref : null }
export const routeHref = (ref: ContentRef) => `/?route=${encodeURIComponent(JSON.stringify(ref))}`
export function readRouteTarget(search = location.search): ContentRef | null {
  const raw = new URLSearchParams(search).get('route'); if (!raw) return null
  try { const value: unknown = JSON.parse(raw); if (!exactRef(value, 'route')) throw new Error(); return value } catch { throw new Error('路线链接缺少有效的完整修订引用，未改为当前路线。') }
}
export function openRoute(session: Session, ref: ContentRef, pinned: boolean, hasDraft: (id: string) => boolean): { kind: 'opened' | 'conflict'; session: Session } {
  const context = routeContext(ref), existing = session.tabs.find(tab => tab.id === tabIdentity(context))
  if (existing && !sameFrozenReferences(existing.context, context)) return { kind: 'conflict', session }
  return { kind: 'opened', session: openTab({ ...session, navigation: 'route' }, context, pinned, hasDraft) }
}
