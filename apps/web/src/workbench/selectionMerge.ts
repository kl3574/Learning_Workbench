import type { Session, ViewContext, ContentRef } from './model'
const refFields = (ref: ContentRef) => [ref.entity, ref.id, ref.revision, ref.sha256]
const contextFields = (context: ViewContext) => JSON.stringify([context.view_kind, context.attempt_id ?? null, refFields(context.active_ref), (context.attached_refs ?? []).map(refFields)])
const sameContext = (left: ViewContext, right: ViewContext) => contextFields(left) === contextFields(right)
/** An unchanged null in the local/base projection is not a selection deletion. */
export function preserveUntouchedSelections(local: Session, base: Session | null, remote: Session): Session {
  return { ...local, tabs: local.tabs.map(tab => {
    const before = base?.tabs.find(value => value.id === tab.id), current = remote.tabs.find(value => value.id === tab.id)
    if (before && current && !before.context.selection && !tab.context.selection && current.context.selection && sameContext(before.context, tab.context) && sameContext(tab.context, current.context)) return { ...tab, context: { ...tab.context, selection: current.context.selection } }
    return tab
  }) }
}
