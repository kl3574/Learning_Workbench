import type { ContentRestoreDraftSnapshot } from '../../../../../packages/contracts/generated/api-types'
import type { RestoreNumericForm } from './restoreNumericForm'
import { sameValue } from '../providers/providerSchema'

type Held = { workspace: string; blockId: string; actor: string; snapshot: ContentRestoreDraftSnapshot; value: RestoreNumericForm }
const held = new Map<string, Held>(), listeners = new Set<() => void>()
let revision = 0
const key = (workspace: string, blockId: string, actor: string) => JSON.stringify([workspace, blockId, actor])
const changed = () => { ++revision; listeners.forEach(listener => listener()) }
export const subscribeRestoreNumericForms = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }
export const restoreNumericFormsVersion = () => revision
export const pendingRestoreNumericForms = (workspace: string, blockId?: string) => [...held.values()].some(item => item.workspace === workspace && (!blockId || item.blockId === blockId))
export function ownRestoreNumericForm(workspace: string, blockId: string, actor: string) {
  const value = actor ? held.get(key(workspace, blockId, actor)) : undefined
  return value ? structuredClone(value) : null
}
export function retainRestoreNumericForm(workspace: string, actor: string, snapshot: ContentRestoreDraftSnapshot, value: RestoreNumericForm) {
  if (!workspace || !actor || !snapshot.source_ref.id) throw new Error('Missing original Restore numeric form owner')
  const id = key(workspace, snapshot.source_ref.id, actor), original = held.get(id)
  if (original && !sameValue(original.snapshot.candidate, snapshot.candidate)) throw new Error('不能覆盖另一份未提交数值材料。')
  held.set(id, structuredClone({ workspace, blockId: snapshot.source_ref.id, actor, snapshot, value })); changed()
}
export function releaseRestoreNumericForm(workspace: string, blockId: string, actor: string, expected?: RestoreNumericForm) {
  const id = key(workspace, blockId, actor), current = held.get(id)
  if (current && (!expected || sameValue(current.value, expected))) { held.delete(id); changed() }
}
export function discardRestoreNumericForms(workspace: string, blockId: string) {
  let deleted = false
  for (const [id, value] of held) if (value.workspace === workspace && value.blockId === blockId) { held.delete(id); deleted = true }
  if (deleted) changed()
}
if (typeof window !== 'undefined') window.addEventListener('beforeunload', event => { if (held.size) { event.preventDefault(); event.returnValue = '' } })
