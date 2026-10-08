import type { JobRef } from '../../../../../packages/contracts/generated/api-types'
import type { CodexArtifactManifestView, CodexArtifactImportWrite, CodexArtifactImportView } from '../../../../../packages/contracts/generated/codex-turn-types'
import { assertDraftWriteAllowed, DraftStore, type DraftRecord, type DraftWriteGuard } from '../../workbench/DraftStore'
import { exactObject, sameValue } from '../providers/providerSchema'
import { turnIdentity } from './turnCommands'
import { artifactClient, checkedArtifact, checkedArtifactAck, type ArtifactPort } from './artifactClient'
export type ArtifactCommand = {
 version: 1; workspace_id: string; actor_session_id: string; command_id: string; target_id: string;
 route: 'POST /api/v1/codex/sessions/{id}/artifacts/import'; basis: CodexArtifactManifestView;
 body: CodexArtifactImportWrite; ack: JobRef | null; error: { status: number; code: string | null } | null
}
export const artifactStore = new DraftStore({ name: 'learning-workbench.codex-artifact-commands.v1' })
const fail = (): never => { throw new Error('回导原命令、完整清单或原回执无法核验；记录保留。') }
export function decodeArtifactCommand(raw: string, workspace: string): ArtifactCommand {
 const c = JSON.parse(raw) as ArtifactCommand
 if (!exactObject(c, ['version', 'workspace_id', 'actor_session_id', 'command_id', 'target_id', 'route', 'basis', 'body', 'ack', 'error']) || c.version !== 1
  || c.workspace_id !== workspace || !turnIdentity(workspace) || !turnIdentity(c.actor_session_id) || !turnIdentity(c.command_id) || !turnIdentity(c.target_id)
  || c.route !== 'POST /api/v1/codex/sessions/{id}/artifacts/import') fail()
 const v = checkedArtifact('CodexArtifactManifestView', c.basis), b = checkedArtifact('CodexArtifactImportWrite', c.body)
 if (v.manifest.source_outcome === 'unknown' || c.target_id !== v.manifest.session_id || b.turn_id !== v.manifest.turn_id || b.expected_manifest_sha256 !== v.manifest_sha256
  || b.artifact_ids.some(id => !v.manifest.entries.some(e => e.artifact_id === id && e.import_kind !== null && e.size > 0))) fail()
 if (c.ack !== null) checkedArtifactAck(c.ack)
 if (c.error !== null && (!exactObject(c.error, ['status', 'code']) || !Number.isSafeInteger(c.error.status) || c.error.status < 400 || c.error.status > 599
  || c.ack !== null || c.error.code !== null && (typeof c.error.code !== 'string' || !/^[A-Z][A-Z0-9_]{0,79}$/.test(c.error.code)))) fail()
 return c
}
export function makeArtifactCommand(workspace: string, actor: string, basis: CodexArtifactManifestView, ids: string[]): ArtifactCommand {
 return decodeArtifactCommand(JSON.stringify({ version: 1, workspace_id: workspace, actor_session_id: actor, command_id: `artifactimport_${crypto.randomUUID()}`,
  target_id: basis.manifest.session_id, route: 'POST /api/v1/codex/sessions/{id}/artifacts/import', basis,
  body: { turn_id: basis.manifest.turn_id, artifact_ids: ids, expected_manifest_sha256: basis.manifest_sha256 }, ack: null, error: null }), workspace)
}
export function readArtifactImport(raw: unknown, command: ArtifactCommand): CodexArtifactImportView {
 const c = decodeArtifactCommand(JSON.stringify(command), command.workspace_id), v = checkedArtifact('CodexArtifactImportView', raw)
 if (!c.ack || v.job.id !== c.ack.id || v.session_id !== c.target_id || v.turn_id !== c.body.turn_id || v.actor_session_id !== c.actor_session_id
  || v.manifest_sha256 !== c.body.expected_manifest_sha256 || !sameValue(v.items.map(i => i.artifact_id), c.body.artifact_ids)
  || v.items.some(i => i.source_sha256 !== c.basis.manifest.entries.find(e => e.artifact_id === i.artifact_id)?.sha256)) fail()
 return v
}
const immutable = (value: ArtifactCommand) => ({ ...value, ack: null, error: null })
export function readArtifactCommand(record: DraftRecord, workspace: string): ArtifactCommand {
 const values = [record.text, ...record.conflicts.map(v => v.text)].map(raw => decodeArtifactCommand(raw, workspace)), first = values[0]
 if (first.command_id !== record.objectId || values.some(v => !sameValue(immutable(v), immutable(first)))) throw new Error('Conflicting original artifact command')
 const confirmed = values.filter(v => v.ack)
 if (confirmed.some(v => !sameValue(v.ack, confirmed[0].ack))) throw new Error('Conflicting artifact ACK')
 return confirmed[0] ?? values.find(v => v.error) ?? first
}
export async function persistArtifactCommand(command: ArtifactCommand, store = artifactStore, guard?: DraftWriteGuard): Promise<ArtifactCommand> {
 let desired = decodeArtifactCommand(JSON.stringify(command), command.workspace_id)
 for (let attempt = 0; attempt < 4; attempt++) {
  assertDraftWriteAllowed(guard)
  const old = (await store.load(command.workspace_id))[command.command_id]
  assertDraftWriteAllowed(guard)
  if (old) {
   const current = readArtifactCommand(old, command.workspace_id)
   if (!sameValue(immutable(current), immutable(desired)) || current.ack && desired.ack && !sameValue(current.ack, desired.ack)) throw new Error('Cannot replace original artifact command or ACK')
   if (current.ack || !desired.ack && !desired.error && current.error) desired = current
   if (!old.conflicts.length && sameValue(current, desired)) return current
  }
  const saved = await store.save(command.workspace_id, command.command_id, JSON.stringify(desired), old?.revision ?? 0, old?.conflicts.map(v => v.id) ?? [], guard)
  const actual = readArtifactCommand(saved.record, command.workspace_id)
  if (!saved.record.conflicts.length && sameValue(actual, desired)) return actual
 }
 throw new Error('Concurrent artifact command remains unresolved')
}
export async function dispatchArtifactCommand(command: ArtifactCommand, port: Pick<ArtifactPort, 'import'> = artifactClient, store = artifactStore,
 options: { guard?: DraftWriteGuard; beforePost?: () => Promise<void>; onAck?: (ack: ArtifactCommand) => void; beforeDelivery?: () => Promise<void> } = {}): Promise<ArtifactCommand> {
 const original = await persistArtifactCommand(command, store, options.guard)
 if (original.ack) { await options.beforeDelivery?.(); return original }
 await options.beforePost?.(); assertDraftWriteAllowed(options.guard)
 const raw = await port.import(original.target_id, original.body, original.command_id)
 const acknowledged = decodeArtifactCommand(JSON.stringify({ ...original, ack: raw, error: null }), original.workspace_id)
 options.onAck?.(acknowledged)
 await options.beforeDelivery?.()
 return persistArtifactCommand(acknowledged, store, options.guard)
}
