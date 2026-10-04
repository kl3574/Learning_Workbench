import { sha256 } from '@noble/hashes/sha2.js'
import { bytesToHex } from '@noble/hashes/utils.js'
import type { JobRef, SessionResponse } from '../../../../../packages/contracts/generated/api-types'
import type { CodexArtifactEntry, CodexArtifactManifestView, CodexArtifactImportWrite, CodexArtifactImportView } from '../../../../../packages/contracts/generated/codex-turn-types'
import schemas from '../../../../../packages/contracts/generated/codex-turn-schemas.json'
import { request } from '../../api/client'
import { checkedProvider } from '../providers/providerSchema'
import { turnClient } from './turnClient'
import { turnIdentity } from './turnCommands'
import { outboundTime } from './turnOutboundClient'

type Wire = { CodexArtifactEntry: CodexArtifactEntry; CodexArtifactManifestView: CodexArtifactManifestView; CodexArtifactImportWrite: CodexArtifactImportWrite; CodexArtifactImportView: CodexArtifactImportView }
const fail = (): never => { throw new Error('产物记录、来源或实际字节无法核验；原选择和命令保留。') }
const id = (value: string) => { if (!turnIdentity(value)) fail(); return value }
const unique = (values: string[]) => { if (new Set(values).size !== values.length) fail() }
export const artifactHash = (bytes: Uint8Array) => bytesToHex(sha256(bytes))
// This closed manifest contains only scalar Unicode strings and bounded integers.
function canonical(value: unknown): string {
 if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`
 if (value !== null && typeof value === 'object') return `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${canonical((value as Record<string, unknown>)[k])}`).join(',')}}`
 return JSON.stringify(value)
}
export function checkedArtifact<N extends keyof Wire>(name: N, raw: unknown): Wire[N] {
 const value = checkedProvider<Wire[N]>(name, raw, schemas.schemas)
 if (name === 'CodexArtifactEntry') {
  const entry = value as CodexArtifactEntry
  if (/[\\:\x00-\x1f\x7f]/.test(entry.logical_path) || entry.logical_path.split('/').some(p => ['', '.', '..'].includes(p))) fail()
 }
 if (name === 'CodexArtifactManifestView') {
  const v = value as CodexArtifactManifestView, m = v.manifest
  outboundTime(m.created_at); m.entries.forEach(e => checkedArtifact('CodexArtifactEntry', e))
  unique([...m.entries.map(e => e.artifact_id), ...m.excluded.map(e => e.entry_id)]); unique(m.entries.map(e => e.logical_path))
  if (m.run_id !== m.source_job_id || m.entries.length + m.excluded.length > 32 || m.total_bytes !== m.entries.reduce((n, e) => n + e.size, 0)
   || artifactHash(new TextEncoder().encode(canonical(m))) !== v.manifest_sha256) fail()
 }
 if (name === 'CodexArtifactImportWrite') unique((value as CodexArtifactImportWrite).artifact_ids)
 if (name === 'CodexArtifactImportView') {
  const v = value as CodexArtifactImportView
  unique(v.items.map(i => i.artifact_id)); unique(v.items.map(i => i.import_id)); unique([v.job.id, ...v.items.map(i => i.job.id)])
 }
 return value
}
export function checkedArtifactAck(raw: unknown): JobRef {
 const ack = checkedProvider<JobRef>('JobRef', raw)
 if (ack.status !== 'queued') fail()
 return ack
}
export type ArtifactPort = {
 session(): Promise<SessionResponse>
 manifest(session: string, turn: string): Promise<CodexArtifactManifestView>
 import(session: string, body: CodexArtifactImportWrite, key: string): Promise<JobRef>
 imports(job: string): Promise<CodexArtifactImportView>
 download(entry: CodexArtifactEntry): Promise<Blob>
}
export const artifactClient: ArtifactPort = {
 session: turnClient.session,
 manifest: async (session, turn) => {
  const v = checkedArtifact('CodexArtifactManifestView', await request('GET /api/v1/codex/sessions/{id}/turns/{turn_id}/artifacts', undefined, undefined, { path: { id: id(session), turn_id: id(turn) } }))
  if (v.manifest.session_id !== session || v.manifest.turn_id !== turn) fail(); return v
 },
 import: async (session, body, key) => checkedArtifactAck(await request('POST /api/v1/codex/sessions/{id}/artifacts/import', checkedArtifact('CodexArtifactImportWrite', body), { 'Idempotency-Key': id(key) }, { path: { id: id(session) } })),
 imports: async job => {
  const v = checkedArtifact('CodexArtifactImportView', await request('GET /api/v1/codex/artifact-imports/{job_id}', undefined, undefined, { path: { job_id: id(job) } }))
  if (v.job.id !== job) fail(); return v
 },
 download: async entry => {
  const e = checkedArtifact('CodexArtifactEntry', entry), blob = await request('GET /api/v1/artifacts/{id}/download', undefined, undefined, { path: { id: id(e.artifact_id) } })
  if (blob.size !== e.size || artifactHash(new Uint8Array(await blob.arrayBuffer())) !== e.sha256) fail()
  return blob
 },
}
