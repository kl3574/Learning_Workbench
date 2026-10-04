import type { CodexArtifactManifestView } from '../../../../../packages/contracts/generated/codex-turn-types'
import { checkedArtifact } from './artifactClient'
import { assertDraftWriteAllowed, DraftStore, type DraftRecord, type DraftWriteGuard } from '../../workbench/DraftStore'
import { exactObject, sameValue } from '../providers/providerSchema'
import { turnIdentity } from './turnCommands'
export type ArtifactFields = { session_id: string; turn_id: string; selection: { basis: CodexArtifactManifestView; artifact_ids: string[] } | null }
export type ArtifactForm = { version: 1; workspace_id: string; actor_session_id: string; snapshot_id: string; draft_id: string; sequence: number; fields: ArtifactFields }
export const artifactFormStore = new DraftStore({ name: 'learning-workbench.codex-artifact-forms.v1' })
export const emptyArtifactFields = (): ArtifactFields => ({ session_id: '', turn_id: '', selection: null })
const fail = (): never => { throw new Error('产物表单快照无法核验；原记录保留。') }
export function decodeArtifactForm(raw: string, workspace: string): ArtifactForm {
 const value = JSON.parse(raw) as ArtifactForm
 if (!exactObject(value, ['version', 'workspace_id', 'actor_session_id', 'snapshot_id', 'draft_id', 'sequence', 'fields']) || value.version !== 1
  || !turnIdentity(workspace) || value.workspace_id !== workspace || !turnIdentity(value.actor_session_id) || !turnIdentity(value.snapshot_id)
  || !turnIdentity(value.draft_id) || !Number.isSafeInteger(value.sequence) || value.sequence < 1
  || !exactObject(value.fields, ['session_id', 'turn_id', 'selection'])
  || [value.fields.session_id, value.fields.turn_id].some(v => typeof v !== 'string' || v.length > 1000)) fail()
 const s = value.fields.selection
 if (s !== null) {
  if (!exactObject(s, ['basis', 'artifact_ids']) || !Array.isArray(s.artifact_ids) || new Set(s.artifact_ids).size !== s.artifact_ids.length) fail()
  const m = checkedArtifact('CodexArtifactManifestView', s.basis).manifest
  if (value.fields.session_id !== m.session_id || value.fields.turn_id !== m.turn_id || s.artifact_ids.some(id => !m.entries.some(e => e.artifact_id === id && e.import_kind !== null && e.size > 0))) fail()
 }
 return value
}
export function snapshotArtifactForm(workspace: string, actor: string, fields: ArtifactFields, previous: ArtifactForm | null): ArtifactForm {
 return decodeArtifactForm(JSON.stringify({ version: 1, workspace_id: workspace, actor_session_id: actor,
  snapshot_id: `artifactform_${crypto.randomUUID()}`, draft_id: previous?.draft_id ?? `artifactdraft_${crypto.randomUUID()}`, sequence: (previous?.sequence ?? 0) + 1, fields }), workspace)
}
export function readArtifactForm(record: DraftRecord, workspace: string): ArtifactForm {
 const values = [record.text, ...record.conflicts.map(v => v.text)].map(raw => decodeArtifactForm(raw, workspace)), first = values[0]
 if (record.objectId !== first.snapshot_id || values.some(v => !sameValue(v, first))) fail()
 return first
}
/** Immutable edit snapshots prevent delayed saves or another tab from replacing an unsent form. */
export async function persistArtifactForm(form: ArtifactForm, store = artifactFormStore, guard?: DraftWriteGuard): Promise<void> {
 const checked = decodeArtifactForm(JSON.stringify(form), form.workspace_id)
 assertDraftWriteAllowed(guard)
 const old = (await store.load(form.workspace_id))[form.snapshot_id]
 assertDraftWriteAllowed(guard)
 if (old) { if (!sameValue(readArtifactForm(old, form.workspace_id), checked)) fail(); return }
 const saved = await store.save(form.workspace_id, form.snapshot_id, JSON.stringify(checked), 0, [], guard)
 if (!sameValue(readArtifactForm(saved.record, form.workspace_id), checked)) fail()
}
