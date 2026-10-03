import { decodeBootstrapCommand, type BootstrapCommand } from './bootstrapCommands'
import { sameValue } from '../providers/providerSchema'
const held = new Map<string, BootstrapCommand>()
const listeners = new Set<() => void>()
let revision = 0
const changed = () => { revision++; listeners.forEach(listener => listener()) }
export const subscribeBootstrapMemory = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }
export const bootstrapMemoryVersion = () => revision
export const heldBootstrapCommands = (workspace: string, actor?: string) => [...held.values()].filter(v => v.workspace_id === workspace && (!actor || v.actor_session_id === actor)).map(v => structuredClone(v))
export function retainBootstrapCommand(command: BootstrapCommand) {
 const next = decodeBootstrapCommand(JSON.stringify(command), command.workspace_id), old = held.get(command.command_id)
 const basis = (v: BootstrapCommand) => ({ ...v, ack: null, error: null })
 if (old && (!sameValue(basis(old), basis(next)) || old.ack && next.ack && !sameValue(old.ack, next.ack))) throw new Error('Original bootstrap command changed')
 held.set(command.command_id, old?.ack ? old : next); changed()
}
export function releaseBootstrapCommand(command: BootstrapCommand) {
 const old = held.get(command.command_id)
 if (old && sameValue(old, command)) { held.delete(command.command_id); changed() }
}
if (typeof window !== 'undefined') window.addEventListener('beforeunload', event => {
 if (held.size) { event.preventDefault(); event.returnValue = '' }
})
