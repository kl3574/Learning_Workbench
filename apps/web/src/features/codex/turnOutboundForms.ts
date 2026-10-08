import { assertDraftWriteAllowed, DraftStore, type DraftRecord, type DraftWriteGuard } from '../../workbench/DraftStore'
import { exactObject, sameValue } from '../providers/providerSchema'
import { turnIdentity } from './turnCommands'
export type OutboundFields = { session_id: string; preparation_id: string; proposal_id: string; consent_id: string; turn_id: string; max_input_tokens: string; max_output_tokens: string; max_cost_usd: string; expires_at: string }
export type OutboundForm = { version: 1; workspace_id: string; actor_session_id: string; snapshot_id: string; draft_id: string; sequence: number; fields: OutboundFields }
export const outboundFormStore = new DraftStore({ name: 'learning-workbench.codex-outbound-forms.v1' })
export const emptyOutboundFields = (): OutboundFields => ({ session_id: '', preparation_id: '', proposal_id: '', consent_id: '', turn_id: '', max_input_tokens: '', max_output_tokens: '', max_cost_usd: '', expires_at: '' })
const fail = (): never => { throw new Error('外发表单快照无法核验；原记录保留。') }
export function decodeOutboundForm(raw: string, workspace: string): OutboundForm {
 const value = JSON.parse(raw) as OutboundForm
 if (!exactObject(value, ['version', 'workspace_id', 'actor_session_id', 'snapshot_id', 'draft_id', 'sequence', 'fields']) || value.version !== 1
  || !turnIdentity(workspace) || value.workspace_id !== workspace || !turnIdentity(value.actor_session_id) || !turnIdentity(value.snapshot_id)
  || !turnIdentity(value.draft_id) || !Number.isSafeInteger(value.sequence) || value.sequence < 1
  || !exactObject(value.fields, ['session_id', 'preparation_id', 'proposal_id', 'consent_id', 'turn_id', 'max_input_tokens', 'max_output_tokens', 'max_cost_usd', 'expires_at'])
  || Object.values(value.fields).some(v => typeof v !== 'string' || v.length > 1000)) fail()
 return value
}
export function snapshotOutboundForm(workspace: string, actor: string, fields: OutboundFields, previous: OutboundForm | null): OutboundForm {
 return decodeOutboundForm(JSON.stringify({ version: 1, workspace_id: workspace, actor_session_id: actor,
  snapshot_id: `outboundform_${crypto.randomUUID()}`, draft_id: previous?.draft_id ?? `outbounddraft_${crypto.randomUUID()}`, sequence: (previous?.sequence ?? 0) + 1, fields }), workspace)
}
export function readOutboundForm(record: DraftRecord, workspace: string): OutboundForm {
 const values = [record.text, ...record.conflicts.map(v => v.text)].map(raw => decodeOutboundForm(raw, workspace)), first = values[0]
 if (record.objectId !== first.snapshot_id || values.some(v => !sameValue(v, first))) fail()
 return first
}
/** Immutable edit snapshots prevent delayed saves or another tab from replacing an unsent form. */
export async function persistOutboundForm(form: OutboundForm, store = outboundFormStore, guard?: DraftWriteGuard): Promise<void> {
 const checked = decodeOutboundForm(JSON.stringify(form), form.workspace_id)
 assertDraftWriteAllowed(guard)
 const old = (await store.load(form.workspace_id))[form.snapshot_id]
 assertDraftWriteAllowed(guard)
 if (old) { if (!sameValue(readOutboundForm(old, form.workspace_id), checked)) fail(); return }
 const saved = await store.save(form.workspace_id, form.snapshot_id, JSON.stringify(checked), 0, [], guard)
 if (!sameValue(readOutboundForm(saved.record, form.workspace_id), checked)) fail()
}
