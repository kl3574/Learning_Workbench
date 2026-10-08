import { sameValue } from '../providers/providerSchema'
import { decodeApprovalCommand, type ApprovalCommand } from './approvalCommands'
import { decodeApprovalForm, type ApprovalForm } from './approvalForms'
const commands = new Map<string, ApprovalCommand>(), forms = new Map<string, ApprovalForm>(), listeners = new Set<() => void>()
let revision = 0
const changed = () => { revision++; listeners.forEach(listener => listener()) }
export const subscribeApprovalMemory = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }
export const approvalMemoryVersion = () => revision
export const heldApprovalCommands = (workspace: string) => [...commands.values()].filter(v => v.workspace_id === workspace).map(v => structuredClone(v))
export const heldApprovalForms = (workspace: string) => [...forms.values()].filter(v => v.workspace_id === workspace).map(v => structuredClone(v))
export function retainApprovalCommand(command: ApprovalCommand) {
 const next = decodeApprovalCommand(JSON.stringify(command), command.workspace_id), old = commands.get(next.command_id)
 const basis = (v: ApprovalCommand) => ({ ...v, ack: null, error: null })
 if (old && (!sameValue(basis(old), basis(next)) || old.ack && next.ack && !sameValue(old.ack, next.ack))) throw new Error('Original turn command changed')
 commands.set(next.command_id, old?.ack ? old : next); changed()
}
export function releaseApprovalCommand(command: ApprovalCommand) {
 const old = commands.get(command.command_id), basis = (v: ApprovalCommand) => ({ ...v, ack: null, error: null })
 // A checked durable ACK also covers an older pending copy. Never release a
 // newer ACK merely because its earlier pending command reached storage.
 if (old && (sameValue(old, command) || sameValue(basis(old), basis(command)) && !old.ack
  && (command.ack || !old.error && command.error))) { commands.delete(command.command_id); changed() }
}
export function retainApprovalForm(form: ApprovalForm) {
 const next = decodeApprovalForm(JSON.stringify(form), form.workspace_id), old = forms.get(next.snapshot_id)
 if (old && !sameValue(old, next)) throw new Error('Original turn form changed')
 forms.set(next.snapshot_id, next); changed()
}
export function releaseApprovalForm(form: ApprovalForm) {
 if (sameValue(forms.get(form.snapshot_id), form)) { forms.delete(form.snapshot_id); changed() }
}
if (typeof window !== 'undefined') window.addEventListener('beforeunload', event => {
 if (commands.size || forms.size) { event.preventDefault(); event.returnValue = '' }
})
