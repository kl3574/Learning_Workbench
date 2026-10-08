import { sameValue } from '../providers/providerSchema'
import { decodeArtifactCommand, type ArtifactCommand } from './artifactCommands'
import { decodeArtifactForm, type ArtifactForm } from './artifactForms'
const commands = new Map<string, ArtifactCommand>(), forms = new Map<string, ArtifactForm>(), listeners = new Set<() => void>()
let revision = 0
const changed = () => { revision++; listeners.forEach(listener => listener()) }
export const subscribeArtifactMemory = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }
export const artifactMemoryVersion = () => revision
export const heldArtifactCommands = (workspace: string) => [...commands.values()].filter(v => v.workspace_id === workspace).map(v => structuredClone(v))
export const heldArtifactForms = (workspace: string) => [...forms.values()].filter(v => v.workspace_id === workspace).map(v => structuredClone(v))
export function retainArtifactCommand(command: ArtifactCommand) {
 const next = decodeArtifactCommand(JSON.stringify(command), command.workspace_id), old = commands.get(next.command_id)
 const basis = (v: ArtifactCommand) => ({ ...v, ack: null, error: null })
 if (old && (!sameValue(basis(old), basis(next)) || old.ack && next.ack && !sameValue(old.ack, next.ack))) throw new Error('Original turn command changed')
 commands.set(next.command_id, old?.ack ? old : next); changed()
}
export function releaseArtifactCommand(command: ArtifactCommand) {
 const old = commands.get(command.command_id), basis = (v: ArtifactCommand) => ({ ...v, ack: null, error: null })
 // A checked durable ACK also covers an older pending copy. Never release a
 // newer ACK merely because its earlier pending command reached storage.
 if (old && (sameValue(old, command) || sameValue(basis(old), basis(command)) && !old.ack
  && (command.ack || !old.error && command.error))) { commands.delete(command.command_id); changed() }
}
export function retainArtifactForm(form: ArtifactForm) {
 const next = decodeArtifactForm(JSON.stringify(form), form.workspace_id), old = forms.get(next.snapshot_id)
 if (old && !sameValue(old, next)) throw new Error('Original turn form changed')
 forms.set(next.snapshot_id, next); changed()
}
export function releaseArtifactForm(form: ArtifactForm) {
 if (sameValue(forms.get(form.snapshot_id), form)) { forms.delete(form.snapshot_id); changed() }
}
if (typeof window !== 'undefined') window.addEventListener('beforeunload', event => {
 if (commands.size || forms.size) { event.preventDefault(); event.returnValue = '' }
})
