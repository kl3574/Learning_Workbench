import type { ImpactObjectDecisionWrite as Write } from '../../../../../packages/contracts/generated/api-types'
import { sameValue } from '../providers/providerSchema'
import { artifacts, type Basis } from './schema'
// Unsaved human input stays only in this page, separately from command/ACK
// recovery. Session secrets are comparison handles here, never journal fields.
export type FormValue = { decision: Write['decision'] | ''; reason: string; ids: string; confirmed: boolean }
export type HeldForm = { basis: Basis; value: FormValue }
const forms = new Map<string, Map<string, HeldForm>>(), listeners = new Set<() => void>()
let revision = 0
const changed = () => { ++revision; listeners.forEach(fn => fn()) }
export const subscribeForms = (fn: () => void) => { listeners.add(fn); return () => { listeners.delete(fn) } }
export const formsVersion = () => revision
export const formsPending = (workspace: string) => !!forms.get(workspace)?.size
export const ownForm = (workspace: string, session: string) => {
  const value = session ? forms.get(workspace)?.get(session) : undefined
  return value ? structuredClone(value) : null
}
export function retainForm(workspace: string, session: string, form: HeldForm) {
  if (!workspace || !session) throw new Error('Missing original form owner')
  let values = forms.get(workspace)
  if (!values) { values = new Map(); forms.set(workspace, values) }
  values.set(session, structuredClone(form)); changed()
}
export function releaseForm(workspace: string, session: string) {
  const values = forms.get(workspace)
  if (values?.delete(session)) { if (!values.size) forms.delete(workspace); changed() }
}
export function consumeForm(workspace: string, session: string, basis: Basis, body: Write) {
  const form = ownForm(workspace, session)
  if (!form || !sameValue(form.basis, basis) || form.value.decision !== body.decision || form.value.reason !== body.reason) return
  try { if (sameValue(artifacts(form.value.ids), body.evidence_artifact_ids)) releaseForm(workspace, session) } catch { /* A different unsent form remains protected. */ }
}
export function discardForms(workspace: string) { if (forms.delete(workspace)) changed() }
if (typeof window !== 'undefined') window.addEventListener('beforeunload', event => { if (forms.size) { event.preventDefault(); event.returnValue = '' } })
