import { sameValue } from '../providers/providerSchema'
import { decodeTurnCommand, type TurnCommand } from './turnCommands'
import { decodeTurnForm, type TurnForm } from './turnForms'
const commands = new Map<string, TurnCommand>(), forms = new Map<string, TurnForm>(), listeners = new Set<() => void>()
let revision = 0
const changed = () => { revision++; listeners.forEach(listener => listener()) }
export const subscribeTurnMemory = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }
export const turnMemoryVersion = () => revision
export const heldTurnCommands = (workspace: string) => [...commands.values()].filter(v => v.workspace_id === workspace).map(v => structuredClone(v))
export const heldTurnForms = (workspace: string) => [...forms.values()].filter(v => v.workspace_id === workspace).map(v => structuredClone(v))
export function retainTurnCommand(command: TurnCommand) {
 const next = decodeTurnCommand(JSON.stringify(command), command.workspace_id), old = commands.get(next.command_id)
 const basis = (v: TurnCommand) => ({ ...v, ack: null, error: null })
 if (old && (!sameValue(basis(old), basis(next)) || old.ack && next.ack && !sameValue(old.ack, next.ack))) throw new Error('Original turn command changed')
 commands.set(next.command_id, old?.ack ? old : next); changed()
}
export function releaseTurnCommand(command: TurnCommand) {
 const old = commands.get(command.command_id), basis = (v: TurnCommand) => ({ ...v, ack: null, error: null })
 // A checked durable ACK also covers an older pending copy. Never release a
 // newer ACK merely because its earlier pending command reached storage.
 if (old && (sameValue(old, command) || sameValue(basis(old), basis(command)) && !old.ack
  && (command.ack || !old.error && command.error))) { commands.delete(command.command_id); changed() }
}
export function retainTurnForm(form: TurnForm) {
 const next = decodeTurnForm(JSON.stringify(form), form.workspace_id), old = forms.get(next.snapshot_id)
 if (old && !sameValue(old, next)) throw new Error('Original turn form changed')
 forms.set(next.snapshot_id, next); changed()
}
export function releaseTurnForm(form: TurnForm) {
 if (sameValue(forms.get(form.snapshot_id), form)) { forms.delete(form.snapshot_id); changed() }
}
if (typeof window !== 'undefined') window.addEventListener('beforeunload', event => {
 if (commands.size || forms.size) { event.preventDefault(); event.returnValue = '' }
})
