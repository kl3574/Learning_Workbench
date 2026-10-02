import type { ContentRestoreDraftCreateWrite } from '../../../../../packages/contracts/generated/api-types'
import { sameValue } from '../providers/providerSchema'
import type { RestoreCreateBasis } from './useRestoreDrafts'

export type RestoreFormValue = { reason: string; confirmed: boolean }
type HeldForm = { workspace: string; blockId: string; session: string; basis: RestoreCreateBasis; value: RestoreFormValue }
const forms = new Map<string, HeldForm>(), listeners = new Set<() => void>()
const key = (workspace: string, blockId: string, session: string) => JSON.stringify([workspace, blockId, session])
let revision = 0
const changed = () => { ++revision; listeners.forEach(listener => listener()) }
export const subscribeRestoreForms = (listener: () => void) => { listeners.add(listener); return () => { listeners.delete(listener) } }
export const restoreFormsVersion = () => revision
export const pendingRestoreForms = (workspace: string, blockId?: string) => [...forms.values()].some(form => form.workspace === workspace && (!blockId || form.blockId === blockId))
export const ownRestoreForm = (workspace: string, blockId: string, session: string) => {
  const form = session ? forms.get(key(workspace, blockId, session)) : null
  return form ? structuredClone(form) : null
}
export function retainRestoreForm(workspace: string, blockId: string, session: string, basis: RestoreCreateBasis, value: RestoreFormValue) {
  if (!workspace || !blockId || !session) throw new Error('Missing original restore form owner')
  if (!value.reason && !value.confirmed) { releaseRestoreForm(workspace, blockId, session); return }
  // The session handle and original protected source stay only in this JS page.
  // Neither is written to the command journal or inherited by another session.
  forms.set(key(workspace, blockId, session), structuredClone({ workspace, blockId, session, basis, value })); changed()
}
export function releaseRestoreForm(workspace: string, blockId: string, session: string) {
  if (forms.delete(key(workspace, blockId, session))) changed()
}
export function consumeRestoreForm(workspace: string, session: string, body: ContentRestoreDraftCreateWrite) {
  const form = ownRestoreForm(workspace, body.source_ref.id, session)
  if (form && form.value.reason === body.reason && sameValue(form.basis.source_ref, body.source_ref)
      && sameValue(form.basis.base_ref, body.expected_current_ref)) releaseRestoreForm(workspace, form.blockId, session)
}
export function discardRestoreForms(workspace: string, blockId: string) {
  let removed = false
  for (const [id, form] of forms) if (form.workspace === workspace && form.blockId === blockId) { forms.delete(id); removed = true }
  if (removed) changed()
}
if (typeof window !== 'undefined') window.addEventListener('beforeunload', event => {
  if (forms.size) { event.preventDefault(); event.returnValue = '' }
})
