import type { CodexBlockRef, CodexTurnPrepareWrite } from '../../../../../packages/contracts/generated/codex-turn-types'
import { assertDraftWriteAllowed, DraftStore, type DraftRecord, type DraftWriteGuard } from '../../workbench/DraftStore'
import { checkedProvider, exactObject, sameValue } from '../providers/providerSchema'
import { turnIdentity } from './turnCommands'
import { checkedTurn } from './turnClient'
export type TurnFields = { session_id: string; message: string; provider_id: string; max_tool_calls: string; wall_seconds: string; context_refs: CodexBlockRef[] }
export type TurnForm = { version: 1; workspace_id: string; actor_session_id: string; snapshot_id: string; draft_id: string; sequence: number; fields: TurnFields }
export const turnFormStore = new DraftStore({ name: 'learning-workbench.codex-turn-forms.v1' })
export const emptyTurnFields = (): TurnFields => ({ session_id: '', message: '', provider_id: '', max_tool_calls: '0', wall_seconds: '30', context_refs: [] })
const fail = (): never => { throw new Error('回合表单快照无法核验；原记录保留。') }
export function decodeTurnForm(raw: string, workspace: string): TurnForm {
 const value = JSON.parse(raw) as TurnForm
 if (!exactObject(value, ['version', 'workspace_id', 'actor_session_id', 'snapshot_id', 'draft_id', 'sequence', 'fields']) || value.version !== 1
  || !turnIdentity(workspace) || value.workspace_id !== workspace || !turnIdentity(value.actor_session_id) || !turnIdentity(value.snapshot_id)
  || !turnIdentity(value.draft_id) || !Number.isSafeInteger(value.sequence) || value.sequence < 1
  || !exactObject(value.fields, ['session_id', 'message', 'provider_id', 'max_tool_calls', 'wall_seconds', 'context_refs'])
  || ['session_id', 'message', 'provider_id', 'max_tool_calls', 'wall_seconds'].some(k => typeof value.fields[k as keyof TurnFields] !== 'string')
  || !Array.isArray(value.fields.context_refs) || value.fields.context_refs.length > 1) fail()
 for (const ref of value.fields.context_refs) {
  checkedProvider('ContentRef', ref)
  if (ref.entity !== 'block' || !turnIdentity(ref.id) || !/^[a-f0-9]{64}$/.test(ref.sha256) || ref.sha256.length !== 64) fail()
 }
 return value
}
export function snapshotTurnForm(workspace: string, actor: string, fields: TurnFields, previous: TurnForm | null): TurnForm {
 return decodeTurnForm(JSON.stringify({ version: 1, workspace_id: workspace, actor_session_id: actor,
  snapshot_id: `turnform_${crypto.randomUUID()}`, draft_id: previous?.draft_id ?? `turndraft_${crypto.randomUUID()}`, sequence: (previous?.sequence ?? 0) + 1, fields }), workspace)
}
export function readTurnForm(record: DraftRecord, workspace: string): TurnForm {
 const values = [record.text, ...record.conflicts.map(v => v.text)].map(raw => decodeTurnForm(raw, workspace)), first = values[0]
 if (record.objectId !== first.snapshot_id || values.some(v => !sameValue(v, first))) fail()
 return first
}
/** Immutable edit snapshots prevent delayed saves or another tab from replacing an unsent form. */
export async function persistTurnForm(form: TurnForm, store = turnFormStore, guard?: DraftWriteGuard): Promise<void> {
 const checked = decodeTurnForm(JSON.stringify(form), form.workspace_id)
 assertDraftWriteAllowed(guard)
 const old = (await store.load(form.workspace_id))[form.snapshot_id]
 assertDraftWriteAllowed(guard)
 if (old) { if (!sameValue(readTurnForm(old, form.workspace_id), checked)) fail(); return }
 const saved = await store.save(form.workspace_id, form.snapshot_id, JSON.stringify(checked), 0, [], guard)
 if (!sameValue(readTurnForm(saved.record, form.workspace_id), checked)) fail()
}
export function turnFormBody(fields: TurnFields, revision: number): CodexTurnPrepareWrite {
 // Number('') and Number('1e1') must not silently invent a chosen integer.
 if (!/^(0|[1-9][0-9]*)$/.test(fields.max_tool_calls) || fields.max_tool_calls.trim() !== fields.max_tool_calls
  || !/^[1-9][0-9]*$/.test(fields.wall_seconds) || fields.wall_seconds.trim() !== fields.wall_seconds) fail()
 return checkedTurn('CodexTurnPrepareWrite', { message: fields.message, context_refs: fields.context_refs, provider_id: fields.provider_id,
  expected_session_revision: revision, tools: { max_tool_calls: Number(fields.max_tool_calls), wall_seconds: Number(fields.wall_seconds) } })
}
