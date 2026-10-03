import { sameValue } from '../providers/providerSchema'
import type { SinglePublicationCommand } from './singlePublicationCommands'
import type { SinglePublicationBasis } from './singlePublicationSchema'

// Session identity is compared only in page memory; never serialized to IDB.
const actors = new Map<string, { actor: string; original: SinglePublicationCommand }>()
const immutable = (command: SinglePublicationCommand) => ({ ...command, ack: null, rejection: null })
export function rememberSinglePublicationActor(command: SinglePublicationCommand, actor: string) {
  const old = actors.get(command.command_id)
  if (!actor || old && (old.actor !== actor || !sameValue(old.original, immutable(command)))) throw new Error('Original publication actor cannot change')
  if (!old) actors.set(command.command_id, { actor, original: structuredClone(immutable(command)) })
}
export function hasSinglePublicationActor(command: SinglePublicationCommand, actor: string) {
  const old = actors.get(command.command_id)
  return !!actor && !!old && old.actor === actor && sameValue(old.original, immutable(command))
}
const commands = new Map<string, { command: SinglePublicationCommand; session: string }>()
export type SinglePublicationForm = { key: string; version: number; workspace: string; basis: SinglePublicationBasis; selected: number[]; confirmed: boolean }
const forms = new Map<string, { form: SinglePublicationForm; session: string }>()
const listeners = new Set<() => void>()
let revision = 0, formVersion = 0
const changed = () => { ++revision; listeners.forEach(listener => listener()) }
export const subscribeSinglePublicationMemory = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }
export const singlePublicationMemoryVersion = () => revision
export function retainSinglePublicationMemory(command: SinglePublicationCommand, session: string) {
  if (!session) throw new Error('Missing original publication session')
  commands.set(command.command_id, { command: structuredClone(command), session }); changed()
}
export const pendingSinglePublicationMemory = (workspace: string) => [...commands.values()].some(row => row.command.workspace_id === workspace)
export const recoverableSinglePublicationMemory = (workspace: string, session: string) => [...commands.values()].filter(row => row.command.workspace_id === workspace && row.session === session).map(row => structuredClone(row.command))
export function releaseSinglePublicationMemory(id: string, session: string) {
  if (commands.get(id)?.session === session) { commands.delete(id); changed() }
}
export function discardSinglePublicationMemory(workspace: string) {
  for (const [id, row] of commands) if (row.command.workspace_id === workspace) commands.delete(id)
  changed()
}
const formKey = (workspace: string, session: string, basis: SinglePublicationBasis) => JSON.stringify([workspace, session, basis])
export function retainSinglePublicationForm(workspace: string, session: string, basis: SinglePublicationBasis, selected: number[], confirmed: boolean) {
  if (!session) throw new Error('Missing original form session')
  const key = formKey(workspace, session, basis)
  if (selected.length || confirmed) forms.set(key, { form: structuredClone({ key, version: ++formVersion, workspace, basis, selected, confirmed }), session })
  else forms.delete(key)
  changed()
}
export const pendingSinglePublicationForms = (workspace: string) => [...forms.values()].some(row => row.form.workspace === workspace)
export const recoverableSinglePublicationForms = (workspace: string, session: string) => [...forms.values()].filter(row => row.form.workspace === workspace && row.session === session).map(row => structuredClone(row.form))
export function releaseSinglePublicationForm(form: SinglePublicationForm, session: string) {
  if (originalSinglePublicationForm(form, form.workspace, session)) { forms.delete(form.key); changed() }
}
export function discardSinglePublicationForms(workspace: string) {
  for (const [key, row] of forms) if (row.form.workspace === workspace) forms.delete(key)
  changed()
}
export function originalSinglePublicationForm(form: SinglePublicationForm, workspace: string, session: string) {
  const held = forms.get(form.key)
  return !!held && held.session === session && held.form.workspace === workspace && sameValue(held.form, form)
}
if (typeof window !== 'undefined') window.addEventListener('beforeunload', event => {
  if (commands.size || forms.size) { event.preventDefault(); event.returnValue = '' }
})
