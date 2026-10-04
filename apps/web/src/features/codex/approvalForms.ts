import { assertDraftWriteAllowed, DraftStore, type DraftRecord, type DraftWriteGuard } from '../../workbench/DraftStore'
import { exactObject, sameValue } from '../providers/providerSchema'
import { turnIdentity } from './turnCommands'
export type ApprovalFields = { turn_id: string }
export type ApprovalForm = { version: 1; workspace_id: string; actor_session_id: string; snapshot_id: string; draft_id: string; sequence: number; fields: ApprovalFields }
export const approvalFormStore = new DraftStore({ name: 'learning-workbench.codex-approval-forms.v1' })
export const emptyApprovalFields = (): ApprovalFields => ({ turn_id: '' })
const fail = (): never => { throw new Error('审批表单快照无法核验；原记录保留。') }
export function decodeApprovalForm(raw: string, workspace: string): ApprovalForm {
 const value = JSON.parse(raw) as ApprovalForm
 if (!exactObject(value, ['version', 'workspace_id', 'actor_session_id', 'snapshot_id', 'draft_id', 'sequence', 'fields']) || value.version !== 1
  || !turnIdentity(workspace) || value.workspace_id !== workspace || !turnIdentity(value.actor_session_id) || !turnIdentity(value.snapshot_id)
  || !turnIdentity(value.draft_id) || !Number.isSafeInteger(value.sequence) || value.sequence < 1
  || !exactObject(value.fields, ['turn_id'])
  || [value.fields.turn_id].some(v => typeof v !== 'string' || v.length > 1000)) fail()
 return value
}
export function snapshotApprovalForm(workspace: string, actor: string, fields: ApprovalFields, previous: ApprovalForm | null): ApprovalForm {
 return decodeApprovalForm(JSON.stringify({ version: 1, workspace_id: workspace, actor_session_id: actor,
  snapshot_id: `approvalform_${crypto.randomUUID()}`, draft_id: previous?.draft_id ?? `approvaldraft_${crypto.randomUUID()}`, sequence: (previous?.sequence ?? 0) + 1, fields }), workspace)
}
export function readApprovalForm(record: DraftRecord, workspace: string): ApprovalForm {
 const values = [record.text, ...record.conflicts.map(v => v.text)].map(raw => decodeApprovalForm(raw, workspace)), first = values[0]
 if (record.objectId !== first.snapshot_id || values.some(v => !sameValue(v, first))) fail()
 return first
}
/** Immutable edit snapshots prevent delayed saves or another tab from replacing an unsent form. */
export async function persistApprovalForm(form: ApprovalForm, store = approvalFormStore, guard?: DraftWriteGuard): Promise<void> {
 const checked = decodeApprovalForm(JSON.stringify(form), form.workspace_id)
 assertDraftWriteAllowed(guard)
 const old = (await store.load(form.workspace_id))[form.snapshot_id]
 assertDraftWriteAllowed(guard)
 if (old) { if (!sameValue(readApprovalForm(old, form.workspace_id), checked)) fail(); return }
 const saved = await store.save(form.workspace_id, form.snapshot_id, JSON.stringify(checked), 0, [], guard)
 if (!sameValue(readApprovalForm(saved.record, form.workspace_id), checked)) fail()
}
