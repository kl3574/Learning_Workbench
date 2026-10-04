import { sameValue } from '../providers/providerSchema'
import { decodeOutboundCommand, type OutboundCommand } from './turnOutboundCommands'
import { decodeOutboundForm, type OutboundForm } from './turnOutboundForms'
const commands = new Map<string, OutboundCommand>(), forms = new Map<string, OutboundForm>(), listeners = new Set<() => void>()
let revision = 0
const changed = () => { revision++; listeners.forEach(listener => listener()) }
export const subscribeOutboundMemory = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }
export const outboundMemoryVersion = () => revision
export const heldOutboundCommands = (workspace: string) => [...commands.values()].filter(v => v.workspace_id === workspace).map(v => structuredClone(v))
export const heldOutboundForms = (workspace: string) => [...forms.values()].filter(v => v.workspace_id === workspace).map(v => structuredClone(v))
export function retainOutboundCommand(command: OutboundCommand) {
 const next = decodeOutboundCommand(JSON.stringify(command), command.workspace_id), old = commands.get(next.command_id)
 const basis = (v: OutboundCommand) => ({ ...v, ack: null, error: null })
 if (old && (!sameValue(basis(old), basis(next)) || old.ack && next.ack && !sameValue(old.ack, next.ack))) throw new Error('Original turn command changed')
 commands.set(next.command_id, old?.ack ? old : next); changed()
}
export function releaseOutboundCommand(command: OutboundCommand) {
 const old = commands.get(command.command_id), basis = (v: OutboundCommand) => ({ ...v, ack: null, error: null })
 // A checked durable ACK also covers an older pending copy. Never release a
 // newer ACK merely because its earlier pending command reached storage.
 if (old && (sameValue(old, command) || sameValue(basis(old), basis(command)) && !old.ack
  && (command.ack || !old.error && command.error))) { commands.delete(command.command_id); changed() }
}
export function retainOutboundForm(form: OutboundForm) {
 const next = decodeOutboundForm(JSON.stringify(form), form.workspace_id), old = forms.get(next.snapshot_id)
 if (old && !sameValue(old, next)) throw new Error('Original turn form changed')
 forms.set(next.snapshot_id, next); changed()
}
export function releaseOutboundForm(form: OutboundForm) {
 if (sameValue(forms.get(form.snapshot_id), form)) { forms.delete(form.snapshot_id); changed() }
}
if (typeof window !== 'undefined') window.addEventListener('beforeunload', event => {
 if (commands.size || forms.size) { event.preventDefault(); event.returnValue = '' }
})
