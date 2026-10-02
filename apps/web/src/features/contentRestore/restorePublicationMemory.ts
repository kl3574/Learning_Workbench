import type { ContentRef } from '../../../../../packages/contracts/generated/api-types'
import { sameValue } from '../providers/providerSchema'
import type { RestorePublicationCommand } from './restorePublicationCommands'

// A failed/aborted IndexedDB write must not erase the already chosen command or
// received ACK. Session secrets are compared only in page memory, never stored.
const held = new Map<string, { command: RestorePublicationCommand; session: string }>()
const listeners = new Set<() => void>()
let revision = 0
const changed = () => { ++revision; listeners.forEach(listener => listener()) }
export const subscribeRestorePublicationMemory = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }
export const restorePublicationMemoryVersion = () => revision
export function retainRestorePublicationMemory(command: RestorePublicationCommand, session: string) {
  if (!session) throw new Error('Missing original publication session')
  held.set(command.command_id, { command: structuredClone(command), session }); changed()
}
export function pendingRestorePublicationMemory(workspace: string, base?: ContentRef) {
  return [...held.values()].some(row => row.command.workspace_id === workspace && (!base || sameValue(row.command.basis.snapshot.base_ref, base)))
}
export function recoverableRestorePublicationMemory(workspace: string, session: string) {
  return [...held.values()].filter(row => row.command.workspace_id === workspace && row.session === session).map(row => structuredClone(row.command))
}
export function releaseRestorePublicationMemory(id: string, session: string) {
  if (held.get(id)?.session === session) { held.delete(id); changed() }
}
export function discardRestorePublicationMemory(workspace: string, base?: ContentRef) {
  for (const [id, row] of held) if (row.command.workspace_id === workspace && (!base || sameValue(row.command.basis.snapshot.base_ref, base))) held.delete(id)
  changed()
}
if (typeof window !== 'undefined') window.addEventListener('beforeunload', event => {
  if (held.size) { event.preventDefault(); event.returnValue = '' }
})
