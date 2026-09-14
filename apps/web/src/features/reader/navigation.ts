import type { ContentRef, ViewContext } from '../../../../../packages/contracts/generated/types'
import { openTab, tabIdentity, type Session } from '../../workbench/model'
import { readerContext, type ReaderTarget } from './target'
export const referenceConflictMessage = '此链接的哈希或上级路径与已打开标签的冻结引用不一致。原标签、课程与草稿仍保留；未用旧正文替代请求。关闭旧标签后可明确打开另一条路径。'
function exact(context: ViewContext): string {
  const fields = (ref: ContentRef) => [ref.entity, ref.id, ref.revision, ref.sha256]
  return JSON.stringify([fields(context.active_ref), [...(context.attached_refs ?? [])].map(fields).sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)))])
}
export const sameFrozenReferences = (a: ViewContext, b: ViewContext) => exact(a) === exact(b)
export function openReader(session: Session, target: ReaderTarget, pinned: boolean, hasDraft: (id: string) => boolean): { kind: 'opened' | 'conflict'; session: Session } {
  const context = readerContext(target)
  const existing = session.tabs.find(tab => tab.id === tabIdentity(context))
  if (existing && !sameFrozenReferences(existing.context, context)) return { kind: 'conflict', session }
  return { kind: 'opened', session: openTab({ ...session, course_ref: target.course, navigation: 'textbook' }, context, pinned, hasDraft) }
}
