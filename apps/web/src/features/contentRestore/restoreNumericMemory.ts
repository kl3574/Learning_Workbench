import { sameValue } from '../providers/providerSchema'
import { decodeRestoreNumericCommand, type RestoreNumericCommand } from './restoreNumericStore'

// Only command/ACK persistence failures are held here. The session handle is an
// in-memory comparison value; neither it nor CSRF/cookies enter the journal.
const held = new Map<string, { command: RestoreNumericCommand; session: string }>()
const listeners = new Set<() => void>()
let revision = 0
const changed = () => { ++revision; listeners.forEach(listener => listener()) }
export const subscribeRestoreNumericMemory = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }
export const restoreNumericMemoryVersion = () => revision
const immutable = (command: RestoreNumericCommand) => ({ ...command, ack: null, rejection: null })
export function retainRestoreNumericMemory(command: RestoreNumericCommand, session: string): void {
  if (!session) throw new Error('Missing original Restore numeric session')
  const value = decodeRestoreNumericCommand(JSON.stringify(command), command.workspace_id), existing = held.get(value.command_id)
  if (existing && (existing.session !== session || !sameValue(immutable(existing.command), immutable(value))
      || existing.command.ack && value.ack && !sameValue(existing.command.ack, value.ack)
      || existing.command.rejection && value.rejection && !sameValue(existing.command.rejection, value.rejection))) {
    throw new Error('恢复数值内存已有不同原命令；未覆盖。')
  }
  const preferred = existing && (existing.command.ack || !value.ack && existing.command.rejection) ? existing.command : value
  held.set(value.command_id, { command: structuredClone(preferred), session }); changed()
}
export function pendingRestoreNumericMemory(workspace: string, draftId?: string): boolean {
  return [...held.values()].some(row => row.command.workspace_id === workspace && (!draftId || row.command.draft_id === draftId))
}
export function recoverableRestoreNumericMemory(workspace: string, session: string): RestoreNumericCommand[] {
  return [...held.values()].filter(row => row.command.workspace_id === workspace && row.session === session).map(row => structuredClone(row.command))
}
export function releaseRestoreNumericMemory(id: string, session: string): void {
  if (held.get(id)?.session === session) { held.delete(id); changed() }
}
export function discardRestoreNumericMemory(workspace: string, draftId?: string): void {
  for (const [id, row] of held) if (row.command.workspace_id === workspace && (!draftId || row.command.draft_id === draftId)) held.delete(id)
  changed()
}
if (typeof window !== 'undefined') window.addEventListener('beforeunload', event => {
  if (held.size) { event.preventDefault(); event.returnValue = '' }
})
